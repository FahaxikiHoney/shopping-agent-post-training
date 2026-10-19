# -*- coding: utf-8 -*-
"""Step 30: 第 18 批 10 条"""
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

# 1. similar_rec - 抱怨冬天不够暖
T.append(make_traj(
    "sft_simrec_047", "similar_rec", "相似品推荐",
    "抱怨保暖性不足 → 推荐更厚/更暖款",
    "之前买的那件羽绒服北京冬天穿明显不够暖，要更厚的同价位款",
    {"query": "羽绒服 90白鸭绒 充绒量500g+ 防寒", "min_price": 800, "max_price": 1500, "filters": {"fill_power_min": 700, "down_content_min": 90}},
    [
        {"product_id": "mock_down_1", "title": "波司登 90白鸭绒 充绒量 580g 长款", "price": 1299, "is_platform_self": True, "rating": 4.9, "key_specs": "90白鸭绒/充绒580g/长款过膝/-30℃防寒", "sales": "月销1.2万"},
        {"product_id": "mock_down_2", "title": "鸭鸭 三防 90白鸭绒 充绒520g 中长款", "price": 899, "is_platform_self": True, "rating": 4.8, "key_specs": "90白鸭绒/充绒520g/防风防水防钻绒", "sales": "月销2.5万"},
        {"product_id": "mock_down_3", "title": "高梵 黑金鹅绒 充绒量600g 大衣款", "price": 1499, "is_platform_self": True, "rating": 4.9, "key_specs": "90%鹅绒/充绒600g/宽松大衣/最保暖", "sales": "月销850"}
    ],
    "北京冬天需要**充绒量 500g+ 且 90% 以上白鸭绒**才够暖，3 款都达标：\n\n**1. 鸭鸭三防 ¥899** ⭐ 性价比首选\n充绒 520g+90% 白鸭绒，**三防（防风/防水/防钻绒）**是真正的户外抗冻。月销 2.5 万件断档。\n\n**2. 波司登 ¥1299** 经典大牌\n充绒 580g+长款过膝，**-30℃ 防寒测试通过**。长款挡风腿部保暖好。\n\n**3. 高梵鹅绒 ¥1499** 保暖天花板\n鹅绒比鸭绒保暖性高 15%，充绒 600g，**极寒党首选**。\n\n## 💡 选购关键\n\n不要只看「含绒量 90%」，**充绒量才是决定暖度的核心**：\n- 300g 以下：0℃ 以上\n- 400-500g：-10℃\n- 520g+：**-20℃ 北京冬天** ✅\n- 600g+：-30℃ 哈尔滨",
    ["鸭鸭三防90白鸭绒+充绒520g+月销2.5万，北京-20℃性价比首选", "波司登90白鸭绒+充绒580g+长款过膝+月销1.2万，大牌-30℃防寒长款", "高梵90%鹅绒+充绒600g+宽松大衣+月销850，极寒保暖天花板"]
))

# 2. similar_rec - 抱怨防水不好
T.append(make_traj(
    "sft_simrec_048", "similar_rec", "相似品推荐",
    "抱怨防水差 → 推荐高防水等级款",
    "上次买的运动鞋雨天进水了，要防水好的同价位跑步鞋",
    {"query": "防水跑步鞋 GTX 防水膜 男", "max_price": 800, "filters": {"waterproof": "GTX_or_high_level"}},
    [
        {"product_id": "mock_run_wp_1", "title": "萨洛蒙 XA PRO GTX 防水越野跑鞋", "price": 799, "is_platform_self": True, "rating": 4.9, "key_specs": "GTX防水/户外越野/防滑大底/雨天泥地专用", "sales": "月销2200"},
        {"product_id": "mock_run_wp_2", "title": "亚瑟士 Gel-Nimbus GTX 防水版", "price": 749, "is_platform_self": True, "rating": 4.9, "key_specs": "GORE-TEX防水+ASICS减震/城市雨天跑步", "sales": "月销1500"},
        {"product_id": "mock_run_wp_3", "title": "New Balance 880 GTX 防水减震", "price": 699, "is_platform_self": True, "rating": 4.8, "key_specs": "GTX防水/减震/城市通勤跑步", "sales": "月销1200"}
    ],
    "普通跑步鞋防水是「泼水处理」（10 分钟进水），**GTX（GORE-TEX）防水是真正的防水**（雨天跑 2 小时不进水）。3 款：\n\n**1. 亚瑟士 GTX 防水 ¥749** ⭐ 城市跑步首选\n亚瑟士减震+GORE-TEX 防水，**城市雨天路面跑步最均衡**。\n\n**2. New Balance 880 GTX ¥699** 最便宜\nNB 经典款+GTX 防水，是 3 款里**最便宜**的正宗 GTX 防水鞋。\n\n**3. 萨洛蒙 XA PRO GTX ¥799** 户外越野首选\n**越野大底+GTX**，雨天泥地防滑最强，但偏硬不适合纯城市路面跑步。\n\n## 💡 选哪个\n- **城市路面**跑步 → 亚瑟士或 NB 都行\n- **户外越野/泥泞路**跑 → 萨洛蒙\n- **最省钱** → NB 880 GTX ¥699",
    ["萨洛蒙XA PRO GTX防水+越野大底防滑+月销2200，户外越野泥地专用", "亚瑟士Gel-Nimbus GTX防水+ASICS减震+月销1500，城市雨天跑步最均衡", "New Balance 880 GTX防水+月销1200，城市跑步最便宜的GTX防水"]
))

# 3. sku_comp - 不同容量版本
T.append(make_traj(
    "sft_skucomp_045", "sku_comp", "商品对比",
    "不同容量版本对比（手机 256G vs 512G vs 1T）",
    "iPhone 15 Pro Max 买 256G 够不够，还是直接上 512G",
    {"skus": ["iPhone 15 Pro Max 256G", "iPhone 15 Pro Max 512G", "iPhone 15 Pro Max 1T"], "mode": "storage_comparison"},
    [
        {"product_id": "mock_ipm_256", "title": "iPhone 15 Pro Max 256G 钛金属", "price": 9999, "is_platform_self": True, "rating": 4.9, "key_specs": "256G基础款/日常够用/月销4500", "sales": "月销4500"},
        {"product_id": "mock_ipm_512", "title": "iPhone 15 Pro Max 512G 钛金属", "price": 11499, "is_platform_self": True, "rating": 4.9, "key_specs": "512G甜点档/单GB价最低/月销2200", "sales": "月销2200"},
        {"product_id": "mock_ipm_1t", "title": "iPhone 15 Pro Max 1T 钛金属", "price": 13999, "is_platform_self": True, "rating": 4.9, "key_specs": "1T顶配/4K ProRes视频党/月销680", "sales": "月销680"}
    ],
    "**结论：512G 是甜点档，¥1500 差价最值**。\n\n## 📊 三档对比\n\n| 配置 | 价格 | 单 GB 价 | 月销 |\n|---|---|---|---|\n| 256G | ¥9999 | ¥39 | **4500** |\n| **512G** | **¥11499** | **¥22** ⭐ | 2200 |\n| 1T | ¥13999 | ¥14 | 680 |\n\n## 💰 256G 真实可用空间\n\niPhone 15 Pro Max 256G 实际可用约 **230G**：\n- iOS 系统 + 预装 App：约 20G\n- 微信+抖音+常用 App：约 30G\n- 照片（10 万张）：约 50G\n- **剩余约 130G**\n\n**130G 够用吗？**\n- 普通用户：够用 2-3 年\n- 爱拍 4K 视频：**1 分钟 4K ProRes ≈ 1.7G，130G 约 77 分钟满**\n- 爱拍延时/Log：必须 512G+\n\n## 🎯 怎么选\n\n- **日常拍照+偶尔视频** → 256G ¥9999（省 ¥1500）\n- **爱拍 4K + 不想清理手机** → **512G ¥11499** ⭐\n- **专业拍摄/ProRes** → 1T ¥13999\n\n**为什么 512G 是甜点**：¥1500 价差让单 GB 成本从 ¥39 降到 ¥22，性价比最高。",
    ["iPhone 15 Pro Max 256G+实际230G+月销4500，日常拍照普通用户够用", "iPhone 15 Pro Max 512G+单GB价最低¥22+月销2200，爱拍视频性价比甜点档", "iPhone 15 Pro Max 1T+4K ProRes专业拍摄+月销680，专业摄影/创作者顶配"]
))

# 4. sku_comp - 形态对比
T.append(make_traj(
    "sft_skucomp_046", "sku_comp", "商品对比",
    "热水器三种形态对比（燃气/电热/热泵）",
    "装修选热水器，燃气热水器/电热水器/热泵热水器怎么选",
    {"categories": ["燃气热水器", "电热水器", "热泵热水器"], "topk_per_category": 1},
    [
        {"product_id": "mock_hw_gas", "title": "海尔 JSQ30-16WT5 燃气热水器 16升", "price": 1899, "is_platform_self": True, "rating": 4.9, "key_specs": "16升/即热式/恒温/适合2-4口家庭", "sales": "月销1.5万"},
        {"product_id": "mock_hw_elec", "title": "美的 F8015-HD3 电热水器 80L", "price": 1599, "is_platform_self": True, "rating": 4.9, "key_specs": "80L大容量/储热式/安全防漏/月销2万", "sales": "月销2万"},
        {"product_id": "mock_hw_pump", "title": "美的 热泵热水器 200L 空气能", "price": 5999, "is_platform_self": True, "rating": 4.9, "key_specs": "200L/热泵/用电量仅1/4电热水器/10年回本", "sales": "月销3500"}
    ],
    "三种热水器**本质是场景和使用成本选择**：\n\n## 📊 核心对比\n\n| 类型 | 代表 | 价格 | 适用场景 | 每次洗澡成本 |\n|---|---|---|---|---|\n| 燃气 | 海尔 16L | ¥1899 | **城市普通家庭** | ¥0.5（燃气）|\n| 电热 | 美的 80L | ¥1599 | **农村/无燃气** | ¥1.5（电）|\n| 热泵 | 美的 200L | ¥5999 | **大家庭/农村/别墅** | ¥0.3（最省）|\n\n## 🎯 怎么选\n\n### 城市有天然气 → 燃气热水器 ¥1899\n- 即热式（开即有热水，不用等）\n- 16L 满足 2-4 人家庭\n- **80% 城市家庭选择**\n\n### 农村/无燃气 → 电热水器 ¥1599\n- 储热式 80L（够 2-3 个人洗）\n- 安装简单\n- 缺点：预热需要 45 分钟\n\n### 大家庭/别墅 → 热泵热水器 ¥5999\n- 200L 够 5-6 人洗澡\n- 热泵原理：**1 度电当 3 度用**\n- 贵 ¥4400 但 10 年省电钱 ¥6000+\n- **农村大家庭/别墅长期住划算**\n\n## ⚠️ 燃气热水器注意\n\n- 必须安装在**通风处**（浴室外）\n- **每年检测燃气管道**\n- 选 16L 以上（10L 冬天水压低时不够用）",
    ["海尔16L燃气热水器+即热式恒温+月销1.5万，城市有天然气80%家庭首选", "美的80L电热水器+储热式+月销2万，农村无燃气家庭首选", "美的热泵200L空气能+用电量1/4+月销3500，大家庭/别墅10年省电划算"]
))

# 5. matching - 卧室软装升级
T.append(make_traj(
    "sft_match_045", "matching_purchase", "搭配购物",
    "书房整体软装搭配",
    "家里书房想升级，配什么书架+台灯+地毯+装饰",
    {"query": "书房软装搭配 书架+台灯+地毯", "filters": {"style": "study_room_aesthetic"}},
    [
        {"product_id": "mock_study_1", "title": "源氏木语 实木书架 胡桃色 6层 含柜", "price": 1899, "is_platform_self": True, "rating": 4.9, "key_specs": "实木胡桃色/6层含柜/书房专用", "sales": "月销680"},
        {"product_id": "mock_study_2", "title": "明基 ScreenBar 屏幕挂灯 书桌专用", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "屏幕挂灯/护眼/无极调光/月销3500", "sales": "月销3500"},
        {"product_id": "mock_study_3", "title": "MUJI 几何羊毛地毯 灰色 140×200", "price": 899, "is_platform_self": True, "rating": 4.9, "key_specs": "MUJI羊毛/几何图案/灰色/140×200", "sales": "月销520"},
        {"product_id": "mock_study_4", "title": "书房装饰画 黑白线条 40×60 组合3幅", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "黑白线条/3幅组合/书房极简风", "sales": "月销2200"}
    ],
    "书房软装 4 件套 ¥3296，**读书工作的精神角落**：\n\n## 📚 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 书架 | **实木胡桃色 6 层含柜** | ¥1899 |\n| 台灯 | 明基 ScreenBar 屏幕挂灯 | ¥299 |\n| 地毯 | MUJI 几何羊毛灰色 | ¥899 |\n| 装饰画 | 黑白线条 3 幅组合 | ¥199 |\n\n## 🎨 书房配色逻辑\n\n**胡桃木书架 + 灰色地毯 + 黑白装饰画** = 沉稳学者风\n- 胡桃木（暖）+ 灰色（冷）形成温度层次\n- 黑白画（焦点）让书房不死板\n- 避免过多颜色（书房要专注）\n\n## 💡 选品理由\n\n### 屏幕挂灯 ¥299 不买台灯\n书房一般有显示器，**屏幕挂灯比台灯更护眼**（不会产生屏幕反光），¥299 是书房护眼性价比天花板。\n\n### MUJI 羊毛地毯\n书房地毯核心功能：**隔音+脚感温暖**。木地板踩上去咚咚响影响下层邻居，铺地毯完美解决。\n\n## 💎 进阶装饰\n- 桌面植物（绿萝/多肉）¥50-100\n- 书立 ¥80\n- 香薰 ¥150（雪松/乳香助集中）",
    ["源氏木语实木胡桃书架6层含柜+月销680，书房核心家具10年不淘汰", "明基ScreenBar屏幕挂灯+护眼无极调光+月销3500，显示器搭配护眼天花板", "MUJI几何羊毛地毯灰色140×200+月销520，书房隔音+脚感温暖", "黑白线条装饰画3幅组合+月销2200，书房极简风视觉焦点"]
))

# 6. matching - 健康饮食整套
T.append(make_traj(
    "sft_match_046", "matching_purchase", "搭配购物",
    "减肥健康饮食整套厨房工具",
    "想开始健康饮食减肥，配齐食物秤+蒸锅+榨汁+便当盒",
    {"query": "健康饮食减肥工具 食物秤+蒸锅+榨汁机+便当盒", "filters": {"category": "healthy_eating"}},
    [
        {"product_id": "mock_diet_1", "title": "膳魔师 食物秤 精准 1g 厨房秤", "price": 79, "is_platform_self": True, "rating": 4.9, "key_specs": "1g精度/食物秤/减脂热量计算必备", "sales": "月销2.5万"},
        {"product_id": "mock_diet_2", "title": "苏泊尔 三层蒸锅 304不锈钢 24cm", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "三层304不锈钢/24cm/蒸菜蒸饭/低脂烹饪", "sales": "月销3.5万"},
        {"product_id": "mock_diet_3", "title": "美的 MJ-WBL2531 便携榨汁机", "price": 129, "is_platform_self": True, "rating": 4.8, "key_specs": "便携随行/USB充电/300ml杯/带走喝", "sales": "月销1.8万"},
        {"product_id": "mock_diet_4", "title": "乐扣乐扣 分格便当盒 1L 密封", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "分格1L/密封/微波可用/减肥控量必备", "sales": "月销2.2万"}
    ],
    "减肥健康饮食 4 件套 ¥496，**告别盲目节食，科学减脂**：\n\n## 🥗 完整方案\n\n| 工具 | 商品 | 价格 | 作用 |\n|---|---|---|---|\n| 食物秤 | **膳魔师 1g 精度** | ¥79 | 精确计算热量 |\n| 蒸锅 | 苏泊尔三层蒸锅 | ¥199 | 零油脂健康烹饪 |\n| 榨汁机 | 美的便携 USB | ¥129 | 代替含糖饮料 |\n| 便当盒 | 乐扣乐扣分格 | ¥89 | 控制食物比例 |\n\n## 💡 每件工具解决的核心问题\n\n### 食物秤 ¥79\n**你以为的一拳米饭 = 其实两拳米饭**。精准称量后很多人发现每餐多吃了 200-300 卡。\n\n### 蒸锅 ¥199\n减脂的核心不是少吃，是**少油**。蒸菜蒸鱼比炒同等食物少 80% 脂肪摄入。\n\n### 便当盒分格 ¥89\n分格设计按「**1/2 蔬菜 + 1/4 蛋白质 + 1/4 主食**」的减脂黄金比例装，不用计算直接控量。\n\n## 💎 配合使用 SOP\n\n```\n早上备餐：\n1. 食物秤称米/鸡胸/蔬菜\n2. 蒸锅蒸好\n3. 分格便当盒装好\n4. 出门前榨一杯果蔬汁（代替奶茶）\n```\n\n一套流程 **30 分钟搞定全天午餐+下午加餐**。",
    ["膳魔师食物秤1g精度+月销2.5万，减脂热量计算精准必备", "苏泊尔三层蒸锅304不锈钢+月销3.5万，零油脂健康烹饪", "美的便携榨汁机USB充电+月销1.8万，代替含糖饮料随身带走", "乐扣乐扣分格便当盒+密封+月销2.2万，黄金比例控量减脂必备"]
))

# 7. bundle - 6000 游戏主机
T.append(make_traj(
    "sft_bundle_043", "bundle_purchase", "组合购物",
    "4000 元家庭游戏主机套装（PS5+显示器+音响）",
    "想配一套家庭游戏主机，4000 预算 PS5+显示器+游戏椅",
    {"query": "PS5游戏主机套装 显示器+椅子", "max_price": 4500},
    [
        {"product_id": "mock_ps5_dig", "title": "PlayStation 5 数字版", "price": 2399, "is_platform_self": True, "rating": 4.9, "key_specs": "PS5数字版/4K120Hz/独占大作多/月销4500", "sales": "月销4500"},
        {"product_id": "mock_ps5_mon", "title": "LG 27GP850 27寸 游戏显示器 2K 144Hz", "price": 1599, "is_platform_self": True, "rating": 4.9, "key_specs": "27寸2K/144Hz/1ms/PS5专用HDMI 2.1", "sales": "月销2500"},
        {"product_id": "mock_ps5_chair", "title": "DXRacer 电竞椅 人体工学 3小时不累", "price": 1299, "is_platform_self": True, "rating": 4.8, "key_specs": "电竞椅/腰靠颈靠/长时间游戏不酸", "sales": "月销1200"},
        {"product_id": "mock_ps5_game", "title": "战神: 诸神黄昏 PS5 实体卡带", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "PS5独占/年度最佳/必入首发游戏", "sales": "月销2200"}
    ],
    "PS5 家庭游戏套装 4 件 ¥5596，**超 ¥1596 建议取舍**：\n\n## 🎮 完整配置\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 主机 | **PS5 数字版** | ¥2399 |\n| 显示器 | LG 27GP850 2K 144Hz | ¥1599 |\n| 椅子 | DXRacer 电竞椅 | ¥1299 |\n| 游戏 | 战神: 诸神黄昏 | ¥299 |\n\n## 🎯 4000 预算怎么取舍\n\n### 方案 A：主机 + 显示器 ¥3998（推荐）\n**PS5 ¥2399 + LG 2K 显示器 ¥1599 = ¥3998**\n- 主机+显示器是核心组合\n- 椅子/游戏后期再加\n- **刚好不超预算**\n\n### 方案 B：主机 + 电竞椅 ¥3698\n- 用电视当显示器\n- 先享受舒适坐姿\n- 之后再买显示器\n\n## 💡 为什么 PS5 数字版不买光驱版\n\n- 数字版 ¥2399 vs 光驱版 ¥3399（**贵 ¥1000**）\n- PS5 游戏**数字版价格经常打折**（PSN 黑卡 ¥300/年节省 30-50%）\n- 不玩二手盘就选数字版\n\n## 💎 显示器选 LG 27GP850 的原因\n\n- HDMI 2.1 接口（PS5 必须用 2.1 才能跑 4K/120Hz）\n- 144Hz 高刷对游戏流畅度**质感提升明显**\n- 普通 60Hz 电视和这个差距像「两个世界」",
    ["PS5数字版+4K120Hz+独占大作+月销4500，家庭游戏主机首选省1000", "LG 27GP850 2K 144Hz+HDMI 2.1+月销2500，PS5专用显示器", "DXRacer电竞椅+腰靠颈靠+月销1200，3小时游戏不腰酸", "战神诸神黄昏PS5实体卡带+年度最佳+月销2200，入手PS5必入首发游戏"]
))

# 8. bundle - 学生
T.append(make_traj(
    "sft_bundle_044", "bundle_purchase", "组合购物",
    "3000 元新婚家庭厨房起步套装",
    "刚结婚搬新家，厨房一切从零开始，3000 配齐基础厨房家电",
    {"query": "新婚厨房家电起步 冰箱+微波炉+烤箱", "max_price": 3200},
    [
        {"product_id": "mock_kitchen_1", "title": "海尔 BCD-216WMPT 双门冰箱 216L", "price": 1499, "is_platform_self": True, "rating": 4.9, "key_specs": "216L双门/家用起步款/节能一级/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "mock_kitchen_2", "title": "美的 PG23K1 微波炉 23L 平板", "price": 469, "is_platform_self": True, "rating": 4.9, "key_specs": "23L平板/免转盘/1分钟热饭/月销1.8万", "sales": "月销1.8万"},
        {"product_id": "mock_kitchen_3", "title": "海氏 C40 电烤箱 40L 专业版", "price": 1199, "is_platform_self": True, "rating": 4.9, "key_specs": "40L独立控温/烤面包蛋糕/月销1.8万", "sales": "月销1.8万"},
        {"product_id": "mock_kitchen_4", "title": "苏泊尔 电水壶 1.7L 304不锈钢", "price": 159, "is_platform_self": True, "rating": 4.9, "key_specs": "1.7L/304不锈钢/快速沸腾/月销5万", "sales": "月销5万"}
    ],
    "新婚厨房基础家电 4 件套 ¥3326，**超 ¥326 建议取舍一件**：\n\n## 🍳 完整方案\n\n| 家电 | 商品 | 价格 | 使用频次 |\n|---|---|---|---|\n| 🥇 冰箱 | 海尔 216L 双门 | ¥1499 | 每天 |\n| 电水壶 | 苏泊尔 1.7L | ¥159 | 每天 |\n| 微波炉 | 美的 PG23K1 | ¥469 | 每天 |\n| 烤箱 | 海氏 C40 40L | ¥1199 | 每周 |\n\n## 🎯 压到 ¥3000 的方案\n\n**去掉烤箱**，总价 ¥2127：\n- 冰箱+电水壶+微波炉是**每日刚需**\n- 烤箱是**提升项**（想烤面包/蛋糕才需要）\n- 以后想烤了再单独买 ¥1199\n\n**或者换小冰箱**：\n- 把 216L 换 150L 小冰箱 ¥899，省 ¥600\n- 两口人 150L 也够\n\n## 💡 冰箱选 216L 而不是更大的理由\n\n新婚两口人，**216L 是最划算的双门冰箱**：\n- 够装 1 周食材\n- 不会因为存太多导致食材浪费\n- 价格是大冰箱的 1/3\n\n**等生了孩子再换大冰箱也不迟**（那时候也有钱了）。",
    ["海尔BCD-216L双门冰箱+一级能效+月销2.5万，两口人起步最划算", "苏泊尔1.7L电水壶304不锈钢+月销5万，新婚厨房最高频使用", "美的PG23K1微波炉23L平板+月销1.8万，日常热饭必备", "海氏C40烤箱40L独立控温+月销1.8万，想烤面包蛋糕可选提升项"]
))

# 9. place_order - 海鲜生鲜
T.append(make_traj(
    "sft_order_024", "place_order", "购物下单",
    "生鲜当日达下单",
    "帮我下单那箱大闸蟹，要今天到明天吃，可以当日达吗",
    {"product_id": "mock_crab_001", "same_day_delivery": True, "address": "DEFAULT"},
    [
        {"product_id": "mock_crab_001", "title": "阳澄湖大闸蟹 公4两母3两 6对 礼盒", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "订单[TRACKING_ID]-CRAB-2284/购物平台生鲜当日达/下午2点前下单今晚到/订单已确认", "sales": "—"}
    ],
    "✅ **下单成功！大闸蟹今晚就到！**\n\n## 📦 订单详情\n\n- **商品**：阳澄湖大闸蟹 公4两/母3两 6 对礼盒\n- **价格**：¥599\n- **订单号**：[TRACKING_ID]-CRAB-2284\n- **配送**：购物平台生鲜**当日达**\n- **预计**：**今晚 20:00 前送达**\n\n## 🦀 大闸蟹收货后操作\n\n### 收到立刻\n1. **不要放冰箱**（低温会让螃蟹死亡，死蟹不能吃）\n2. 放通风阴凉处，或放水盆盖湿毛巾\n3. **当天吃完最佳**\n\n### 蒸螃蟹 SOP\n1. 冷水入锅（不要提前解绳子）\n2. 水开后蒸 **12-15 分钟**（公蟹 15 分钟，母蟹 12 分钟）\n3. 配姜末+黄酒+香醋蘸食\n\n### 怎么判断熟没熟\n- 蟹壳变**橘红色**\n- 蟹脚可以轻松掰开\n\n## ⚠️ 当日达生鲜注意\n\n- **下午 2 点前下单**才能保证当晚到（你现在下单没问题）\n- 如果超时没到，在 App 申请「购物平台生鲜赔付」\n- 购物平台生鲜**死蟹包赔**（照片拍下来申请即可）\n\n## 🍶 今晚请准备\n\n- 姜一块（切末）\n- 镇江香醋\n- 黄酒（喝一点暖胃）\n- 餐巾纸（吃蟹必备）\n\n吃完别忘了喝姜茶，螃蟹性寒 🦀",
    ["阳澄湖大闸蟹6对礼盒+当日达今晚到+死蟹包赔，购物平台生鲜下单成功"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase
T.append(make_traj(
    "sft_repurchase_022", "repurchase", "复购召回",
    "复购护肤品+保质期预警",
    "再买之前那款防晒，用完了",
    {"category_keyword": "防晒霜", "time_range": "last_5_months", "check_expiry": True},
    [
        {"product_id": "mock_sunscreen_old", "title": "安热沙金瓶SPF50+ 60ml (你3月前购买)", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "你3月前购买/订单[ORDER_ID]/用完了", "sales": "月销4.5万"},
        {"product_id": "mock_sunscreen_now", "title": "安热沙金瓶 SPF50+ 60ml 当前款", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "当前价199同价/60ml/夏季防晒旺季/月销4.5万", "sales": "月销4.5万"},
        {"product_id": "mock_sunscreen_large", "title": "安热沙金瓶 SPF50+ 90ml 大容量款", "price": 259, "is_platform_self": True, "rating": 4.9, "key_specs": "90ml/比60ml多50%/单ml便宜12%", "sales": "月销1.8万"}
    ],
    "你 3 个月前买的安热沙金瓶用完了，正好来复购。\n\n## 📊 购买历史\n\n- 上次：2026-03-24（3 个月前）¥199\n- **用完时间约 3 个月**（夏季防晒用量大）\n\n## 🛒 两个选择\n\n### 选项 A：继续买 60ml ¥199（同款直接复购）\n- 价格不变\n- **你已经用习惯的规格**\n\n### 选项 B：升级 90ml ¥259 ⭐ 推荐\n\n| 规格 | 价格 | 单 ml | 能用多久 |\n|---|---|---|---|\n| 60ml | ¥199 | ¥3.32 | 约 3 个月 |\n| **90ml** | **¥259** | **¥2.88** | **约 4.5 个月** |\n\n**多花 ¥60，多用 1.5 个月，单 ml 便宜 13%**。\n\n## 💡 夏季防晒建议\n\n6-8 月是防晒用量最大的时期：\n- 出门前 15 分钟涂\n- 户外每隔 **2 小时补涂**\n- 游泳后**立刻补涂**\n- 按这个频次 60ml 约 45-60 天用完\n\n## ⚠️ 防晒开封保质期\n\n安热沙金瓶开封后**12 个月有效**。如果你确定一年内用完 90ml，升级更划算；如果不确定，60ml 稳妥。\n\n你想直接下单 60ml 复购，还是升级 90ml？",
    ["安热沙金瓶SPF50+ 60ml+你3月前购买+价格199不变+月销4.5万，直接复购同款", "安热沙金瓶SPF50+ 90ml+单ml便宜13%+月销1.8万，多花60元多用1.5个月"],
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
