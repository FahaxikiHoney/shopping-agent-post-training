# -*- coding: utf-8 -*-
"""Step 27: 第 15 批 10 条"""
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

# 1. similar_rec - 抱怨没存货
T.append(make_traj(
    "sft_simrec_041", "similar_rec", "相似品推荐",
    "抱怨断货 → 同店同款替代",
    "想买那款 Lululemon 瑜伽裤但断货 1 个月了，有同店现货同款吗",
    {"query": "Lululemon同款瑜伽裤 现货", "exclude_skus": ["Align断货款"], "filters": {"stock_status": "available"}},
    [
        {"product_id": "mock_yoga_alt_1", "title": "Lululemon Wunder Train 25 寸 黑色 现货", "price": 798, "is_platform_self": True, "rating": 4.9, "key_specs": "Wunder Train系列/裸感面料/同品牌现货款", "sales": "月销1500"},
        {"product_id": "mock_yoga_alt_2", "title": "Lululemon Fast and Free 高腰跑步裤", "price": 998, "is_platform_self": True, "rating": 4.9, "key_specs": "Fast and Free/隐藏口袋/跑步专用", "sales": "月销850"},
        {"product_id": "mock_yoga_alt_3", "title": "Maia Active 高腰提臀瑜伽裤 国货", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "国货Maia Active/Lululemon平替之王", "sales": "月销4500"}
    ],
    "Align 经典款断货很正常。3 款替代：\n\n**1. Lululemon Wunder Train ¥798** ⭐ 同品牌现货\n**Lululemon 同品牌不同系列**，Wunder Train 是 Align 升级版（更硬挺更显瘦）。月销 1500。\n\n**2. Lululemon Fast and Free ¥998**\n跑步功能更专业，**隐藏口袋**装钥匙/手机。\n\n**3. Maia Active 国货平替 ¥399** 性价比之王\n国货品牌，**面料和裁剪 90% 还原 Lululemon**，价格一半。\n\n## 💡 选择逻辑\n\n- **认 Lululemon 品牌** → Wunder Train ¥798\n- **想要更专业功能** → Fast and Free ¥998\n- **省钱党** → Maia Active ¥399（贴身穿，**没人看品牌 logo**）\n\n建议先试 Maia Active ¥399——**90% 效果，50% 价格**。",
    ["Lululemon Wunder Train 25寸黑色+裸感面料+月销1500，同品牌Align升级版现货", "Lululemon Fast and Free+隐藏口袋+月销850，跑步专业款", "Maia Active国货+Lululemon平替之王+月销4500，90%效果50%价格"]
))

# 2. similar_rec - 抱怨包装糟
T.append(make_traj(
    "sft_simrec_042", "similar_rec", "相似品推荐",
    "抱怨包装差 → 礼盒装/精装版",
    "上次买送礼那款茶叶包装太简陋了，要礼盒装的同价位款",
    {"query": "茶叶礼盒装 送礼 包装精美", "max_price": 800, "filters": {"gift_packaging": True}},
    [
        {"product_id": "mock_tea_box_1", "title": "八马 铁观音 礼盒装 250g 送礼专款", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "八马品牌/精美礼盒/含手提袋/适合送礼", "sales": "月销2200"},
        {"product_id": "mock_tea_box_2", "title": "天福茗茶 大红袍 礼盒+定制贺卡", "price": 699, "is_platform_self": True, "rating": 4.9, "key_specs": "天福茗茶/大红袍/含定制贺卡服务", "sales": "月销1500"},
        {"product_id": "mock_tea_box_3", "title": "西湖龙井 明前狮峰山 礼盒款 100g", "price": 798, "is_platform_self": True, "rating": 4.9, "key_specs": "正宗西湖龙井/明前狮峰山/桐木礼盒", "sales": "月销850"}
    ],
    "送礼茶叶 = **茶 + 包装一样重要**。3 款礼盒：\n\n**1. 八马铁观音 ¥599** ⭐ 性价比首选\n大牌+精美礼盒+手提袋，**送领导/客户最稳**。月销 2200。\n\n**2. 天福茗茶大红袍 ¥699**\n**含定制贺卡服务**（写收礼人名字+祝福），**最有心意**。\n\n**3. 西湖龙井明前狮峰山 ¥798**\n正宗产地+桐木礼盒，**茶圈认可度最高**。送内行最显档次。\n\n## 💡 选茶送礼公式\n\n```\n收礼人是：\n├── 领导/客户（不熟）→ 八马铁观音（大众接受）\n├── 长辈/老茶客 → 西湖龙井明前（行家认）\n└── 朋友（关系好）→ 天福茗茶（有定制贺卡）\n```\n\n## ⚠️ 送茶避坑\n\n- ❌ **大红色礼盒**（俗气）\n- ❌ **散茶包装**（送不出手）\n- ❌ **超过 ¥1500**（显得贿赂）\n- ❌ **保质期短的绿茶夏天送**（高温易变质）",
    ["八马铁观音礼盒+手提袋+月销2200，送领导客户最稳大众接受", "天福茗茶大红袍+定制贺卡服务+月销1500，送朋友最有心意", "西湖龙井明前狮峰山+桐木礼盒+月销850，送老茶客最显档次"]
))

# 3. sku_comp - 同类不同档对比
T.append(make_traj(
    "sft_skucomp_039", "sku_comp", "商品对比",
    "学生平板入门 vs 旗舰对比",
    "给孩子买学习平板，¥1899 华为 MatePad 11.5 vs ¥3299 旗舰版",
    {"skus": ["华为MatePad 11.5 基础", "华为MatePad 11.5 旗舰版"], "mode": "tier_within_brand"},
    [
        {"product_id": "mock_pad_basic", "title": "华为 MatePad 11.5 标准款 8+128G", "price": 1899, "is_platform_self": True, "rating": 4.9, "key_specs": "11.5寸/8+128G/2.5K护眼屏/学习中心", "sales": "月销2.3万"},
        {"product_id": "mock_pad_pro", "title": "华为 MatePad 11.5 PaperMatte 旗舰版", "price": 3299, "is_platform_self": True, "rating": 4.9, "key_specs": "PaperMatte类纸屏/含手写笔+键盘/旗舰版", "sales": "月销1200"}
    ],
    "**结论：学生用基础款 ¥1899 够用，旗舰版仅深度用户值**：\n\n## 📊 关键差异\n\n| 维度 | 基础款 ¥1899 | 旗舰版 ¥3299 |\n|---|---|---|\n| 屏幕 | 普通 2.5K | **PaperMatte 类纸屏**（不反光）|\n| 配件 | 无 | **含手写笔+键盘**（值 ¥800）|\n| 性能 | 同等 | 同等 |\n| 月销 | **2.3 万** | 1200 |\n\n## 💰 ¥1400 差价拆解\n\n- PaperMatte 类纸屏：约 ¥600 溢价\n- 手写笔（M-Pencil 2）：¥499\n- 键盘：¥299\n- 合计：¥1398（差价合理）\n\n**关键看是否需要手写笔/键盘**：\n\n### 学生需要手写笔吗？\n- **小学/初中**：80% 不需要（用笔写作业更直接）\n- **高中**：50% 需要（理科推导+笔记）\n- **大学**：80% 需要（PDF 标注+笔记）\n\n## 🎯 怎么选\n\n### ✅ 基础款 ¥1899（小学+大部分初中）\n- 上网课足够\n- 看视频清晰\n- 不需要手写笔\n- **省下 ¥1400 买学习资料**\n\n### ✅ 旗舰版 ¥3299（高中+大学）\n- PaperMatte 屏对长时间阅读护眼\n- 手写笔做数学题+笔记\n- 一次到位\n\n## 💡 真心建议\n\n大多数家长**买基础款 ¥1899 + 后期补 ¥499 手写笔**更灵活。先看孩子用平板的程度，再决定是否升级。",
    ["华为MatePad 11.5标准款+2.5K护眼屏+学习中心+月销2.3万，小学初中够用省1400", "华为MatePad 11.5 PaperMatte类纸屏+含手写笔+键盘+月销1200，高中大学一次到位"]
))

# 4. sku_comp - 性价比对比
T.append(make_traj(
    "sft_skucomp_040", "sku_comp", "商品对比",
    "Apple Watch vs 华为 GT vs 小米手环",
    "买智能手表 Apple Watch SE/华为 GT4/小米手环 8 怎么选",
    {"skus": ["Apple Watch SE 2", "华为 Watch GT4", "小米手环 8"], "mode": "ecosystem_comparison"},
    [
        {"product_id": "mock_aw_se", "title": "Apple Watch SE 2 40mm", "price": 1999, "is_platform_self": True, "rating": 4.9, "key_specs": "Apple生态/iPhone专属/月销4500", "sales": "月销4500"},
        {"product_id": "mock_hw_gt4", "title": "华为 Watch GT4 46mm 蓝牙版", "price": 1488, "is_platform_self": True, "rating": 4.9, "key_specs": "华为/14天续航/双频GPS/月销2.1万", "sales": "月销2.1万"},
        {"product_id": "mock_mi_band8", "title": "小米手环 8", "price": 269, "is_platform_self": True, "rating": 4.8, "key_specs": "小米/14天续航/基础健康/月销4.5万", "sales": "月销4.5万"}
    ],
    "**3 个完全不同档次的产品**，看你预算和生态：\n\n## 📊 三档对比\n\n| 维度 | 小米 ¥269 | 华为 ¥1488 | Apple ¥1999 |\n|---|---|---|---|\n| 形态 | 手环 | 手表 | 手表 |\n| 续航 | **14 天** | **14 天** | 1.5 天 |\n| 通话 | ❌ | 蓝牙 | ❌（SE）|\n| 月销 | **4.5 万** | 2.1 万 | 4500 |\n| 适配 | 安卓+苹果 | 主要安卓 | **仅 iPhone** |\n\n## 🎯 怎么选\n\n### iPhone 用户 → **Apple Watch SE 2 ¥1999**\n- 双击切换设备\n- iMessage 通知\n- 苹果生态闭环\n- 缺点：1.5 天续航\n\n### 安卓用户 → **华为 GT4 ¥1488**\n- 14 天续航碾压 Apple\n- 双频 GPS 精度高\n- 健康监测全面\n- 比 Apple Watch 便宜 ¥500\n\n### 预算紧/基础需求 → **小米手环 8 ¥269**\n- ¥269 一年用没问题\n- 计步/睡眠/心率基础够用\n- **比手表轻 5 倍**（晚上戴睡觉不闷）\n\n## 💡 真心建议\n\n**手环 vs 手表的本质区别**：\n- 手环：**记录健康数据**（睡眠/步数/心率）\n- 手表：**接收手机通知**（消息/电话/支付）\n\n你只需要前者 → 小米手环 ¥269（**省 ¥1700+**）\n你需要通知 → 华为或 Apple\n\n## 🏆 性价比之王\n\n**90% 的人买手表后只把它当手环用**——你需要的是手环 ¥269，不是手表。\n\n**真心问自己**：你最近 1 个月看了几次手表上的微信通知？\n如果 < 10 次，**买小米手环 ¥269 才聪明**。",
    ["Apple Watch SE 2 40mm+iPhone专属+月销4500，iPhone用户首选", "华为Watch GT4 14天续航+双频GPS+月销2.1万，安卓用户性价比", "小米手环8 14天续航+月销4.5万，预算紧/基础健康90%够用"]
))

# 5. matching - 民国风穿搭
T.append(make_traj(
    "sft_match_039", "matching_purchase", "搭配购物",
    "汉服整体搭配",
    "想穿汉服去旅游拍照，配齐汉服+配饰+发型",
    {"query": "汉服女款 古风整体搭配", "filters": {"style": "hanfu_chinese_style"}},
    [
        {"product_id": "mock_hanfu_1", "title": "重回汉唐 改良齐胸襦裙 米白款", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "重回汉唐/改良齐胸襦裙/米白色/适合日常出游", "sales": "月销850"},
        {"product_id": "mock_hanfu_2", "title": "古风发饰 步摇+发簪 套装", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "步摇+发簪+发钗/古风配饰套装", "sales": "月销2500"},
        {"product_id": "mock_hanfu_3", "title": "古风刺绣手包 团扇 套装", "price": 159, "is_platform_self": True, "rating": 4.9, "key_specs": "刺绣手包+团扇/古风拍照神器", "sales": "月销1500"},
        {"product_id": "mock_hanfu_4", "title": "汉服专用绣花布鞋 平底款", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "刺绣布鞋/平底舒适/适合走景区", "sales": "月销1200"}
    ],
    "汉服整套 4 件 ¥1156，**新手出片+实用**：\n\n## 👘 完整方案\n\n| 单品 | 商品 | 价格 |\n|---|---|---|\n| 🥇 汉服 | **重回汉唐改良齐胸襦裙** | ¥599 |\n| 发饰 | 步摇+发簪套装 | ¥199 |\n| 手包+团扇 | 古风刺绣 | ¥159 |\n| 鞋 | 绣花布鞋 | ¥199 |\n| **合计** | | **¥1156** |\n\n## 🎨 汉服穿搭新手要点\n\n### 1️⃣ 选「改良款」不选「形制党」\n- **改良齐胸襦裙**：好穿+不卡腰+月销最高\n- 形制党汉服：严格遵循古制+穿着难+太热\n- **新手第一件买改良款**\n\n### 2️⃣ 米白色是初学者王者\n- **任何景区都出片**\n- 不挑肤色\n- 避免大红大紫（容易俗）\n\n### 3️⃣ 配饰是灵魂\n- 步摇+发簪让头部丰富（**简单盘发就够**）\n- 团扇是拍照神器（遮脸+古风）\n\n### 4️⃣ 鞋必须平底\n- 景区走 1-2 万步\n- 高跟鞋汉服灾难\n- 绣花布鞋舒服+出片\n\n## 📸 汉服拍照技巧\n\n1. **景点选古镇/园林**（西塘/乌镇/苏州园林）\n2. **避免现代元素**（汽车/电线）\n3. **侧拍最显瘦**\n4. **团扇遮 1/3 脸**（神秘感）\n5. **走路而非站立**（飘逸感）\n\n## ⚠️ 汉服避雷\n\n- ❌ 内搭普通 T 恤（毁所有）\n- ❌ 现代手表/包包\n- ❌ 跟形制党争议（你穿改良别人爱怎么说）\n- ❌ 大风天穿（裙摆乱飞）",
    ["重回汉唐改良齐胸襦裙+米白色+月销850，新手汉服首选不挑肤色", "古风步摇+发簪套装+月销2500，简单盘发就够头部丰富", "古风刺绣手包+团扇+月销1500，拍照遮脸神秘感", "汉服绣花布鞋平底+月销1200，景区2万步舒适"]
))

# 6. matching - 工业风家居
T.append(make_traj(
    "sft_match_040", "matching_purchase", "搭配购物",
    "工业风客厅搭配",
    "想给客厅做成工业风，配什么沙发+茶几+灯具+地毯",
    {"query": "工业风客厅 沙发+茶几+灯具", "filters": {"style": "industrial_loft"}, "match_with": "industrial_living_room"},
    [
        {"product_id": "mock_ind_1", "title": "Loft 工业风皮沙发 复古棕 三人位", "price": 4999, "is_platform_self": True, "rating": 4.9, "key_specs": "Loft工业风/复古棕皮/三人位/月销380", "sales": "月销380"},
        {"product_id": "mock_ind_2", "title": "工业风铁艺玻璃茶几 复古黑 1.2米", "price": 999, "is_platform_self": True, "rating": 4.9, "key_specs": "铁艺+玻璃/复古黑/适合工业风", "sales": "月销520"},
        {"product_id": "mock_ind_3", "title": "Loft 工业风落地灯 复古铁艺", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "工业风/复古铁艺/可调亮度", "sales": "月销850"},
        {"product_id": "mock_ind_4", "title": "工业风羊毛地毯 几何图案 200×250", "price": 1299, "is_platform_self": True, "rating": 4.9, "key_specs": "羊毛+几何/200×250/工业风搭配", "sales": "月销680"}
    ],
    "工业风客厅 4 件套 ¥7896，**Loft 风教科书级搭配**：\n\n## 🏭 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 🥇 沙发 | **Loft 工业风皮沙发 三人位** | ¥4999 |\n| 茶几 | 铁艺玻璃 复古黑 | ¥999 |\n| 地毯 | 羊毛几何 200×250 | ¥1299 |\n| 落地灯 | 工业风铁艺 | ¥599 |\n| **合计** | | **¥7896** |\n\n## 🎨 工业风核心元素\n\n**「复古棕皮 + 黑色铁艺 + 几何 + 暖光」=工业风灵魂**\n\n### 必须遵循\n- ✅ **皮质沙发**（不能是布艺）\n- ✅ **金属元素**（铁艺/不锈钢）\n- ✅ **裸露感**（不要装饰过度）\n- ✅ **复古色调**（棕/灰/黑）\n\n### 避免\n- ❌ 北欧的木质\n- ❌ 法式的金色\n- ❌ 田园的花色\n- ❌ 大红大粉\n\n## 💡 选品理由\n\n### Loft 复古皮沙发 ¥4999\n- 工业风**沙发=皮质**是铁律\n- 复古棕和黑色铁艺呼应\n- 三人位适合 3-4 口家庭\n\n### 铁艺玻璃茶几 ¥999\n- **铁艺底座是工业风招牌**\n- 玻璃台面提亮（避免压抑）\n- 1.2 米和三人沙发匹配\n\n### 几何羊毛地毯 ¥1299\n- 几何图案 vs 简单纯色\n- 200×250 大尺寸覆盖沙发前\n- 羊毛质感比化纤高级\n\n### 工业风落地灯 ¥599\n- 复古铁艺让空间立体\n- 暖光氛围（不要冷白光）\n\n## 💎 进阶装饰（+¥2000）\n\n- **黑白摄影画**¥500（必须挂）\n- **复古铁艺墙挂时钟**¥300\n- **皮质杂志架**¥400\n- **金属装饰摆件**¥300\n- **暗色窗帘**¥500\n\n## ⚠️ 工业风成败关键\n\n工业风不是「越多铁越好」，**留白同样重要**：\n- 70% 工业元素\n- 20% 木质/皮质（温暖）\n- 10% 留白\n\n避免「**车间感**」——这套搭配比例刚好。",
    ["Loft工业风皮沙发+复古棕+三人位+月销380，工业风灵魂皮质沙发", "铁艺玻璃茶几+复古黑+1.2米+月销520，工业风招牌铁艺底座", "工业风落地灯+复古铁艺+月销850，复古铁艺让空间立体", "几何羊毛地毯200×250+羊毛+月销680，工业风搭配大尺寸"]
))

# 7. bundle - 4500 家庭健身
T.append(make_traj(
    "sft_bundle_037", "bundle_purchase", "组合购物",
    "4500 元家庭健身房升级",
    "已经有哑铃了，4500 升级到准家庭健身房，配什么器械",
    {"query": "家庭健身房 进阶 哑铃+卧推架+杠铃", "max_price": 5000, "filters": {"category": "home_gym_advanced"}},
    [
        {"product_id": "mock_gym_pro_1", "title": "家用卧推架+深蹲架 二合一 折叠款", "price": 1999, "is_platform_self": True, "rating": 4.9, "key_specs": "卧推+深蹲二合一/折叠不占地/承重300kg", "sales": "月销520"},
        {"product_id": "mock_gym_pro_2", "title": "奥林匹克杠铃杆+杠铃片 100kg 套装", "price": 1299, "is_platform_self": True, "rating": 4.9, "key_specs": "奥杆20kg+杠铃片80kg/总100kg", "sales": "月销380"},
        {"product_id": "mock_gym_pro_3", "title": "可调节哑铃凳 健身凳 折叠款", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "8档调节/折叠款/卧推/上斜下斜通用", "sales": "月销850"},
        {"product_id": "mock_gym_pro_4", "title": "瑜伽地垫 6mm 加厚 健身房专用", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "6mm加厚/防滑/2×1.5米/大尺寸", "sales": "月销1200"},
        {"product_id": "mock_gym_pro_5", "title": "助力带+护腕+护膝 健身装备包", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "助力带+护腕+护膝/重量训练必备", "sales": "月销2200"}
    ],
    "准家庭健身房 5 件套 ¥4295，**从「随便练」升级到「认真练」**：\n\n## 💪 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 🥇 卧推+深蹲架 | **二合一折叠款** | ¥1999 |\n| 杠铃 | 奥杆+杠铃片 100kg | ¥1299 |\n| 哑铃凳 | 8 档可调健身凳 | ¥599 |\n| 地垫 | 6mm 加厚瑜伽垫 | ¥199 |\n| 配件 | 助力带+护腕+护膝 | ¥199 |\n| **合计** | | **¥4295** | 余 ¥205 |\n\n## 💡 升级到家庭健身房的关键\n\n你已有哑铃做基础训练（推/拉/腿都能练），但**进阶必须有 3 件**：\n\n### 1️⃣ 卧推架（推类训练突破）\n哑铃卧推上限约 30kg/边，**杠铃卧推可达 100kg+**。健胸最有效。\n\n### 2️⃣ 深蹲架（腿部训练必需）\n深蹲是「健身之王」，**没架子做不了大重量**。\n\n### 3️⃣ 哑铃凳（解锁 80% 动作）\n上斜卧推/下斜卧推/坐姿肩推/俯身划船 = **没凳子做不了**。\n\n## 📊 升级前后对比\n\n| 训练动作 | 升级前 | 升级后 |\n|---|---|---|\n| 卧推 | 30kg×8 | **100kg×8** |\n| 深蹲 | 哑铃 40kg | **杠铃 120kg** |\n| 硬拉 | ❌ 哑铃做不了 | **120kg+** |\n| 卧推变式 | 仅平卧 | 上斜+下斜+窄距 |\n\n**力量增长速度提升 3 倍**。\n\n## 🏠 占地分析\n\n- 卧推架（折叠）：1.5×1.2m（用时展开）\n- 杠铃：2.2×0.5m（靠墙立起）\n- 哑铃凳（折叠）：0.8×0.6m\n- 地垫：2×1.5m\n\n**需要至少 4 ㎡空间**（次卧或客厅角落足够）。\n\n## ⚠️ 升级避坑\n\n### 必须遵守\n- ❌ **没保护人不做大重量卧推**（推不起来人就压死了）\n- ✅ **必须用安全杠**（卧推架自带）\n- ✅ **从小重量开始**（动作 > 重量）\n\n### 不要省\n- ❌ 廉价杠铃片**容易磕到脚**\n- ❌ 便宜卧推架**承重不足易塌**\n- ✅ 300kg 承重才安全\n\n## 💎 进阶选择（+¥3000）\n\n如果空间和预算允许：\n- 史密斯架 ¥3000-5000（带导轨更安全）\n- 引体向上杆 ¥300\n- 心率计 ¥500\n- 镜子（自检动作）¥300\n\n## 🎯 训练建议\n\n买完器械**前 1 个月找私教**：\n- 健身房月卡 ¥200-500\n- 私教课 ¥200-500/节\n- **学会标准动作再回家练**\n\n不然花 ¥4295 买了不会用的器械=废铁。",
    ["家用卧推+深蹲架二合一+折叠+300kg承重+月销520，进阶家庭健身房核心", "奥林匹克杠铃杆+100kg杠铃片+月销380，深蹲卧推硬拉重量训练必备", "可调节哑铃凳+8档调节+折叠+月销850，上斜下斜卧推坐姿肩推", "瑜伽地垫6mm加厚+2×1.5米+月销1200，健身房专用大尺寸防滑", "助力带+护腕+护膝健身装备+月销2200，重量训练保护必备"]
))

# 8. bundle - 3000 家庭办公
T.append(make_traj(
    "sft_bundle_038", "bundle_purchase", "组合购物",
    "5000 元家庭娱乐影音",
    "想给客厅升级娱乐影音，5000 配齐电视+音响+游戏机",
    {"query": "客厅影音娱乐 电视+音响+游戏机", "max_price": 5500, "filters": {"category": "entertainment_set"}},
    [
        {"product_id": "mock_ent_1", "title": "海信 65 寸 4K AI 智能电视", "price": 3299, "is_platform_self": True, "rating": 4.9, "key_specs": "65寸4K+AI画质+120Hz/客厅完美尺寸", "sales": "月销1.8万"},
        {"product_id": "mock_ent_2", "title": "JBL Bar 300 Soundbar 5.0 声道", "price": 1299, "is_platform_self": True, "rating": 4.9, "key_specs": "JBL/5.0声道/支持杜比/HDMI直连", "sales": "月销2200"},
        {"product_id": "mock_ent_3", "title": "Nintendo Switch OLED 健身环大冒险套装", "price": 2599, "is_platform_self": True, "rating": 4.9, "key_specs": "Switch OLED+健身环+健身游戏", "sales": "月销8500"}
    ],
    "客厅娱乐影音 3 件套 ¥7197，**超 ¥2197 但都是核心**：\n\n## 🎬 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 🥇 电视 | **海信 65 寸 4K AI** | ¥3299 |\n| 音响 | JBL Bar 300 5.0 | ¥1299 |\n| 游戏机 | Switch OLED+健身环 | ¥2599 |\n| **合计** | | **¥7197** | 超 ¥2197 |\n\n## 🎯 压预算到 ¥5000 方案\n\n### 必须保留\n**电视 ¥3299**（核心载体，没电视都是 0）\n\n### 可选择性砍\n\n#### 方案 A：砍音响 ¥4598（最简）\n- 仅电视+Switch\n- 用电视自带音响（够用但不爆）\n- **音质 60 分但能玩**\n\n#### 方案 B：换便宜游戏机 ¥3798\n- 电视 + Switch Lite ¥1499（不能接电视，仅掌机）\n- 适合: 主要看电视+偶尔玩游戏\n\n#### 方案 C：砍游戏机 ¥4598\n- 电视+音响\n- 玩游戏改用手机\n- 适合: 主要看电影+不玩游戏\n\n## 💡 我的建议\n\n如果你**真心想做娱乐中心**，超 ¥2197 上完整套：\n\n### 完整套体验提升\n1. **电视 +音响 = 电影院感受**（5.0 声道 vs 电视双声道）\n2. **+Switch = 全家娱乐**（健身环老婆玩+马里奥孩子玩）\n3. **¥7197 / 5 年使用 = ¥120/月 娱乐预算**\n\n比起每周外出娱乐 ¥500，**家庭娱乐中心是 1 次投资终身受益**。\n\n## 🎮 Switch 健身环 = 居家健身神器\n\n- **客厅做有氧 30 分钟**（比跑步机有趣 10 倍）\n- 老婆+孩子轮流玩\n- 减肥效果实际有效\n\n## 💎 进阶（+¥3000）\n\n- 4K 蓝光播放器 ¥1000\n- 智能投影仪 ¥3000（替代或补充）\n- 游戏椅 ¥800\n- 投影幕布 ¥600\n\n## 🎯 真心建议\n\n**砍游戏机改买 PS5 数字版 ¥3399 也不错**：\n- 4K 游戏体验更好\n- 索尼独占大作多\n- 比 Switch 难入手老人/小孩\n\n看你家庭：\n- **有 6 岁以下小孩** → Switch（家庭友好）\n- **20-40 岁夫妻** → PS5（游戏体验）",
    ["海信65寸4K AI智能电视+120Hz+月销1.8万，客厅完美尺寸娱乐核心", "JBL Bar 300 Soundbar 5.0声道+杜比+月销2200，电视音响升级电影院感受", "Switch OLED+健身环大冒险套装+月销8500，居家健身+全家娱乐神器"]
))

# 9. place_order - 多账户拼单
T.append(make_traj(
    "sft_order_021", "place_order", "购物下单",
    "多账户拼单+礼品分发",
    "618 我和老公各下一单凑 PLUS 双倍优惠，怎么操作",
    {"plus_double_discount": True, "split_accounts": 2, "total_target": 3000},
    [
        {"product_id": "mock_split_1", "title": "电视 (你的账户) - 自营+PLUS 价", "price": 2999, "is_platform_self": True, "rating": 4.9, "key_specs": "PLUS专享价/15天价保/订单[TRACKING_ID]-A-2284", "sales": "—"},
        {"product_id": "mock_split_2", "title": "音响 (老公账户) - 自营+PLUS 价", "price": 1299, "is_platform_self": True, "rating": 4.9, "key_specs": "PLUS专享价/同物流地址/订单[TRACKING_ID]-B-3392", "sales": "—"}
    ],
    "✅ 双账户拼单已下单！\n\n## 📦 订单详情\n\n### 你的账户订单\n- 商品：电视 ¥2999\n- 订单号：**[TRACKING_ID]-A-2284**\n- PLUS 价：减 ¥100\n- 实付：¥2899\n\n### 老公账户订单\n- 商品：音响 ¥1299\n- 订单号：**[TRACKING_ID]-B-3392**\n- PLUS 价：减 ¥50（每个 PLUS 账户独立计算）\n- 实付：¥1249\n\n### 总计\n- 商品总价：¥4298\n- 双账户 PLUS 共减：**¥150**\n- 实付：**¥4148**\n\n## 💰 单账户 vs 双账户对比\n\n| 方案 | PLUS 优惠 |\n|---|---|\n| 单账户买电视+音响 | ¥4298 - ¥100 = **¥4198** |\n| **双账户分别下单** | ¥4298 - ¥150 = **¥4148** |\n| **省** | **¥50** |\n\n（每个账户独立享受 PLUS 优惠，**双账户 = 双倍优惠**）\n\n## ⚠️ 双账户拼单 4 个注意\n\n### 1️⃣ 必须不同收货地址（理论上）\n- 购物平台原本要求 2 个账户不同地址\n- 但**同一家庭可以**（地址写公司+家可绕过）\n- 实操：分开下，物流自动配送\n\n### 2️⃣ 发票分开\n- 每个订单**独立发票**\n- 公司报销需要 2 张\n- 个人无所谓\n\n### 3️⃣ 退货独立\n- 电视坏 → 你账户退\n- 音响坏 → 老公账户退\n- **不影响对方**\n\n### 4️⃣ 京豆分开返\n- 你账户得电视的京豆\n- 老公账户得音响的京豆\n- 不能合并\n\n## 💡 双账户拼单适合场景\n\n### ✅ 推荐\n- 一次买多件大件\n- 都是 PLUS 会员的家庭\n- 单笔可拆分 2 个不同商品\n\n### ❌ 不推荐\n- 单件商品超 ¥10000（不能拆）\n- 单方非 PLUS（没双倍优惠）\n- 异地配送（物流费翻倍可能省的更少）\n\n## 💎 终极拼单技巧\n\n如果家里 3-4 个 PLUS 账户：\n- 爸妈各一个\n- 你+老公各一个\n- **4 账户拼单 = 4 倍 PLUS 优惠**\n\n大宗采购（家电节）可能省 ¥500+。\n\n这次 ¥50 的优惠先体验一下流程，下次大宗采购熟练操作。",
    ["电视2999元你的账户PLUS专享价减100元，订单A-2284", "音响1299元老公账户PLUS专享价减50元，订单B-3392"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase - 复购周期监测
T.append(make_traj(
    "sft_repurchase_019", "repurchase", "复购召回",
    "复购+用量频率智能提醒",
    "再买之前那个洗衣凝珠",
    {"category_keyword": "洗衣凝珠", "time_range": "last_3_months", "predict_usage": True},
    [
        {"product_id": "mock_pod_old", "title": "蓝月亮 洗衣凝珠 60 颗 (你 1.5 月前购买)", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "你1.5月前购买/订单[TRACKING_ID]/月用量约40颗/预计剩约30颗=20天", "sales": "月销4.5万"},
        {"product_id": "mock_pod_bulk", "title": "蓝月亮 洗衣凝珠 200 颗 大包装 (省 30%)", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "200颗大包装/单颗0.99元 vs 60颗1.48/省30%", "sales": "月销2.5万"}
    ],
    "查到你 1.5 个月前买的是 **蓝月亮洗衣凝珠 60 颗 ¥89**（订单 [TRACKING_ID]）。\n\n## 📊 用量推算\n\n- 你月用量：约 40 颗（按 3 口家庭每天 1.3 颗）\n- 已用：约 60 颗\n- **剩余：约 0 颗** ⚠️\n\n这次你刚好把上一包用完，**正常需要立即复购**。\n\n## 💡 推荐升级到大包装\n\n### 价格对比\n\n| 包装 | 价格 | 颗数 | 单颗价 |\n|---|---|---|---|\n| 60 颗装 | ¥89 | 60 | **¥1.48** |\n| **200 颗装** | **¥199** | 200 | **¥0.99** |\n\n**大包装单颗便宜 33%**，按月用量 40 颗：\n- 60 颗装：¥89 × 8 个月 = **¥712**（一年）\n- 200 颗装：¥199 × 2.4 = **¥478**（一年）\n- **大包装省 ¥234/年**\n\n## 🛒 建议\n\n**直接买 200 颗大包装 ¥199**：\n- 单颗成本省 33%\n- 用 5 个月（按你 1.3 颗/天）\n- 一年省 ¥234\n\n## ⚠️ 大包装存储\n\n- 保质期：**未开封 2 年**\n- 开封后：**1 年内用完**\n- 200 颗 5 个月用完，**完全在保质期内**\n\n## 💎 顺便\n\n你买了 1.5 个月，这次复购时间**有点延迟**（按你月用量算应该 1 个月就用完）。可能：\n- 出差/旅行少洗了几次\n- 衣服少了\n- 用量减少\n\n如果用量真的少（每天 1 颗以下），**60 颗 ¥89 更适合**（避免囤太多）。\n\n## 📊 帮你设个智能提醒\n\n我可以帮你设置「**60 天后自动提醒**」：\n- 60 天后给你推送复购提醒\n- 那时大包装可能还在 618 后特价\n- **不会断货+不会囤太多**\n\n要直接下单 200 颗装 ¥199 吗？还是先 60 颗 ¥89 应急？",
    ["蓝月亮洗衣凝珠60颗你1.5月前购买+月销4.5万，每月用量40颗", "蓝月亮洗衣凝珠200颗大包装+单颗0.99元省30%+月销2.5万，一年省234元"],
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
