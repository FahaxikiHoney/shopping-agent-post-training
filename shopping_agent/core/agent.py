# -*- coding: utf-8 -*-
"""
ShoppingAgent 基类 — 对应真实项目的 WorkflowAgent

真实 WorkflowAgent：
    async def _execute(oxy_request: OxyRequest):
        response = await oxy_request.call(callee="tool_name", arguments={...})
        result = parse_json_dict_or_empty(response.output)

本框架（同步版）：
    def run(ctx: AgentContext) -> dict:
        result = self._call_tool("tool_name", params, ctx)
        self._final_response(content, product_cards)
        return self._build_trajectory(...)

_build_trajectory 输出的 dict 可直接写入 trajectories_final.jsonl。
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field, asdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from shopping_agent.core.context import AgentContext
from shopping_agent.core.tool_registry import ToolRegistry

if TYPE_CHECKING:
    from shopping_agent.llm.client import LLMClient


@dataclass
class StepRecord:
    """
    单个执行步骤的记录，对应 trajectories_final.jsonl 中 steps 数组的每一项。
    """
    step_id: int
    step_type: str                          # "tool_call" | "final_response"
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    product_cards: List[Dict[str, Any]] = field(default_factory=list)
    error_type: Optional[str] = None


class ShoppingAgent:
    """
    购物 Agent 基类。

    子类只需实现 run(ctx) 方法，在里面：
    1. 调用 self._call_tool(tool_name, params, ctx) 执行工具
    2. 调用 self._final_response(content, product_cards) 记录最终回复
    3. 调用 self._build_trajectory(...) 序列化为 SFT 格式

    示例（SearchRecommendAgent）：
        def run(self, ctx):
            self._steps = []
            result = self._call_tool("SkuRecallShopping", {"query": "耳机"}, ctx)
            products = result.get("products", [])
            content, cards = self._format_response(ctx, products)
            self._final_response(content, cards)
            return self._build_trajectory("sft_gen_xxx", ctx, "search_recommend", "购物搜索推荐")
    """

    def __init__(
        self,
        registry: ToolRegistry,
        mock_mode: bool = True,
        llm_client: Optional["LLMClient"] = None,
        thinking_client: Optional["LLMClient"] = None,
    ) -> None:
        self.registry = registry
        self.mock_mode = mock_mode
        self.llm_client = llm_client
        self.thinking_client = thinking_client  # 专门生成 raw_thinking 的模型（如 GLM-5.1）
        self._steps: List[StepRecord] = []

    def _llm_response(self, system_prompt: str, user_prompt: str,
                       ctx: Optional["AgentContext"] = None) -> str:
        """
        调用 LLM 生成回复，同时把 raw_thinking 存入 ctx.shared_data["raw_thinking"]。

        如果设置了 thinking_client，额外调用一次专门生成思维链。
        llm_client 为 None 或调用失败时返回空字符串（fallback 到规则回复）。
        """
        if self.llm_client is None:
            return ""
        try:
            content, raw_thinking = self.llm_client.generate(system_prompt, user_prompt)
            if ctx is not None and raw_thinking:
                ctx.set("raw_thinking", raw_thinking)

            # 如果设置了专门的 thinking_client，传完整 prompt 让它生成更有价值的思维链
            if ctx is not None and self.thinking_client and not ctx.get("raw_thinking"):
                try:
                    _, rt = self.thinking_client.generate(system_prompt, user_prompt)
                    if rt:
                        ctx.set("raw_thinking", rt)
                except Exception:
                    pass

            return content
        except Exception:
            return ""

    # ── 核心记录方法 ──────────────────────────────────────────────────────

    def _call_tool(self, tool_name: str, params: Dict[str, Any],
                   ctx: AgentContext) -> Dict[str, Any]:
        """
        调用工具并记录 StepRecord。

        对应真实框架：
            response = await oxy_request.call(callee=tool_name, arguments=params)
            result = parse_json_dict_or_empty(response.output)
        """
        result = self.registry.call(tool_name, ctx, params)
        step = StepRecord(
            step_id=len(self._steps) + 1,
            step_type="tool_call",
            tool_name=tool_name,
            tool_input=params,
            tool_output=result,
            error_type=result.get("_error_type") if isinstance(result, dict) else None,
        )
        self._steps.append(step)
        return result

    def _final_response(self, content: str,
                        product_cards: Optional[List[Dict[str, Any]]] = None) -> None:
        """记录最终回复步骤。"""
        self._steps.append(StepRecord(
            step_id=len(self._steps) + 1,
            step_type="final_response",
            content=content,
            product_cards=product_cards or [],
        ))

    # ── 序列化 ──────────────────────────────────────────────────────────

    def _build_trajectory(
        self,
        trajectory_id: str,
        ctx: AgentContext,
        scenario_type: str,
        category: str,
        training_focus: str = "",
        quality_label: str = "good",
    ) -> Dict[str, Any]:
        """
        将 _steps 序列化为与 trajectories_final.jsonl 完全对齐的 dict。

        card_id 防幻觉校验：product_cards 中的每个 card_id 必须出现在
        某个 tool_call step 的 tool_output.products 中，否则 assert 失败。
        """
        # 收集所有 tool_output 中的 product_id
        all_product_ids: set = set()
        for s in self._steps:
            if s.step_type == "tool_call" and s.tool_output:
                for p in s.tool_output.get("products", []):
                    if "product_id" in p:
                        all_product_ids.add(p["product_id"])

        # 校验 card_id 无幻觉
        for s in self._steps:
            for card in s.product_cards:
                cid = card.get("card_id", "")
                assert cid in all_product_ids, (
                    f"card_id 幻觉检测: {cid!r} 不在任何 tool_output.products 中"
                )

        # 提取 final_response 文本
        final_content = ""
        for s in self._steps:
            if s.step_type == "final_response":
                final_content = s.content or ""
                break

        # 序列化 steps（移除 dataclass 内部私有字段）
        steps_list = []
        for s in self._steps:
            d = asdict(s)
            # 清理 None 值的 tool_name 等（final_response 步骤不需要 tool 相关字段）
            if s.step_type == "final_response":
                d.pop("tool_name", None)
                d.pop("tool_input", None)
                d.pop("tool_output", None)
                d.pop("error_type", None)
            else:
                d.pop("content", None)
            steps_list.append(d)

        return {
            "trajectory_id": trajectory_id,
            "scenario_type": scenario_type,
            "category": category,
            "quality_label": quality_label,
            "training_focus": training_focus,
            "is_multi_turn": bool(ctx.history),
            "conversation_history": ctx.history,
            "user_query": ctx.user_query,
            "thinking": ctx.get("thinking", f"分析{category}需求"),
            "raw_thinking": ctx.get("raw_thinking", ""),
            "steps": steps_list,
            "final_response": final_content,
            "eval_score": 1.0 if quality_label == "good" else 0.0,
            "sft_source": "shopping_agent_llm_v1",
        }

    # ── 工具函数（子类可复用）──────────────────────────────────────────

    @staticmethod
    def _make_cards(products: List[Dict[str, Any]],
                    reasons: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        从 products 列表生成 product_cards，card_id 严格取自 product_id。

        Args:
            products: tool_output["products"] 列表
            reasons:  可选的推荐理由列表（与 products 一一对应）
        """
        cards = []
        for i, p in enumerate(products):
            reason = (reasons[i] if reasons and i < len(reasons)
                      else f"{p.get('title', '')} - {p.get('key_specs', '')}")
            cards.append({
                "card_id": p["product_id"],
                "display_price": p.get("price", 0),
                "reason": reason,
            })
        return cards

    @staticmethod
    def _gen_tid(prefix: str = "sft_gen") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def run(self, ctx: AgentContext) -> Dict[str, Any]:
        """子类实现。返回 trajectory dict（SFT 格式）。"""
        raise NotImplementedError
