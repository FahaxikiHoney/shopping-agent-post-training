# -*- coding: utf-8 -*-
"""Step 35: 第 23 批 10 条"""
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

# 1. similar_rec - 抱怨收纳空间不够
T.append(make_traj(
    "sft_simrec_057", "similar_rec", "相似品推荐",
    "抱怨收纳不足 → 推荐带抽屉/更多收纳空间款",
    "上次买的床头柜只有一层，放不下东西，要收纳多的同价位款",
    {"query": "床头柜 多层抽屉 大容量收纳", "max_price": 600, "filters": {"drawers_min": 3}},
    [
        {"product_id": "mock_bedside_1", "title": "源氏木语 实木床头柜 三抽款 胡桃色", "price": 499, "is_platform_self": True, "rating": 4.9, "key_specs": "三层抽屉/实木胡桃/55cm高/月销1500", "sales": "月销1500"},
        {"product_id": "mock_bedside_2", "title": "简易床头柜 四格抽屉 北欧白色", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "四层抽屉/北欧白/轻巧好安装/月销3500", "sales": "月销3500"},
        {"product_id": "mock_bedside_3", "title": "MUJI 同款 床头柜带开放格 三抽+上层开放", "price": 559, "is_platform_self": True, "rating": 4.9, "key_specs": "三抽+上层开放格/复合收纳/MUJI风格", "sales": "月销850"}
    ],
    "床头柜一层根本不够放，3 款多收纳款：\n\n**1. 北欧四层抽屉（¥299）** ⭐ 性价比最高\n四层抽屉是最多的，**¥299 超值**。白色百搭，轻量好安装，月销 3500 件。\n\n**2. 源氏木语实木三抽（¥499）**\n实木质感高级，胡桃色温暖，**三抽够用同时颜值有保障**。适合已经有木质家具的卧室。\n\n**3. MUJI 同款三抽+开放格（¥559）**\n三层抽屉+上方开放格，**可以放手机/眼镜/水杯**随手拿，最实用。\n\n## 💡 床头柜多少层够用\n\n按需求分：\n- 1-2 层：只放手机充电/眼镜（最少需求）\n- **3 层**：常用药+书+杂物+充电，**大多数人的标准**\n- 4 层：东西特别多，建议整理习惯",
    ["北欧四层抽屉299元+白色百搭+月销3500，最多收纳层最便宜", "源氏木语实木三抽+胡桃色+月销1500，木质家具卧室颜值匹配", "MUJI同款三抽+上层开放格+月销850，手机眼镜水杯随手拿最实用"]
))

# 2. similar_rec - 抱怨油烟大
T.append(make_traj(
    "sft_simrec_058", "similar_rec", "相似品推荐",
    "抱怨厨房油烟大 → 推荐大吸力油烟机",
    "家里炒菜油烟太大，上次买的抽油烟机不够吸，换个吸力强的",
    {"query": "抽油烟机 大吸力 22m³/min以上", "min_price": 2000, "max_price": 4000, "filters": {"suction_m3_min": 22}},
    [
        {"product_id": "mock_hood_1", "title": "方太 JQC1TX 近吸式 22m³/min 侧吸", "price": 3299, "is_platform_self": True, "rating": 4.9, "key_specs": "侧吸22m³/min/近吸油烟不扩散/自清洁", "sales": "月销2200"},
        {"product_id": "mock_hood_2", "title": "老板 CXW-218 顶吸式 23m³/min 大风量", "price": 2599, "is_platform_self": True, "rating": 4.9, "key_specs": "顶吸23m³/min/适合大炒锅/月销3500", "sales": "月销3500"},
        {"product_id": "mock_hood_3", "title": "华帝 侧吸+顶吸双模 24m³/min 旗舰", "price": 3799, "is_platform_self": True, "rating": 4.8, "key_specs": "双模切换/24m³/min最大/大厨房专用", "sales": "月销850"}
    ],
    "油烟吸不干净根源是**风量不够**，3 款都达到 22m³/min 以上：\n\n**1. 老板顶吸 CXW-218（¥2599）** ⭐ 性价比首选\n顶吸 23m³/min，**大风量+价格合理**，月销 3500 件是家用油烟机主流。适合炒中式菜。\n\n**2. 方太侧吸近吸（¥3299）**\n侧吸设计贴近灶台，**油烟还没飘起就吸走**，效率更高。自清洁功能省去手动洗烟机的痛苦。\n\n**3. 华帝双模 24m³/min（¥3799）**\n双模切换（侧吸+顶吸），**24m³/min 最大风量**，适合大厨房或重口味爆炒。\n\n## 💡 侧吸 vs 顶吸\n\n- **侧吸**：距离锅近，油烟不扩散，**爆炒推荐**\n- **顶吸**：安装在头顶，覆盖范围广，**大风量型**\n- 厨房面积 < 8㎡ → 侧吸；> 8㎡ → 顶吸/双模",
    ["老板CXW-218顶吸23m³/min+月销3500，大风量价格合理主流首选", "方太JQC1TX侧吸近吸22m³/min+自清洁+月销2200，爆炒油烟贴近灶台效率最高", "华帝双模24m³/min最大+月销850，大厨房重口味爆炒旗舰"]
))

# 3. sku_comp
T.append(make_traj(
    "sft_skucomp_055", "sku_comp", "商品对比",
    "不同价位鼠标 100/300/700 三档对比",
    "买鼠标，罗技 G102/MX Master/MX Anywhere，100/400/600 元差在哪",
    {"skus": ["罗技G102 有线游戏鼠标", "罗技MX Anywhere 3S 无线", "罗技MX Master 3S 旗舰"], "mode": "price_tier_comparison"},
    [
        {"product_id": "mock_mouse_1", "title": "罗技 G102 有线游戏鼠标 8000DPI", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "有线/8000DPI/游戏/月销8万", "sales": "月销8万"},
        {"product_id": "mock_mouse_2", "title": "罗技 MX Anywhere 3S 便携无线", "price": 549, "is_platform_self": True, "rating": 4.9, "key_specs": "三设备无线/磁吸滚轮/便携/月销3.5万", "sales": "月销3.5万"},
        {"product_id": "mock_mouse_3", "title": "罗技 MX Master 3S 旗舰办公鼠标", "price": 699, "is_platform_self": True, "rating": 4.9, "key_specs": "全键静音/MagSpeed滚轮/三设备/旗舰", "sales": "月销1.5万"}
    ],
    "**结论：办公选 MX Anywhere，游戏选 G102，旗舰选 MX Master**。\n\n## 📊 三款核心差异\n\n| 维度 | G102 ¥99 | MX Anywhere 3S ¥549 | MX Master 3S ¥699 |\n|---|---|---|---|\n| 连接 | 有线 | **无线三设备** | **无线三设备** |\n| 尺寸 | 标准 | **便携小巧** | 标准（偏大）|\n| 滚轮 | 普通 | **磁吸超快** | **MagSpeed 最顶** |\n| 静音 | 否 | 部分 | **全键静音** |\n| 适合 | 游戏 | 出差/便携 | 长时间办公 |\n\n## 🎯 怎么选\n\n### G102 ¥99（游戏/学生）\n- 有线零延迟，游戏表现稳定\n- 月销 8 万是鼠标绝对销冠\n- 不适合出差（有线）\n\n### MX Anywhere 3S ¥549（便携办公）\n- 三台设备切换（电脑+平板+手机）\n- **体积小装包方便**，出差神器\n- 磁吸滚轮查资料一划到底\n\n### MX Master 3S ¥699（固定工作站）\n- **全键静音**开会不打扰别人\n- 大手掌握持最舒适\n- 侧滚轮（Excel 横向滚动方便）\n\n## 💡 ¥150 差价的判断\n\nMX Anywhere 和 MX Master 功能接近，差距：\n- **尺寸**：Anywhere 更小（便携）\n- **静音**：Master 全键静音\n- 如果不出差 → 选 Master（静音更好用）\n- 如果经常出差 → 选 Anywhere（便携关键）",
    ["罗技G102有线8000DPI+月销8万绝对销冠，游戏学生零延迟首选", "罗技MX Anywhere 3S无线三设备+便携+月销3.5万，出差便携办公神器", "罗技MX Master 3S全键静音+MagSpeed滚轮+月销1.5万，固定工作站旗舰"]
))

# 4. sku_comp - 净水vs矿泉水
T.append(make_traj(
    "sft_skucomp_056", "sku_comp", "商品对比",
    "家用净水方案年成本全面对比",
    "家里饮水一年算下来，净水器/矿泉水/桶装水/直接烧开哪个最划算",
    {"skus": ["RO净水器5年成本", "瓶装矿泉水年成本", "桶装水年成本", "自来水烧开年成本"], "mode": "annual_cost_comparison"},
    [
        {"product_id": "mock_ro_water", "title": "小米 RO 反渗透净水器 厨下式", "price": 1999, "is_platform_self": True, "rating": 4.9, "key_specs": "RO净水/直饮/1年滤芯300/5年总成本3499", "sales": "月销2.2万"},
        {"product_id": "mock_bottle_water", "title": "农夫山泉 饮用天然水 550ml×24瓶", "price": 49, "is_platform_self": True, "rating": 4.9, "key_specs": "550ml×24/一家人一周用量/年成本2548", "sales": "月销45万"},
        {"product_id": "mock_barrel_water", "title": "怡宝 纯净水 19L 桶装 10桶起送", "price": 120, "is_platform_self": True, "rating": 4.8, "key_specs": "19L/¥12一桶/一家3口月用5桶/年成本720", "sales": "月销8万"},
        {"product_id": "mock_kettle_water", "title": "苏泊尔 304不锈钢电水壶 1.7L", "price": 159, "is_platform_self": True, "rating": 4.9, "key_specs": "304不锈钢/烧自来水/电费年约50元/总成本最低", "sales": "月销5万"}
    ],
    "按**3 口家庭年饮水**算一算谁最划算：\n\n## 📊 5 年综合成本对比\n\n| 方案 | 首次投入 | 年运营费 | **5 年总成本** |\n|---|---|---|---|\n| 烧自来水 | ¥159（水壶）| ¥50（电）| **¥409** |\n| 桶装水 | ¥0 | ¥720 | **¥3600** |\n| RO 净水器 | ¥1999 | ¥300（滤芯）| **¥3499** |\n| 瓶装矿泉水 | ¥0 | ¥2548 | **¥12740** |\n\n## 💡 各方案实际体验\n\n### 烧自来水（¥409 /5 年）✅ 最省\n- 自来水煮沸杀灭细菌，但**无法去除重金属/余氯**\n- 适合：水质好的城市（大城市主城区一般没问题）\n- 不适合：老房子铁管、水质差的区域\n\n### 桶装水（¥3600/5 年）⚠️ 性价比低\n- 搬桶麻烦，桶口二次污染概率高\n- 比 RO 净水器更贵但品质不如\n- **5 年比净水器多花 ¥100**，还要搬桶\n\n### RO 净水器（¥3499/5 年）⭐ 综合最优\n- 直饮级过滤，随开随用\n- 不用搬桶，方便\n- **5 年比桶装水便宜 ¥100** 还方便\n\n### 瓶装矿泉水（¥12740/5 年）❌ 最贵\n- 5 年花 1.27 万！\n- 大量塑料垃圾\n- 只有追求特定矿物质成分才值得\n\n## 🎯 结论\n\n- **水质好的大城市** → 直接烧开（¥409）\n- **大部分家庭** → **RO 净水器（¥3499）**，3 年后比桶装水更便宜\n- **瓶装矿泉水** → 外出带 1-2 瓶尝鲜可以，日常饮水性价比最差",
    ["小米RO净水器1999+直饮级+年滤芯300+月销2.2万，5年成本3499比桶装水更划算", "农夫山泉550ml×24+月销45万，瓶装矿泉水5年成本1.27万家庭饮水最贵不推荐日常", "怡宝桶装水19L+¥12一桶+月销8万，年成本720搬桶麻烦5年比净水器贵", "苏泊尔电水壶304不锈钢+月销5万，烧自来水5年仅409元最省但无法去余氯"]
))

# 5. matching
T.append(make_traj(
    "sft_match_055", "matching_purchase", "搭配购物",
    "冬日居家保暖整套",
    "冬天在家穿着要暖和，配居家服+保暖袜+热水袋+加热坐垫",
    {"query": "冬日居家保暖套装 居家服+保暖袜+热水袋", "filters": {"season": "winter", "use": "indoor_warmth"}},
    [
        {"product_id": "mock_warm_1", "title": "蕉内 保暖居家服套装 绒感面料", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "双面绒/保暖/吸汗透气/冬日居家标配", "sales": "月销3万"},
        {"product_id": "mock_warm_2", "title": "Wook 纯羊毛袜 加厚保暖 冬季款", "price": 129, "is_platform_self": True, "rating": 4.9, "key_specs": "纯羊毛/加厚/地板袜/脚不冷关键", "sales": "月销1.5万"},
        {"product_id": "mock_warm_3", "title": "暖手宝 充电款 二合一 充电宝功能", "price": 129, "is_platform_self": True, "rating": 4.9, "key_specs": "暖手+充电宝二合一/10000mAh/速热", "sales": "月销2.5万"},
        {"product_id": "mock_warm_4", "title": "USB 加热坐垫 办公室/沙发两用", "price": 89, "is_platform_self": True, "rating": 4.8, "key_specs": "USB供电/三档调温/坐久暖身体/沙发椅子通用", "sales": "月销4.5万"}
    ],
    "冬日居家保暖 4 件套 ¥646，**从脚到手全方位**：\n\n## 🧣 完整方案\n\n| 物品 | 商品 | 价格 | 保暖部位 |\n|---|---|---|---|\n| 居家服 | 蕉内绒感居家服 | ¥299 | 全身 |\n| 保暖袜 | Wook 纯羊毛加厚 | ¥129 | 脚部（最重要）|\n| 暖手宝 | 充电宝二合一款 | ¥129 | 手部 |\n| 加热坐垫 | USB 三档调温 | ¥89 | 臀部/背部 |\n\n## 💡 冬天在家为什么还冷\n\n居家冷的根源不是穿的少，而是**热量散失部位没处理**：\n- **脚最散热**（地板导热，普通棉袜根本不够）\n- **手摸手机冷**（指尖毛细血管多）\n- **久坐臀部/腰部冷**（不动血液循环差）\n\n**4 件套针对这 4 个部位各个击破**。\n\n## 💡 羊毛袜 vs 棉袜\n\n冬天在家穿羊毛袜是**性价比最高的保暖升级**：\n- 纯羊毛保暖性是棉袜的 3 倍\n- 莫比乌斯纤维结构锁温\n- ¥129 一双，穿 3 年不变形\n\n## 💡 二合一暖手宝的妙用\n\n当充电宝用出门+当暖手宝在家用，**¥129 买的是两个产品**，不浪费。\n\n## 💎 加 ¥200 升级\n\n- 蕉内发热内衣 ¥199（全身最暖）\n- 电热暖脚器 ¥150（脚伸进去）\n- 浴室加热灯 ¥99",
    ["蕉内绒感居家服套装+双面绒保暖+月销3万，冬日居家全身保暖标配", "Wook纯羊毛加厚袜+脚部最散热+月销1.5万，居家保暖最关键的部位", "暖手宝+充电宝二合一10000mAh+月销2.5万，手冷+出门充电一物两用", "USB加热坐垫三档调温+月销4.5万，久坐臀部腰部冷血液循环差解决"]
))

# 6. matching
T.append(make_traj(
    "sft_match_056", "matching_purchase", "搭配购物",
    "开学季大学新生宿舍小家电",
    "开学带去宿舍用的小家电，配台灯+风扇+小音箱+手持挂烫机",
    {"query": "大学宿舍小家电套装 台灯+风扇+音箱", "filters": {"power_max_w": 800, "category": "college_dorm_appliance"}},
    [
        {"product_id": "mock_dorm_e1", "title": "明基台灯 MindDuo 1 护眼 USB供电", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "AA级护眼/USB供电/插排就能用/月销3500", "sales": "月销3500"},
        {"product_id": "mock_dorm_e2", "title": "艾美特 USB 小风扇 夹式 宿舍专用", "price": 79, "is_platform_self": True, "rating": 4.9, "key_specs": "USB夹式/贴床头/静音/月销4.5万", "sales": "月销4.5万"},
        {"product_id": "mock_dorm_e3", "title": "小米蓝牙音箱 Redmi 小爱款 床头版", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "蓝牙/小爱同学/闹钟/床头适合/月销2.8万", "sales": "月销2.8万"},
        {"product_id": "mock_dorm_e4", "title": "手持挂烫机 迷你蒸汽 宿舍专用", "price": 99, "is_platform_self": True, "rating": 4.8, "key_specs": "手持蒸汽/30秒出蒸汽/出行必备/月销1.5万", "sales": "月销1.5万"}
    ],
    "宿舍小家电 4 件套 ¥576，**限功率内全部可用**：\n\n## 🎓 完整方案\n\n| 家电 | 商品 | 价格 | 用途 |\n|---|---|---|---|\n| 台灯 | 明基 MindDuo 1 护眼 | ¥299 | 夜间学习护眼 |\n| 风扇 | 艾美特 USB 夹式 | ¥79 | 热天睡觉/学习降温 |\n| 音箱 | 小米小爱床头款 | ¥99 | 听歌/闹钟/语音助手 |\n| 挂烫机 | 迷你蒸汽手持 | ¥99 | 衣服褶皱快速处理 |\n\n## ⚠️ 宿舍用电功率限制\n\n大多数宿舍有**400W 或 800W** 功率限制，以上 4 件：\n- 台灯：约 10W\n- 风扇：约 5W（USB 供电）\n- 音箱：约 5W\n- 挂烫机：约 700W（**最大功率件，注意**）\n\n挂烫机单独用不超标，但同时开其他大功率设备（吹风机等）会跳闸。\n\n## 💡 选品理由\n\n### 明基台灯 ¥299\n大学**每晚学习 3-4 小时**，护眼台灯是视力保护的核心投资。\n\n### USB 夹式风扇 ¥79\n夹在床头直接吹脸，**熄灯后比大风扇安静**，不影响室友。\n\n### 小爱音箱 ¥99\n**「小爱，早上 7 点叫我」**是宿舍最常用的场景，替代手机闹钟还能控制其他小米设备。\n\n### 手持挂烫机 ¥99\n宿舍没熨烫台，挂烫机**悬挂在衣架上蒸**，面试/出席重要场合前救命利器。",
    ["明基MindDuo 1护眼台灯+USB供电+月销3500，每晚3-4h学习视力保护首选", "艾美特USB夹式风扇+贴床头静音+月销4.5万，熄灯后吹脸不影响室友", "小米小爱床头音箱+蓝牙+闹钟+月销2.8万，语音助手替代手机闹钟", "手持挂烫机迷你蒸汽+月销1.5万，面试前衣服褶皱30秒解决"]
))

# 7. bundle
T.append(make_traj(
    "sft_bundle_053", "bundle_purchase", "组合购物",
    "4000 元独立游戏工作室装备",
    "想在家打造一个独立游戏工作站，4000 配电脑椅+显示器支架+RGB灯+音箱",
    {"query": "游戏工作站外设 椅子+灯+音箱+支架", "max_price": 4500},
    [
        {"product_id": "mock_game_ws_1", "title": "傲风 人体工学椅 电竞款 4D扶手", "price": 1499, "is_platform_self": True, "rating": 4.9, "key_specs": "4D扶手/腰托/网布透气/游戏+办公通用", "sales": "月销1.5万"},
        {"product_id": "mock_game_ws_2", "title": "爱格升 双显示器支架 北欧风 铝合金", "price": 899, "is_platform_self": True, "rating": 4.9, "key_specs": "双显示器支架/铝合金/可调高度/桌面整洁", "sales": "月销3500"},
        {"product_id": "mock_game_ws_3", "title": "漫步者 R1000BT 2.1 蓝牙桌面音箱", "price": 799, "is_platform_self": True, "rating": 4.9, "key_specs": "2.1声道/低音炮/蓝牙5.0/游戏影院感", "sales": "月销1.2万"},
        {"product_id": "mock_game_ws_4", "title": "Nanoleaf 智能灯板 9 片 RGB 氛围灯", "price": 699, "is_platform_self": True, "rating": 4.9, "key_specs": "RGB氛围灯/9片可拼接/游戏背景墙/月销2200", "sales": "月销2200"}
    ],
    "游戏工作站 4 件套 ¥3896，**功能+颜值双在线**：\n\n## 🎮 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 🥇 椅子 | 傲风人体工学椅 4D 扶手 | ¥1499 |\n| 显示器支架 | 爱格升双显 铝合金 | ¥899 |\n| 音箱 | 漫步者 R1000BT 2.1 | ¥799 |\n| RGB 灯板 | Nanoleaf 9 片 | ¥699 |\n\n## 💡 为什么这套装备\n\n### 1. 椅子是投资最高的 ¥1499\n**游戏/工作一坐 5-8 小时**，傲风 4D 扶手让手肘有支撑，减少肩膀酸痛。比普通椅子价值大 10 倍。\n\n### 2. 双显示器支架让桌面整洁\n两台显示器放桌面占用 2/3 空间，**支架抬起来**，桌面全空，还能调高度减少颈椎压力。\n\n### 3. 漫步者 2.1 音响≠音质，是氛围\n2.1 声道（含低音炮）打游戏**枪声/爆炸有重量感**，看电影有影院感。蓝牙连接，干净无线。\n\n### 4. Nanoleaf RGB 灯板\n背景墙氛围灯 ≠ 装饰，实际功能是**减少长时间盯屏幕的视觉疲劳**（背景有光）。可以随音乐/游戏节奏变色。\n\n## 💰 还差 ¥104 到 4000，可以加\n\n- **桌面走线夹** ¥49（整理线缆）\n- **桌面保护垫** ¥49（防划不用再买桌垫）",
    ["傲风人体工学椅4D扶手+月销1.5万，游戏工作5-8h肩颈保护核心投资", "爱格升双显示器铝合金支架+月销3500，桌面空间整洁颈椎高度可调", "漫步者R1000BT 2.1声道低音炮+月销1.2万，游戏爆炸枪声有重量感", "Nanoleaf RGB灯板9片+月销2200，背景墙氛围灯减少视觉疲劳"]
))

# 8. bundle
T.append(make_traj(
    "sft_bundle_054", "bundle_purchase", "组合购物",
    "2000 元宝宝辅食制作全套",
    "宝宝 6 个月开始添加辅食，2000 配齐辅食机+蒸锅+餐具+研磨",
    {"query": "宝宝辅食制作工具 辅食机+蒸锅+餐具", "max_price": 2200},
    [
        {"product_id": "mock_food_1", "title": "Beaba 辅食机 蒸煮搅打 四合一", "price": 899, "is_platform_self": True, "rating": 4.9, "key_specs": "蒸+煮+搅+热四合一/法国品牌/食品级/月销1500", "sales": "月销1500"},
        {"product_id": "mock_food_2", "title": "贝亲 婴儿餐具套装 碗+勺+叉 5件", "price": 129, "is_platform_self": True, "rating": 4.9, "key_specs": "软头勺/防滑碗/5件套/6月+适用", "sales": "月销4.5万"},
        {"product_id": "mock_food_3", "title": "宝宝辅食研磨碗 手动 陶瓷 研磨组", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "陶瓷手动研磨/无电机/食物纤维保留更好", "sales": "月销3500"},
        {"product_id": "mock_food_4", "title": "硅胶辅食冰格 密封储存 20格", "price": 69, "is_platform_self": True, "rating": 4.9, "key_specs": "20格硅胶/冷冻储存/一格一份/辅食囤货", "sales": "月销2.2万"},
        {"product_id": "mock_food_5", "title": "婴儿硅胶围兜 自带兜 防漏 6月+", "price": 59, "is_platform_self": True, "rating": 4.9, "key_specs": "硅胶/自带兜/防漏/一抹就干净/月销3万", "sales": "月销3万"}
    ],
    "宝宝辅食工具 5 件套 ¥1245，余 ¥755：\n\n## 🥣 完整方案\n\n| 工具 | 商品 | 价格 | 用途 |\n|---|---|---|---|\n| 🥇 辅食机 | Beaba 四合一 | ¥899 | 蒸熟+打泥一步完成 |\n| 餐具 | 贝亲 5 件套 | ¥129 | 喂饭专用 |\n| 研磨碗 | 陶瓷手动 | ¥89 | 少量临时研磨 |\n| 冰格 | 硅胶 20 格 | ¥69 | 辅食批量制作冷冻 |\n| 围兜 | 硅胶自带兜 | ¥59 | 防止辅食弄脏衣服 |\n\n## 💡 辅食机是最重要的投资\n\n**Beaba 四合一**：倒入食材→蒸熟→自动打泥，**整个流程 15 分钟内完成**。比手动研磨+分开蒸快 3 倍，打出的泥更细腻（6 个月宝宝只能接受极细泥）。\n\n## 💡 辅食冰格是省时神器\n\n**周末一次做一周的辅食量**，用硅胶冰格分格冷冻，每格正好一餐。吃前热一格，省去每天现做。\n\n## 💡 硅胶围兜的优势\n\n布围兜需要洗，**硅胶围兜一抹就干净**，自带兜兜住落下的食物，宝宝学自己吃饭必备。\n\n## 💰 余 ¥755 用于\n\n- **婴儿辅食食材**（南瓜/胡萝卜/土豆/苹果等）¥200\n- **婴儿橄榄油**（拌辅食用）¥80\n- **骨汤/蔬菜汤底**（给辅食加味）¥100\n- **儿科复诊**（6 个月体检+医生指导辅食添加顺序）",
    ["Beaba辅食机四合一蒸+打泥+月销1500，辅食制作15分钟最省时", "贝亲婴儿餐具软头勺5件套+月销4.5万，喂饭护牙龈防误伤", "陶瓷手动研磨碗+月销3500，少量临时研磨纤维保留更好", "硅胶辅食冰格20格+月销2.2万，周末一次做一周的量批量冷冻", "硅胶围兜自带兜防漏+月销3万，硅胶一抹干净学自己吃饭必备"]
))

# 9. place_order
T.append(make_traj(
    "sft_order_029", "place_order", "购物下单",
    "订单合并+地址统一",
    "我同时在购物车有 3 件东西想一起下单，到同一个地址",
    {"items": ["mock_item_a", "mock_item_b", "mock_item_c"], "address": "DEFAULT", "merge_order": True},
    [
        {"product_id": "mock_merged_001", "title": "合并订单：3 件商品同地址下单", "price": 0, "is_platform_self": True, "rating": 5.0, "key_specs": "已合并3件/同地址/订单号[TRACKING_ID]-MERGED-2284/预计明天送达", "sales": "—"}
    ],
    "✅ 3 件商品已合并到同一订单！\n\n## 📦 合并订单详情\n\n- **订单号**：[TRACKING_ID]-MERGED-2284\n- **收货地址**：默认地址\n- **商品**：3 件（已全部确认）\n- **预计送达**：明天\n\n## 💡 关于「合并下单」\n\n### 什么可以合并\n- ✅ **同一卖家（平台自营）** → 自动合并，一票发货\n- ✅ **不同商品同类物流** → 系统合并，减少拆包\n- ❌ **不同第三方卖家** → 无法合并（各自发货）\n\n### 合并发货 vs 分开发货\n\n| 情况 | 建议 |\n|---|---|\n| 3 件都是平台自营 | **自动合并**，一箱到达 |\n| 有第三方卖家 | 各自发货，时间可能不同 |\n| 急用某一件 | **分开下单**，那件优先发 |\n\n## 💰 合并的好处\n\n1. **减少包装垃圾**（环保）\n2. 签收**一次拆箱**（省时）\n3. 部分促销满减**合并金额触发**（省钱）\n\n## ⚠️ 合并注意\n\n- 合并订单后，退一件需要**申请拆分退款**\n- 如果有一件到货慢，整单会等最慢的那件\n- 急用的东西建议**单独下单**\n\n## 💡 购物平台购物车技巧\n\n**「凑满减」** 时利用购物车合并：\n- 多件商品同时勾选结算\n- 跨店满减自动计算\n- **凑单后再确认支付**\n\n你的这 3 件已经最优合并发货，明天到！",
    ["合并3件商品同地址+订单[TRACKING_ID]-MERGED-2284+明天送达，已自动合并一次拆箱"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase
T.append(make_traj(
    "sft_repurchase_027", "repurchase", "复购召回",
    "复购宠物食品+品牌替代推荐",
    "猫咪的那个零食没了，再买一包，但听说有新品更好吃",
    {"category_keyword": "猫咪零食", "time_range": "last_2_months", "show_new_products": True},
    [
        {"product_id": "mock_cat_snack_old", "title": "乐可滋 冻干零食 鸡肉 50g (你1月前购买)", "price": 39, "is_platform_self": True, "rating": 4.9, "key_specs": "你1月前购买/订单[ORDER_ID]/冻干鸡肉", "sales": "月销2万"},
        {"product_id": "mock_cat_snack_new", "title": "乐可滋 新品冻干三文鱼 50g 2026年款", "price": 45, "is_platform_self": True, "rating": 4.9, "key_specs": "新品2026款/三文鱼冻干/Omega-3更高/月销5000", "sales": "月销5000"},
        {"product_id": "mock_cat_snack_mix", "title": "猫咪零食混合大礼包 10种口味 500g", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "10种口味/500g大包/换着喂不厌食", "sales": "月销4500"}
    ],
    "你 1 个月前买的是**乐可滋冻干鸡肉零食 ¥39**（订单 [ORDER_ID]）。\n\n## 🐱 新品推荐\n\n**乐可滋刚出了 2026 年新品：冻干三文鱼款 ¥45**：\n- 原料换成三文鱼（比鸡肉多 Omega-3，对皮毛更好）\n- 冻干工艺相同\n- 比鸡肉款贵 ¥6\n\n**要不要换成三文鱼口味？**\n\n## 💡 猫咪零食换口味建议\n\n猫咪和人一样会腻，**长期同一种零食猫会不感兴趣**（兴奋度降低）。建议：\n- 一种口味连续喂 2-3 个月 → 换一种\n- **交替喂**（今天鸡肉，明天三文鱼）保持新鲜感\n\n## 🎁 大礼包方案 ¥99\n\n**10 种口味混合大礼包**：\n- 500g，单 g 价格和 50g 小包一样\n- **10 种口味轮换**，猫咪永远觉得新鲜\n- 适合对零食挑剔的猫\n\n## 🎯 我的建议\n\n- **猫咪吃鸡肉没问题，只是用来训练/当零食** → 继续买鸡肉款 ¥39（省 ¥6）\n- **猫咪皮毛状态一般，想补充 Omega-3** → 试试三文鱼新品 ¥45\n- **猫咪对零食挑剔/容易腻** → 大礼包 ¥99 一次解决\n\n你猫咪对现在这款零食反应怎么样（还积极抢吃吗）？",
    ["乐可滋冻干鸡肉你1月前购买+月销2万，继续复购同款稳定", "乐可滋新品冻干三文鱼2026款+Omega-3更高+月销5000，换口味+营养升级", "猫咪零食混合大礼包10种口味500g+月销4500，挑剔猫咪换着喂不腻"],
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
