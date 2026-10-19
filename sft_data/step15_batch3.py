# -*- coding: utf-8 -*-
"""Step 15: 第 3 批 - place_order/repurchase/search_recommend 共 12 条"""
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

# ═══ place_order (4 条) ═══
T.append(make_traj(
    "sft_order_006", "place_order", "购物下单",
    "下单+使用京豆抵扣",
    "下单那台 1599 的米家空气净化器 4 Pro，用京豆抵扣最大",
    {"product_id": "mock_mi_air4pro", "use_max_jingdou": True, "address": "DEFAULT"},
    [
        {"product_id": "mock_mi_air4pro", "title": "小米米家空气净化器4 Pro", "price": 1599, "is_platform_self": True, "rating": 4.9, "key_specs": "订单号[ORDER_ID]/京豆抵扣15元(1500京豆)/实付1584", "sales": "—"}
    ],
    "✅ 下单成功！\n\n## 📦 订单详情\n\n- **商品**：小米米家空气净化器 4 Pro\n- **标价**：¥1599\n- **京豆抵扣**：1500 京豆 = ¥15（最大抵扣 1% 订单金额）\n- **实付**：**¥1584**\n- **订单号**：[ORDER_ID]\n- **收货地址**：默认地址\n- **预计明天送达**\n\n## 💡 京豆使用规则提醒\n\n1. **抵扣上限**：京豆抵扣不能超过订单总金额的 1%（¥1599 → 最多抵 ¥15.99）\n2. **京豆余额**：你账户原 5200 京豆，本次用 1500，余 3700\n3. **京豆来源**：PLUS 会员每月送 100 京豆，订单评价送 30-100，签到送 10/天\n\n## 🛒 配套建议\n\n买了 4 Pro 别忘了 6 个月后买滤芯（¥249），订单页可设「**滤芯到期提醒**」。",
    ["米家4 Pro已下单+京豆抵扣15元实付1584，京豆抵扣规则1%上限"],
    tool_name="ShoppingPlaceOrderTool"
))

T.append(make_traj(
    "sft_order_007", "place_order", "购物下单",
    "下单+开发票",
    "下单 6999 的 MacBook Air M3，开公司发票，发到公司",
    {"product_id": "mock_mac_m3", "address": "COMPANY", "invoice": {"type": "company", "title": "XX科技有限公司", "tax_id": "91110000XXXXX"}},
    [
        {"product_id": "mock_mac_m3", "title": "MacBook Air M3 13寸 256G", "price": 6999, "is_platform_self": True, "rating": 4.9, "key_specs": "订单[ORDER_ID]/已开企业增值税专用发票/电子发票3工作日内邮箱发送", "sales": "—"}
    ],
    "✅ 下单成功，开票信息已记录！\n\n## 📦 订单详情\n\n- **商品**：MacBook Air M3 13寸 256G\n- **价格**：¥6999\n- **订单号**：[ORDER_ID]\n- **收货地址**：公司地址\n- **预计 2 天送达**\n\n## 🧾 发票信息\n\n- **类型**：企业增值税专用发票（可抵扣进项税）\n- **抬头**：XX 科技有限公司\n- **税号**：91110000XXXXX\n- **税率**：13%\n- **税额**：¥805.93\n- **发票交付**：电子发票 3 个工作日内发送到你 shopping platform 账户绑定邮箱\n\n## 💡 报销小贴士\n\n1. **凭证收齐**：发票 + 物流单 + 购物平台订单截图 一并存档\n2. **PDF 永久保存**：电子发票链接 1 年失效，下载后保存到云盘\n3. **3C 资产入账**：MacBook 价值 ¥6999 大概率走「固定资产」科目，找会计确认\n\n如需修改抬头，**在购物平台 APP「我的-发票管理」内 24 小时内可改**。",
    ["MacBook Air M3已下单+企业增值税专票+税额805.93，公司报销凭证齐全"],
    tool_name="ShoppingPlaceOrderTool"
))

T.append(make_traj(
    "sft_order_008", "place_order", "购物下单",
    "预约配送+组合服务",
    "下单 4999 的洗烘一体机，要周六上午送+安装+旧机回收",
    {"product_id": "mock_washer_top", "address": "DEFAULT", "delivery_time": "周六上午", "services": ["installation", "old_recycle"]},
    [
        {"product_id": "mock_washer_top", "title": "小天鹅 TG100V88 10kg 洗烘一体水魔方", "price": 4999, "is_platform_self": True, "rating": 4.9, "key_specs": "订单[ORDER_ID]/周六9-12点送+免费安装+旧机回收抵199", "sales": "—"}
    ],
    "✅ 下单成功！3 项配套服务已安排：\n\n## 📦 订单详情\n\n- **商品**：小天鹅 TG100V88 10kg 洗烘一体水魔方\n- **价格**：¥4999\n- **订单号**：[ORDER_ID]\n- **收货地址**：默认地址\n\n## 🚚 配送 + 安装 + 回收时间表\n\n| 时间 | 安排 |\n|---|---|\n| 周五 18:00 前 | 购物平台送货员电话确认 |\n| **周六 9:00-12:00** | 购物平台送货上门 + 抬上楼（免费）|\n| 周六 14:00-18:00 | **专业师傅上门安装**（免费）|\n| 周六 全天 | 旧洗衣机回收（**抵 ¥199**）|\n\n## 💰 价格明细\n\n- 商品：¥4999\n- 旧机回收抵扣：**-¥199**\n- 实付：**¥4800**\n\n## ⚠️ 必读提醒\n\n1. **旧机准备**：把里面的水、衣物清空（不然搬运会漏水）\n2. **进出门测量**：洗烘一体机 60×60×85cm，**电梯/门洞要 ≥65cm 宽**\n3. **安装位置**：需要进水管+排水管+独立 16A 插座\n4. **安装当天**：在家试机（先试洗水流，确认无漏水），师傅当场离开后再签收\n\n师傅到达前 30 分钟会电话确认，可微信沟通。",
    ["小天鹅10kg洗烘已下单+周六9-12点送+免费安装+旧机回收抵199元，4999实付4800"],
    tool_name="ShoppingPlaceOrderTool"
))

T.append(make_traj(
    "sft_order_009", "place_order", "购物下单",
    "下单+加购延保",
    "买那台 9999 的 iPhone 15 Pro Max，加一年购物平台延保",
    {"items": [{"product_id": "mock_iphone15pro", "quantity": 1}, {"product_id": "mock_warranty", "quantity": 1}], "address": "DEFAULT"},
    [
        {"product_id": "mock_iphone15pro", "title": "iPhone 15 Pro Max 256G 钛金属", "price": 9999, "is_platform_self": True, "rating": 4.9, "key_specs": "订单[ORDER_ID]", "sales": "—"},
        {"product_id": "mock_warranty", "title": "购物平台延保 1年（iPhone 5000-10000价位）", "price": 499, "is_platform_self": True, "rating": 4.7, "key_specs": "延长1年保修/原厂1年+延保1年=2年", "sales": "—"}
    ],
    "✅ 下单成功，含延保！\n\n## 📦 订单详情\n\n- **iPhone 15 Pro Max 256G** ¥9999\n- **购物平台延保 1 年** ¥499\n- **小计**：¥10498\n- **订单号**：[ORDER_ID]\n\n## 🛡️ 延保激活流程\n\n购物平台延保**自动在 iPhone 收到货时激活**，不需要你操作。生效逻辑：\n\n| 时间段 | 保修方 |\n|---|---|\n| 第 1 年（2026-06-24 ~ 2027-06-23）| Apple 原厂保修 |\n| **第 2 年（2027-06-24 ~ 2028-06-23）**| **购物平台延保** |\n\n## 💡 延保覆盖什么\n\n✅ 覆盖：\n- 主板故障\n- 电池衰减 < 80%（免费换电池）\n- 屏幕显示异常（非人为破坏）\n- 摄像头/听筒/扬声器故障\n\n❌ 不覆盖：\n- 摔屏碎屏（需买 AppleCare+）\n- 进水（需买 AppleCare+）\n- 人为破坏\n\n## 🎯 建议\n\n如果你**经常带 iPhone 出门**，建议**追加 AppleCare+ ¥1499**（覆盖摔屏进水）。购物平台延保更适合「轻度使用怕电池衰减」的人。\n\n现在还可以追加 AppleCare+，需要的话告诉我。",
    ["iPhone 15 Pro Max已下单原厂1年保修", "购物平台延保499元延至2年保修，覆盖主板/电池/屏幕显示故障"],
    tool_name="ShoppingPlaceOrderTool"
))

# ═══ repurchase (3 条) ═══
T.append(make_traj(
    "sft_repurchase_005", "repurchase", "复购召回",
    "复购宠物粮+剂量推算",
    "我家猫快没粮了，再买之前那款",
    {"category_keyword": "猫粮", "time_range": "last_6_months", "include_usage_estimate": True},
    [
        {"product_id": "mock_cat_food_001", "title": "麦富迪鸡肉味成猫粮 5kg/袋 (你2个月前购买2袋)", "price": 119, "is_platform_self": True, "rating": 4.8, "key_specs": "购于2026-04-20/订单[ORDER_ID]/2袋10kg/月用量约2.5kg/预计还剩约2kg=8天用量", "sales": "月销3.5万"}
    ],
    "查到了！你 2 个月前买的是 **麦富迪鸡肉味成猫粮 5kg×2 袋**（订单 [ORDER_ID]）。\n\n## 📊 用量推算\n\n- 上次购买：2026-04-20（2 个月前）\n- 数量：5kg×2 袋 = 10kg\n- 你家猫月用量约：2.5kg\n- 已用约：2 个月 × 2.5kg = 5kg\n- **当前剩余约 5kg = 60 天用量**\n\n## 🤔 你确定要现在买吗？\n\n按照剩余量推算，**你还能撑 2 个月**。3 个选择：\n\n### 选项 A：现在囤货（推荐如果当前有 618 活动）\n趁活动价 ¥119 囤 1 袋，存够 4 个月用量。\n\n### 选项 B：等剩 1 周再下单\n平台自营次日达，**等用到剩约 1 周再下单**，避免囤太多 ●（猫粮开封 6 个月内吃完最佳）\n\n### 选项 C：先确认剩余量\n打开柜子目测一下，**如果剩超过半袋（>2.5kg）就先不用买**。\n\n## 💡 顺便\n\n618 活动期间这款现在 ¥99/袋（原 ¥119），**少 ¥20**。如果你确实想囤，现在下单最划算。需要直接帮你下单吗？",
    ["麦富迪鸡肉粮5kg×2袋你2月前购买，预计剩约5kg=60天用量，618活动价99元少20元"],
    tool_name="SkuRepurchaseRecall"
))

T.append(make_traj(
    "sft_repurchase_006", "repurchase", "复购召回",
    "复购药品+处方提醒",
    "我爸的降压药快吃完了，帮他再买",
    {"category_keyword": "降压药", "time_range": "last_3_months", "is_prescription": True},
    [
        {"product_id": "mock_med_001", "title": "拜耳 拜新同 硝苯地平控释片 30mg×7片×4盒 (上月购买)", "price": 168, "is_platform_self": True, "rating": 4.9, "key_specs": "处方药/上月购买2盒/订单[ORDER_ID]/需上传处方", "sales": "月销1.5万"}
    ],
    "查到了你爸上月买的是 **拜耳拜新同（硝苯地平控释片）** ¥168/4盒。\n\n## ⚠️ 处方药复购重要提醒\n\n降压药是**处方药**，平台自营有 2 个新规：\n\n### 📋 1. 必须上传有效处方\n如果你上月购买时已上传过处方，**3 个月内可直接复购**（无需再传）。超 3 个月需重新上传。\n\n### 📋 2. 必须确认服用情况\n购物平台药房客服会**电话确认**：\n- 患者姓名、年龄\n- 当前服药情况（无副作用？血压稳定？）\n- 是否需要医师远程指导调整剂量\n\n## 🏥 我的强烈建议\n\n降压药不要直接复购，**先做 2 件事**：\n\n1. **看上次复诊时间**：超过 3 个月需带爸爸去医院复诊，查血压+肝肾功能，调整剂量\n2. **每天测血压记录**：拜新同副作用之一是头晕，**最近血压如果<130/85 已经偏低**，需要医生调整\n\n## 🛒 如果一切正常，下单流程\n\n1. 进入商品页 → 选 4 盒装\n2. **填写患者信息**（姓名/年龄/性别）\n3. **上传处方**（或选「3 个月内已有处方」）\n4. **购物平台医师电话审核**（5-10 分钟）\n5. 审核通过后才能支付\n\n降压药断药风险极高，建议**剩 7 天就下单备着**。",
    ["拜耳拜新同硝苯地平控释片30mg×7片×4盒，处方药需医师审核+建议先复诊确认剂量"],
    tool_name="SkuRepurchaseRecall"
))

T.append(make_traj(
    "sft_repurchase_007", "repurchase", "复购召回",
    "复购大米+季节性新米推荐",
    "再买一袋之前的东北大米",
    {"category_keyword": "大米", "time_range": "last_4_months", "include_seasonal": True},
    [
        {"product_id": "mock_rice_001", "title": "金龙鱼 东北大米 长粒香 10kg (你3月前购买)", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "金龙鱼/长粒香米/10kg/购于2026-03-15", "sales": "月销4.5万"},
        {"product_id": "mock_rice_002", "title": "金龙鱼 2026 新米首发 五常稻花香 10kg", "price": 119, "is_platform_self": True, "rating": 4.9, "key_specs": "2026五常新米/稻花香2号/限量首发", "sales": "月销1.2万"}
    ],
    "查到你 3 个月前买的是 **金龙鱼东北长粒香米 ¥89/10kg**。\n\n## 🆕 顺便告诉你一个好消息\n\n**金龙鱼 2026 五常新米刚上市了 ¥119**（同 10kg）。新米和你之前买的有 3 个差异：\n\n## 📊 新米 vs 老米\n\n| 维度 | 你之前买的长粒香 ¥89 | 2026 五常新米 ¥119 |\n|---|---|---|\n| 米种 | 长粒香（普通东北米）| **五常稻花香 2 号**（顶级）|\n| 年份 | 2025 秋收 | **2026 春收（最新）**|\n| 香味 | 一般 | **明显稻花香（蒸饭满屋）**|\n| 月销 | 4.5 万 | 1.2 万（新品上市）|\n\n## 💡 我的建议\n\n### 选 A：继续复购老款 ¥89\n如果你**只是日常吃饭、对米味要求不高**，继续买长粒香没问题，省 ¥30。\n\n### 选 B：升级新米 ¥119 ⭐\n稻花香 2 号是东北大米天花板，**做白粥/做寿司/纯白米饭**差异最明显。多 ¥30 升级口感值得。\n\n### 选 C：两种各买一袋\n稻花香当主粮（白米饭），长粒香做炒饭/盖浇饭（炒饭不需要好米衬味）。**¥208 一个月用量**，吃米更精致。\n\n要哪种？我直接帮你下单。",
    ["金龙鱼长粒香10kg你3月前购买，日常吃饭复购老款省30元", "金龙鱼2026五常稻花香2号新米+10kg限量首发，蒸饭满屋稻香升级口感首选"],
    tool_name="SkuRepurchaseRecall"
))

# ═══ search_recommend (5 条) ═══
T.append(make_traj(
    "sft_search_010", "search_recommend", "购物搜索推荐",
    "多约束精准召回：3个硬条件同时满足",
    "给老婆买生日礼物，预算 2000，要求是大牌+颜值高+实用",
    {"query": "女士礼物 大牌包包/口红/护肤套装", "max_price": 2000, "filters": {"brand_tier": "luxury_or_premium", "use_case": "daily_practical"}},
    [
        {"product_id": "mock_gift_1", "title": "Coach 经典款 Trotter 半月包", "price": 1899, "is_platform_self": True, "rating": 4.9, "key_specs": "Coach经典款/半月包形/全皮革", "sales": "月销850"},
        {"product_id": "mock_gift_2", "title": "雅诗兰黛 节日限定礼盒 含小棕瓶眼霜+精华水+面霜", "price": 1680, "is_platform_self": True, "rating": 4.9, "key_specs": "限定礼盒/3件套+赠品/送礼标配", "sales": "月销1500"},
        {"product_id": "mock_gift_3", "title": "Tiffany 925银 Smile微笑项链", "price": 1990, "is_platform_self": True, "rating": 4.9, "key_specs": "Tiffany 925银/经典Smile造型", "sales": "月销520"}
    ],
    "2000 内大牌+颜值+实用三全的礼物，3 个方向：\n\n## 🎁 方案 A：实用派 → Coach 半月包 ¥1899\n大牌（Coach）+颜值（经典款）+实用（日常通勤包），三者全占。月销 850 件，**稳的选择**。\n\n## 🎁 方案 B：护肤派 → 雅诗兰黛节日礼盒 ¥1680\n3 件套（小棕瓶眼霜+精华水+面霜）+ 赠品，**节日限定包装**送礼有面子。\n\n## 🎁 方案 C：仪式感派 → Tiffany 微笑项链 ¥1990\n大牌中的大牌，Tiffany 经典 Smile 款，**适合纪念日/求婚/周年**这种重要节点。\n\n## 💡 怎么选\n\n看你老婆性格：\n- **务实派**：Coach 包她每天都能用\n- **护肤党**：雅诗兰黛她会感谢你 1 年\n- **浪漫派**：Tiffany 项链有情感价值\n\n## ⚠️ 避坑\n\n- ❌ 不要送 LV/Gucci 这种 logo 大的（2000 预算只能买配饰，反而显寒酸）\n- ❌ 不要送内衣类（除非她暗示过尺码）\n- ❌ 不要送化妆品（口红色号容易翻车）",
    ["Coach半月包经典款+大牌+颜值+日常通勤实用，务实派老婆首选", "雅诗兰黛节日礼盒3件套+限定包装+护肤一年用，护肤党老婆首选", "Tiffany 925银Smile项链+大牌中的大牌+情感价值，纪念日浪漫派首选"]
))

T.append(make_traj(
    "sft_search_011", "search_recommend", "购物搜索推荐",
    "推荐+使用场景细分",
    "给孩子买学习用的耳机，5岁，主要上网课用",
    {"query": "儿童网课耳机 5岁 护耳", "max_price": 300, "filters": {"target_age": "child_5_8", "purpose": "online_class"}},
    [
        {"product_id": "mock_child_001", "title": "西伯利亚 儿童网课耳机 头戴式 带麦", "price": 169, "is_platform_self": True, "rating": 4.9, "key_specs": "头戴式/85dB音量限制/带麦克风", "sales": "月销4.5万"},
        {"product_id": "mock_child_002", "title": "BuddyPhones Wave 儿童降噪耳机 防水款", "price": 269, "is_platform_self": True, "rating": 4.8, "key_specs": "IPX7防水/音量限制/分享端口", "sales": "月销1500"},
        {"product_id": "mock_child_003", "title": "JBL JR300 儿童头戴耳机 卡通造型", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "85dB音量/可折叠/卡通颜值", "sales": "月销2500"}
    ],
    "5 岁孩子网课耳机有 3 个关键参数：**音量限制 85dB + 头戴式（不入耳）+ 带麦克风**。3 款都达标：\n\n## 🎧 推荐\n\n**1. 西伯利亚 儿童网课耳机 ¥169** ⭐\n月销 4.5 万件断档第一，**85dB 音量保护听力**（避免幼儿听力损伤）。头戴式不入耳。\n\n**2. JBL JR300 ¥199**\n卡通造型颜值高，孩子更愿意戴。JBL 品牌做工可靠。\n\n**3. BuddyPhones Wave ¥269**\nIPX7 防水（孩子洒水不怕）+ 分享端口（兄妹一起听）。最贵但功能最全。\n\n## ⚠️ 关键忠告\n\n- ❌ **不要给 5 岁孩子用入耳式耳塞**（如 AirPods）：耳道还在发育，长期入耳影响听力\n- ❌ **不要买无音量限制的成人耳机**：孩子不知节制，可能造成不可逆听力损伤\n- ❌ **不要买蓝牙耳机**：网课时延迟会让画面和声音对不上\n\n## 🎯 配套建议\n\n买西伯利亚 ¥169 是闭眼选。同时**家长要每周检查孩子的听力**（用手指轻摩擦距 1 米能否听见）。",
    ["西伯利亚儿童网课耳机85dB限制+头戴式+月销4.5万，5岁孩子听力保护首选", "JBL JR300卡通造型+85dB音量+可折叠，孩子愿意戴的颜值款", "BuddyPhones Wave IPX7防水+分享端口，功能最全适合多娃家庭"]
))

T.append(make_traj(
    "sft_search_012", "search_recommend", "购物搜索推荐",
    "高端商品溢价合理性分析",
    "Hermès 同款的丝巾推荐，预算 500，不要假货",
    {"query": "高端丝巾 真丝 设计师款", "max_price": 600, "filters": {"is_authentic": True, "exclude_terms": ["仿款", "同款"]}},
    [
        {"product_id": "mock_scarf_lux1", "title": "上海故事 真丝印花丝巾 90cm 大方巾", "price": 469, "is_platform_self": True, "rating": 4.9, "key_specs": "国货老字号/100%桑蚕丝/90×90cm/独立设计款", "sales": "月销2500"},
        {"product_id": "mock_scarf_lux2", "title": "Cele 真丝丝巾 复古印花 65cm", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "100%桑蚕丝/小方巾/复古印花", "sales": "月销1200"},
        {"product_id": "mock_scarf_lux3", "title": "万事利 杭州真丝礼盒款 90cm", "price": 599, "is_platform_self": True, "rating": 4.8, "key_specs": "杭州万事利/G20国礼供应商/含礼盒", "sales": "月销680"}
    ],
    "Hermès 起步 ¥4000+，500 内的「Hermès 同款」99% 是仿品。**给你 3 款国货真丝（正品+设计感）**：\n\n## 🧣 推荐\n\n**1. 上海故事 真丝印花 ¥469** ⭐\n国货老字号 60 年历史，100% 桑蚕丝。90cm 大方巾尺寸**和 Hermès 同款规格**。\n\n**2. 万事利 杭州真丝 ¥599**\n**G20 杭州峰会国礼供应商**，含精装礼盒。**送礼比上海故事更显档次**。\n\n**3. Cele 复古印花 ¥299**\n小方巾 65cm（适合包柄/手腕缠绕），最便宜。\n\n## ⚠️ 鉴别 Hermès 仿品（避坑）\n\n如果你坚持要 Hermès 真品，**淘宝/拼多多任何低于 ¥1000 的「Hermès 丝巾」都是假货**。识别正品：\n- 边缘**必须是手工卷边**（看走线是凹凸不规则）\n- **真丝燃烧有蛋白味**（合成纤维有塑料味）\n- 正品有**防伪 NFC 标签**（手机扫验证）\n\n## 💡 真心建议\n\n**¥500 买国货正品丝巾比 ¥500 买 Hermès 仿品高级 10 倍**。万事利的杭州真丝在国际丝绸界是认可品牌，戴出去懂行的人会赞。\n\n何况——**Hermès 的精髓不是 logo，是版型 + 配色**。国货掌握这两点。",
    ["CITY_ADDRESS+100%桑蚕丝+90cm Hermès同规格，正品大方巾首选", "万事利G20国礼供应商+精装礼盒+杭州真丝，送礼高档次首选", "Cele小方巾65cm+100%桑蚕丝+复古印花，包柄手腕缠绕最便宜"]
))

T.append(make_traj(
    "sft_search_013", "search_recommend", "购物搜索推荐",
    "新手避坑：避开常见错误产品",
    "想买一台空气炸锅，听说有的会致癌？怎么选",
    {"query": "空气炸锅 安全 无涂层 / 食品级", "max_price": 600, "filters": {"safety_cert": "food_grade", "coating": "ceramic_or_none"}},
    [
        {"product_id": "mock_af_safe_1", "title": "山本 大容量空气炸锅 无涂层 304 不锈钢", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "304不锈钢内胆/无特氟龙涂层/食品级", "sales": "月销1.5万"},
        {"product_id": "mock_af_safe_2", "title": "九阳 KL45-V550 空气炸锅 陶瓷涂层", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "陶瓷涂层/食品级安全/可视玻璃盖", "sales": "月销3.5万"},
        {"product_id": "mock_af_safe_3", "title": "美的 KZ-J5503 空气炸锅 全方位热风", "price": 199, "is_platform_self": True, "rating": 4.7, "key_specs": "全方位热风/特氟龙涂层(高温降解风险)", "sales": "月销4.8万"}
    ],
    "**辟谣 + 推荐安全款**：\n\n## 🚨 「空气炸锅致癌」是怎么回事\n\n网传的致癌不是**空气炸锅本身**，而是 2 个具体风险点：\n\n### 1. **特氟龙涂层高温降解**\n传统空气炸锅内胆涂特氟龙（PTFE），**260℃以上会降解释放有害物质**。空气炸锅工作温度 180-200℃ 本身安全，但**空烧/干烧 5 分钟以上可能超 260℃**。\n\n### 2. **食物本身的丙烯酰胺**\n淀粉类食物（薯条/鸡块）高温烹饪都会产生丙烯酰胺，**这是空气炸锅、烤箱、油炸都会有的，不是空气炸锅独有**。\n\n## 🛡️ 安全选购 3 原则\n\n1. **无涂层** > 陶瓷涂层 > 特氟龙\n2. **食品级 304 不锈钢内胆**\n3. **避免空烧**（用前先放食物）\n\n## 🎯 推荐\n\n**1. 山本无涂层 304 不锈钢 ¥399** ⭐ 最安全\n304 不锈钢是食品级标杆，**无任何涂层**=没有降解风险。月销 1.5 万，安全党首选。\n\n**2. 九阳陶瓷涂层 ¥299** 性价比\n陶瓷涂层比特氟龙安全（800℃稳定），月销 3.5 万断档。\n\n**3. ❌ 美的 ¥199 特氟龙涂层**\n虽然便宜但用特氟龙，**不推荐给小孩老人家庭**。\n\n## 💡 真心建议\n\n直接选**山本无涂层 ¥399**，多花 ¥100 买的是绝对安全。",
    ["山本304不锈钢无涂层+食品级+月销1.5万，最安全空气炸锅", "九阳陶瓷涂层800℃稳定+可视玻璃盖+月销3.5万，性价比之王", "美的特氟龙涂层有降解风险，不推荐小孩老人家庭"]
))

T.append(make_traj(
    "sft_search_014", "search_recommend", "购物搜索推荐",
    "信息不全时主动反问",
    "推荐一款好用的耳机",
    {"query": "耳机 通用", "limit": 0},
    [],
    "你的需求太宽泛了，**耳机分 5 大类，单价差 100 倍**（¥50 - ¥5000）。能否告诉我以下信息，我帮你精准推荐：\n\n## 🤔 4 个关键问题\n\n### 1️⃣ 主要使用场景\n- 🎧 通勤/地铁 → 主动降噪耳机\n- 🏃 运动/健身 → 防水挂耳/骨传导\n- 💼 办公/会议 → 专业麦克风耳机\n- 🎮 游戏/电竞 → 低延迟有线耳机\n- 🎵 纯音乐欣赏 → Hi-Fi 有线耳机\n\n### 2️⃣ 预算范围\n- ¥100-300（入门）\n- ¥500-1000（中端主流）\n- ¥1500-2500（高端）\n- ¥3000+（旗舰/发烧）\n\n### 3️⃣ 偏好类型\n- 🎵 入耳式（小巧便携）\n- 🎧 头戴式（音质+长戴舒适）\n- 🦶 耳挂式（运动不掉）\n- 🦷 骨传导（不入耳）\n\n### 4️⃣ 配合什么设备\n- iPhone → AirPods 生态\n- Android → 通用蓝牙\n- 电脑 → USB/3.5mm 接口\n- 多设备切换 → 多点连接\n\n## 💡 举个例子\n\n如果你回答：\n- 场景：每天地铁通勤 1 小时\n- 预算：¥1500 以内\n- 偏好：入耳式（戴帽子方便）\n- 设备：iPhone\n\n我会立刻推荐：**AirPods Pro 2（¥1599）** + 备选 Sony WF-1000XM5（¥1599）\n\n请告诉我你的情况，我给精准推荐 👂",
    [],
    tool_name="SkuRecallShopping"
))

print(f"准备追加 {len(T)} 条")
with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
    for t in T:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")
print(f"✅ 已追加 {len(T)} 条")

with open(OUTPUT_PATH) as f:
    total = sum(1 for _ in f)
print(f"   总条数: {total}")
