# -*- coding: utf-8 -*-
"""RepurchaseAgent — repurchase 场景"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple

from joybuy_agent.core.agent import ShoppingAgent
from joybuy_agent.core.context import AgentContext
from joybuy_agent.llm.prompts import REPURCHASE_SYSTEM, build_repurchase_user_prompt


class RepurchaseAgent(ShoppingAgent):
    """
    复购召回 Agent。

    场景：用户历史购买过某品类，要求复购或询问升级款/新品。
    steps：1×SkuRepurchaseRecall → final_response（含历史购买记录+推荐方案）

    训练重点：
    - 识别历史购买信息（订单号+购买时间）
    - 区分「直接复购」vs「升级推荐」vs「加购新品」三种方案
    - 明确告知购买时间（X月前）激活复购心智
    """

    SCENARIO = "repurchase"
    CATEGORY = "复购召回"

    def run(self, ctx: AgentContext) -> Dict[str, Any]:
        self._steps = []

        keyword = self._extract_keyword(ctx.user_query)
        ctx.set("thinking", f"识别复购意图：{keyword}，查询历史订单")

        params = {
            "category_keyword": keyword,
            "time_range": "last_6_months",
        }
        result = self._call_tool("SkuRepurchaseRecall", params, ctx)
        products = result.get("products", [])

        # 优先使用 LLM 生成回复，否则 fallback 到规则
        if self.llm_client and products:
            user_prompt = build_repurchase_user_prompt(
                ctx.user_query,
                products,
                result.get("purchase_months_ago", "?"),
                result.get("order_id", ""),
            )
            content = self._llm_response(REPURCHASE_SYSTEM, user_prompt, ctx)

        if not (self.llm_client and products) or not content:
            content, _ = self._build_response(ctx.user_query, products, result)

        reasons = [f"{p['key_specs']}，{p.get('sales','')}" for p in products]
        cards = self._make_cards(products, reasons)
        self._final_response(content, cards)

        return self._build_trajectory(
            trajectory_id=self._gen_tid("sft_repurchase"),
            ctx=ctx,
            scenario_type=self.SCENARIO,
            category=self.CATEGORY,
            training_focus=f"复购{keyword}+推荐升级/新品",
        )

    def _extract_keyword(self, query: str) -> str:
        """提取品类关键词"""
        import re
        # 去掉动词词语
        q = re.sub(r"再买|复购|补货|快用完|快没|要买|顺便推荐|问下|询问", "", query)
        return q.strip()[:10]

    def _build_response(self, query: str, products: List[Dict],
                        result: Dict) -> Tuple[str, List]:
        if not products:
            return "没有找到相关历史购买记录。", []

        hist = products[0]  # 历史购买商品
        recs = products[1:]  # 推荐款

        months_ago = result.get("purchase_months_ago", "?")
        order_id = result.get("order_id", "")

        lines = [
            f"你 **{months_ago} 个月前**购买了：**{hist['title'].split('（')[0]}**",
        ]
        if order_id:
            lines.append(f"订单：{order_id}\n")

        lines.append("## 🛒 购买方案")

        # 方案A：直接复购
        lines.append(f"\n**方案 A：直接复购（¥{hist['price']:.0f}）**")
        lines.append("- 已知体验好，不冒险")
        lines.append(f"- {hist['key_specs']}")

        # 方案B：推荐升级/新品
        if recs:
            lines.append(f"\n**方案 B：{len(recs)} 款升级/新品推荐** ⭐")
            for r in recs:
                lines.append(f"\n**{r['title']}（¥{r['price']:.0f}）**")
                lines.append(f"{r['key_specs']}，{r.get('sales', '')}")

        lines.append("\n## 💡 建议")
        if recs:
            best_rec = max(recs, key=lambda x: x["rating"])
            lines.append(f"→ 推荐试试 **{best_rec['title'].split()[0]}**：{best_rec['key_specs'][:40]}")
        else:
            lines.append("→ 继续复购同款，体验稳定可靠")

        content = "\n".join(lines)
        reasons = [f"{p['key_specs']}，{p.get('sales','')}" for p in products]
        cards = self._make_cards(products, reasons)
        return content, cards
