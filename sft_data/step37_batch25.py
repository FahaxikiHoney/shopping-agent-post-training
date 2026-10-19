# -*- coding: utf-8 -*-
"""Step 37: 第 25 批 10 条"""
import json
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "trajectories_final.jsonl"

def make_traj(tid, sc, cat, focus, query, tool_input, products, final_content, card_reasons, tool_name="SkuRecallShopping", multi_turn=False, history=None):
    cards = [{"card_id": p["product_id"], "display_price": p["price"], "reason": r} for p, r in zip(products, card_reasons)]
    return {
        "trajectory_id": tid, "scenario_type": sc, "category": cat, "quality_label": "good",
        "training_focus": focus, "is_multi_turn": multi_turn, "conversation_history": history or [],
        "user_query": query, "thinking": f"分析{focus}",
        "steps": [
            {"step_id": 1, "step_type": "tool_call", "tool_name": tool_name, "tool_input": tool_input,
             "tool_output": {"status": "SUCCESS", "products": products}, "error_type": None},
            {"step_id": 2, "step_type": "final_response", "content": final_content, "product_cards": cards}
        ],
        "final_response": final_content, "eval_score": 1.0, "sft_source": "claude_local_v1"
    }


T = []

# 1. similar_rec - 抱怨屏幕刷新率低
T.append(make_traj(
    "sft_simrec_061", "similar_rec", "相似品推荐",
    "抱怨刷新率低卡顿 → 推荐 120Hz 及以上款",
    "之前买的手机刷新率 60Hz，滑动很卡，换个 120Hz 同价位款",
    {"query": "手机 120Hz 高刷新率 流畅", "min_price": 2000, "max_price": 3000, "filters": {"refresh_rate_min": 120}},
    [
        {"product_id": "mock_phone_120_1", "title": "小米 Redmi Note 13 Pro+ 120Hz AMOLED", "price": 2199, "is_platform_self": True, "rating": 4.9, "key_specs": "120Hz AMOLED/2K屏/骁龙7s Gen 2/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "mock_phone_120_2", "title": "OPPO Reno 11 5G 120Hz 旗舰曲屏", "price": 2499, "is_platform_self": True, "rating": 4.8, "key_specs": "120Hz曲屏/旗舰拍照/人像哈苏调校", "sales": "月销1.2万"},
        {"product_id": "mock_phone_120_3", "title": "荣耀 90 5G 120Hz 护眼 骁龙878", "price": 2299, "is_platform_self": True, "rating": 4.8, "key_specs": "120Hz护眼认证/骁龙878/5000mAh大电池", "sales": "月销1.5万"}
    ],
    "60Hz → 120Hz 是**体验质变**，滚动/动画流畅度差距明显。3 款都带 120Hz：\n\n**1. Redmi Note 13 Pro+（¥2199）** ⭐ 性价比首选\n120Hz AMOLED 2K 屏，骁龙 7s Gen2，**月销 2.5 万断档**。这个价位屏幕素质最高。\n\n**2. 荣耀 90（¥2299）**\n120Hz 有护眼认证，**长时间看手机眼睛更舒服**。5000mAh 大电池续航强。\n\n**3. OPPO Reno 11（¥2499）**\n120Hz 曲屏+哈苏人像，**颜值和拍照都很强**，更贵一点。\n\n## 💡 120Hz 实际体验差异\n\n- **滚动网页/刷抖音**：120Hz 比 60Hz 流畅感提升 50%\n- **游戏**：支持高帧率游戏后差距更大\n- **功耗**：120Hz 比 60Hz 多耗约 10% 电量（可开自适应节能）",
    ["Redmi Note 13 Pro+ 120Hz AMOLED+2K屏+月销2.5万，2000档最高屏幕素质", "荣耀90 120Hz护眼认证+5000mAh+月销1.5万，长时间使用护眼续航强", "OPPO Reno 11 120Hz曲屏+哈苏人像+月销1.2万，颜值拍照双强"]
))

# 2. similar_rec - 抱怨价格涨了
T.append(make_traj(
    "sft_simrec_062", "similar_rec", "相似品推荐",
    "抱怨价格涨价 → 推荐性能接近但更便宜的替代",
    "原来买的那款咖啡豆 280 块，现在涨到 380 了，有性价比好的替代款吗",
    {"query": "咖啡豆 精品 单品 性价比 产地直发", "max_price": 250, "filters": {"grade": "specialty"}},
    [
        {"product_id": "mock_coffee_alt_1", "title": "永璞 挂耳咖啡 精品单品 10g×20包", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "精品产地/10g×20包/挂耳方便/月销8万", "sales": "月销8万"},
        {"product_id": "mock_coffee_alt_2", "title": "隅田川 新鲜烘焙 精品豆 云南产地 250g", "price": 168, "is_platform_self": True, "rating": 4.8, "key_specs": "云南精品/新鲜烘焙/250g/日期可查/月销3.5万", "sales": "月销3.5万"},
        {"product_id": "mock_coffee_alt_3", "title": "鱼眼咖啡 精品单品豆 埃塞俄比亚 200g", "price": 218, "is_platform_self": True, "rating": 4.9, "key_specs": "精品级SCA 84+/埃塞耶加雪菲产地/花香果香", "sales": "月销2200"}
    ],
    "涨了 ¥100 还是有更划算的选择，3 款平替：\n\n**1. 隅田川云南精品豆（¥168）** ⭐ 直接平替\n**云南精品产地**+新鲜烘焙，250g 比原来可能还多。¥168 比原来省 ¥112，月销 3.5 万。\n\n**2. 鱼眼埃塞精品豆（¥218）**\n**SCA 评分 84+** 是专业精品咖啡级别，埃塞耶加雪菲花香果香明显。比原来贵你的涨价款还便宜 ¥162。\n\n**3. 永璞挂耳精品（¥89）**\n**最便宜+最方便**，挂耳免磨豆，不买磨豆机直接用。月销 8 万断档。\n\n## 💡 怎么判断精品咖啡值不值\n\n**SCA 评分**是判断精品豆的标准：\n- ≥80 分：精品咖啡\n- ≥85 分：高端精品\n- ≥90 分：顶级精品（通常 ¥500+）\n\n¥168-218 的精品豆 SCA 80-84 分，**比你原来那款性价比更高**。",
    ["隅田川云南精品豆168元+新鲜烘焙+月销3.5万，直接平替原来款省100", "鱼眼精品豆SCA 84+埃塞耶加雪菲+月销2200，专业精品级花香果香", "永璞挂耳精品咖啡89元+月销8万，最便宜免磨豆方便首选"]
))

# 3. sku_comp - 电饭煲 vs 高压锅 vs 电炖锅
T.append(make_traj(
    "sft_skucomp_059", "sku_comp", "商品对比",
    "三种加热方式厨电对比",
    "买煮饭/炖汤的厨电，电饭煲/高压锅/电炖锅哪个更适合家用",
    {"categories": ["智能IH电饭煲", "电压力锅", "电炖锅"], "max_price": 1000, "topk_per_category": 1},
    [
        {"product_id": "mock_cooker_rice", "title": "美的 IH 电饭煲 MB-FZ4057 4L", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "IH电磁加热/4L/煮饭最好/烹饪模式多", "sales": "月销2.5万"},
        {"product_id": "mock_cooker_pressure", "title": "九阳 JYY-50C98 5L 多功能电压力锅", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "5L/高压快速/炖肉炖骨/适合时间少家庭", "sales": "月销4.5万"},
        {"product_id": "mock_cooker_stew", "title": "九阳 电炖锅 3.5L 慢炖 紫砂内胆", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "紫砂内胆/慢炖8h/老火靓汤/月销1.5万", "sales": "月销1.5万"}
    ],
    "三种厨电核心用途完全不同，**选错了体验很差**：\n\n## 📊 三种对比\n\n| 维度 | IH 电饭煲 ¥599 | 电压力锅 ¥399 | 电炖锅 ¥299 |\n|---|---|---|---|\n| 核心功能 | **煮米饭最好** | 快速炖煮 | **慢炖最好** |\n| 炖肉时间 | 1h | **20 分钟** | 6-8h |\n| 米饭口感 | **最好（IH）** | 一般 | 不适合 |\n| 汤的质量 | 一般 | 中 | **最好（慢炖）**|\n| 适合谁 | 在乎饭香的人 | 时间少工作忙 | 追求老火汤 |\n\n## 🎯 怎么选\n\n### 在乎米饭口感 → IH 电饭煲 ¥599\nIH 电磁加热比普通底部加热均匀，**煮出来的饭更香更软**。\n\n### 工作忙时间少 → 电压力锅 ¥399\n20 分钟出炖肉，**月销 4.5 万件是厨电销冠**——工作日快速出锅。\n\n### 追求老火汤/养生 → 电炖锅 ¥299\n紫砂内胆慢炖 6-8 小时，**汤色清澈、营养不流失**。下班前设好，回家直接喝。\n\n## 💡 哪两件最值得组合\n\n**电压力锅 + 电炖锅 = ¥698**：\n- 电压力锅：每日快速出锅（工作日）\n- 电炖锅：周末慢炖补身（闲时）\n- 这两件加起来比 IH 电饭煲还便宜",
    ["美的IH电饭煲4L+电磁加热均匀+月销2.5万，最在乎米饭香软口感", "九阳电压力锅5L+高压20分钟出肉+月销4.5万，工作忙时间少快速出锅", "九阳电炖锅紫砂内胆慢炖8h+月销1.5万，追求老火汤养生周末备汤"]
))

# 4. sku_comp - 跑步鞋档次对比
T.append(make_traj(
    "sft_skucomp_060", "sku_comp", "商品对比",
    "日常跑步鞋 300/600/1200 三档对比",
    "买跑步鞋 300/600/1200 三个价位差在哪，哪个最值",
    {"skus": ["300元跑步鞋入门", "600元跑步鞋中端", "1200元跑步鞋旗舰"], "mode": "price_tier_comparison"},
    [
        {"product_id": "mock_run_300", "title": "李宁 超轻19 入门跑步鞋 300元档", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "轻量/EVA中底/适合初跑者/月销3.5万", "sales": "月销3.5万"},
        {"product_id": "mock_run_600", "title": "Nike Pegasus 40 常青款 600元档", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "React缓震/日常训练主力/经典常青款/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "mock_run_1200", "title": "耐克 Alphafly 3 碳板竞速 1200元档", "price": 1299, "is_platform_self": True, "rating": 4.9, "key_specs": "碳板+ZoomX泡棉/竞速/半马以上/月销4500", "sales": "月销4500"}
    ],
    "**结论：日常跑步 600 元是性价比拐点，1200 元碳板仅比赛用**。\n\n## 📊 三档差异\n\n| 维度 | ¥299 入门 | ¥599 中端 | ¥1299 旗舰 |\n|---|---|---|---|\n| 中底材料 | EVA（普通）| **React（缓震好）**| **ZoomX+碳板（回弹最佳）**|\n| 适合里程 | < 5km/次 | **5-15km（日常）**| 半马+全马竞速 |\n| 耐磨度 | 500km | 700km | 400km（竞速损耗快）|\n| 日常训练 | 基础够用 | **最佳方案** | 超出需要 |\n| 月销 | 3.5 万 | **2.5 万** | 4500 |\n\n## 🎯 怎么选\n\n### 刚开始跑步（< 3km/次）→ ¥299 入门款\n- 还没确定能坚持，**试跑阶段不值得花大钱**\n- 够用 6 个月，确定爱好再升级\n\n### 每周 3 次、5-15km → **Nike Pegasus ¥599** ⭐\n- **日常训练的黄金选择**\n- React 缓震保护膝盖\n- 常青款年年更新，口碑 30 年稳定\n- 月销 2.5 万不是没有原因\n\n### 备战半马/全马 → 碳板 ¥1299\n- 碳板提升效率但**对肌腱压力大**（需要肌肉强度）\n- 日常训练用碳板会加速疲劳\n- 正确做法：**日常用 Pegasus，比赛换碳板**\n\n## ⚠️ 新手别直接买碳板\n\n脚踝肌肉不够强壮就穿碳板，**受伤风险比普通鞋高 2 倍**。先跑 6 个月再考虑。",
    ["李宁超轻19 EVA中底+月销3.5万，初跑者5km内试跑入门首选", "Nike Pegasus 40 React缓震+日常训练主力+月销2.5万，5-15km日常跑步性价比拐点", "耐克Alphafly 3碳板ZoomX+月销4500，半马以上比赛竞速专用"]
))

# 5. matching - 冬季女士整套
T.append(make_traj(
    "sft_match_059", "matching_purchase", "搭配购物",
    "春节回家整套穿搭（女生）",
    "春节回家拜年，穿什么衣服显喜庆又不土，配大衣+内搭+鞋",
    {"query": "春节拜年穿搭 女生 喜庆不土", "filters": {"occasion": "chinese_new_year", "style": "festive_modern"}},
    [
        {"product_id": "mock_cny_1", "title": "气质感红色中长大衣 双面呢 改良汉元素", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "暗红色/改良汉元素/双面呢/端庄喜庆", "sales": "月销2200"},
        {"product_id": "mock_cny_2", "title": "奶白针织内搭毛衣 高领修身 打底款", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "奶白色/高领/修身/内搭大衣完美", "sales": "月销1.5万"},
        {"product_id": "mock_cny_3", "title": "复古中跟玛丽珍鞋 黑色 喜庆配色", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "黑色中跟/玛丽珍/复古气质/月销4500", "sales": "月销4500"}
    ],
    "春节穿搭核心：**喜庆但不大红大俗**，3 件套打造现代国风：\n\n## 🧧 完整方案\n\n| 单品 | 商品 | 价格 |\n|---|---|---|\n| 外套 | **改良汉元素暗红大衣** | ¥599 |\n| 内搭 | 奶白针织高领毛衣 | ¥199 |\n| 鞋子 | 黑色中跟玛丽珍 | ¥299 |\n| **合计** | | **¥1097** |\n\n## 🎨 配色公式\n\n**暗红大衣 + 奶白内搭 + 黑色鞋子 = 现代改良国风**\n\n### 为什么选暗红不选大红\n- 大红过于鲜艳显俗气\n- **暗红（酒红/深红）**：喜庆+高级感双赢\n- 改良汉元素的盘扣/对襟细节：**有文化底蕴不显土**\n\n### 奶白内搭的作用\n- 和暗红形成**暖色对比**而不是撞色\n- 高领修身+大衣外套=**显颈长显瘦**\n\n## 💡 拜年场合特殊提醒\n\n- 如果走亲戚多**建议穿平底或低跟**（走路多）\n- 大衣里备**口袋**（发红包/收红包频繁）\n- **配红色腰带**（束腰更显气质，加 ¥50）\n\n## ⚠️ 春节穿搭禁忌\n\n- ❌ 黑色为主（有些老人忌讳）\n- ❌ 全白（不吉利观念）\n- ❌ 过于休闲（拜年有仪式感要求）",
    ["改良汉元素暗红大衣双面呢+月销2200，喜庆高级感现代国风外套", "奶白高领针织毛衣+内搭大衣完美+月销1.5万，暖色对比显颈长显瘦", "黑色中跟玛丽珍+复古气质+月销4500，暗红大衣完美配色"]
))

# 6. matching - 咖啡店风格家居
T.append(make_traj(
    "sft_match_060", "matching_purchase", "搭配购物",
    "日系简约卫浴整体搭配",
    "卫生间想换成日系简约风，配洗手台+镜柜+毛巾架+置物架",
    {"query": "日系简约卫浴 洗手台+镜柜+毛巾架", "filters": {"style": "japanese_minimalist_bathroom"}},
    [
        {"product_id": "mock_jp_bath_1", "title": "九牧 日系简约浴室柜 原木色 80cm", "price": 1699, "is_platform_self": True, "rating": 4.9, "key_specs": "原木色/80cm/含陶瓷台盆/日系简约", "sales": "月销1500"},
        {"product_id": "mock_jp_bath_2", "title": "智能镜柜 带触控灯 防雾 60cm", "price": 699, "is_platform_self": True, "rating": 4.9, "key_specs": "智能触控灯/防雾/60cm/收纳+镜子二合一", "sales": "月销2200"},
        {"product_id": "mock_jp_bath_3", "title": "太空铝毛巾架 日式原木 双层", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "太空铝+原木/双层/日式风格/月销4500", "sales": "月销4500"},
        {"product_id": "mock_jp_bath_4", "title": "竹木置物架 卫生间 三层 防水", "price": 159, "is_platform_self": True, "rating": 4.8, "key_specs": "竹木材质/三层防水/收纳洗漱用品", "sales": "月销2500"}
    ],
    "日系简约卫浴 4 件套 ¥2756，**温暖清爽「无印良品风」**：\n\n## 🛁 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 🥇 浴室柜 | 九牧原木色 80cm | ¥1699 |\n| 镜柜 | 智能触控防雾 60cm | ¥699 |\n| 毛巾架 | 太空铝+原木双层 | ¥199 |\n| 置物架 | 竹木三层防水 | ¥159 |\n\n## 🎨 日系简约配色公式\n\n**原木色 + 白色 + 竹木** = 日系温暖简约\n\n### 绝对禁止\n- ❌ 大量黑色金属（偏工业风）\n- ❌ 花纹/印花（破坏简约感）\n- ❌ 超过 3 种颜色\n\n### 日系细节\n- **原木纹**是日系灵魂（哪怕是仿木也要有木纹）\n- 毛巾叠**同色系**整齐挂放\n- 台面**保持空旷**（不放超过 3 件东西）\n\n## 💡 智能镜柜的价值\n\n镜柜替代镜子+收纳盒两件：\n- 触控灯化妆补光\n- 防雾（洗澡后不用擦镜子）\n- 柜内收纳药品/护肤品\n- **¥699 实际是 ¥999 价值**\n\n## 💎 加 ¥500 完成度最高\n\n- 日式竹制牙刷杯 ¥39\n- 白色硅藻泥地垫 ¥89\n- 香薰蜡烛（木质调）¥150\n- 绿植（绿萝/吊兰）¥39",
    ["九牧日系简约浴室柜原木色80cm+含陶瓷台盆+月销1500，卫浴日系风核心", "智能镜柜触控灯防雾60cm+月销2200，镜子+收纳+补光三合一", "太空铝+原木双层毛巾架+月销4500，日式细节统一风格", "竹木三层置物架防水+月销2500，洗漱用品收纳日式材质"]
))

# 7. bundle - 新生活
T.append(make_traj(
    "sft_bundle_057", "bundle_purchase", "组合购物",
    "3000 元独居青年厨房首配",
    "第一次独居，3000 配齐一个人的厨房基础",
    {"query": "独居青年厨房首配 一人食 炒锅+电饭煲+冰箱+刀具", "max_price": 3200},
    [
        {"product_id": "mock_single_1", "title": "海尔 BCD-170TMPT 双门小冰箱 170L", "price": 999, "is_platform_self": True, "rating": 4.9, "key_specs": "170L/双门/一人份刚好/省电一级", "sales": "月销3.5万"},
        {"product_id": "mock_single_2", "title": "美的 3L 迷你电饭煲 一人食专用", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "3L/1-2人量/IH加热/月销3万", "sales": "月销3万"},
        {"product_id": "mock_single_3", "title": "苏泊尔 28cm 不粘炒锅 一人食版", "price": 159, "is_platform_self": True, "rating": 4.9, "key_specs": "28cm一人食/不粘/轻量/月销4.5万", "sales": "月销4.5万"},
        {"product_id": "mock_single_4", "title": "双立人 Now S 3件套 主厨刀+刀架", "price": 499, "is_platform_self": True, "rating": 4.9, "key_specs": "德国双立人/含主厨刀+水果刀+刀架", "sales": "月销2200"},
        {"product_id": "mock_single_5", "title": "美的 小型微波炉 700W 20L 平板", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "700W/20L平板/热菜热饭/一人份", "sales": "月销2.8万"}
    ],
    "独居青年厨房 5 件套 ¥2155，余 ¥845：\n\n## 🍳 完整方案\n\n| 家电 | 商品 | 价格 | 频率 |\n|---|---|---|---|\n| 🥇 冰箱 | 海尔 170L 双门小冰箱 | ¥999 | 每天 |\n| 微波炉 | 美的 20L 平板 | ¥299 | 每天（最高频）|\n| 电饭煲 | 美的 3L 一人食 | ¥199 | 每天 |\n| 炒锅 | 苏泊尔 28cm 不粘 | ¥159 | 4-5 次/周 |\n| 刀具 | 双立人 3 件套 | ¥499 | 每次做饭 |\n\n## 💡 独居厨房的优先级\n\n**最高频**：微波炉（热外卖/热剩饭）> 冰箱（存储）> 电饭煲（煮饭）> 炒锅（炒菜）\n\n### 为什么微波炉排这么高\n独居青年**外卖和剩菜率高**，微波炉使用频率可能比炒锅高——先买微波炉比先买豪华炒锅更务实。\n\n## 💰 余 ¥845 加\n\n**油盐酱醋+调料**：¥200-300（起步口味够）\n\n**锅具补充**（按需）：\n- 汤锅 ¥80（煮面/汤）\n- 煎锅 ¥100（煎蛋/牛排）\n\n**厨房收纳**：¥100\n\n## ⚠️ 独居厨房买小件而非大件\n\n- 冰箱选 170L 不选 300L（一个人 170L 绰绰有余）\n- 电饭煲选 3L 不选 5L（3L 可以煮 1-2 人量）\n- 炒锅选 28cm 不选 36cm（小锅刷洗容易）",
    ["海尔170L双门小冰箱+一级能效+月销3.5万，独居1-2人量刚好不浪费", "美的20L微波炉平板+月销2.8万，独居最高频热外卖热剩饭", "美的3L一人食电饭煲IH+月销3万，小锅快熟1-2人量精准", "苏泊尔28cm不粘炒锅轻量+月销4.5万，小锅好刷好收纳", "双立人Now S 3件套含刀架+月销2200，独居厨房刀具入门德国品质"]
))

# 8. bundle
T.append(make_traj(
    "sft_bundle_058", "bundle_purchase", "组合购物",
    "6000 元新婚礼品清单（长辈送）",
    "侄子结婚，6000 预算准备婚礼礼物，实用耐用的",
    {"query": "结婚礼物 长辈送 实用耐用 6000预算", "max_price": 6500},
    [
        {"product_id": "mock_wedding_gift_1", "title": "九阳 美食料理机 全能款 婚礼礼物", "price": 1299, "is_platform_self": True, "rating": 4.9, "key_specs": "9合1多功能/搅打煮打一体/婚礼实用礼", "sales": "月销1500"},
        {"product_id": "mock_wedding_gift_2", "title": "松下 净化加湿器 婚房专用 智能款", "price": 1599, "is_platform_self": True, "rating": 4.9, "key_specs": "净化+加湿二合一/婚房刚需/智能控制", "sales": "月销850"},
        {"product_id": "mock_wedding_gift_3", "title": "WMF 福腾宝 不锈钢锅具 6件套", "price": 1499, "is_platform_self": True, "rating": 4.9, "key_specs": "德国福腾宝/6件套/炒锅+汤锅+奶锅", "sales": "月销780"},
        {"product_id": "mock_wedding_gift_4", "title": "九牧 智能马桶盖 自动冲洗 暖座", "price": 899, "is_platform_self": True, "rating": 4.9, "key_specs": "智能冲洗/暖座/婚房升级必备", "sales": "月销4500"}
    ],
    "长辈送结婚礼物 4 件套 ¥5296，**实用+显档次**：\n\n## 🎊 完整方案（¥5296）\n\n| 礼物 | 商品 | 价格 |\n|---|---|---|\n| 🥇 智能马桶盖 | 九牧智能暖座 | ¥899 |\n| 净化加湿器 | 松下婚房专用 | ¥1599 |\n| 锅具套装 | 德国福腾宝 6 件 | ¥1499 |\n| 料理机 | 九阳 9 合 1 | ¥1299 |\n\n## 💡 长辈送婚礼礼物原则\n\n**实用 > 颜值 > 贵重感**\n\n最受年轻夫妻欢迎的婚礼礼物是：\n- **每天都用得到的（排名靠前）**：智能马桶盖、净化器、锅具\n- **新家必备**：净化加湿器（新装修甲醛+空气干燥）\n\n## 💡 为什么选这 4 件\n\n### 智能马桶盖 ¥899（必须包含）\n年轻夫妻最爱，**自己不舍得买、长辈送最合适**。使用频率高，每天感受长辈的心意。\n\n### 德国福腾宝锅具 ¥1499\n德国品牌，**用 20 年不换**，体现长辈对小家庭的重视。比买便宜锅强 10 倍（贵的不只是品牌）。\n\n## ⚠️ 婚礼礼物禁忌\n\n- ❌ 送钟（谐音不好）\n- ❌ 送伞（谐音「散」）\n- ❌ 送刀（有分割之意，除非你知道他们真需要）\n- ❌ 送梨（谐音「离」）\n- ✅ 送**成双成对的**（两个杯子、两套餐具更有心意）",
    ["九牧智能马桶盖+暖座自动冲洗+月销4500，年轻夫妻最爱自己不舍得买", "松下净化加湿器二合一+月销850，婚房新装修必备净化+加湿", "德国福腾宝锅具6件套+月销780，用20年不换体现长辈对小家重视", "九阳9合1料理机+月销1500，婚房厨房全能得力助手"]
))

# 9. place_order
T.append(make_traj(
    "sft_order_031", "place_order", "购物下单",
    "亲子课程/服务预约下单",
    "给孩子买个绘画兴趣课，选了那个 20 节课包，帮我下单",
    {"product_id": "mock_art_course", "quantity": 1, "address": "DEFAULT", "type": "service_booking"},
    [
        {"product_id": "mock_art_course", "title": "童画艺术 儿童绘画兴趣课 20节 5-10岁 线上", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "订单[TRACKING_ID]-ART-2284/20节在线直播/发课表+微信群/5-10岁适合", "sales": "—"}
    ],
    "✅ 绘画兴趣课已下单！\n\n## 📚 订单详情\n\n- **课程**：童画艺术儿童绘画兴趣课（5-10 岁）\n- **数量**：20 节课包\n- **价格**：¥599\n- **订单号**：[TRACKING_ID]-ART-2284\n- **形式**：线上直播课\n\n## 📋 下单后接下来的步骤\n\n### 1. 收到课程信息\n付款后 30 分钟内，**商家会通过微信联系你**：\n- 发送课程安排表\n- 邀请进入学员微信群\n- 确认孩子年龄和绘画基础\n\n### 2. 首课前准备\n**需要自备材料**（通常在群里告知）：\n- 素描本（A4/A3 各 1 本）约 ¥15\n- HB/2B 铅笔各 2 支 约 ¥5\n- 彩铅/水彩一套 约 ¥30-80\n- 橡皮、尺子各 1 个\n\n**合计 ¥50-100**，买基础款就好，别急着买贵的（先看孩子兴趣）。\n\n### 3. 上课准备\n- **固定上课时间**：让孩子养成规律\n- **家长陪 1-2 节**：了解教学方式\n- **课后作品拍照保存**：记录成长\n\n## 💡 兴趣课报名建议\n\n### 先报 5-10 节「试课包」再决定\n如果课程提供试课包（¥150-200），**先试再报 20 节**更稳妥。不过你已经下单了，7 天内如果觉得不合适可以申请退款（课程类通常有 7 天退款条款）。\n\n### 好的绘画课评判标准\n- ✅ 每节课有作品完成（不是只听讲）\n- ✅ 老师有互动点评\n- ✅ 课后发作品反馈\n- ❌ 全程录播不互动\n- ❌ 每节课都在临摹同款图\n\n希望孩子喜欢！🎨",
    ["童画艺术20节绘画课包+线上直播+5-10岁+订单[TRACKING_ID]-ART-2284，课程已下单"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase
T.append(make_traj(
    "sft_repurchase_029", "repurchase", "复购召回",
    "复购运动营养品+进阶建议",
    "蛋白粉快没了，再买一袋，用了 3 个月了效果怎么样提升",
    {"category_keyword": "蛋白粉", "time_range": "last_4_months", "include_progress_advice": True},
    [
        {"product_id": "mock_protein_repeat", "title": "MyProtein 乳清蛋白 1kg 巧克力 (3月前购买)", "price": 269, "is_platform_self": True, "rating": 4.9, "key_specs": "你3月前购买/订单[ORDER_ID]/约33份", "sales": "月销1.8万"},
        {"product_id": "mock_protein_creatine", "title": "肌酸 微粉化 300g 力量提升", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "微粉化肌酸/增加力量/3g/日/进阶必备", "sales": "月销1.2万"},
        {"product_id": "mock_protein_complex", "title": "复合蛋白粉 乳清+酪蛋白 缓释款 1kg", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "双蛋白/睡前缓释/增肌期升级/月销5500", "sales": "月销5500"}
    ],
    "你 3 个月前买的 **MyProtein 乳清蛋白 ¥269**，坚持 3 个月了，给一些进阶建议：\n\n## 💪 3 个月的进度节点\n\n**如果你是从零开始训练**：\n- 肌肉增加约 1-2kg（新手效应）\n- 力量应该有明显提升（深蹲/卧推重量增加）\n- 体脂可能略有下降（取决于饮食）\n\n**如果进步不明显**，先检查：\n- 训练强度够吗（每组要力竭感）\n- 总蛋白质摄入够吗（体重 × 1.6g/kg）\n- 睡眠够 7 小时吗\n\n## 🛒 继续买 vs 升级\n\n### 选项 A：继续买同款 ¥269 ✅\n- **3 个月证明没有过敏/不耐受**\n- 同款不需要适应期\n- **直接复购最稳妥**\n\n### 选项 B：加购肌酸 ¥89（进阶）⭐\n**肌酸是训练 3 个月以上才建议加的**：\n- 增加磷酸肌酸储备\n- **深蹲/卧推重量提升 5-10%**\n- 每日 3g 混入蛋白粉一起喝\n- 月销 1.2 万件，效果有充分临床证据\n\n### 选项 C：换复合蛋白粉 ¥299\n乳清+酪蛋白双蛋白：\n- 酪蛋白**缓释 6-8 小时**\n- 睡前喝防止睡眠中肌肉分解\n- 适合**增肌期强化**\n\n## 🎯 我的建议\n\n**同款复购 + 加购肌酸** = ¥269 + ¥89 = **¥358**\n\n这是**3 个月后最有效的升级组合**：蛋白粉保证肌肉修复，肌酸提升训练强度上限。\n\n要帮你下单两件吗？",
    ["MyProtein乳清蛋白1kg你3月前购买+已证明无过敏，继续复购最稳妥", "微粉化肌酸300g+力量提升5-10%+月销1.2万，训练3个月后进阶必备", "复合蛋白粉双蛋白缓释+月销5500，睡前喝增肌期强化升级"],
    tool_name="SkuRepurchaseRecall"
))

print(f"准备追加 {len(T)} 条")
with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
    for t in T:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")
print(f"✅ 已追加 {len(T)} 条")
with open(OUTPUT_PATH) as f:
    total = sum(1 for _ in f)
print(f"   总条数: {total}")
