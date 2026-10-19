# -*- coding: utf-8 -*-
"""SimilarRecAgent — similar_rec 场景"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

from shopping_agent.core.agent import ShoppingAgent
from shopping_agent.core.context import AgentContext
from shopping_agent.llm.prompts import SIMILAR_REC_SYSTEM, build_similar_rec_user_prompt

# 抱怨维度 → 搜索关键词补充
_COMPLAINT_MAP = {
    "漏音": ("密封", "封闭式", "隔音"),
    "保温": ("保温", "24h", "真空双层"),
    "噪音": ("静音", "超静音", "低噪"),
    "续航": ("长续航", "大电池", "低功耗"),
    "太重": ("轻量", "轻薄", "便携"),
    "太硬": ("软底", "缓震", "记忆棉"),
    "掉涂层": ("铸铁", "无涂层", "不掉"),
    "发热": ("散热", "安全", "石墨烯"),
    "刮不干净": ("贴面", "高效", "三头"),
    "不能调": ("调光", "多档", "调节"),
    "腰疼": ("人体工学", "腰托", "护腰"),
    "滤芯贵": ("长效", "大容量", "耐用"),
    "慢": ("速热", "快速", "高效"),
    "滚轮": ("鼠标", "顺滑", "高精度"),
    "卡顿": ("鼠标", "顺滑", "响应快"),
    "不防水": ("防水", "防泼水", "IPX"),
    "电量少": ("大电池", "长续航", "快充"),
    "刷不干净": ("强效", "大功率", "深层"),
    "收不到": ("高增益", "信号强", "WiFi6"),
    "太亮": ("护眼", "无频闪", "调光"),
    "屏幕小": ("大屏", "高清", "宽屏"),
}


class SimilarRecAgent(ShoppingAgent):
    """
    相似品推荐 Agent。

    场景：用户抱怨当前商品的某个缺点，要换同价位改进款。
    steps：1×SkuRecallShopping（根据抱怨调整参数）→ final_response

    训练重点：识别用户抱怨维度 → 转化为精确的搜索约束
    """

    SCENARIO = "similar_rec"
    CATEGORY = "相似品推荐"

    def run(self, ctx: AgentContext) -> Dict[str, Any]:
        self._steps = []
        complaint, fix_kws = self._extract_complaint(ctx.user_query)
        ctx.set("thinking", f"用户抱怨：{complaint}，需要推荐{'/'.join(fix_kws)}款替代品")

        params = self._build_params(ctx.user_query, fix_kws)
        result = self._call_tool("SkuRecallShopping", params, ctx)
        products = result.get("products", [])

        # 优先使用 LLM 生成回复，否则 fallback 到规则
        if self.llm_client and products:
            user_prompt = build_similar_rec_user_prompt(ctx.user_query, products)
            content = self._llm_response(SIMILAR_REC_SYSTEM, user_prompt, ctx)

        if not (self.llm_client and products) or not content:
            content, _ = self._build_response(ctx.user_query, complaint, fix_kws, products)

        cards = self._make_cards(products, [f"{p['key_specs']}，{p['sales']}" for p in products])
        self._final_response(content, cards)

        return self._build_trajectory(
            trajectory_id=self._gen_tid("sft_simrec"),
            ctx=ctx,
            scenario_type=self.SCENARIO,
            category=self.CATEGORY,
            training_focus=f"抱怨{complaint}→推荐{'/'.join(fix_kws[:2])}款",
        )

    def _extract_complaint(self, query: str) -> Tuple[str, List[str]]:
        """提取抱怨维度和对应的改进关键词"""
        for complaint, fix_kws in _COMPLAINT_MAP.items():
            if complaint in query:
                return complaint, list(fix_kws)
        return "功能不足", ["升级款", "改进款"]

    def _build_params(self, query: str, fix_kws: List[str]) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "query": f"{fix_kws[0]} {fix_kws[1] if len(fix_kws) > 1 else ''}",
            "page_size": 3,
            "is_platform_self": True,
        }
        # 提取价格区间
        m = re.search(r"(\d+)\s*元以内|预算\s*(\d+)", query)
        if m:
            params["max_price"] = int(next(g for g in m.groups() if g))
        return params

    def _build_response(self, query: str, complaint: str,
                        fix_kws: List[str], products: List[Dict]) -> Tuple[str, List]:
        if not products:
            return f"抱歉，暂时没有找到符合需求的相似品。", []

        fix_desc = "/".join(fix_kws[:2])
        lines = [f"你抱怨当前商品「{complaint}」，为你找了 {len(products)} 款 **{fix_desc}** 改进款：\n"]

        stars = ["⭐ 首选", "", ""]
        for i, p in enumerate(products):
            star = stars[i] if i < len(stars) else ""
            lines.append(f"**{i+1}. {p['title']}（¥{p['price']:.0f}）** {star}")
            lines.append(f"{p['key_specs']}，{p['sales']}\n")

        lines.append(f"\n## 💡 为什么推荐这些")
        lines.append(f"你原来商品的问题是「{complaint}」，以上 {len(products)} 款都在这个维度上有明显改进，")
        lines.append(f"按 **{fix_desc}** 筛选，价格区间与原款相近。")

        content = "\n".join(lines)
        cards = self._make_cards(products, [f"{p['key_specs']}，{p['sales']}" for p in products])
        return content, cards

