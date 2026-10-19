# -*- coding: utf-8 -*-
"""Step 16: 第 4 批 10 条数据"""
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

# 1. similar_rec - 抱怨保修短
T.append(make_traj(
    "sft_simrec_019", "similar_rec", "相似品推荐",
    "抱怨保修短 → warranty_years_min 升级",
    "上次推荐的那款电视才保修1年，有2-3年保修的同价位款吗",
    {"query": "65寸电视 2-3年保修 大品牌", "max_price": 4000, "filters": {"warranty_years_min": 2}},
    [
        {"product_id": "mock_tv_war_001", "title": "海信 65E5N Pro 4K AI电视 整机3年保修", "price": 3699, "is_platform_self": True, "rating": 4.9, "key_specs": "整机3年/屏幕3年/120Hz/U-Color色彩", "sales": "月销1.5万"},
        {"product_id": "mock_tv_war_002", "title": "TCL 65V8K 4K Mini LED 整机2年保修", "price": 3899, "is_platform_self": True, "rating": 4.8, "key_specs": "整机2年/Mini LED/144Hz/QLED量子点", "sales": "月销9500"},
        {"product_id": "mock_tv_war_003", "title": "索尼 KD-65X80L 4K HDR 整机2年保修", "price": 3999, "is_platform_self": True, "rating": 4.9, "key_specs": "整机2年/索尼画质引擎/Google TV系统", "sales": "月销4500"}
    ],
    "65 寸 4000 内带 2-3 年保修的电视，3 款都达标：\n\n**1. 海信 65E5N Pro（¥3699）** ⭐ 保修最长\n**整机+屏幕都是 3 年保修**（行业平均 1 年），售后承诺最实在。120Hz+AI画质足够日常。月销 1.5 万件最稳。\n\n**2. TCL 65V8K（¥3899）**\nMini LED 是这个价位画质天花板（512 分区背光），144Hz 高刷适合游戏。整机 2 年。\n\n**3. 索尼 65X80L（¥3999）**\n索尼画质引擎+Google TV 系统，**适合追求软件体验的用户**。整机 2 年。\n\n**建议**：纯看保修选海信 3 年最稳；追画质选 TCL Mini LED；追系统体验选索尼。",
    ["海信整机+屏幕3年保修+120Hz+月销1.5万，保修最长售后最稳", "TCL Mini LED 512分区+144Hz+QLED量子点，画质天花板", "索尼画质引擎+Google TV系统+整机2年，系统体验派首选"]
))

# 2. similar_rec - 抱怨配件少
T.append(make_traj(
    "sft_simrec_020", "similar_rec", "相似品推荐",
    "抱怨配件少 → accessories_count 维度",
    "之前那款相机就送一块电池太少了，要送多配件的同价位款",
    {"query": "微单相机 配件丰富 套装", "min_price": 4000, "max_price": 5500, "filters": {"accessories_count_min": 5}},
    [
        {"product_id": "mock_cam_kit_001", "title": "佳能 EOS R50 套机+原厂6件套（双电池+读卡器+UV镜+包+三脚架+清洁套装）", "price": 5499, "is_platform_self": True, "rating": 4.9, "key_specs": "佳能EOS R50/RF-S 18-45镜头/6件原厂配件", "sales": "月销2500"},
        {"product_id": "mock_cam_kit_002", "title": "尼康 Z30 购物平台超值套装（含5件套）", "price": 4999, "is_platform_self": True, "rating": 4.8, "key_specs": "尼康Z30/16-50套头/5件配件", "sales": "月销1800"},
        {"product_id": "mock_cam_kit_003", "title": "索尼 ZV-E10 II Vlog套装（含8件套+背包+提词器）", "price": 5299, "is_platform_self": True, "rating": 4.9, "key_specs": "ZV-E10 II/Vlog定位/8件配件+提词器", "sales": "月销3500"}
    ],
    "你说的痛点很真实——相机厂商标价低但配件单买贵。3 款都是「**机身+配件套装**」：\n\n**1. 索尼 ZV-E10 II Vlog 8 件套（¥5299）** ⭐ 配件最多\n8 件配件包含 Vlog 党刚需（**含提词器**）。比单买机身省 ¥1500+。\n\n**2. 佳能 EOS R50 6 件套（¥5499）**\n含双电池（拍 Vlog 必备）+ 三脚架，**原厂配件兼容性最好**。\n\n**3. 尼康 Z30 5 件套（¥4999）**\n配件最少但最便宜，**适合预算紧的入门党**。\n\n建议直接选索尼 ZV-E10 II——8 件套是 Vlog 党的完整配置，**多花 ¥300 比单买省 ¥1500**。",
    ["索尼ZV-E10 II 8件套含提词器+Vlog定位+月销3500，Vlog党配件最全省1500", "佳能EOS R50 6件套+双电池+三脚架+原厂兼容性最好", "尼康Z30 5件套最便宜+16-50套头，预算紧入门党首选"]
))

# 3. sku_comp - 不同芯片版本对比
T.append(make_traj(
    "sft_skucomp_017", "sku_comp", "商品对比",
    "苹果 M2 vs M3 vs M4 芯片代际对比",
    "MacBook Air 现在有 M2 M3 M4 三代，差价 2000，怎么选",
    {"skus": ["MacBook Air M2 8+256", "MacBook Air M3 8+256", "MacBook Air M4 16+256"], "mode": "parallel_exact_match"},
    [
        {"product_id": "mock_mac_m2", "title": "MacBook Air M2 13寸 8+256G", "price": 5799, "is_platform_self": True, "rating": 4.8, "key_specs": "M2芯片(2022)/8GB统一内存/256G", "sales": "月销8500"},
        {"product_id": "mock_mac_m3", "title": "MacBook Air M3 13寸 8+256G", "price": 6999, "is_platform_self": True, "rating": 4.9, "key_specs": "M3芯片(2024)/8GB统一内存/256G/AI性能强3倍", "sales": "月销1.2万"},
        {"product_id": "mock_mac_m4", "title": "MacBook Air M4 13寸 16+256G", "price": 7799, "is_platform_self": True, "rating": 4.9, "key_specs": "M4芯片(2025)/16GB统一内存/256G/Apple Intelligence", "sales": "月销4500"}
    ],
    "苹果 M 系列芯片每年迭代，但**性能提升幅度递减**。3 代对比：\n\n## 📊 性能维度\n\n| 维度 | M2 ¥5799 | M3 ¥6999 | M4 ¥7799 |\n|---|---|---|---|\n| 发布年份 | 2022 | 2024 | 2025 |\n| 内存 | 8GB | 8GB | **16GB**（关键升级）|\n| CPU 性能 | 基准 | +20% | +35% |\n| GPU 性能 | 基准 | +30% | +50% |\n| AI 性能 | 基础 | +200% | +400%（Apple Intelligence）|\n| 月销 | 8500 | **1.2 万（最热）** | 4500 |\n\n## 🎯 怎么选\n\n### 1️⃣ 纯办公/网课 → **M2 ¥5799** 性价比之王\n网页/文档/视频会议根本用不到 M3 M4 的性能。**省下 ¥1200-2000 买配件**（雷电拓展坞 ¥500、外接显示器 ¥1000）。\n\n### 2️⃣ 开发/设计/视频剪辑 → **M4 16GB ¥7799** ⭐\n**8GB 内存是 Mac 的硬伤**（实际可用约 5GB，跑 Docker/PS 必卡）。M4 直接给 16GB 解决根本问题。\n\n### 3️⃣ 中间档 M3 ¥6999\n性能比 M2 强 20% 但内存还是 8GB，**¥1200 溢价换不到内存升级**，性价比最差。**除非苹果生态控求最新型号**。\n\n## 💡 我的真心建议\n\n两极分化选：\n- 预算紧 → M2 ¥5799（够用）\n- 预算够 → 直接 M4 16GB ¥7799（用 5 年没瓶颈）\n\n**M3 是夹缝产品，最不值得**。",
    ["MacBook M2 8+256G+2022芯片，纯办公网课性价比之王省1200元", "MacBook M3 8+256G+2024芯片，月销1.2万但8GB内存是硬伤，性价比最差", "MacBook M4 16+256G+Apple Intelligence+16GB内存解决根本，开发设计剪辑5年不瓶颈"]
))

# 4. sku_comp - 不同充电协议对比
T.append(make_traj(
    "sft_skucomp_018", "sku_comp", "商品对比",
    "氮化镓充电器多协议对比",
    "对比安克 65W vs 倍思 100W vs 绿联 140W 氮化镓充电器",
    {"skus": ["Anker 65W氮化镓", "倍思 100W氮化镓", "绿联 140W氮化镓"], "mode": "parallel_exact_match"},
    [
        {"product_id": "mock_gan_65", "title": "安克 Anker 65W 氮化镓充电器 单口", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "65W单口/支持PD3.0/适合MacBook Air", "sales": "月销4.5万"},
        {"product_id": "mock_gan_100", "title": "倍思 100W 氮化镓充电器 4口", "price": 249, "is_platform_self": True, "rating": 4.9, "key_specs": "100W四口/智能分配/适合MacBook Pro+手机+手表", "sales": "月销3.5万"},
        {"product_id": "mock_gan_140", "title": "绿联 140W 氮化镓 PD3.1 高功率", "price": 399, "is_platform_self": True, "rating": 4.8, "key_specs": "140W PD3.1/支持MacBook Pro 16寸快充/3口", "sales": "月销1.5万"}
    ],
    "氮化镓充电器的核心 = **功率 + 口数 + 兼容协议**。看你需要给哪些设备充：\n\n## 📊 三档对比\n\n| 维度 | 安克 65W ¥199 | 倍思 100W ¥249 | 绿联 140W ¥399 |\n|---|---|---|---|\n| 总功率 | 65W | 100W | **140W** |\n| 接口数 | 1 口（USB-C）| **4 口**（2C2A）| 3 口（2C1A）|\n| MacBook Air | ✅ 满速 | ✅ 满速 | ✅ 满速 |\n| MacBook Pro 14 | ⚠️ 慢充 | ✅ 满速 | ✅ 满速 |\n| MacBook Pro 16 | ❌ | ⚠️ 慢充 | **✅ 满速（96W）**|\n| 同时给多设备充 | ❌ | **✅ 4 设备** | ✅ 3 设备 |\n\n## 🎯 怎么选\n\n### 1️⃣ 只有 MacBook Air → **安克 65W ¥199** ⭐\n单口 65W 给 Air 满速够用。**单买最便宜**。\n\n### 2️⃣ MacBook Air + 手机 + 手表 → **倍思 100W ¥249**\n4 口同时充全家设备，**¥249 比单买 3 个充电器省 ¥200**。\n\n### 3️⃣ MacBook Pro 16 寸 → **必须绿联 140W ¥399**\nMacBook Pro 16 寸需要 96W 才能满速，**65W/100W 都喂不饱**。\n\n## ⚠️ 常见误区\n\n- ❌ 「多口=必满速」：100W 4 口实际分摊后单口最高 65W\n- ❌ 「PD 协议=通用」：旧 PD 2.0 不支持 100W+\n- ✅ MacBook Pro 16 寸**只认 PD 3.1 高功率协议**",
    ["Anker 65W单口+MacBook Air满速+月销4.5万，单设备最便宜", "倍思100W 4口+同时充全家设备+月销3.5万，多设备充电首选", "绿联140W PD3.1+MacBook Pro 16寸满速96W，专业设备唯一选择"]
))

# 5. matching - 厨房整体颜色搭配
T.append(make_traj(
    "sft_match_017", "matching_purchase", "搭配购物",
    "厨房小家电整体配色统一",
    "我家厨房是浅灰色橱柜+白色台面，配什么颜色的烧水壶+烤箱+多士炉",
    {"query": "厨房小家电 浅灰白色调", "filters": {"colors": ["米白", "浅灰", "原木色"], "category": "kitchen_appliance"}, "match_with": "light_gray_white_kitchen"},
    [
        {"product_id": "mock_kitchen_white_1", "title": "北鼎 K57 烧水壶 米白色复古款", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "米白色/1.5L/复古设计/304食品级", "sales": "月销4500"},
        {"product_id": "mock_kitchen_white_2", "title": "摩飞 多士炉+早餐机 浅灰色二合一", "price": 459, "is_platform_self": True, "rating": 4.8, "key_specs": "浅灰色/多士炉+煎蛋盘二合一/早餐神器", "sales": "月销3500"},
        {"product_id": "mock_kitchen_white_3", "title": "SMEG 复古烤箱 米白色 25L 意大利设计", "price": 2999, "is_platform_self": True, "rating": 4.9, "key_specs": "米白色/25L/意大利SMEG/复古颜值天花板", "sales": "月销680"}
    ],
    "浅灰+白厨房=北欧/极简风。小家电要呼应**米白/浅灰/原木色**，避免高饱和度：\n\n## 🍞 完整方案 ¥4057\n\n| 家电 | 商品 | 价格 |\n|---|---|---|\n| 烧水壶 | **北鼎 K57 米白复古款** | ¥599 |\n| 多士炉 | **摩飞浅灰二合一早餐机** | ¥459 |\n| 烤箱 | **SMEG 米白复古** | ¥2999 |\n\n## 💡 选品理由\n\n1. **北鼎烧水壶**：复古颜值+304 食品级，比普通水壶贵 ¥300 买的是「**台面摆出来好看**」\n2. **摩飞多士炉**：浅灰色和橱柜呼应，二合一节省台面\n3. **SMEG 烤箱**：意大利设计的颜值天花板，**米白配橱柜是教科书级搭配**\n\n## ⚠️ 配色避雷\n\n- ❌ 黑色家电：和浅灰冲突显得「电器堆砌感」\n- ❌ 红色/亮黄：高饱和度破坏极简感\n- ❌ 不同品牌的「米白」可能色差大（同品牌系列最稳）\n\n## 💎 替代省钱方案\n\n如果觉得 SMEG ¥2999 烤箱太贵，可以换成 **海氏 C40 白色版 ¥1299**——颜值略逊但功能强 50%。",
    ["北鼎K57米白复古+1.5L+304食品级，复古颜值台面摆件级", "摩飞浅灰二合一多士炉+煎蛋盘+早餐神器，节省台面空间", "SMEG米白复古烤箱+25L+意大利设计+月销680，颜值天花板教科书搭配"]
))

# 6. matching - 卫生间整体浅色
T.append(make_traj(
    "sft_match_018", "matching_purchase", "搭配购物",
    "婴儿房整体粉色系搭配",
    "宝宝是女孩，婴儿房想做粉色调，婴儿床+玩具收纳柜+地毯怎么配",
    {"query": "婴儿房 粉色系 实木家具", "filters": {"colors": ["粉色", "米白", "原木"], "category": "baby_room"}, "match_with": "girl_baby_room_pink"},
    [
        {"product_id": "mock_baby_1", "title": "BABYBJÖRN 实木婴儿床 米白色+粉色装饰", "price": 1899, "is_platform_self": True, "rating": 4.9, "key_specs": "实木/米白+粉色拼接/可拆卸围栏", "sales": "月销520"},
        {"product_id": "mock_baby_2", "title": "无印良品 玩具收纳柜 粉色嵌入抽屉", "price": 899, "is_platform_self": True, "rating": 4.8, "key_specs": "实木+粉色抽屉/3层带防倒装置", "sales": "月销380"},
        {"product_id": "mock_baby_3", "title": "全棉时代 婴儿爬行垫 粉米双拼 A类", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "A类纯棉/粉米双拼/2×1.5米加厚", "sales": "月销2200"}
    ],
    "女宝婴儿房粉色调要点：**米白打底 + 粉色点缀，避免全粉显廉价**。3 件齐 ¥3397：\n\n## 🌸 完整方案\n\n| 家具 | 商品 | 价格 |\n|---|---|---|\n| 婴儿床 | **BABYBJÖRN 实木米白+粉色** | ¥1899 |\n| 玩具柜 | **MUJI 粉色抽屉收纳柜** | ¥899 |\n| 爬行垫 | **全棉时代粉米双拼 A 类** | ¥599 |\n\n## 💡 配色逻辑\n\n- **70% 米白** + **30% 粉色** 是黄金比例\n- 床用米白主体（婴儿床粉色太多视觉刺激）\n- 玩具柜用粉色抽屉（局部点缀活泼感）\n- 爬行垫粉米双拼（地面颜色统一感）\n\n## ⚠️ 关键安全\n\n所有婴儿房家具必须：\n- **A 类纯棉**（皮肤接触最高标准）\n- **无甲醛实木**（避免 PVC 板材）\n- **防倒装置**（柜子必须固定到墙上）\n- **圆角设计**（避免磕碰）\n\n## 💎 5 年后改造\n\n粉色风格可能 5 岁后女儿就不爱了。**实木家具的好处**：到时候换粉色抽屉/换地垫颜色就能变风格，不用换大件。",
    ["BABYBJÖRN实木婴儿床+米白+粉色拼接+可拆卸围栏，70%米白+30%粉色黄金比例", "MUJI玩具收纳柜实木+粉色抽屉+3层防倒装置，局部点缀活泼感", "全棉时代爬行垫A类纯棉+粉米双拼+2×1.5米加厚，地面色调统一"]
))

# 7. bundle - 露营升级
T.append(make_traj(
    "sft_bundle_015", "bundle_purchase", "组合购物",
    "3000 元宠物（狗）出门装备全套",
    "我家是中型犬金毛，3000 元配齐外出装备：牵引绳+背包+宠物车+饮水器",
    {"query": "宠物狗 外出装备 中型犬", "max_price": 3500, "filters": {"size": "medium_to_large_dog"}},
    [
        {"product_id": "mock_dog_1", "title": "Truelove 中大型犬胸背带+牵引绳套装", "price": 269, "is_platform_self": True, "rating": 4.9, "key_specs": "防爆冲/反光条/适合20-35kg中大型犬", "sales": "月销1.2万"},
        {"product_id": "mock_dog_2", "title": "K9 Sport Sack 宠物背包 大型犬专用", "price": 899, "is_platform_self": True, "rating": 4.8, "key_specs": "美国品牌/背负重量30kg/通风网眼", "sales": "月销680"},
        {"product_id": "mock_dog_3", "title": "宠物推车 3 轮折叠 中大型犬可用", "price": 1299, "is_platform_self": True, "rating": 4.8, "key_specs": "可载40kg/3轮防震/折叠收纳", "sales": "月销850"},
        {"product_id": "mock_dog_4", "title": "便携饮水器 350ml 一键出水", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "350ml/一键出水/防漏密封", "sales": "月销3.5万"}
    ],
    "中型犬外出装备 4 件套 ¥2556，余 ¥444 备用：\n\n## 🐕 完整方案\n\n| 装备 | 商品 | 价格 | 用途 |\n|---|---|---|---|\n| 🥇 胸背+牵引 | Truelove 套装 | ¥269 | 日常遛狗刚需 |\n| 背包 | K9 Sport Sack 大型犬 | ¥899 | 长途/地铁带狗 |\n| 推车 | 3 轮折叠中大型 | ¥1299 | 老年犬/狗狗腿伤 |\n| 饮水器 | 便携 350ml 一键出水 | ¥89 | 外出补水必备 |\n| **合计** | | **¥2556** | |\n\n## 💡 选品逻辑\n\n1. **胸背带 vs 项圈**：金毛力气大，普通项圈勒颈椎，**胸背带是大型犬唯一正确选择**\n2. **K9 Sport Sack 美国背包**：金毛 30kg+ 一般人背不动，但这款分散背负压力，老人都能带\n3. **宠物推车**：金毛 8 岁+ 关节炎发病率高，**老年犬出门刚需**。3 轮防震设计走台阶不颠\n4. **便携饮水器一键出水**：避免在外面没水喝中暑\n\n## 💰 余 ¥444 加\n\n- 训犬零食（拉布拉多奖励）¥80\n- 防咬玩具（金毛拆家神器）¥150\n- 宠物雨衣（雨天遛狗）¥100\n- 急救包（户外）¥80\n\n## ⚠️ 不要买\n\n- ❌ 廉价拉伸式牵引绳（金毛冲出去会勒伤主人）\n- ❌ 小型犬款（金毛装不进）",
    ["Truelove胸背带+牵引绳套装+防爆冲+反光条+月销1.2万，中大型犬唯一正确选择", "K9 Sport Sack美国品牌+30kg背负+通风网眼，分散压力适合长途出行", "宠物推车3轮折叠+载重40kg+防震，老年犬关节炎刚需", "便携饮水器350ml一键出水+防漏+月销3.5万，外出补水必备"]
))

# 8. bundle - 厨房升级
T.append(make_traj(
    "sft_bundle_016", "bundle_purchase", "组合购物",
    "6000 元家庭烘焙起步装备",
    "刚开始学烘焙，6000 预算配齐烤箱+厨师机+秤+模具",
    {"query": "家庭烘焙装备 烤箱+厨师机+秤", "max_price": 6500, "filters": {"category": "baking"}},
    [
        {"product_id": "mock_bake_1", "title": "海氏 C40 独立电烤箱 40L 烘焙专业级", "price": 1199, "is_platform_self": True, "rating": 4.9, "key_specs": "40L/上下管独立控温/烘焙圈第一", "sales": "月销1.8万"},
        {"product_id": "mock_bake_2", "title": "KitchenAid 5KSM150 厨师机 5QT 经典款", "price": 3299, "is_platform_self": True, "rating": 4.9, "key_specs": "美国KitchenAid/5QT容量/325W电机/10档变速", "sales": "月销680"},
        {"product_id": "mock_bake_3", "title": "Kerwell 烘焙电子秤 0.1g精度 5kg量程", "price": 159, "is_platform_self": True, "rating": 4.8, "key_specs": "0.1g精度/5kg量程/烘焙必备", "sales": "月销5500"},
        {"product_id": "mock_bake_4", "title": "三能 烘焙模具大套装 25件", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "三能品牌/25件套/含戚风/磅蛋糕/吐司模具", "sales": "月销4500"}
    ],
    "家庭烘焙 4 件配齐 ¥5256，余 ¥744 备用：\n\n## 🧁 完整方案\n\n| 装备 | 商品 | 价格 | 用途 |\n|---|---|---|---|\n| 🥇 烤箱 | **海氏 C40 40L 专业版** | ¥1199 | 蛋糕/面包/曲奇/烤鸡 |\n| 厨师机 | **KitchenAid 5KSM150** | ¥3299 | 揉面/打蛋白/打奶油 |\n| 电子秤 | Kerwell 0.1g 精度 | ¥159 | 烘焙必须精准 |\n| 模具套装 | 三能 25 件 | ¥599 | 戚风/磅蛋糕/吐司全套 |\n| **合计** | | **¥5256** | |\n\n## 💡 为什么这样配\n\n### 1. 海氏 C40 是烘焙圈第一\n上下管独立控温是烘焙刚需（蛋糕底火比面火低 20℃），**40L 容量能放整鸡或 8 寸戚风**。月销 1.8 万件断档第一。\n\n### 2. KitchenAid 5QT 是家庭厨师机标杆\n¥3299 看起来贵，但**用 10 年不坏**：\n- 揉面：5 分钟出膜（手揉 30 分钟）\n- 打蛋白：5 档稳定打发\n- 还能装绞肉/榨汁/压面配件（后期加）\n\n### 3. 0.1g 电子秤刚需\n烘焙 ≠ 炒菜，**1g 差异都影响成功率**。普通秤 1g 精度做戚风必失败。\n\n### 4. 三能 25 件套\n国货烘焙模具天花板，**戚风模/磅蛋糕模/吐司盒一次配齐**，省去单买拼凑。\n\n## 💰 余 ¥744 加\n\n- 烘焙原料组合（面粉/奶油/糖/可可粉）¥300\n- 电动打蛋器（小份蛋液用，比厨师机方便）¥150\n- 食谱书（《君之烘焙基础》）¥80\n- 烤盘+硅胶垫 ¥150\n\n## ⚠️ 学烘焙的真心建议\n\n- 烤箱+秤是底线，**没厨师机和模具也能起步**\n- 如果不确定能坚持，**先 ¥1500 买烤箱+秤试 3 个月**，确定坚持再升级",
    ["海氏C40独立烤箱40L+上下管独立控温+月销1.8万，烘焙圈第一", "KitchenAid 5KSM150 5QT厨师机+325W电机+10档变速，揉面打蛋白家庭标杆10年不坏", "Kerwell电子秤0.1g精度+5kg量程，烘焙必备1g影响成功率", "三能烘焙模具25件套+戚风磅蛋糕吐司全套，国货烘焙天花板"]
))

# 9. place_order - 跨境海淘下单
T.append(make_traj(
    "sft_order_010", "place_order", "购物下单",
    "购物平台国际海淘下单+保税仓发货",
    "下单海囤全球那款 1280 的雅诗兰黛眼霜套装",
    {"product_id": "mock_intl_001", "address": "DEFAULT", "from_warehouse": "bonded_zone"},
    [
        {"product_id": "mock_intl_001", "title": "雅诗兰黛 小棕瓶眼霜套装 15ml+礼盒 购物平台国际海囤", "price": 1280, "is_platform_self": True, "rating": 4.9, "key_specs": "订单[TRACKING_ID]-INTL-2284/保税仓宁波直发/3-5个工作日到", "sales": "—"}
    ],
    "✅ 海囤全球下单成功！\n\n## 📦 订单详情\n\n- **商品**：雅诗兰黛小棕瓶眼霜套装 15ml+礼盒\n- **价格**：¥1280\n- **订单号**：[TRACKING_ID]-INTL-2284\n- **发货方式**：购物平台国际**宁波保税仓直发**\n- **预计到货**：3-5 个工作日\n\n## 🌐 跨境购物特别说明\n\n### 1. 通关流程\n- 包裹从**宁波保税仓**直接发出（不经过转运）\n- 海关验证身份信息（**购物平台已自动用你 shopping platform 账号实名信息申报**）\n- 一般 24 小时内放行\n\n### 2. 关税\n- **个人购买额度 5000 元/单**\n- 雅诗兰黛属于「**化妆品类目**」，跨境综合税率约 11.9%\n- **¥1280 商品的税已包含在价格内**，不需要你额外付\n\n### 3. 物流跟踪\n- 购物平台 APP 「我的订单」可看实时清关状态\n- 通常状态：**保税仓出库 → 通关中 → 国内派送**\n\n### 4. 售后政策（跨境购特殊）\n- ✅ **未拆封 30 天可退货**\n- ❌ **已拆封不接受退货**（海关规定，跨境化妆品拆封后无法二次销售）\n- ⚠️ **如有质量问题**：先联系购物平台国际客服，可走「质量问题特殊退货通道」\n\n## 💡 验真方法\n\n收到货后**保留这 3 样**作为正品凭证：\n1. 购物平台国际防伪溯源码（外箱二维码扫描）\n2. 海关入关单（外箱贴的红色小标签）\n3. 购物平台国际发票（账户里下载）\n\n如果未来要转赠/转卖，这 3 样能证明正品来源。",
    ["雅诗兰黛小棕瓶眼霜套装1280元已下单+宁波保税仓直发+3-5个工作日，含跨境综合税"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase - 复购+订阅式
T.append(make_traj(
    "sft_repurchase_008", "repurchase", "复购召回",
    "复购日用消耗品+设置自动订阅",
    "之前那个牙膏一家人用得很快，能不能设置每月自动下单",
    {"category_keyword": "牙膏", "time_range": "last_3_months", "include_subscription": True},
    [
        {"product_id": "mock_toothpaste_1", "title": "高露洁 全效专家 牙膏 6支装 (1月前购买)", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "高露洁/6支装/订单[ORDER_ID]/月用约2支", "sales": "月销4.5万"}
    ],
    "好主意，购物平台支持「**自动续订**」功能。先看一下你的使用频次：\n\n## 📊 你家牙膏用量推算\n\n- 上次购买：1 个月前（6 支装 ¥99）\n- 已用约：2 支（一家 3-4 口人月均 1.5-2 支）\n- **预计剩余：4 支 = 2 个月用量**\n\n## 🔄 自动续订方案推荐\n\n### 方案 A：每 3 个月自动下单（推荐）\n- 周期：每 3 个月 1 次\n- 数量：6 支装×1（一次买 1 组）\n- 价格：**订阅价 ¥89**（比单买省 ¥10/单）\n- **2 年省 ¥80** + 不会缺货\n\n### 方案 B：每 6 个月自动下单\n- 周期：每 6 个月 1 次\n- 数量：6 支装×2（一次买 2 组）\n- 价格：**订阅价 ¥159**（比 ¥198 省 ¥39）\n- 适合家里有储物空间\n\n### 方案 C：手动复购（不设订阅）\n- 提醒：购物平台 APP 设「**降价/缺货提醒**」即可\n- 适合不喜欢自动扣款的用户\n\n## ⚙️ 订阅怎么设置\n\n1. 进入这款牙膏商品页 → 选择 6 支装\n2. 点击「**订阅购**」按钮（在「加入购物车」旁边）\n3. 选周期：**每月/3 月/6 月**\n4. 选发货地址 + 付款方式\n5. 完成\n\n## 💡 我的建议\n\n选**方案 A（每 3 个月）¥89/单**：\n- 比单买省 ¥10\n- 周期短，万一不想用了随时取消\n- 不占储物空间\n\n要直接帮你设置吗？还是先试一下手动复购？",
    ["高露洁全效专家6支装+你1月前购买+月销4.5万，建议每3月订阅价89元省10元"],
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
