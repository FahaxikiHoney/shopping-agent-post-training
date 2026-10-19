# -*- coding: utf-8 -*-
"""OrderAgent — place_order 场景"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

from joybuy_agent.core.agent import ShoppingAgent
from joybuy_agent.core.context import AgentContext
from joybuy_agent.llm.prompts import ORDER_SYSTEM, build_order_user_prompt

# 意图 → 工具名映射
_INTENT_TOOL = {
    "query": "OrderQuerySkill",
    "logistics": "OrderQuerySkill",
    "refund": "OrderQuerySkill",
    "exchange": "OrderQuerySkill",
    "afs": "OrderQuerySkill",
    "invoice": "OrderQuerySkill",
    "cancel": "OrderQuerySkill",
    "price_protection": "OrderQuerySkill",
    "place_order": "ShoppingPlaceOrderTool",
    "reservation": "ShoppingPlaceOrderTool",
    "early_payoff": "ShoppingPlaceOrderTool",
}

_INTENT_KEYWORDS = {
    "refund": ["退款", "退货", "退换", "不想要", "质量问题"],
    "exchange": ["换货", "换一个", "颜色不对", "尺寸不对", "发错"],
    "logistics": ["物流", "快递", "发货", "查件", "到哪了", "没到"],
    "cancel": ["取消", "不要了", "取消订单"],
    "invoice": ["发票", "开票", "增值税"],
    "price_protection": ["价保", "降价", "便宜了", "差价"],
    "early_payoff": ["提前还款", "还清", "白条", "分期"],
    "reservation": ["预约", "预订", "抢购", "限量", "发售"],
    "place_order": ["下单", "怎么买", "怎么付", "支付", "购买"],
}


class OrderAgent(ShoppingAgent):
    """
    购物下单/订单处理 Agent。

    场景：下单操作、订单查询、退换货、价保、发票等。
    steps：1×(OrderQuerySkill 或 ShoppingPlaceOrderTool) → final_response（含操作步骤）

    训练重点：
    - 准确识别意图（查询/退货/换货/价保/发票/下单/预约）
    - final_response 必须包含具体操作路径（App → 菜单 → 按钮）
    """

    SCENARIO = "place_order"
    CATEGORY = "购物下单"

    def run(self, ctx: AgentContext) -> Dict[str, Any]:
        self._steps = []

        intent, tool_name = self._detect_intent(ctx.user_query)
        order_id = self._extract_order_id(ctx.user_query)
        ctx.set("thinking", f"识别意图：{intent}，使用工具：{tool_name}")

        params = {
            "action": intent,
            "issue_type": intent,
        }
        if order_id:
            params["order_id"] = order_id

        result = self._call_tool(tool_name, params, ctx)
        products = result.get("products", [])
        guide = result.get("operation_guide", "")

        # 优先使用 LLM 生成回复，否则 fallback 到规则
        if self.llm_client:
            user_prompt = build_order_user_prompt(ctx.user_query, intent, products, guide)
            content = self._llm_response(ORDER_SYSTEM, user_prompt, ctx)

        if not self.llm_client or not content:
            content, _ = self._build_response(ctx.user_query, intent, products, guide)

        cards = self._make_cards(products, [p.get("key_specs", "操作指引") for p in products]) if products else []
        self._final_response(content, cards)

        return self._build_trajectory(
            trajectory_id=self._gen_tid("sft_order"),
            ctx=ctx,
            scenario_type=self.SCENARIO,
            category=self.CATEGORY,
            training_focus=f"{intent}操作指引+App操作路径",
        )

    def _detect_intent(self, query: str) -> Tuple[str, str]:
        """检测用户意图并返回 (intent, tool_name)"""
        for intent, kws in _INTENT_KEYWORDS.items():
            if any(kw in query for kw in kws):
                return intent, _INTENT_TOOL.get(intent, "OrderQuerySkill")
        return "query", "OrderQuerySkill"

    def _extract_order_id(self, query: str) -> str:
        """从 query 中提取订单号"""
        m = re.search(r"JD\d{8,}", query)
        return m.group(0) if m else ""

    def _build_response(self, query: str, intent: str,
                        products: List[Dict], guide: str) -> Tuple[str, List]:
        intent_names = {
            "refund": "退款/退货", "exchange": "换货", "logistics": "物流查询",
            "cancel": "取消订单", "invoice": "开发票", "price_protection": "价保申请",
            "early_payoff": "提前还款", "reservation": "预约抢购", "place_order": "下单操作",
            "query": "订单查询",
        }
        intent_name = intent_names.get(intent, "操作指引")

        lines = [f"关于你的「{intent_name}」需求，以下是详细操作指引：\n"]
        if guide:
            lines.append(guide)
        else:
            lines.append("请前往京东 App → 我的订单，找到对应订单操作。")

        content = "\n".join(lines)
        cards = self._make_cards(products, [p.get("key_specs", "操作指引") for p in products]) if products else []
        return content, cards
