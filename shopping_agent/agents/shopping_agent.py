# -*- coding: utf-8 -*-
"""SearchRecommendAgent — search_recommend 场景"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple

from shopping_agent.core.agent import ShoppingAgent
from shopping_agent.core.context import AgentContext
from shopping_agent.llm.prompts import SEARCH_RECOMMEND_SYSTEM, build_search_recommend_user_prompt


class SearchRecommendAgent(ShoppingAgent):
    """
    购物搜索推荐 Agent。

    场景：用户有明确购物意图，描述品类+约束条件（预算/用途/人群）。
    steps：1×SkuRecallShopping → final_response（推荐3款+选购建议）

    对应训练数据：sft_ecom_* / search_recommend 场景
    """

    SCENARIO = "search_recommend"
    CATEGORY = "购物搜索推荐"

    def run(self, ctx: AgentContext) -> Dict[str, Any]:
        self._steps = []
        ctx.set("thinking", f"分析用户搜索需求：{ctx.user_query[:30]}")

        params = self._parse_query(ctx.user_query)
        result = self._call_tool("SkuRecallShopping", params, ctx)
        products = result.get("products", [])

        # 优先使用 LLM 生成回复，否则 fallback 到规则
        if self.llm_client and products:
            user_prompt = build_search_recommend_user_prompt(ctx.user_query, products)
            content = self._llm_response(SEARCH_RECOMMEND_SYSTEM, user_prompt, ctx)

        if not (self.llm_client and products) or not content:
            content, _ = self._build_response(ctx.user_query, products, params)

        reasons = [f"{p['key_specs']}，{p['sales']}" for p in products]
        cards = self._make_cards(products, reasons)
        self._final_response(content, cards)

        return self._build_trajectory(
            trajectory_id=self._gen_tid("sft_search"),
            ctx=ctx,
            scenario_type=self.SCENARIO,
            category=self.CATEGORY,
            training_focus=f"多约束搜索推荐：{ctx.user_query[:30]}",
        )

    def _parse_query(self, query: str) -> Dict[str, Any]:
        """从用户 query 中提取搜索参数"""
        params: Dict[str, Any] = {"query": query, "page_size": 3, "is_platform_self": True}

        # 提取价格约束
        m = re.search(r"(\d+)\s*元以内|预算\s*(\d+)|不超过\s*(\d+)", query)
        if m:
            price = int(next(g for g in m.groups() if g))
            params["max_price"] = price

        m2 = re.search(r"(\d+)\s*[~-至到]\s*(\d+)\s*元", query)
        if m2:
            params["min_price"] = int(m2.group(1))
            params["max_price"] = int(m2.group(2))

        return params

    def _build_response(self, query: str, products: List[Dict], params: Dict) -> Tuple[str, List]:
        if not products:
            return f"抱歉，暂时没有找到符合「{query}」的商品。", []

        max_p = params.get("max_price", 0)
        budget_str = f"，预算 ¥{max_p} 以内" if max_p else ""

        lines = [f"根据你的需求「{query}」{budget_str}，为你推荐 {len(products)} 款：\n"]

        stars = ["⭐ 综合推荐", "", ""]
        for i, p in enumerate(products):
            star = stars[i] if i < len(stars) else ""
            lines.append(f"**{i+1}. {p['title']}（¥{p['price']:.0f}）** {star}")
            lines.append(f"{p['key_specs']}，{p['sales']}\n")

        lines.append("\n## 💡 选购建议")
        if len(products) >= 2:
            cheapest = min(products, key=lambda x: x["price"])
            priciest = max(products, key=lambda x: x["price"])
            lines.append(f"- **性价比优先** → 推荐 {cheapest['title'].split()[0]}（¥{cheapest['price']:.0f}）")
            lines.append(f"- **品质优先** → 推荐 {priciest['title'].split()[0]}（¥{priciest['price']:.0f}）")

        content = "\n".join(lines)
        reasons = [f"{p['key_specs']}，{p['sales']}" for p in products]
        cards = self._make_cards(products, reasons)
        return content, cards
