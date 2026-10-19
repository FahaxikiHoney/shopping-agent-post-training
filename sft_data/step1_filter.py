# -*- coding: utf-8 -*-
"""
清理脚本：按 shopping 真实项目场景过滤现有数据
保留：search/recommend、sku_comp、下单、相似品/复购、组合购物相关
砍掉：外卖/机酒/PLUS价保/以旧换新/延保/物流/退换货/纯咨询等项目无对应能力的
"""
import json
from pathlib import Path

SRC = Path(__file__).parent / "trajectories.jsonl"
DST = Path(__file__).parent / "trajectories_cleaned.jsonl"

# ──── 保留白名单（按真实项目场景分类）────────────────────────────────
# 每条标注新的 scenario_type，对应 shopping agent_flow
KEEP_MAP = {
    # ─── 单品搜索推荐（search/recommend）─────────────────────────
    "sft_ecom_001": "search_recommend",   # 老人按摩仪
    "sft_ecom_002": "search_recommend",   # 空气净化器
    "sft_ecom_003": "search_recommend",   # 跑步鞋
    "sft_ecom_004": "search_recommend",   # 笔记本跑PS
    "sft_ecom_005": "search_recommend",   # 干皮面霜
    "sft_ecom_006": "search_recommend",   # 遮光窗帘
    "sft_ecom_007": "search_recommend",   # 婴儿车
    "sft_good_021": "search_recommend",   # 学生平板
    "sft_good_023": "search_recommend",   # 扫地机器人
    "sft_good_024": "search_recommend",   # 游戏本（坦诚预算）
    "sft_good_026": "search_recommend",   # 抗老眼霜
    "sft_good_027": "search_recommend",   # 婴儿米粉
    "sft_good_028": "search_recommend",   # 扫地机WiFi(多轮)
    "sft_good_029": "search_recommend",   # 净化器砍预算(多轮)

    # ─── 商品对比（sku_comp）─────────────────────────────────────
    "sft_good_022": "sku_comp",           # 小米 vs 华为 对比

    # ─── 下单（ShoppingPlaceOrderTool）─────────────────────────
    "sft_order_001": "place_order",       # 下单按摩仪

    # ─── 复购召回（SkuRepurchaseRecall）─────────────────────────
    "sft_history_001": "repurchase",      # 查净化器历史订单→推滤芯（典型复购场景）

    # ─── 组合购物（多次工具+预算拆分）──────────────────────────
    "sft_budget_001": "bundle_purchase",  # 3000元学习装备 平板+键盘+耳机
    "sft_consult_002": "bundle_purchase", # 健身入门装备组合
    "sft_order_002": "bundle_purchase",   # 猫粮+罐头凑满减（多商品下单）

    # ─── 负样本：search_recommend 场景的 reward hacking ────────
    "sft_bad_001": "search_recommend",    # 蓝牙耳机幻觉card_id
    "sft_bad_002": "search_recommend",    # 跑步鞋需求理解失败
    "sft_bad_005": "search_recommend",    # 净化器全套话
    "sft_bad_006": "search_recommend",    # 按摩仪价格幻觉
    "sft_bad_007": "search_recommend",    # 儿童牙刷推剃须刀(品类错配)
    "sft_bad_008": "search_recommend",    # 平板假装没找到
    "sft_bad_009": "search_recommend",    # 扫地机价格幻觉
    "sft_bad_010": "search_recommend",    # 瑜伽垫推卷尺
    "sft_bad_011": "search_recommend",    # 口红全套话
    "sft_bad_012": "search_recommend",    # 游戏本超预算
    "sft_bad_013": "search_recommend",    # 电动牙刷不调工具
    "sft_bad_014": "search_recommend",    # 电烤箱半幻觉价格漂移
    "sft_bad_015": "search_recommend",    # 破壁机忽略静音约束
    "sft_bad_016": "search_recommend",    # 血压计夸大功效
    "sft_bad_017": "search_recommend",    # 小冰箱平淡信息堆砌
    "sft_bad_018": "search_recommend",    # 雨伞错误推荐顺序
    "sft_bad_020": "search_recommend",    # 蓝牙音箱促销价混淆
    "sft_bad_021": "place_order",         # 电吹风工具调用顺序错乱(下单场景)
    "sft_bad_022": "search_recommend",    # 洗发水上下文遗忘(多轮)
    "sft_bad_024": "search_recommend",    # 编程笔记本性别偏见
    "sft_bad_026": "search_recommend",    # U盘过度推贵的
    "sft_bad_028": "search_recommend",    # 扫地机隐瞒负面信息

    # ─── 负样本：sku_comp 场景的 reward hacking ────────────────
    "sft_bad_003": "sku_comp",            # 手机对比过短规避
    "sft_bad_025": "sku_comp",            # 手环虚假对比表格
}

# ──── 砍掉的（项目无对应能力）────────────────────────────────────
# 外卖类：sft_waimai_* / sft_bad_004 / sft_bad_023
# 机酒类：sft_travel_*
# PLUS价保/以旧换新/延保/物流/退换货：
#   sft_discount_* / sft_good_030 / sft_good_032 / sft_good_034-040
#   sft_history_002 / sft_bad_019
# 纯咨询(项目里没有 consultative_skill)：
#   sft_consult_001 / sft_good_025 / sft_good_031 / sft_good_041 / sft_bad_029
# 谄媚附和(项目里没对应价值观维度)：sft_bad_027


def main():
    with open(SRC, "r", encoding="utf-8") as f:
        all_data = [json.loads(line) for line in f]

    print(f"原始数据: {len(all_data)} 条")
    print()

    kept = []
    dropped = []

    for t in all_data:
        tid = t.get("trajectory_id")
        if tid in KEEP_MAP:
            # 加上 scenario_type 标签
            t["scenario_type"] = KEEP_MAP[tid]
            kept.append(t)
        else:
            dropped.append(t)

    print(f"✅ 保留: {len(kept)} 条")
    print(f"❌ 砍掉: {len(dropped)} 条")
    print()

    # 按 scenario_type 分布
    from collections import Counter
    scenario_dist = Counter(t["scenario_type"] for t in kept)
    label_dist = Counter(t.get("quality_label", "good") for t in kept)

    print("📊 保留数据 - 场景分布:")
    for sc, n in sorted(scenario_dist.items(), key=lambda x: -x[1]):
        print(f"  {sc:<22}: {n} 条")

    print()
    print("📊 保留数据 - 正负样本:")
    for lb, n in label_dist.items():
        print(f"  {lb:<8}: {n} 条")

    print()
    print("🗑️  砍掉的明细:")
    for t in dropped:
        print(f"  - {t['trajectory_id']:<22} {t.get('category','?'):<14} | {t.get('user_query','')[:40]}")

    # 写入清理后的文件
    with open(DST, "w", encoding="utf-8") as f:
        for t in kept:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    print()
    print(f"✅ 已写入 {DST}")
    print(f"   共 {len(kept)} 条")


if __name__ == "__main__":
    main()
