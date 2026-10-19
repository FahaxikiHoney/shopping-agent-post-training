# -*- coding: utf-8 -*-
"""MatchingAgent — matching_purchase 场景"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

from joybuy_agent.core.agent import ShoppingAgent
from joybuy_agent.core.context import AgentContext
from joybuy_agent.llm.prompts import MATCHING_SYSTEM, build_matching_user_prompt

# 风格关键词映射
_STYLE_MAP = {
    "nordic": ["北欧", "简约", "白橡木", "原木", "极简"],
    "mid_century": ["中古", "胡桃木", "复古", "黄铜", "工业风"],
    "business_formal": ["商务", "正式", "西装", "商务正装", "职场"],
    "fitness": ["健身", "运动", "锻炼", "跑步机", "哑铃"],
    "iphone15promax": ["iPhone 15 Pro Max", "iPhone15 Pro Max", "苹果手机壳"],
}


class MatchingAgent(ShoppingAgent):
    """
    搭配购物 Agent。

    场景：用户买了主商品，需要配套搭配单品。
    steps：1×SkuRecallShopping（matching 模式，filters.style）→ final_response（整套方案表格）

    训练重点：
    - 不传价格约束（搭配购物不以价格为首要维度）
    - filters.style 字段驱动匹配逻辑
    - 输出整套方案表格 + 风格搭配理由
    """

    SCENARIO = "matching_purchase"
    CATEGORY = "搭配购物"

    def run(self, ctx: AgentContext) -> Dict[str, Any]:
        self._steps = []
        style, match_with = self._extract_style(ctx.user_query)
        ctx.set("thinking", f"识别搭配风格：{style}，为主商品「{match_with}」推荐搭配")

        params = {
            "query": ctx.user_query,
            "match_with": match_with,
            "filters": {"style": style, "max_count": 4},
        }
        result = self._call_tool("SkuRecallShopping", params, ctx)
        products = result.get("products", [])

        # 优先使用 LLM 生成回复，否则 fallback 到规则
        if self.llm_client and products:
            user_prompt = build_matching_user_prompt(ctx.user_query, products)
            content = self._llm_response(MATCHING_SYSTEM, user_prompt, ctx)

        if not (self.llm_client and products) or not content:
            content, _ = self._build_response(ctx.user_query, style, match_with, products)

        style_names = {
            "nordic": "北欧简约", "mid_century": "中古复古",
            "business_formal": "商务正式", "fitness": "运动健身",
            "iphone15promax": "苹果配件",
        }
        style_name = style_names.get(style, style)
        reasons = [f"{style_name}风格/{p['key_specs'][:30]}，{p.get('sales','')}" for p in products]
        cards = self._make_cards(products, reasons)
        self._final_response(content, cards)

        return self._build_trajectory(
            trajectory_id=self._gen_tid("sft_match"),
            ctx=ctx,
            scenario_type=self.SCENARIO,
            category=self.CATEGORY,
            training_focus=f"{style}风格搭配方案，{len(products)}件单品",
        )

    def _extract_style(self, query: str) -> Tuple[str, str]:
        """提取风格标签和主商品"""
        style = "nordic"  # 默认北欧风
        match_with = ""
        for s, kws in _STYLE_MAP.items():
            if any(kw in query for kw in kws):
                style = s
                break
        # 提取主商品（「买了X」「有X」）
        m = re.search(r"买了(.{2,15})[，,\s]|已经有(.{2,10})[，,\s]|配(.{2,10})搭配", query)
        if m:
            match_with = next(g for g in m.groups() if g)
        return style, match_with

    def _build_response(self, query: str, style: str,
                        match_with: str, products: List[Dict]) -> Tuple[str, List]:
        if not products:
            return "暂未找到合适的搭配方案。", []

        style_names = {
            "nordic": "北欧简约", "mid_century": "中古复古",
            "business_formal": "商务正式", "fitness": "运动健身",
            "iphone15promax": "苹果配件",
        }
        style_name = style_names.get(style, style)
        main_str = f"「{match_with}」" if match_with else ""

        total_price = sum(p["price"] for p in products)
        lines = [
            f"为{main_str}推荐 **{style_name}** 整套搭配方案（{len(products)} 件，共 ¥{total_price:.0f}）：\n",
            "## 🎨 整套方案",
            "| 单品 | 商品 | 价格 |",
            "|---|---|---|",
        ]
        for p in products:
            lines.append(f"| {p.get('category', p['title'].split()[0])} | {p['title'][:25]} | ¥{p['price']:.0f} |")

        lines.append(f"\n**合计：¥{total_price:.0f}**\n")

        lines.append("## 💡 搭配理由")
        lines.append(f"以上 {len(products)} 件都属于 **{style_name}** 风格体系：")
        for p in products:
            lines.append(f"- **{p['title'].split()[0]}**：{p['key_specs'][:40]}")

        content = "\n".join(lines)
        reasons = [f"{style_name}风格/{p['key_specs'][:30]}，{p.get('sales','')}" for p in products]
        cards = self._make_cards(products, reasons)
        return content, cards
