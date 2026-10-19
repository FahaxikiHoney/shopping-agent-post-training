# -*- coding: utf-8 -*-
"""Step 39: 第 27 批 10 条"""
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

# 1. similar_rec - 抱怨不耐脏
T.append(make_traj(
    "sft_simrec_065", "similar_rec", "相似品推荐",
    "抱怨颜色不耐脏 → 推荐深色或防污面料款",
    "上次买的白色布艺沙发一个月就脏了，要耐脏好清洁的同价位款",
    {"query": "沙发 深色 防污 易清洁 布艺", "min_price": 3000, "max_price": 6000, "filters": {"stain_resistant": True}},
    [
        {"product_id": "mock_sofa_dark_1", "title": "源氏木语 深灰色科技布沙发 防水防污三人位", "price": 3999, "is_platform_self": True, "rating": 4.9, "key_specs": "科技布/防水防污/深灰色/可擦拭/月销1200", "sales": "月销1200"},
        {"product_id": "mock_sofa_dark_2", "title": "芝华仕 深蓝色头等舱功能沙发 真皮", "price": 4999, "is_platform_self": True, "rating": 4.9, "key_specs": "真皮/深蓝色/防污耐用/10年不褪色", "sales": "月销850"},
        {"product_id": "mock_sofa_dark_3", "title": "顾家家居 军绿色猫爪布沙发 耐抓耐脏", "price": 3699, "is_platform_self": True, "rating": 4.8, "key_specs": "猫爪布/军绿/耐抓耐脏/养宠家庭首选", "sales": "月销2200"}
    ],
    "白色布艺沙发确实是噩梦，3 款耐脏解决方案：\n\n**1. 顾家猫爪布军绿（¥3699）** ⭐ 综合最实用\n猫爪布是专门为**养宠家庭/有孩子家庭**设计的面料：\n- **耐抓抓**（猫爪划不坏）\n- **耐脏**（颜色深+肌理遮污）\n- 军绿色日常显脏率最低之一\n- 月销 2200 件\n\n**2. 源氏木语科技布深灰（¥3999）**\n科技布=高端合成面料，**防水+防污+可擦拭**，脏了湿布一擦干净。\n\n**3. 芝华仕深蓝真皮（¥4999）**\n真皮最耐脏，**湿布一擦 OK**，深蓝色 10 年不褪色。贵但用 10 年以上最省钱。\n\n## 💡 颜色耐脏排行\n\n最耐脏：深灰 > 军绿 > 深蓝 > 黑 > 棕\n最不耐脏：白 > 浅米 > 浅粉 > 浅蓝\n\n白色沙发 **99% 会后悔**——无论多贵都会显旧。",
    ["顾家猫爪布军绿沙发+耐抓耐脏+月销2200，养宠有娃家庭最实用", "源氏木语科技布深灰+防水防污可擦拭+月销1200，科技面料轻松清洁", "芝华仕深蓝真皮+湿布一擦+10年不褪色+月销850，一次买用10年最耐久"]
))

# 2. similar_rec - 抱怨不防水
T.append(make_traj(
    "sft_simrec_066", "similar_rec", "相似品推荐",
    "抱怨不防水下雨渗水 → 推荐防水背包",
    "上次买的背包下雨电脑进水了，要能防水的同价位款",
    {"query": "防水背包 笔记本 防雨罩 户外通勤", "max_price": 600, "filters": {"waterproof_level": "IPX4+"}},
    [
        {"product_id": "mock_bag_wp_1", "title": "Osprey 天秤 日包 24L TPU防水", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "TPU防水膜/15.6寸电脑仓/24L/登山徒步通勤", "sales": "月销2200"},
        {"product_id": "mock_bag_wp_2", "title": "迪卡侬 NH 旅行包 20L 防水涂层", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "防水涂层+防雨罩/20L/轻量/月销4500", "sales": "月销4500"},
        {"product_id": "mock_bag_wp_3", "title": "Tumi 商务防水 Ballistic 尼龙 17L", "price": 5999, "is_platform_self": True, "rating": 4.9, "key_specs": "Ballistic尼龙/防水/商务顶级/进水直接赔", "sales": "月销380"}
    ],
    "电脑进水是真正的代价高昂失误，3 款真防水款：\n\n**1. 迪卡侬 NH 防水 20L（¥199）** ⭐ 性价比首选\n**防水涂层+自带防雨罩**，月销 4500。¥199 是真防水里最便宜的，暴雨可以保护内容。\n\n**2. Osprey 天秤 TPU 防水（¥599）**\nTPU 防水膜是真正的专业防水（不是涂层），**暴雨游泳级别**。15.6 寸电脑仓+24L 通勤够用。\n\n**3. Tumi Ballistic 尼龙（¥5999）**\n顶级商务防水，贵但 Ballistic 尼龙是**军用级别防弹材料**，划不破+防水，进水直接赔偿。\n\n## 💡 防水等级说明\n\n- **防水涂层（DWR）**：小雨可以，大雨时间长会渗\n- **防雨罩**：套上去真正防暴雨\n- **TPU 防水膜**：内衬覆盖，雨水不会渗入\n- 最重要的是：**防水不等于防浸泡**（不要泡水里）",
    ["迪卡侬NH防水20L+防水涂层+防雨罩+月销4500，¥199最便宜真防水", "Osprey天秤TPU防水膜24L+月销2200，专业级防水通勤户外两用", "Tumi Ballistic防水商务包+月销380，顶级商务军用级别一包用20年"]
))

# 3. sku_comp
T.append(make_traj(
    "sft_skucomp_063", "sku_comp", "商品对比",
    "智能音箱三大品牌对比",
    "买智能音箱，小爱/天猫精灵/小度哪个好",
    {"skus": ["小米小爱同学 Pro", "阿里天猫精灵 X6", "百度小度 CC"], "mode": "ecosystem_comparison"},
    [
        {"product_id": "mock_speaker_xiaomi", "title": "小米小爱同学 Pro 智能音箱", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "米家生态/语音控制家电/Hi-Fi音质/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "mock_speaker_ali", "title": "天猫精灵 X6 全屋音频 阿里生态", "price": 349, "is_platform_self": True, "rating": 4.8, "key_specs": "阿里生态/购物播报/淘宝下单/月销1.5万", "sales": "月销1.5万"},
        {"product_id": "mock_speaker_baidu", "title": "小度 CC 人工智能屏幕音箱 百度", "price": 399, "is_platform_self": True, "rating": 4.8, "key_specs": "百度/带屏幕/视频通话/知识问答/月销1.2万", "sales": "月销1.2万"}
    ],
    "三款智能音箱**核心是看你的生态圈**，不是比音质：\n\n## 📊 三大生态对比\n\n| 品牌 | 价格 | 生态 | 最强场景 |\n|---|---|---|---|\n| 小米小爱 | ¥299 | **米家全家桶** | 控制家电/音乐 |\n| 天猫精灵 | ¥349 | **阿里系** | 淘宝购物/娱乐 |\n| 小度 CC | ¥399 | **百度** | 知识问答/视频通话 |\n\n## 🎯 怎么选\n\n### 家里有大量米家设备 → **小爱同学 ¥299**\n- 「小爱，开灯/关空调/扫地机器人去卧室」全语音控制\n- 米家生态联动是三款里最成熟的\n- **价格最便宜**，月销 2.5 万断档\n\n### 经常在淘宝购物/有孩子看内容 → 天猫精灵 ¥349\n- 「精灵，帮我在淘宝买 XX」直接购物\n- 亿点儿童内容（故事/英语）\n- 支付宝绑定方便\n\n### 老人/孩子爱问问题/视频通话 → 小度 CC ¥399\n- 带屏幕，**视频通话最清晰**\n- 百度知识库回答问题最广\n- 适合老人独居用（可以和子女视频）\n\n## 💡 真心建议\n\n**如果家里没有智能家电**，3 款音箱都会使用率极低。\n\n先买 1-2 个米家智能开关/灯泡（¥30-50），**体验到语音控制家电的便利**，再买小爱配套使用才最值。",
    ["小米小爱同学Pro+米家生态控家电+月销2.5万，有米家设备首选", "天猫精灵X6+淘宝购物+月销1.5万，阿里系+经常淘宝适合", "小度CC带屏幕+视频通话+月销1.2万，老人视频通话/知识问答适合"]
))

# 4. sku_comp
T.append(make_traj(
    "sft_skucomp_064", "sku_comp", "商品对比",
    "不同档次护肤精华的成分和效果对比",
    "精华液买 100 元/300 元/800 元，差在哪里",
    {"skus": ["100元级精华", "300元级精华", "800元级精华"], "mode": "ingredient_comparison"},
    [
        {"product_id": "mock_serum_100", "title": "玉泽 屏障修护精华液 50ml 百元档", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "神经酰胺+B5/修护屏障/敏感肌/月销1.5万", "sales": "月销1.5万"},
        {"product_id": "mock_serum_300", "title": "宝拉珍选 维生素C精华 20% 抗氧化", "price": 289, "is_platform_self": True, "rating": 4.9, "key_specs": "VC 20%/抗氧化/美白提亮/月销4500", "sales": "月销4500"},
        {"product_id": "mock_serum_800", "title": "雅诗兰黛 小棕瓶 精华 30ml 抗老", "price": 749, "is_platform_self": True, "rating": 4.9, "key_specs": "二裂酵母/抗老修护/30+推荐/月销1.2万", "sales": "月销1.2万"}
    ],
    "**精华的价差来自有效成分浓度+技术壁垒**，不是品牌溢价本身：\n\n## 📊 三档成分对比\n\n| 价格 | 代表 | 核心成分 | 主要功效 |\n|---|---|---|---|\n| ¥99 | 玉泽 | 神经酰胺+B5 | **修护屏障**（基础必需）|\n| ¥289 | 宝拉珍选 | VC 20% | **美白抗氧化**（提亮肤色）|\n| ¥749 | 雅诗兰黛 | 二裂酵母 | **抗老修护**（30+ 刚需）|\n\n## 💡 三种成分解决不同问题\n\n### 神经酰胺（¥99 玉泽）→ 皮肤屏障\n- 皮肤红/干/敏感的根本原因是**屏障破损**\n- 神经酰胺是组成皮肤屏障的核心成分\n- **所有人都应该有这一步**，不分年龄\n\n### 20% VC（¥289 宝拉珍选）→ 美白抗氧化\n- 维生素 C 阻断黑色素生成\n- 20% 浓度是**有效浓度**（市面很多只有 2-5%）\n- 主要解决：暗沉/色斑/不均匀\n\n### 二裂酵母（¥749 雅诗兰黛）→ 抗老\n- 促进细胞修复，**减缓细纹/松弛**\n- 30 岁前用感受不明显\n- **30 岁以上是真正的刚需**\n\n## 🎯 按年龄推荐\n\n- **20 岁初段**：玉泽 ¥99（屏障修护就够）\n- **25-30 岁**：玉泽 + 宝拉珍选（屏障+美白）\n- **30 岁以上**：全部三步，或升级到雅诗兰黛小棕瓶\n\n**不要为了「贵=好」买超过自己年龄需求的产品**。",
    ["玉泽屏障修护精华神经酰胺+B5+月销1.5万，所有人基础必备修护屏障", "宝拉珍选VC 20%精华+抗氧化美白提亮+月销4500，暗沉色斑不均匀", "雅诗兰黛小棕瓶二裂酵母+月销1.2万，30岁以上抗老细纹松弛刚需"]
))

# 5. matching - 宿舍装饰
T.append(make_traj(
    "sft_match_063", "matching_purchase", "搭配购物",
    "摄影工作室整体灯光布置",
    "要搭个人像摄影小工作室，配主光+辅光+背景纸+反光板",
    {"query": "人像摄影工作室布光 主光+辅光+背景", "filters": {"category": "portrait_studio_lighting"}},
    [
        {"product_id": "mock_studio_1", "title": "神牛 AD200Pro 外拍灯 主光 200W", "price": 2399, "is_platform_self": True, "rating": 4.9, "key_specs": "200W主灯/无线控制/专业人像/月销1500", "sales": "月销1500"},
        {"product_id": "mock_studio_2", "title": "Godox 神牛 SL60W 持续灯 辅光", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "60W持续灯/辅光补光/视频兼顾/月销2500", "sales": "月销2500"},
        {"product_id": "mock_studio_3", "title": "北恩背景纸 2.7m宽 10色套装", "price": 399, "is_platform_self": True, "rating": 4.8, "key_specs": "2.7m宽/10色换背景/纯色无接缝/月销3500", "sales": "月销3500"},
        {"product_id": "mock_studio_4", "title": "反光板 5合1 110cm 折叠收纳", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "5合1/白金银黑透5种/折叠/月销4500", "sales": "月销4500"}
    ],
    "人像摄影工作室 4 件套 ¥3486，**专业级布光方案**：\n\n## 📸 完整方案\n\n| 器材 | 商品 | 价格 |\n|---|---|---|\n| 🥇 主光 | 神牛 AD200Pro 200W | ¥2399 |\n| 辅光 | 神牛 SL60W 持续灯 | ¥599 |\n| 背景纸 | 北恩 2.7m 10 色 | ¥399 |\n| 反光板 | 5 合 1 折叠 | ¥89 |\n\n## 💡 人像摄影布光 4 要素\n\n### 主光 = 灵魂\n神牛 AD200Pro 是业内**外拍灯入门标准**，200W 功率适合各种造型光（蝴蝶光/伦勃朗光/侧光）。\n\n### 辅光消除死阴影\n主光单独打会产生硬阴影，SL60W 60W 持续灯从另一侧**柔化阴影**。持续灯同时适合视频录制。\n\n### 背景纸 10 色换风格\n- 白色：商业棚拍标准\n- 黑色：暗调高级感\n- 其他色：不同风格主题\n- 2.7m 宽**全身人像不露边**\n\n### 反光板三分钟学会用\n补光最便宜的方式，自然光+反光板 = 0 成本柔光。5 合 1 白/金/银/黑/透五种效果。\n\n## 💡 入门布光 SOP\n\n**蝴蝶光（最适合女性人像）**：\n1. 主光放正面45°高位\n2. 反光板（白色）放被摄者胸前仰角\n3. SL60W 作为背景灯打背景纸\n4. 参数：主光 1/2 功率，反光板反射",
    ["神牛AD200Pro 200W主光+无线控制+月销1500，业内外拍灯入门标准", "神牛SL60W 60W持续灯辅光+视频兼顾+月销2500，柔化阴影视频拍摄通用", "北恩背景纸2.7m 10色+无接缝+月销3500，全身人像不露边换风格", "5合1反光板110cm折叠+月销4500，最便宜的柔光方案5种效果"]
))

# 6. matching - 北欧风卧室
T.append(make_traj(
    "sft_match_064", "matching_purchase", "搭配购物",
    "高颜值桌面文具整套",
    "桌面文具想统一风格，配钢笔+记事本+收纳+桌面台历",
    {"query": "高颜值桌面文具套装 钢笔+本子+收纳+台历", "filters": {"style": "desk_aesthetic"}},
    [
        {"product_id": "mock_stationery_1", "title": "百乐 PILOT 细嘴钢笔 日系经典款", "price": 159, "is_platform_self": True, "rating": 4.9, "key_specs": "日本百乐/细嘴/书写流畅/钢笔入门首选", "sales": "月销1.2万"},
        {"product_id": "mock_stationery_2", "title": "Moleskine 经典笔记本 A5 横线", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "Moleskine经典/A5横线/高颜值/月销3.5万", "sales": "月销3.5万"},
        {"product_id": "mock_stationery_3", "title": "MUJI 桌面收纳 亚克力抽屉 3层", "price": 129, "is_platform_self": True, "rating": 4.9, "key_specs": "亚克力透明/3层抽屉/极简收纳/月销2万", "sales": "月销2万"},
        {"product_id": "mock_stationery_4", "title": "无印良品 桌面台历 2026年 简洁设计", "price": 49, "is_platform_self": True, "rating": 4.8, "key_specs": "MUJI简洁设计/2026年款/桌面点缀", "sales": "月销5500"}
    ],
    "高颜值桌面文具 4 件套 ¥436，**有格调的工作台**：\n\n## ✏️ 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 🥇 钢笔 | 百乐 PILOT 细嘴 | ¥159 |\n| 笔记本 | Moleskine A5 横线 | ¥99 |\n| 收纳 | MUJI 亚克力 3 层 | ¥129 |\n| 台历 | 无印良品 2026 年 | ¥49 |\n\n## 🎨 配色逻辑\n\n**黑色钢笔 + 黑封面 Moleskine + 透明亚克力 + 白色台历** = 极简黑白风格\n\n### 为什么选这 4 件\n\n**百乌钢笔 ¥159**：书写体验质变。圆珠笔/中性笔没有钢笔顺滑，一旦用过钢笔**很难回去**。\n\n**Moleskine ¥99**：每个用钢笔写字的人的标配本，**质感够用 1 年不散架**。\n\n**MUJI 亚克力收纳 ¥129**：透明材质**一眼找到想要的东西**，不用每次翻找。3 层装笔/便利贴/剪刀分类清晰。\n\n**MUJI 台历 ¥49**：桌面上一个简洁台历，**减少手机依赖**（不用开手机看日期），也是装饰品。\n\n## 💡 搭配心理学\n\n桌面整洁 → 思路清晰 → 工作效率提升。**¥436 的文具投资，年化效率提升远高于这个价格**。\n\n## 💎 加 ¥200 终极文具桌\n\n- 蜡烛/香薰 ¥150（让桌面有香气）\n- 白色陶瓷笔筒 ¥49\n- 便利贴组合 ¥30",
    ["百乐PILOT细嘴钢笔+月销1.2万，书写流畅质变体验入门钢笔首选", "Moleskine A5横线笔记本+月销3.5万，高颜值用1年不散架配钢笔标配", "MUJI亚克力3层抽屉收纳+月销2万，透明一眼找到极简桌面收纳", "MUJI台历2026年+月销5500，桌面点缀减少手机依赖"]
))

# 7. bundle - 健康
T.append(make_traj(
    "sft_bundle_061", "bundle_purchase", "组合购物",
    "3000 元减脂期全套补剂",
    "开始减脂，3000 配齐补剂+餐具+运动装备一套",
    {"query": "减脂期全套 补剂+餐具+运动", "max_price": 3200},
    [
        {"product_id": "mock_diet_sup_1", "title": "MyProtein 乳清蛋白粉 巧克力 1kg", "price": 269, "is_platform_self": True, "rating": 4.9, "key_specs": "乳清蛋白/80%蛋白含量/训练后补充/月销1.8万", "sales": "月销1.8万"},
        {"product_id": "mock_diet_sup_2", "title": "汤臣倍健 维生素B族 90片", "price": 69, "is_platform_self": True, "rating": 4.9, "key_specs": "B族维生素/减脂期代谢支持/月销3.5万", "sales": "月销3.5万"},
        {"product_id": "mock_diet_sup_3", "title": "Swisse 高浓度鱼油 Omega-3 200粒", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "Omega-3/抗炎护心/减脂辅助/月销2.2万", "sales": "月销2.2万"},
        {"product_id": "mock_diet_equip_1", "title": "膳魔师 1L 运动水壶 刻度款", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "1L大容量/刻度线/减脂喝水量监控", "sales": "月销4.5万"},
        {"product_id": "mock_diet_equip_2", "title": "华为体脂秤 3 Pro 体成分 11项", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "11项体成分/体脂率/肌肉量/减脂监测核心", "sales": "月销1.2万"},
        {"product_id": "mock_diet_equip_3", "title": "摩飞 分格便当盒 1L 减脂套装", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "分格1L/减脂比例/微波可用/月销2.2万", "sales": "月销2.2万"}
    ],
    "减脂期 6 件套 ¥1324，余 ¥1676：\n\n## 💪 完整方案\n\n| 类别 | 商品 | 价格 | 作用 |\n|---|---|---|---|\n| 蛋白粉 | MyProtein 乳清 1kg | ¥269 | 保住肌肉不减肌 |\n| 维生素 B | 汤臣倍健 B 族 | ¥69 | 支持代谢效率 |\n| 鱼油 | Swisse Omega-3 | ¥199 | 抗炎护心脏 |\n| 体脂秤 | 华为 3 Pro 11 项 | ¥599 | 追踪减脂进度 |\n| 运动水壶 | 膳魔师 1L 刻度 | ¥99 | 保证日饮水量 |\n| 便当盒 | 摩飞分格 1L | ¥89 | 控制饮食比例 |\n\n## 💡 减脂期的科学逻辑\n\n**减脂 = 热量缺口 + 保住肌肉**\n\n### 蛋白粉防止减肌\n热量缺口时身体会分解肌肉，**保证 1.6g/kg 蛋白摄入**是保住肌肉的关键。\n\n### 体脂秤追踪精度\n减脂成功的关键是**数据驱动**。体重秤看不出减的是脂肪还是水分，**体脂率才是核心指标**。华为 3 Pro 11 项数据最全。\n\n### 1L 刻度水壶\n减脂期**每天 2-3L 水**加速代谢。刻度水壶帮你知道喝了多少，不是靠感觉。\n\n## 💰 余 ¥1676 分配\n\n- **健身房月卡/课程** ¥500-800（运动才是真正减脂）\n- **健康食材**（鸡胸/蔬菜/坚果）¥400/月\n- **运动装备**（跑步鞋/运动裤）¥400\n- 体检（测基础代谢/甲状腺）¥200",
    ["MyProtein乳清蛋白1kg+80%蛋白+月销1.8万，减脂保住肌肉关键补剂", "汤臣倍健B族维生素+月销3.5万，减脂期代谢支持必备", "Swisse Omega-3鱼油+月销2.2万，抗炎护心脏减脂辅助", "华为体脂秤11项+月销1.2万，追踪体脂率减脂数据核心", "膳魔师1L刻度水壶+月销4.5万，减脂喝够水刻度监控", "摩飞分格便当盒1L+月销2.2万，饮食比例控制减脂饮食管理"]
))

# 8. bundle
T.append(make_traj(
    "sft_bundle_062", "bundle_purchase", "组合购物",
    "5000 元家庭绘画兴趣班装备",
    "全家想一起学水彩画，5000 配齐画材+灯具+收纳",
    {"query": "水彩画入门装备 颜料+画纸+笔+灯", "max_price": 5500},
    [
        {"product_id": "mock_watercolor_1", "title": "史明克 专业水彩颜料 12色大管", "price": 899, "is_platform_self": True, "rating": 4.9, "key_specs": "德国史明克/专业级/12色大管/用5年不完", "sales": "月销680"},
        {"product_id": "mock_watercolor_2", "title": "获多福 水彩纸 300g 30×40 30张", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "获多福棉浆/300g不起皱/专业水彩纸", "sales": "月销3500"},
        {"product_id": "mock_watercolor_3", "title": "达芬奇 水彩笔 8支套装 圆头", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "达芬奇/8支/圆头吸水好/专业笔首选", "sales": "月销1500"},
        {"product_id": "mock_watercolor_4", "title": "北客 A3 LED 拷贝台 调光", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "A3拷贝台/调光/描线透光/水彩辅助", "sales": "月销2200"},
        {"product_id": "mock_watercolor_5", "title": "水彩收纳包 大容量 画材专用 帆布", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "大容量/帆布/颜料+笔+纸分层/月销1800", "sales": "月销1800"}
    ],
    "全家水彩入门 5 件套 ¥2295，余 ¥2705：\n\n## 🎨 完整方案\n\n| 器材 | 商品 | 价格 |\n|---|---|---|\n| 🥇 颜料 | 史明克 12 色专业大管 | ¥899 |\n| 水彩纸 | 获多福 300g 30 张 | ¥299 |\n| 水彩笔 | 达芬奇 8 支套装 | ¥599 |\n| 拷贝台 | 北客 A3 LED 调光 | ¥299 |\n| 收纳包 | 水彩专用大容量 | ¥199 |\n\n## 💡 为什么买专业而不是入门\n\n**入门套装便宜但体验差**：廉价颜料不透明+笔不吸水+纸洇水起皱，**一次体验后就不想画了**。\n\n史明克+获多福+达芬奇是「**专业三件套**」，用好工具才能感受到水彩的美。\n\n## 💡 全家画的乐趣\n\n- 大人：可以画风景/植物，**减压效果极好**\n- 孩子：从临摹简单图案开始，不用完美\n- 一起画：**比看手机亲子关系好 10 倍**\n\n## 💰 余 ¥2705 用于\n\n- **水彩基础课（B 站/抖音）**：免费课程足够入门\n- **临摹用线稿打印**：¥50 打印 50 张\n- **调色盘**：¥30-80\n- **洗笔桶+遮蔽液**：¥80\n- 如果想学快一点，**1 对 1 水彩老师**：¥200-300/次",
    ["史明克专业水彩12色大管+月销680，专业级颜料透明度高用5年不完", "获多福棉浆水彩纸300g+月销3500，专业水彩纸不起皱吸水好", "达芬奇水彩笔8支+月销1500，专业笔吸水弹力好首选", "北客A3 LED拷贝台调光+月销2200，描线打稿水彩辅助", "水彩收纳包大容量帆布+月销1800，颜料笔纸分层收纳携带"]
))

# 9. place_order
T.append(make_traj(
    "sft_order_033", "place_order", "购物下单",
    "商品被限购处理",
    "想买那款限购 1 件的茅台，买了一件还想多买几瓶怎么办",
    {"product_id": "mock_maotai_ltd", "action": "purchase_limited", "desired_qty": 3, "limit_per_account": 1},
    [
        {"product_id": "mock_maotai_ltd", "title": "茅台 飞天 53度 500ml 限购1瓶/账号", "price": 1499, "is_platform_self": True, "rating": 4.9, "key_specs": "订单[TRACKING_ID]-MAO-2284/已购1瓶/账号限购规则", "sales": "—"}
    ],
    "✅ 第 1 瓶已下单（订单 [TRACKING_ID]-MAO-2284）。但**限购政策不能绕过**，给你几个合规建议：\n\n## ⚠️ 限购是真实规则\n\n茅台限购 1 瓶/账号是**购物平台和茅台官方联合限制**，目的是防止炒货囤积。\n\n### 不能做的\n- ❌ 用同一账号重复下单（系统自动拦截）\n- ❌ 用虚拟手机号注册新账号（可能封号）\n- ❌ 找黄牛加价代购（不划算且可能买到假货）\n\n### 合规的方法\n\n**家人账号各买 1 瓶**：\n- 让老婆/父母账号分别下单\n- 每个实名账号限购 1 瓶\n- 3 个账号 = 3 瓶\n\n**等补货预约**：\n- 茅台会定期新货补货\n- 在商品页点「**到货提醒**」\n- 补货时每个账号可再购 1 瓶\n\n**购物平台拍卖购买**：\n- 购物平台拍卖有时有陈年茅台/批次茅台\n- 无限购限制\n- 价格可能更高但来源正规\n\n## 💰 价格参考\n\n| 渠道 | 价格 | 保真程度 |\n|---|---|---|\n| 平台自营（你这瓶）| ¥1499 | **100% 正品** |\n| 黄牛溢价 | ¥1800-2500 | 有假货风险 |\n| 二级市场 | ¥1700-2200 | 中等风险 |\n\n**建议通过家人账号多买，而不是找黄牛**。茅台真假难辨，黄牛渠道的假货率不低。",
    ["茅台飞天53度500ml已购1瓶+限购1瓶/账号+订单[TRACKING_ID]-MAO-2284，限购规则不可绕过"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase
T.append(make_traj(
    "sft_repurchase_031", "repurchase", "复购召回",
    "复购婴儿用品+成长阶段产品升级",
    "宝宝的安抚奶嘴快没了，再买，宝宝现在 8 个月了",
    {"category_keyword": "安抚奶嘴", "time_range": "last_4_months", "check_stage_upgrade": True},
    [
        {"product_id": "mock_nipple_old", "title": "贝亲 安抚奶嘴 S 码 0-3 月 (你3月前买)", "price": 49, "is_platform_self": True, "rating": 4.9, "key_specs": "0-3月S码/你3月前购买/现在需要升级码数", "sales": "月销4.5万"},
        {"product_id": "mock_nipple_m", "title": "贝亲 安抚奶嘴 M 码 3-6 月", "price": 49, "is_platform_self": True, "rating": 4.9, "key_specs": "M码/3-6月/月销3.5万", "sales": "月销3.5万"},
        {"product_id": "mock_nipple_l", "title": "贝亲 安抚奶嘴 L 码 6-18 月 宝宝版", "price": 49, "is_platform_self": True, "rating": 4.9, "key_specs": "L码/6-18月/吸孔更大/8月宝宝适合", "sales": "月销2.8万"}
    ],
    "**重要！** 你 3 个月前买的是 **S 码（0-3 月）**，但你的宝宝现在 **8 个月**了，需要升级到 **L 码**！\n\n## ⚠️ 奶嘴码数不对的后果\n\n- S 码吸孔太小 → 宝宝用力吸 → **吸气吞入更多空气 → 胀气腹痛**\n- 外圈太小 → **压嘴周围皮肤 → 留痕**\n\n## 📊 贝亲奶嘴码数对照\n\n| 码数 | 月龄 | 特点 |\n|---|---|---|\n| S 码 | 0-3 个月 | 你现在用的（已不适合）|\n| M 码 | 3-6 个月 | 过渡期用 |\n| **L 码** | **6-18 个月** | **8 个月宝宝应该用这个** |\n| LL 码 | 18 个月+ | 更大 |\n\n## 🛒 直接买 L 码 ¥49\n\n**同品牌贝亲 L 码**，8 个月到 1 岁半都可以用。\n\n## 💡 额外建议\n\n**8 个月是考虑断奶嘴的时机**：\n- 美国儿科协会建议 **1 岁后开始减少使用**\n- 1 岁半前断完不影响牙齿发育\n- 现在可以逐渐只在睡觉时用，白天减少\n\n## 📦 买多少合适\n\n- 买 **2-3 个 L 码**（家里备用+出门带）\n- 奶嘴每 **2 个月换新**（硅胶会老化）\n\n要帮你下单 L 码 ¥49 × 2 个吗？",
    ["贝亲S码0-3月你3月前购买，8个月宝宝已不适合需要升级", "贝亲M码3-6月，过渡期短不推荐直接跳L", "贝亲L码6-18月+月销2.8万，8个月宝宝直接买L码用到1岁半"],
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
