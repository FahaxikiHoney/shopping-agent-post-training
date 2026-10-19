# -*- coding: utf-8 -*-
"""SkuCompAgent — sku_comp 场景"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple

from joybuy_agent.core.agent import ShoppingAgent
from joybuy_agent.core.context import AgentContext
from joybuy_agent.llm.prompts import SKU_COMP_SYSTEM, build_sku_comp_user_prompt


class SkuCompAgent(ShoppingAgent):
    """
    商品对比 Agent。

    场景：用户明确点名 2-4 款商品，要求对比分析。
    steps：1×SkuRecallShopping（精确匹配 skus）→ final_response（含 Markdown 对比表格）

    训练重点：
    - 精确匹配用户指定的商品（不自行替换）
    - 多维度对比表格（价格/核心参数/月销/适合人群）
    - 给出明确的倾向性建议
    """

    SCENARIO = "sku_comp"
    CATEGORY = "商品对比"

    def run(self, ctx: AgentContext) -> Dict[str, Any]:
        self._steps = []
        skus = self._extract_skus(ctx.user_query)
        ctx.set("thinking", f"提取对比商品：{skus}，按精确名称召回后进行多维对比")

        result = self._call_tool("SkuRecallShopping", {"skus": skus, "page_size": len(skus)}, ctx)
        products = result.get("products", [])

        # 优先使用 LLM 生成回复，否则 fallback 到规则
        if self.llm_client and products:
            user_prompt = build_sku_comp_user_prompt(ctx.user_query, products)
            content = self._llm_response(SKU_COMP_SYSTEM, user_prompt, ctx)

        if not (self.llm_client and products) or not content:
            content, _ = self._build_comp_response(ctx.user_query, products)

        reasons = [f"¥{p['price']:.0f}/{p['key_specs']}/{p.get('sales','')}" for p in products]
        cards = self._make_cards(products, reasons)
        self._final_response(content, cards)

        return self._build_trajectory(
            trajectory_id=self._gen_tid("sft_skucomp"),
            ctx=ctx,
            scenario_type=self.SCENARIO,
            category=self.CATEGORY,
            training_focus=f"精确对比 {len(products)} 款：{'/'.join(skus[:2])}",
        )

    def _extract_skus(self, query: str) -> List[str]:
        """简单启发式：按「和」「与」「vs」「/」分割商品名"""
        import re
        # 移除问句词
        q = re.sub(r"帮我|对比|哪个|哪款|比较|怎么选|有什么区别|怎样|如何", "", query)
        for sep in [" vs ", " VS ", " 和 ", " 与 ", " 或 ", "/"]:
            if sep in q:
                parts = [p.strip() for p in q.split(sep) if p.strip()]
                if len(parts) >= 2:
                    return parts[:4]
        # 无法分割时返回完整 query 作为单个 sku
        return [query.strip()]

    def _build_comp_response(self, query: str, products: List[Dict]) -> Tuple[str, List]:
        if not products:
            return "抱歉，未能找到你指定的商品信息。", []

        lines = [f"以下是 {len(products)} 款商品的对比分析：\n"]

        # 对比总览表格
        lines.append("## 📊 核心对比")
        lines.append("| 维度 | " + " | ".join(p["title"].split()[0] for p in products) + " |")
        lines.append("|---|" + "---|" * len(products))
        lines.append("| 价格 | " + " | ".join(f"¥{p['price']:.0f}" for p in products) + " |")
        lines.append("| 评分 | " + " | ".join(str(p["rating"]) for p in products) + " |")
        lines.append("| 月销 | " + " | ".join(p.get("sales", "-") for p in products) + " |")
        lines.append("")

        # 各商品核心卖点
        lines.append("## 🔍 各款详细说明")
        stars = ["⭐ 综合推荐", "", "", ""]
        for i, p in enumerate(products):
            star = stars[i] if i == 0 else ""
            lines.append(f"\n### {p['title']} {star}")
            lines.append(f"**价格**：¥{p['price']:.0f}  **月销**：{p.get('sales', '-')}")
            for spec in p.get("key_specs", "").split("/"):
                if spec.strip():
                    lines.append(f"- {spec.strip()}")

        # 结论
        lines.append("\n## 🎯 我的建议")
        if len(products) >= 2:
            cheapest = min(products, key=lambda x: x["price"])
            best_rated = max(products, key=lambda x: x["rating"])
            lines.append(f"- **性价比优先** → **{cheapest['title'].split()[0]}**（¥{cheapest['price']:.0f}）")
            if best_rated["product_id"] != cheapest["product_id"]:
                lines.append(f"- **品质优先** → **{best_rated['title'].split()[0]}**（评分 {best_rated['rating']}）")

        content = "\n".join(lines)
        reasons = [f"¥{p['price']:.0f}/{p['key_specs']}/{p.get('sales','')}" for p in products]
        cards = self._make_cards(products, reasons)
        return content, cards
