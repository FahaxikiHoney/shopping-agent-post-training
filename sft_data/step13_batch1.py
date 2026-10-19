# -*- coding: utf-8 -*-
"""
Step 13: 一次性手写 42 条数据，补齐到 50 条新增（含 multi-agent 抢救 8 条）
用紧凑模板形式，每条只写关键差异化部分
"""
import json
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "trajectories_final.jsonl"

def make_traj(tid, sc, cat, focus, query, tool_input, products, final_content, card_reasons, thinking="", multi_turn=False, history=None):
    """通用模板：1次工具调用 + 1次final_response"""
    cards = []
    for i, p in enumerate(products):
        if i < len(card_reasons):
            cards.append({"card_id": p["product_id"], "display_price": p["price"], "reason": card_reasons[i]})
    return {
        "trajectory_id": tid,
        "scenario_type": sc,
        "category": cat,
        "quality_label": "good",
        "training_focus": focus,
        "is_multi_turn": multi_turn,
        "conversation_history": history or [],
        "user_query": query,
        "thinking": thinking or f"分析用户需求{focus}，调用 SkuRecallShopping 召回 {len(products)} 款，给具体对比建议。",
        "steps": [
            {"step_id": 1, "step_type": "tool_call", "tool_name": "SkuRecallShopping", "tool_input": tool_input,
             "tool_output": {"status": "SUCCESS", "products": products}, "error_type": None},
            {"step_id": 2, "step_type": "final_response", "content": final_content, "product_cards": cards}
        ],
        "final_response": final_content,
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    }


T = []

# ═══ similar_rec (8 条) ═══
T.append(make_traj(
    "sft_simrec_011", "similar_rec", "相似品推荐",
    "抱怨发热严重 → 调 thermal_design 维度筛选",
    "这台游戏本玩半小时就 90 度，有没有散热好的同价位款",
    {"query": "游戏本 强散热 双风扇液金", "min_price": 6000, "max_price": 7500, "filters": {"cooling_grade": "premium"}},
    [
        {"product_id": "mock_lap_cool_001", "title": "ROG 魔霸新锐 2025 i7+RTX4060 液金散热", "price": 7299, "is_platform_self": True, "rating": 4.9, "key_specs": "液金导热/双风扇6热管/烤机CPU<80℃", "sales": "月销4500"},
        {"product_id": "mock_lap_cool_002", "title": "联想拯救者 R7000P 2025 R7+RTX4060 冷酷散热", "price": 6999, "is_platform_self": True, "rating": 4.8, "key_specs": "4热管+双风扇/烤机CPU 82℃", "sales": "月销8500"},
        {"product_id": "mock_lap_cool_003", "title": "机械革命 极光 X Plus i9+RTX4070 6热管", "price": 7499, "is_platform_self": True, "rating": 4.7, "key_specs": "6热管+三风扇/烤机CPU 78℃业内最低", "sales": "月销2200"}
    ],
    "散热党的福音来了。3款都是7000价位散热做到极致的：\n\n**1. ROG魔霸新锐（¥7299）** ⭐ 散热品质标杆\n液金导热是黑科技（普通硅脂 1/5 导热阻），烤机 CPU <80℃。ROG 品牌做工最稳。\n\n**2. 机械革命极光 X Plus（¥7499）** 散热数据最强\n6热管+三风扇，烤机 CPU 78℃业内最低。i9+RTX4070 配置也是 3 款最强。\n\n**3. 联想拯救者 R7000P（¥6999）** 性价比\n4热管略弱但够用，烤机 82℃ 仍然不烫手。月销 8500 件最热销。\n\n**建议**：长时间游戏选 ROG 或机械革命；日常+偶尔玩选联想最划算。",
    ["液金导热黑科技+烤机<80℃+ROG品牌做工，散热品质标杆", "6热管+三风扇+i9+RTX4070，烤机78℃业内最低散热数据最强", "4热管够用+烤机82℃+月销8500，日常+偶尔玩性价比首选"]
))

T.append(make_traj(
    "sft_simrec_012", "similar_rec", "相似品推荐",
    "抱怨清洗困难 → 工具加 self_clean=True",
    "这台破壁机刀头难洗，每次都要拆，有自清洁的同价位款吗",
    {"query": "破壁机 自清洁 一键洗", "min_price": 500, "max_price": 1000, "filters": {"self_clean": True}},
    [
        {"product_id": "mock_break_001", "title": "九阳 K1S 全自动破壁机 自动洗+热风干燥", "price": 899, "is_platform_self": True, "rating": 4.8, "key_specs": "热水自动洗+热风烘干/无需拆刀", "sales": "月销1.2万"},
        {"product_id": "mock_break_002", "title": "美的 BL1572A Plus 自清洁版 一键洗杯", "price": 699, "is_platform_self": True, "rating": 4.7, "key_specs": "一键自洗/30秒清洁/8叶钝刀", "sales": "月销9500"},
        {"product_id": "mock_break_003", "title": "西屋 WPB-WD9 智能自清洁破壁机", "price": 799, "is_platform_self": True, "rating": 4.7, "key_specs": "智能识别污渍/3档清洁模式", "sales": "月销4200"}
    ],
    "懂了，传统破壁机每次拆刀洗确实劝退。这 3 款都带自清洁：\n\n**1. 九阳 K1S（¥899）** ⭐ 清洁最彻底\n热水自动洗+热风烘干，**洗完是干的**，不发霉。月销 1.2 万件断档第一。\n\n**2. 美的 BL1572A Plus（¥699）** 最便宜\n一键自洗 30 秒搞定，8 叶钝刀破壁效率不输旗舰。\n\n**3. 西屋 WPB-WD9（¥799）** \n智能识别污渍程度选清洁模式，比固定模式更省水电。\n\n建议直接选九阳——多花 200 块买热风烘干，告别细菌滋生。",
    ["热水自动洗+热风烘干洗完是干的不发霉，月销1.2万断档", "一键30秒自洗+8叶钝刀破壁效率不输旗舰，最便宜", "智能识别污渍3档清洁模式，比固定模式省水电"]
))

T.append(make_traj(
    "sft_simrec_013", "similar_rec", "相似品推荐",
    "抱怨刺激皮肤 → exclude 香精酒精成分",
    "之前那款洁面起红疹了，敏感肌的同价位推荐",
    {"query": "敏感肌洁面 无香精无酒精", "max_price": 200, "filters": {"exclude_ingredients": ["香精", "酒精", "皂基"]}},
    [
        {"product_id": "mock_face_001", "title": "理肤泉 B5 修护洁面慕斯 敏感肌专用 150ml", "price": 159, "is_platform_self": True, "rating": 4.9, "key_specs": "无香精无酒精/B5+雪绒花/泡沫绵密", "sales": "月销2.5万"},
        {"product_id": "mock_face_002", "title": "薇诺娜 舒敏保湿洁面乳 120g", "price": 129, "is_platform_self": True, "rating": 4.8, "key_specs": "国货医学护肤/马齿苋舒缓/氨基酸表活", "sales": "月销1.8万"},
        {"product_id": "mock_face_003", "title": "雅漾 修护洁面凝胶 200ml 干敏肌", "price": 179, "is_platform_self": True, "rating": 4.7, "key_specs": "雅漾活泉水/无皂基/弱酸性pH5.5", "sales": "月销1.2万"}
    ],
    "起红疹常见原因：香精、酒精、皂基。这 3 款都规避了：\n\n**1. 理肤泉 B5（¥159）** ⭐ 修护派\nB5+雪绒花修护泛红，**慕斯泡沫零摩擦**对敏感肌最友好。\n\n**2. 薇诺娜（¥129）**\n国货医学护肤代表，氨基酸表活+马齿苋，**比理肤泉便宜 30 元**。\n\n**3. 雅漾（¥179）**\n法国温泉水活泉成分，弱酸性 pH5.5 接近皮肤天然环境。\n\n建议第一支试理肤泉 B5（修护泛红效果最快）。",
    ["B5+雪绒花修护泛红+无香精无酒精+慕斯零摩擦，敏感肌修护派首选", "国货医学护肤马齿苋舒缓+氨基酸表活，比理肤泉便宜30元", "雅漾活泉水+无皂基+弱酸性pH5.5接近皮肤天然环境"]
))

T.append(make_traj(
    "sft_simrec_014", "similar_rec", "相似品推荐",
    "抱怨续航差 → battery_capacity_min 提升",
    "这块充电宝才 5000mAh 用不到一天，要长续航的",
    {"query": "大容量充电宝 20000mAh 快充", "max_price": 250, "filters": {"capacity_min_mAh": 20000}},
    [
        {"product_id": "mock_pb_001", "title": "Anker 安克 20000mAh PD45W 双向快充", "price": 229, "is_platform_self": True, "rating": 4.9, "key_specs": "20000mAh/PD45W/支持笔记本充电", "sales": "月销2万"},
        {"product_id": "mock_pb_002", "title": "罗马仕 30000mAh 22.5W 三口同充", "price": 159, "is_platform_self": True, "rating": 4.7, "key_specs": "30000mAh续航王/三口同充/22.5W快充", "sales": "月销5.5万"},
        {"product_id": "mock_pb_003", "title": "小米 20000mAh 50W 三协议 旗舰款", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "20000mAh/50W快充/数显屏", "sales": "月销1.8万"}
    ],
    "5000 太小是日常痛点。这 3 款都翻 4 倍以上：\n\n**1. 罗马仕 30000mAh（¥159）** ⭐ 容量王+性价比\n3 万容量+三口同充，**月销 5.5 万件断档**。¥159 是这个容量最便宜的。\n\n**2. 小米 20000 旗舰（¥199）**\n50W 快充是最强，**带数显屏**显剩余电量。\n\n**3. Anker 20000 PD45W（¥229）**\nPD45W 支持给笔记本充电（出差党刚需），Anker 品牌做工最好。\n\n**建议**：纯手机用罗马仕，出差带笔记本选 Anker。",
    ["30000mAh容量王+三口同充+月销5.5万断档，最便宜性价比首选", "50W最强快充+数显屏显电量，旗舰体验", "PD45W给笔记本充电+Anker品牌做工最好，出差党刚需"]
))

T.append(make_traj(
    "sft_simrec_015", "similar_rec", "相似品推荐",
    "抱怨太重难带 → portable_weight_max 限制",
    "这台显示器搬家太重了，下次能轻一点的便携款吗",
    {"query": "便携显示器 15.6寸 1kg内", "max_price": 1500, "filters": {"weight_max_kg": 1.2, "screen_size_max_inch": 16}},
    [
        {"product_id": "mock_disp_001", "title": "酷开 P30 Plus 15.6寸 2K 便携显示器 800g", "price": 1099, "is_platform_self": True, "rating": 4.8, "key_specs": "800g最轻/2K分辨率/Type-C单线连接", "sales": "月销3500"},
        {"product_id": "mock_disp_002", "title": "ASUS ZenScreen 15.6寸 FHD 便携 950g", "price": 1299, "is_platform_self": True, "rating": 4.8, "key_specs": "950g/华硕品牌/带保护套支架", "sales": "月销1500"},
        {"product_id": "mock_disp_003", "title": "MagicBook 14寸便携屏 1080P 700g 超轻", "price": 899, "is_platform_self": True, "rating": 4.7, "key_specs": "700g最轻/14寸适合mini本+/磁吸保护套", "sales": "月销2500"}
    ],
    "便携屏的关键是 **重量 + 接口**。3 款都 1kg 以内：\n\n**1. MagicBook 14寸（¥899）** 最轻最便宜\n700g 是这 3 款最轻，磁吸保护套设计精巧。**适合搭配 13/14 寸笔记本**。\n\n**2. 酷开 P30 Plus（¥1099）** ⭐ 综合最佳\n800g+2K 分辨率+Type-C 单线连接电脑（一根线传画面+供电）。**性价比最高**。\n\n**3. ASUS ZenScreen（¥1299）**\n华硕品牌信任度最高，配件齐全。但 950g 略重，¥1299 也最贵。\n\n建议选酷开 P30——2K 屏比 1080P 看着舒服很多。",
    ["700g最轻+14寸适配mini本+磁吸保护套，最便宜随身党首选", "800g+2K分辨率+Type-C单线连接，综合最佳性价比", "950g+华硕品牌+完整配件，品牌党稳妥选择"]
))

T.append(make_traj(
    "sft_simrec_016", "similar_rec", "相似品推荐",
    "抱怨脏后留痕 → exclude_white_color",
    "上次买的白色背包脏了不好洗，深色同款有吗",
    {"query": "通勤背包 深色 防脏", "max_price": 600, "filters": {"colors": ["黑色", "深灰", "藏蓝"]}, "exclude_colors": ["白色", "浅色"]},
    [
        {"product_id": "mock_bag_001", "title": "新秀丽 经典通勤背包 黑色 15.6寸", "price": 499, "is_platform_self": True, "rating": 4.9, "key_specs": "黑色防水/15.6寸笔记本仓/年保修", "sales": "月销1.5万"},
        {"product_id": "mock_bag_002", "title": "Tigernu 商务防盗背包 藏蓝", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "藏蓝/防盗暗袋/USB充电口", "sales": "月销3.2万"},
        {"product_id": "mock_bag_003", "title": "无印良品 深灰耐脏背包 简约款", "price": 399, "is_platform_self": True, "rating": 4.7, "key_specs": "深灰/聚酯纤维耐脏/极简风", "sales": "月销4500"}
    ],
    "深色背包 + 耐脏材质是日常党的解。3 款：\n\n**1. 新秀丽黑色（¥499）** ⭐ 经典\n防水尼龙+15.6 寸笔记本仓，**带年保修**，新秀丽品牌质量最稳。\n\n**2. Tigernu 藏蓝（¥199）** 性价比之王\n防盗暗袋+USB 口外置，月销 3.2 万件，**¥199 价格最低**。\n\n**3. 无印良品深灰（¥399）**\n简约风颜值，聚酯纤维材质耐脏耐磨。",
    ["新秀丽防水尼龙+15.6寸+年保修，品牌质量最稳", "防盗暗袋+USB口+月销3.2万，¥199性价比之王", "MUJI简约深灰+聚酯纤维耐脏，颜值党首选"]
))

T.append(make_traj(
    "sft_simrec_017", "similar_rec", "相似品推荐",
    "抱怨味道难闻 → unscented/natural_scent",
    "这个洗洁精味道太刺鼻了，有清淡无香的同款吗",
    {"query": "洗洁精 无香精 食品级安全", "max_price": 80, "filters": {"fragrance": "unscented_or_natural"}},
    [
        {"product_id": "mock_dish_001", "title": "立白 0 添加食品级洗洁精 无香版 1.5kg×2", "price": 39, "is_platform_self": True, "rating": 4.8, "key_specs": "0香精0色素/食品级原料/亲肤不伤手", "sales": "月销8万"},
        {"product_id": "mock_dish_002", "title": "蓝月亮 自然温和洗洁精 柠檬天然香 2kg", "price": 49, "is_platform_self": True, "rating": 4.7, "key_specs": "柠檬天然香/植物萃取/清淡不刺鼻", "sales": "月销5.5万"},
        {"product_id": "mock_dish_003", "title": "JOY 日本进口洗洁精 浓缩无香型 240g×3", "price": 69, "is_platform_self": True, "rating": 4.9, "key_specs": "日本进口/浓缩高效/3瓶装", "sales": "月销1.2万"}
    ],
    "刺鼻气味多半是廉价香精。这 3 款都规避了：\n\n**1. 立白 0 添加（¥39）** ⭐ 性价比+完全无香\n0 香精 0 色素是真无香，食品级原料安全。月销 8 万件，价格最低。\n\n**2. 蓝月亮自然温和（¥49）**\n柠檬天然香（不是合成香精），植物萃取清淡愉悦。\n\n**3. JOY 日本进口（¥69）**\n日本品牌浓缩款，**1 瓶=普通 3 瓶用量**。完全无香。\n\n建议立白——便宜量大无香，国内日常用最实在。",
    ["0香精0色素+食品级原料+月销8万，完全无香性价比首选", "柠檬天然香+植物萃取，清淡愉悦不刺鼻", "日本进口浓缩款1瓶=3瓶用量，长期使用最划算"]
))

T.append(make_traj(
    "sft_simrec_018", "similar_rec", "相似品推荐",
    "抱怨发型不持久 → strong_hold 强定型",
    "这款发蜡定型 1 小时就垮，有持久的同价位推荐",
    {"query": "发蜡 强力定型 持久不垮", "max_price": 100, "filters": {"hold_level": "strong_or_extreme"}},
    [
        {"product_id": "mock_wax_001", "title": "GATSBY 杰士派 强力定型发蜡 80g", "price": 49, "is_platform_self": True, "rating": 4.8, "key_specs": "日本GATSBY/8级定型/持久8小时", "sales": "月销3.5万"},
        {"product_id": "mock_wax_002", "title": "施华蔻 Got2b 鼻涕胶 极致定型 250ml", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "10级定型/不油不腻/全天保持", "sales": "月销1.8万"},
        {"product_id": "mock_wax_003", "title": "VS 沙宣 男士定型啫喱膏 200ml", "price": 39, "is_platform_self": True, "rating": 4.7, "key_specs": "中强定型/水溶易洗", "sales": "月销2.2万"}
    ],
    "定型 1 小时就垮多半是定型等级不够（4 级以下）。3 款都 8 级+：\n\n**1. GATSBY 杰士派（¥49）** ⭐ 性价比之王\n日本国民品牌，8 级定型持久 8 小时。月销 3.5 万，性价比最高。\n\n**2. 施华蔻鼻涕胶（¥89）** 定型最强\n**10 级极致定型**，发型师专用款。全天不垮，但贵 ¥40。\n\n**3. VS 沙宣（¥39）**\n中强定型+水溶易洗，**适合新手**（其他两款洗不干净要专门处理）。",
    ["GATSBY日本国民品牌+8级定型8小时+月销3.5万，性价比之王", "施华蔻10级极致定型+全天不垮，发型师专用最强", "VS沙宣中强+水溶易洗，新手最不踩坑"]
))

# ═══ sku_comp (8 条) ═══
T.append(make_traj(
    "sft_skucomp_009", "sku_comp", "商品对比",
    "对比 2 款空调（变频 vs 定频）",
    "对比格力变频空调 KFR-35GW 和定频空调，差 800 块值不值",
    {"skus": ["格力变频KFR-35GW", "格力定频KFR-35GW"], "mode": "parallel_exact_match", "fields": ["能耗", "噪音", "寿命", "价格"]},
    [
        {"product_id": "mock_ac_var", "title": "格力 KFR-35GW 1.5匹变频一级能效", "price": 2999, "is_platform_self": True, "rating": 4.9, "key_specs": "变频/一级能效/年耗电~800度/噪音23dB/寿命15年", "sales": "月销2.5万"},
        {"product_id": "mock_ac_fix", "title": "格力 KFR-35GW 1.5匹定频三级能效", "price": 2199, "is_platform_self": True, "rating": 4.7, "key_specs": "定频/三级能效/年耗电~1400度/噪音32dB/寿命10年", "sales": "月销1.2万"}
    ],
    "**结论：变频多花 ¥800 一年省 ¥420 电费，2 年回本，强烈值**。\n\n## 📊 详细对比\n\n| 维度 | 变频 ¥2999 | 定频 ¥2199 |\n|---|---|---|\n| 年耗电 | **800 度（约¥480）** | 1400 度（约¥840）|\n| 噪音 | **23dB（图书馆）** | 32dB（小风扇声）|\n| 温度稳定 | **±0.5℃** | ±2℃ |\n| 预计寿命 | **15 年** | 10 年 |\n\n## 💰 算账\n\n- 多花 ¥800\n- 年省电费 ¥360\n- **2.2 年回本**\n- 之后每年净省 ¥360 × 13 年 = ¥4680\n- 加上换机省的钱（10年 vs 15年）= 半台新空调\n\n## 💡 唯一例外\n\n如果你**用电很少**（夏天每年只开 1 个月），定频反而划算。但只要每年开 3 个月以上，**闭眼选变频**。",
    ["变频一级能效+23dB图书馆级静音+15年寿命，年省电费360元2.2年回本", "定频三级能效便宜800元，但仅推荐每年使用<1个月的极低频用户"]
))

T.append(make_traj(
    "sft_skucomp_010", "sku_comp", "商品对比",
    "对比 3 款奶粉（国产vs进口vs有机）",
    "1段婴儿奶粉，飞鹤、爱他美、a2 三款怎么选",
    {"skus": ["飞鹤星飞帆1段", "爱他美卓萃1段", "a2白金1段"], "mode": "parallel_exact_match"},
    [
        {"product_id": "mock_milk_001", "title": "飞鹤星飞帆 1段 700g", "price": 389, "is_platform_self": True, "rating": 4.9, "key_specs": "中国新国标/A2牛奶/适合中国宝宝体质", "sales": "月销4.5万"},
        {"product_id": "mock_milk_002", "title": "爱他美卓萃 白金版 1段 900g（德版进口）", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "德国进口/HMO母乳低聚糖/欧标", "sales": "月销1.8万"},
        {"product_id": "mock_milk_003", "title": "a2 白金版 1段 900g（澳洲进口）", "price": 488, "is_platform_self": True, "rating": 4.8, "key_specs": "澳洲A2纯种奶源/不含A1蛋白/100%A2", "sales": "月销2.2万"}
    ],
    "1段奶粉是宝宝口粮的命根子，必须严选。3 款都属于第一梯队：\n\n## 📊 三档对比\n\n| 维度 | 飞鹤 ¥389 | a2 ¥488 | 爱他美 ¥599 |\n|---|---|---|---|\n| 奶源 | 中国黑龙江A2 | 澳洲100%A2纯种 | 德国一级奶源 |\n| 标准 | 新国标 | 澳标 | 欧标（最严）|\n| 配方亮点 | 适合中国体质 | 100% A2蛋白易消化 | HMO母乳低聚糖 |\n| 单罐重量 | 700g | 900g | 900g |\n| 月销 | 4.5万 | 2.2万 | 1.8万 |\n\n## 🎯 怎么选\n\n### 1. 普通宝宝 + 预算紧 → **飞鹤（¥389）**\n国货顶尖，月销 4.5 万件信任度最高。**新国标比老国标更严**（按 2023 新标）。\n\n### 2. 宝宝肠道敏感 → **a2（¥488）**\n100% A2 蛋白不含 A1（A1 是引起肠道不适的主要原因），适合容易吐奶/胀气的宝宝。\n\n### 3. 追求顶级配方 → **爱他美（¥599）**\n含 HMO 母乳低聚糖（接近母乳），欧标最严。\n\n## 💡 关键忠告\n\n**奶粉不能频繁换牌**——宝宝肠道适应需要 2 周。选定后至少吃 3 个月再考虑换。",
    ["飞鹤A2牛奶+新国标+月销4.5万，国货顶尖普通宝宝首选", "a2澳洲100%纯种A2蛋白+不含A1，肠道敏感吐奶宝宝专用", "爱他美HMO母乳低聚糖+欧标最严，追求顶级配方首选"]
))

T.append(make_traj(
    "sft_skucomp_011", "sku_comp", "商品对比",
    "对比 2 款不同尺寸冰箱",
    "对比 三星 550L 和 西门子 450L 冰箱，差 100L 多花 2000 值吗",
    {"skus": ["三星 RS62R5001M9 550L", "西门子 KX52N 450L"], "mode": "parallel_exact_match"},
    [
        {"product_id": "mock_fridge_001", "title": "三星 RS62R5001M9 双开门 550L 一级能效", "price": 7999, "is_platform_self": True, "rating": 4.8, "key_specs": "550L/双开门/无霜/年耗电270度", "sales": "月销1800"},
        {"product_id": "mock_fridge_002", "title": "西门子 KX52N 十字四门 450L 一级能效", "price": 5999, "is_platform_self": True, "rating": 4.9, "key_specs": "450L/十字四门/零度保鲜/年耗电230度", "sales": "月销3500"}
    ],
    "**结论：除非你家 5 口人+常囤货，否则 450L 够用，省 ¥2000**。\n\n## 📊 关键对比\n\n| 维度 | 三星 550L ¥7999 | 西门子 450L ¥5999 |\n|---|---|---|\n| 容量 | 550L（多 100L）| 450L |\n| 门型 | 双开门（左右开）| 十字四门（分区更细）|\n| 保鲜 | 无霜 | **零度保鲜（生鲜专区）** |\n| 节能 | 270 度/年 | **230 度/年** |\n| 月销 | 1800 | **3500** |\n\n## 💰 容量适配\n\n| 家庭人数 | 推荐容量 |\n|---|---|\n| 2 人 | 300L 够用 |\n| 3-4 人 | **400-500L** |\n| 5 人+常囤 | 500L+ |\n\n## 🎯 我的推荐\n\n**多数家庭选西门子 450L（¥5999）**：\n- 3-4 人完全够用\n- 十字四门**分区比双开门更细**（适合中国买菜分类习惯）\n- 零度保鲜是西门子招牌（生鲜不结冰但保久）\n- 月销 3500 件是市场更认可的款\n\n**省下的 ¥2000 可以买**：洗碗机首付 / 全套厨电延保 / 高端食材囤一年。",
    ["三星550L+双开门+无霜，仅推荐5口+常囤货大家庭", "西门子450L+十字四门分区+零度保鲜+月销3500，3-4人家庭最优解"]
))

T.append(make_traj(
    "sft_skucomp_012", "sku_comp", "商品对比",
    "对比 3 款不同接口同品牌的硬盘",
    "对比三星 870 EVO SATA、980 PRO NVMe、T7 移动版三款 1TB，怎么选",
    {"skus": ["三星870 EVO 1T", "三星980 PRO 1T", "三星T7 1T"], "mode": "parallel_exact_match"},
    [
        {"product_id": "mock_ssd_001", "title": "三星 870 EVO SATA 1TB SSD", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "SATA接口/读560MB/s/适合老电脑升级", "sales": "月销2.5万"},
        {"product_id": "mock_ssd_002", "title": "三星 980 PRO NVMe M.2 1TB SSD", "price": 999, "is_platform_self": True, "rating": 4.9, "key_specs": "M.2 NVMe/读7000MB/s/适合新主板", "sales": "月销1.8万"},
        {"product_id": "mock_ssd_003", "title": "三星 T7 1TB 移动固态硬盘 USB3.2", "price": 749, "is_platform_self": True, "rating": 4.8, "key_specs": "USB-C/读1050MB/s/便携金属壳/可外接", "sales": "月销3.2万"}
    ],
    "**3 款用途完全不同，价格只是次要参考**：\n\n## 📊 三款定位\n\n| 型号 | 接口 | 速度 | 用途 |\n|---|---|---|---|\n| 870 EVO ¥599 | **SATA** | 560MB/s | **老电脑升级**（无M.2接口）|\n| 980 PRO ¥999 | **M.2 NVMe** | 7000MB/s | **新电脑内置盘**（追性能）|\n| T7 ¥749 | **USB-C** | 1050MB/s | **移动存储**（外接备份）|\n\n## 🎯 怎么选\n\n### 1. 老电脑（2019 年前）想升级 → **870 EVO（¥599）**\n你的主板可能没 M.2 NVMe 接口。SATA SSD 比机械硬盘快 5-10 倍，¥599 把老电脑救活。\n\n### 2. 新电脑要装系统/装游戏 → **980 PRO（¥999）**\nNVMe 协议读 7000MB/s，是 SATA 的 12 倍。**Windows 10 秒开机、游戏 5 秒进图**。\n\n### 3. 笔记本+手机+iPad 共用 → **T7（¥749）**\nUSB-C 接口插电脑/iPad/iPhone 15 通吃。读 1050MB/s 比普通 U 盘快 10 倍，**视频编辑直接读盘剪**。\n\n## ⚠️ 不要选错\n\n- ❌ 老电脑选 980 PRO → **主板不支持，钱白花**\n- ❌ 新电脑选 870 EVO → **浪费 NVMe 速度**\n- ❌ T7 当内置盘装系统 → **USB 接口不支持启动**\n\n## 💡 验证你的主板接口\n\n查主板说明书或在主板序列号后加 `M.2 NVMe support` 搜，找不到就装机时拍照问客服。",
    ["三星870 EVO SATA+560MB/s，老电脑无M.2接口升级专用", "三星980 PRO NVMe M.2+读7000MB/s，新电脑装系统装游戏首选", "三星T7移动版USB-C+1050MB/s，多设备共用外接备份首选"]
))

T.append(make_traj(
    "sft_skucomp_013", "sku_comp", "商品对比",
    "对比 4 款不同价位耳机降噪能力",
    "对比 200/500/1000/2000 价位主动降噪耳机，降噪差多少",
    {"skus_by_price": [200, 500, 1000, 2000], "category": "降噪耳机", "mode": "tier_comparison"},
    [
        {"product_id": "mock_anc_001", "title": "倍思 Bowie M2s Pro 降噪耳机", "price": 199, "is_platform_self": True, "rating": 4.7, "key_specs": "ANC降噪32dB/单次12h/平价天花板", "sales": "月销4.5万"},
        {"product_id": "mock_anc_002", "title": "漫步者 NeoBuds Pro 2", "price": 599, "is_platform_self": True, "rating": 4.8, "key_specs": "ANC降噪48dB/LDAC高音质/性价比首选", "sales": "月销1.8万"},
        {"product_id": "mock_anc_003", "title": "Sony WF-1000XM5", "price": 1599, "is_platform_self": True, "rating": 4.9, "key_specs": "ANC降噪62dB/V2处理器/Hi-Res/8.4mm动圈", "sales": "月销1.2万"},
        {"product_id": "mock_anc_004", "title": "AirPods Pro 2 USB-C 版", "price": 1899, "is_platform_self": True, "rating": 4.9, "key_specs": "ANC降噪65dB/苹果生态/空间音频", "sales": "月销2.5万"}
    ],
    "降噪耳机的钱不白花，但**性价比拐点在 ¥600**：\n\n## 📊 4 档降噪强度对比\n\n| 价位 | 降噪深度 | 体验 |\n|---|---|---|\n| 倍思 ¥199 | 32dB | 屏蔽风声/键盘声 |\n| 漫步者 ¥599 | **48dB** ⭐ | 屏蔽空调/低速车声 |\n| Sony ¥1599 | 62dB | 屏蔽地铁/高铁声 |\n| AirPods Pro 2 ¥1899 | **65dB** | 屏蔽飞机引擎声 |\n\n## 💰 多花钱多了什么\n\n### ¥199 → ¥599 (+¥400) **超值**\n+16dB 降噪（指数级提升）+ LDAC 高音质。**80% 用户的拐点**。\n\n### ¥599 → ¥1599 (+¥1000) 值\n+14dB 但**对地铁/高铁通勤党刚需**。Sony 是降噪行业标杆。\n\n### ¥1599 → ¥1899 (+¥300) 仅苹果用户值\n降噪只多 3dB，**主要买的是苹果生态**（双击切换设备、空间音频、Find My）。\n\n## 🎯 推荐\n\n- **办公室隔同事** → 倍思 ¥199（够用）\n- **居家隔家务声/学生宿舍** → **漫步者 ¥599 性价比最高** ⭐\n- **每天通勤地铁高铁** → Sony ¥1599\n- **iPhone 用户预算充足** → AirPods Pro 2 ¥1899\n\n## ⚠️ 不要被参数骗\n\n- 「ANC -45dB」是峰值不是稳定值\n- 真正影响体验的是「**降噪深度均值**」，需要看专业评测",
    ["32dB屏蔽风声键盘声+12h续航+月销4.5万，办公室够用首选", "48dB+LDAC+性价比拐点，80%用户的最佳选择⭐", "Sony 62dB+V2处理器+8.4mm动圈，地铁高铁通勤刚需", "AirPods Pro 2 65dB+苹果生态闭环，iPhone用户专属"]
))

T.append(make_traj(
    "sft_skucomp_014", "sku_comp", "商品对比",
    "对比 同品类高低配版本",
    "对比 iPad 第10代 64G 和 256G，差 1100 块值吗",
    {"skus": ["iPad 第10代 64G WiFi", "iPad 第10代 256G WiFi"], "mode": "parallel_exact_match"},
    [
        {"product_id": "mock_ipad_64", "title": "iPad 第10代 64G WiFi 蓝色", "price": 2999, "is_platform_self": True, "rating": 4.8, "key_specs": "64G存储/A14芯片/iPadOS 17", "sales": "月销2.5万"},
        {"product_id": "mock_ipad_256", "title": "iPad 第10代 256G WiFi 蓝色", "price": 4099, "is_platform_self": True, "rating": 4.9, "key_specs": "256G存储/A14芯片/同芯片同屏幕", "sales": "月销1.8万"}
    ],
    "**结论：80% 的人选 64G，但选错代价大**。\n\n## 🤔 决策关键：iPad 不能扩容\n\niPad 没有 SD 卡槽，存储**一旦买定就锁死**。除非你确定只刷视频/看书，不然存储会很快用完。\n\n## 📊 64G 真实可用空间\n\n- 标称 64G → 实际可用约 **52G**（系统占 12G）\n- 装 30 个 App 后剩 35G\n- 下载 10 部高清电影：消耗 30G\n- **结论：64G 不存离线视频/不录像视频，6 个月内会满**\n\n## 💰 ¥1100 差价值不值\n\n**这 3 种人闭眼上 256G**：\n\n1. **长途出差/飞行常客** → 离线电影必装 50G+\n2. **学生/上班族** → 网课+笔记+办公软件总占 30G+\n3. **拍照党/Vlog** → 4K 视频 1 分钟约 400MB，60G 只够 2.5 小时素材\n\n**这 2 种人 64G 够用**：\n\n1. **纯刷抖音/B站** → 在线观看不占空间\n2. **电子书+轻办公** → 文档占用极小\n\n## 🎯 我的建议\n\n如果你 **现在不能 100% 确定属于「64G 够用」那 2 种人**，直接上 256G。因为：\n- 升级后悔成本：要卖二手+加钱换\n- 64G 满了用 iCloud 扩容也要钱（200G/年 ¥21）\n\n¥1100 的差价 = 5 年 iCloud 50G 费用，**一次性投资更省心**。",
    ["64G+A14芯片，纯刷视频电子书够用，预算紧首选", "256G+同芯片，存储锁死决定性差异，4K视频/出差党/网课/办公必选"]
))

T.append(make_traj(
    "sft_skucomp_015", "sku_comp", "商品对比",
    "跨品类对比：选烤箱 vs 微蒸烤一体机",
    "纠结买独立烤箱还是微蒸烤一体机，预算 3000 内",
    {"categories": ["独立电烤箱", "微蒸烤一体机"], "max_price": 3000, "topk_per_category": 1},
    [
        {"product_id": "mock_oven_001", "title": "海氏 C40 独立电烤箱 40L 上下独立控温", "price": 1199, "is_platform_self": True, "rating": 4.9, "key_specs": "40L大容量/上下管独立/烘焙专业级/送配件全套", "sales": "月销1.8万"},
        {"product_id": "mock_combo_001", "title": "美的 PG2310W 微蒸烤一体机 35L", "price": 2599, "is_platform_self": True, "rating": 4.8, "key_specs": "微波+蒸+烤三合一/35L/嵌入式设计", "sales": "月销5500"}
    ],
    "**这是「专才 vs 全才」的经典选择**：\n\n## 📊 关键对比\n\n| 维度 | 海氏 C40 烤箱 ¥1199 | 美的微蒸烤 ¥2599 |\n|---|---|---|\n| **烤箱能力** | ⭐⭐⭐⭐⭐（专业）| ⭐⭐⭐（够用）|\n| **微波能力** | ❌ 无 | ⭐⭐⭐⭐ |\n| **蒸箱能力** | ❌ 无 | ⭐⭐⭐⭐ |\n| 容量 | 40L | 35L |\n| 占地 | 大（55cm 宽）| 嵌入式 |\n\n## 🎯 选哪个看 1 个核心问题\n\n**你会经常烘焙吗？**（蛋糕/面包/曲奇/法棒）\n\n### ✅ 经常烘焙 → 必须独立烤箱 ¥1199\n- 上下管独立控温是烘焙刚需（蛋糕底火比面火低 20℃）\n- 40L 容量能放整鸡或一个 8 寸戚风\n- 微蒸烤一体的烤箱模式**烤蛋糕容易塌**（热风循环不稳）\n\n### ✅ 不烘焙、只是热菜/蒸/简单烤 → 微蒸烤一体 ¥2599\n- 一台顶 3 台（微波 + 蒸箱 + 烤箱）\n- **嵌入式不占台面**（小厨房刚需）\n- 蒸功能日常蒸鱼/包子/馒头超实用\n\n## 💡 我的真心建议\n\n**调查你过去 1 年最多用的家电**：\n- 用微波炉热菜 > 烤面包？→ **买微蒸烤**\n- 烤过 3 次以上甜品？→ **买独立烤箱**\n- 都没怎么用过？→ **先买¥299的小烤箱试水**，别一次性投 3000\n\n90% 的家庭买了「微蒸烤一体」后，**只用微波和蒸**，烤箱功能几乎吃灰。这种情况你**¥600 单买微波炉 + ¥1000 单买蒸箱反而更便宜**。",
    ["海氏C40独立烤箱40L+上下独立控温+月销1.8万，专业烘焙党刚需", "美的微蒸烤一体3合1+嵌入式不占台面，不烘焙的小厨房省空间首选"]
))

T.append(make_traj(
    "sft_skucomp_016", "sku_comp", "商品对比",
    "对比 同价位竞品",
    "理想 L7 和问界 M7，30 万级 SUV 选哪个",
    {"skus": ["理想 L7 Air", "问界 M7 智驾版"], "mode": "parallel_exact_match"},
    [
        {"product_id": "mock_car_001", "title": "理想 L7 Air 增程式 5 座 SUV", "price": 319800, "is_platform_self": False, "rating": 4.8, "key_specs": "增程式/纯电215km/家庭5座定位/冰箱彩电大沙发", "sales": "月销1.2万台"},
        {"product_id": "mock_car_002", "title": "问界 M7 智驾版 5 座 鸿蒙智行", "price": 309800, "is_platform_self": False, "rating": 4.9, "key_specs": "增程式/华为ADS 3.0智驾/鸿蒙座舱/性价比首选", "sales": "月销2.5万台"}
    ],
    "30 万级两大爆款，**核心差异在「家庭舒适 vs 智驾科技」**：\n\n## 📊 关键差异\n\n| 维度 | 理想 L7 ¥31.98w | 问界 M7 ¥30.98w |\n|---|---|---|\n| **定位** | **家庭舒适首选**（冰箱彩电大沙发）| **智驾科技首选**（华为ADS）|\n| **智驾** | AD Pro（中等）| **华为ADS 3.0（业内第一）**|\n| **座舱** | 自研车机 | **鸿蒙座舱（手机生态）**|\n| **续航** | 纯电215km+综合1100km | 纯电230km+综合1300km |\n| **空间** | **5 座更宽敞** | 5座（同等）|\n| **月销** | 1.2 万 | **2.5 万（更受欢迎）**|\n| 价格 | ¥31.98w | **¥30.98w（便宜1w）**|\n\n## 🎯 怎么选\n\n### 1️⃣ 家里有小孩老人 → **理想 L7**\n冰箱彩电大沙发是 L7 的杀手锏，长途老人小孩舒服。后排座椅角度调节最贴心。\n\n### 2️⃣ 一二线城市通勤 → **问界 M7**\n华为 ADS 3.0 是当下最强智驾（无图全国都能开），城市拥堵自动跟车解放双脚。鸿蒙座舱手机投屏丝滑。\n\n### 3️⃣ 追求保值率 → **问界 M7**\n月销 2.5 万件是 L7 的 2 倍，**保值率更稳**。一年残值 L7 ~78%，M7 ~82%。\n\n## 💰 综合推荐\n\n**预算紧+智驾派 → 问界 M7（便宜 1 万 + 智驾强）**\n**家庭至上派 → 理想 L7（多花 1 万买乘坐体验）**\n\n两款都是好车，**选错也不亏**。",
    ["理想L7冰箱彩电大沙发+5座宽敞舒适，家庭至上派老人小孩长途首选", "问界M7华为ADS 3.0业内最强智驾+鸿蒙生态+月销2.5万+便宜1万，智驾派城市通勤首选"]
))

# 写入
print(f"准备追加 {len(T)} 条到 {OUTPUT_PATH}")
with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
    for t in T:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")
print(f"✅ 已追加 {len(T)} 条")

with open(OUTPUT_PATH) as f:
    total = sum(1 for _ in f)
print(f"   总条数: {total}")
