# -*- coding: utf-8 -*-
"""BundleAgent — bundle_purchase 场景"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple

from joybuy_agent.core.agent import ShoppingAgent
from joybuy_agent.core.context import AgentContext
from joybuy_agent.llm.prompts import BUNDLE_SYSTEM, build_bundle_user_prompt

# 场景 → 品类列表 + 预算占比
BUNDLE_STRATEGIES: Dict[str, List[Dict]] = {
    "kitchen": [
        {"name": "炒锅", "ratio": 0.35, "query": "炒锅 不粘锅"},
        {"name": "刀具", "ratio": 0.30, "query": "厨房刀具套装 不锈钢"},
        {"name": "汤锅", "ratio": 0.20, "query": "汤锅 304不锈钢"},
        {"name": "煎锅", "ratio": 0.15, "query": "平底煎锅 不粘"},
    ],
    "home_office": [
        {"name": "椅子", "ratio": 0.50, "query": "人体工学椅 久坐"},
        {"name": "显示器", "ratio": 0.30, "query": "显示器 2K IPS"},
        {"name": "键鼠套装", "ratio": 0.15, "query": "键盘鼠标套装 无线"},
        {"name": "台灯", "ratio": 0.05, "query": "护眼台灯 调光"},
    ],
    "fitness": [
        {"name": "哑铃", "ratio": 0.40, "query": "哑铃 可调节 家用"},
        {"name": "瑜伽垫", "ratio": 0.15, "query": "瑜伽垫 加厚 天然橡胶"},
        {"name": "弹力带", "ratio": 0.10, "query": "弹力带 训练 套装"},
        {"name": "跳绳", "ratio": 0.10, "query": "智能跳绳 计数"},
        {"name": "蛋白粉", "ratio": 0.25, "query": "乳清蛋白粉 健身"},
    ],
    "student": [
        {"name": "台灯", "ratio": 0.40, "query": "护眼台灯 学生 AA级"},
        {"name": "风扇", "ratio": 0.20, "query": "台式风扇 宿舍"},
        {"name": "收纳架", "ratio": 0.20, "query": "桌面收纳架 整理"},
        {"name": "插排", "ratio": 0.20, "query": "排插 宿舍用 安全"},
    ],
    "skincare": [
        {"name": "洁面", "ratio": 0.15, "query": "氨基酸洁面 温和"},
        {"name": "精华", "ratio": 0.40, "query": "保湿精华 补水"},
        {"name": "面霜", "ratio": 0.30, "query": "面霜 保湿 滋润"},
        {"name": "眼霜", "ratio": 0.15, "query": "眼霜 抗老"},
    ],
    "default": [
        {"name": "主商品", "ratio": 0.50, "query": ""},
        {"name": "配件1", "ratio": 0.30, "query": ""},
        {"name": "配件2", "ratio": 0.20, "query": ""},
    ],
}

# 场景关键词 → 策略名
_SCENE_DETECT = {
    "kitchen": ["炒锅", "厨房", "锅具", "刀具", "厨具", "烹饪"],
    "home_office": ["办公", "工作", "椅子", "显示器", "键盘", "书房"],
    "fitness": ["健身", "运动", "哑铃", "跑步", "训练", "锻炼"],
    "student": ["宿舍", "学生", "大学", "台灯", "开学"],
    "skincare": ["护肤", "精华", "面霜", "洁面", "眼霜", "护肤品"],
}


class BundleAgent(ShoppingAgent):
    """
    组合购物 Agent。

    场景：用户有明确预算+场景，需要配齐整套。
    steps：N×SkuRecallShopping（每品类一次）+ PythonCalculator（算账）→ final_response

    训练重点：
    - 多次调用 SkuRecallShopping（每品类独立召回）
    - 必须调用 PythonCalculator 算账（否则 grader 扣分）
    - 输出总价明细表格 + 3套方案（升级/实用/性价比）
    """

    SCENARIO = "bundle_purchase"
    CATEGORY = "组合购物"

    def run(self, ctx: AgentContext) -> Dict[str, Any]:
        self._steps = []

        budget, scene = self._parse_query(ctx.user_query)
        strategy = BUNDLE_STRATEGIES.get(scene, BUNDLE_STRATEGIES["default"])

        # 动态填充 default 策略的 query
        if scene == "default":
            for i, cat in enumerate(strategy):
                cat["query"] = ctx.user_query.split("，")[i] if i < 2 else ctx.user_query

        ctx.set("thinking",
                f"预算{budget}元，场景{scene}，按{len(strategy)}个品类分别召回再算账")

        # 多次召回（每品类一次）
        products_by_cat: List[List[Dict]] = []
        for cat in strategy:
            max_p = int(budget * cat["ratio"]) if budget > 0 else 0
            params: Dict[str, Any] = {
                "query": cat["query"] or ctx.user_query,
                "page_size": 2,
                "is_jd_self": True,
            }
            if max_p > 0:
                params["max_price"] = max_p
            result = self._call_tool("SkuRecallShopping", params, ctx)
            products_by_cat.append(result.get("products", []))

        # 调用 PythonCalculator 算账
        calc_code = self._build_calc_code(products_by_cat, budget, strategy)
        calc_result = self._call_tool("PythonCalculator", {"code": calc_code}, ctx)
        calc_output = calc_result.get("output", "")

        # 生成 final_response
        all_products = [p for cat_prods in products_by_cat for p in cat_prods[:1]]  # 每类取第一款

        # 优先使用 LLM 生成回复，否则 fallback 到规则
        if self.llm_client and all_products:
            user_prompt = build_bundle_user_prompt(
                ctx.user_query, products_by_cat, strategy, budget, calc_output
            )
            content = self._llm_response(BUNDLE_SYSTEM, user_prompt, ctx)

        if not (self.llm_client and all_products) or not content:
            content, _ = self._build_response(
                ctx.user_query, budget, strategy, products_by_cat, calc_output
            )

        reasons = [
            f"{strategy[i]['name']}/{p['key_specs'][:30]}，{p.get('sales','')}"
            for i, p in enumerate(all_products) if i < len(strategy)
        ]
        cards = self._make_cards(all_products, reasons)
        self._final_response(content, cards)

        return self._build_trajectory(
            trajectory_id=self._gen_tid("sft_bundle"),
            ctx=ctx,
            scenario_type=self.SCENARIO,
            category=self.CATEGORY,
            training_focus=f"预算{budget}元{scene}场景，{len(strategy)}品类组合购",
        )

    def _parse_query(self, query: str) -> Tuple[float, str]:
        """提取预算和场景"""
        # 提取预算
        m = re.search(r"(\d+)\s*元|¥\s*(\d+)", query)
        budget = float(next(g for g in m.groups() if g)) if m else 1000.0

        # 识别场景
        for scene, kws in _SCENE_DETECT.items():
            if any(kw in query for kw in kws):
                return budget, scene
        return budget, "default"

    def _build_calc_code(self, products_by_cat: List[List[Dict]],
                         budget: float, strategy: List[Dict]) -> str:
        """生成 PythonCalculator 的代码字符串"""
        lines = []
        cat_prices = []
        for i, (cat, prods) in enumerate(zip(strategy, products_by_cat)):
            if prods:
                p = prods[0]["price"]
                cat_prices.append(p)
                lines.append(f'{cat["name"]} = {p}  # {prods[0]["title"][:20]}')
            else:
                cat_prices.append(0)
                lines.append(f'{cat["name"]} = 0')

        total = sum(cat_prices)
        remaining = budget - total
        lines.append(f'total = {total}')
        lines.append(f'budget = {budget}')
        lines.append(f'remaining = budget - total')
        lines.append(f'print(f"推荐套餐合计: {{total:.0f}}元")')
        lines.append(f'print(f"预算: {{budget:.0f}}元，余{{remaining:.0f}}元")')
        if remaining >= 0:
            lines.append(f'print(f"在预算内，余额可用于配件升级")')
        else:
            lines.append(f'print(f"超出预算{{abs(remaining):.0f}}元，建议降级部分品类")')
        return "\n".join(lines)

    def _build_response(self, query: str, budget: float, strategy: List[Dict],
                        products_by_cat: List[List[Dict]],
                        calc_output: str) -> Tuple[str, List]:
        lines = [f"**{budget:.0f}元**组合购物方案，按{len(strategy)}个品类配置：\n"]

        # 方案表格
        lines.append("## 📦 推荐套餐")
        lines.append("| 品类 | 商品 | 价格 |")
        lines.append("|---|---|---|")

        all_products = []
        total = 0.0
        for cat, prods in zip(strategy, products_by_cat):
            if prods:
                p = prods[0]
                all_products.append(p)
                lines.append(f"| {cat['name']} | {p['title'][:22]} | ¥{p['price']:.0f} |")
                total += p["price"]

        lines.append(f"\n**合计：¥{total:.0f}**，余 ¥{budget - total:.0f}\n")

        # 计算器输出
        if calc_output.strip():
            lines.append("## 💰 预算计算")
            for ln in calc_output.strip().split("\n"):
                lines.append(f"> {ln}")

        # 说明
        lines.append("\n## 💡 配置逻辑")
        for cat, prods in zip(strategy, products_by_cat):
            if prods:
                p = prods[0]
                alloc = budget * cat["ratio"]
                lines.append(f"- **{cat['name']}**（预算占比 {cat['ratio']*100:.0f}%，≤¥{alloc:.0f}）：{p['title'].split()[0]}")

        content = "\n".join(lines)
        reasons = [
            f"{strategy[i]['name']}/{p['key_specs'][:30]}，{p.get('sales','')}"
            for i, p in enumerate(all_products) if i < len(strategy)
        ]
        cards = self._make_cards(all_products, reasons)
        return content, cards
