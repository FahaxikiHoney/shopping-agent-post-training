# -*- coding: utf-8 -*-
"""
Step 2: 工具名替换
把现有数据里的工具名换成 joybuy 真实项目里的工具名

参考真实工具列表（来自 core/multi_agent/*/tool_list.py）：
- SkuRecallShopping      : 主搜索召回（最常用）
- SkuRecallToolJkc       : 京客超召回
- SkuRepurchaseRecall    : 复购召回（用过的商品再推）
- SkuImageRecall         : 图搜召回
- ShoppingPlaceOrderTool : 下单
- WebSearchTool          : 网页搜索兜底
- master_skill 的子能力(read_file 读 skill)
"""
import json
from pathlib import Path

SRC = Path(__file__).parent / "trajectories_cleaned.jsonl"
DST = Path(__file__).parent / "trajectories_v2_renamed.jsonl"

# ──── 工具名映射表 ──────────────────────────────────────────────────
TOOL_RENAME = {
    "product_search": "SkuRecallShopping",
    "order_create": "ShoppingPlaceOrderTool",
    "order_query": "OrderQuerySkill",          # master_skill 下的能力
    "order_update_address": "AddressManageSkill",
    "logistics_track": "OrderQuerySkill",       # 物流也归到 order query 下
    "trade_in_quote": "WebSearchTool",          # 项目里没有，归到 web search
    "waimai_search": "SkuRecallToolLbsOneStep", # 外卖召回（虽然砍了，保险起见也映射）
    "flight_search": "SkuRecallToolTrip",
    "hotel_search": "SkuRecallToolTrip",
    "after_sales_appointment": "WebSearchTool",
    "python_calculator": "PythonCalculator",    # 保留这个工具名（agent 框架常见）
    "read_file": "ReadFile",                    # skill 加载
    "check_promotions": "SkuRecallShopping",    # 合并到主搜索（带促销字段）
}

# 也修正 quality_label 等字段
SCENARIO_DISPLAY_MAP = {
    "search_recommend": "购物搜索推荐",
    "sku_comp": "商品对比",
    "similar_rec": "相似品推荐",
    "place_order": "购物下单",
    "repurchase": "复购召回",
    "bundle_purchase": "组合购物",
    "matching_purchase": "搭配购物",
}


def rename_tools_in_traj(traj: dict) -> dict:
    """递归替换 trajectory 中所有 tool_name 字段。"""
    for step in traj.get("steps", []):
        if step.get("tool_name") in TOOL_RENAME:
            step["tool_name"] = TOOL_RENAME[step["tool_name"]]
    # 也加上 category_display 方便面试展示
    sc = traj.get("scenario_type")
    if sc and sc in SCENARIO_DISPLAY_MAP:
        traj["category"] = SCENARIO_DISPLAY_MAP[sc]
    return traj


def main():
    with open(SRC, "r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f]

    print(f"输入: {len(data)} 条")

    # 统计原始工具使用
    from collections import Counter
    orig_tools = Counter()
    for t in data:
        for s in t.get("steps", []):
            if s.get("tool_name"):
                orig_tools[s["tool_name"]] += 1

    print()
    print("📊 原始工具名分布:")
    for tn, c in sorted(orig_tools.items(), key=lambda x: -x[1]):
        new_name = TOOL_RENAME.get(tn, tn)
        mark = "→" if new_name != tn else " "
        print(f"  {tn:<30} {mark} {new_name:<30} ({c} 次)")

    # 执行替换
    renamed = [rename_tools_in_traj(t) for t in data]

    # 统计替换后的工具使用
    new_tools = Counter()
    for t in renamed:
        for s in t.get("steps", []):
            if s.get("tool_name"):
                new_tools[s["tool_name"]] += 1

    print()
    print("📊 替换后工具名分布:")
    for tn, c in sorted(new_tools.items(), key=lambda x: -x[1]):
        print(f"  {tn:<35} {c} 次")

    # 场景分布
    sc_dist = Counter(t["scenario_type"] for t in renamed)
    print()
    print("📊 场景类型分布:")
    for sc, n in sorted(sc_dist.items(), key=lambda x: -x[1]):
        display = SCENARIO_DISPLAY_MAP.get(sc, sc)
        print(f"  {sc:<22} ({display}): {n} 条")

    # 写入新文件
    with open(DST, "w", encoding="utf-8") as f:
        for t in renamed:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    print()
    print(f"✅ 已写入 {DST}")
    print(f"   共 {len(renamed)} 条")


if __name__ == "__main__":
    main()
