# -*- coding: utf-8 -*-
"""Step 31: 第 19 批 10 条"""
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

# 1. similar_rec - 抱怨不防摔
T.append(make_traj(
    "sft_simrec_049", "similar_rec", "相似品推荐",
    "抱怨不防摔 → 推荐有军规防摔认证的同价位",
    "上次那个蓝牙音箱摔了一下就坏了，要防摔耐用的同价位款",
    {"query": "蓝牙音箱 防摔 军规 户外", "min_price": 300, "max_price": 800, "filters": {"drop_resistance": "MIL-STD"}},
    [
        {"product_id": "mock_spk_tough_1", "title": "JBL Charge 5 防水防摔 蓝牙音箱", "price": 799, "is_platform_self": True, "rating": 4.9, "key_specs": "IP67防水/防摔/20h续航/内置充电宝", "sales": "月销1.5万"},
        {"product_id": "mock_spk_tough_2", "title": "索尼 SRS-XB23 重低音 防水防摔", "price": 499, "is_platform_self": True, "rating": 4.8, "key_specs": "IP67/防摔认证/EXTRA BASS/月销9500", "sales": "月销9500"},
        {"product_id": "mock_spk_tough_3", "title": "UE Wonderboom 3 防摔360°音效", "price": 399, "is_platform_self": True, "rating": 4.8, "key_specs": "IP67/360°立体声/防摔/可挂包上", "sales": "月销6500"}
    ],
    "普通音箱摔一下就坏，是因为没有防摔结构。**IP67 防水+军规防摔**才是真正耐用：\n\n**1. UE Wonderboom 3（¥399）** ⭐ 性价比首选\n360° 全向音效+IP67+防摔，**可以直接挂包上**。月销 6500 件，最便宜的真防摔款。\n\n**2. 索尼 SRS-XB23（¥499）**\nEXTRA BASS 低音最强+IP67+防摔，月销 9500 件。\n\n**3. JBL Charge 5（¥799）**\n最贵但功能最全：20h 超长续航+**内置充电宝（能给手机充电）**，户外出行刚需。\n\n## 💡 防摔音箱关键参数\n- **IP67**：水下 1 米可泡 30 分钟\n- **防摔高度**：UE/JBL 均通过 1.5m 跌落测试\n- 不是防摔的音箱摔了就废，**买一次耐用的比摔坏两次合算**",
    ["UE Wonderboom 3 IP67+防摔+360°音效+月销6500，最便宜真防摔", "索尼SRS-XB23 IP67+EXTRA BASS低音强+月销9500，音质防摔均衡", "JBL Charge 5 IP67+20h续航+内置充电宝+月销1.5万，户外出行功能最全"]
))

# 2. similar_rec - 抱怨屏幕反光
T.append(make_traj(
    "sft_simrec_050", "similar_rec", "相似品推荐",
    "抱怨屏幕反光 → 推荐磨砂/防反光屏款",
    "上次买的平板屏幕反光厉害，户外完全看不清，要防反光的同价位款",
    {"query": "平板 防反光 磨砂屏 户外可见", "min_price": 2000, "max_price": 4000, "filters": {"anti_glare": True}},
    [
        {"product_id": "mock_tab_ag_1", "title": "华为 MatePad 11.5 PaperMatte 类纸屏", "price": 2699, "is_platform_self": True, "rating": 4.9, "key_specs": "PaperMatte类纸屏/抗反光/户外清晰/阅读护眼", "sales": "月销1.5万"},
        {"product_id": "mock_tab_ag_2", "title": "iPad Air 6 磨砂钢化膜版 贴膜方案", "price": 4999, "is_platform_self": True, "rating": 4.8, "key_specs": "iPad Air 6+贴paperfeel磨砂膜/模拟类纸屏/月销4500", "sales": "月销4500"},
        {"product_id": "mock_tab_ag_3", "title": "BOOX Tab Ultra C Pro 墨水屏彩色平板", "price": 3999, "is_platform_self": True, "rating": 4.8, "key_specs": "彩色墨水屏/零反光/户外直射完全可见/长时间阅读", "sales": "月销850"}
    ],
    "普通 LCD 屏幕在强光下反光是硬伤，3 种解决方案：\n\n**1. 华为 MatePad 11.5 PaperMatte（¥2699）** ⭐ 性价比首选\nPaperMatte 类纸屏是目前最好的「防反光 LCD」方案，**户外可见度提升 60%**，还护眼。月销 1.5 万。\n\n**2. BOOX 彩色墨水屏（¥3999）**\n墨水屏物理零反光，直射阳光完全可见。但屏幕刷新率低，**不适合看视频**，主要用于阅读/文档。\n\n**3. iPad Air 6 贴磨砂膜（¥4999）**\n贴 Paperfeel 类纸膜可以减少 50% 反光，但画质有损失，性价比最差。\n\n## 💡 按用途选\n- **通用（看视频+阅读+工作）** → 华为 PaperMatte\n- **主要户外阅读/文档** → BOOX 墨水屏\n- **已有 iPad 不想换机** → 贴 Paperfeel 磨砂膜 ¥89（单独买贴膜）",
    ["华为MatePad 11.5 PaperMatte类纸屏+防反光+月销1.5万，通用防反光性价比首选", "BOOX Tab Ultra C Pro彩色墨水屏+物理零反光+月销850，户外阅读文档极致", "iPad Air 6贴Paperfeel磨砂膜，已有iPad不换机的低成本方案"]
))

# 3. sku_comp - 家用打印机三类
T.append(make_traj(
    "sft_skucomp_047", "sku_comp", "商品对比",
    "喷墨 vs 激光 vs 照片打印机对比",
    "家里买打印机，喷墨/激光/照片打印机哪种适合家用",
    {"categories": ["彩色喷墨连供打印机", "黑白激光打印机", "照片打印机"], "topk_per_category": 1},
    [
        {"product_id": "mock_print_inkjet", "title": "爱普生 L3253 彩色喷墨连供打印机", "price": 1099, "is_platform_self": True, "rating": 4.9, "key_specs": "连供墨水/打印复印扫描一体/单页¥0.03/适合家用", "sales": "月销1.8万"},
        {"product_id": "mock_print_laser", "title": "奔图 P2209 黑白激光打印机", "price": 699, "is_platform_self": True, "rating": 4.9, "key_specs": "黑白激光/打印快22页/min/碳粉不堵头/办公高频", "sales": "月销4.5万"},
        {"product_id": "mock_print_photo", "title": "佳能 CP1500 照片打印机 随身款", "price": 699, "is_platform_self": True, "rating": 4.8, "key_specs": "4寸照片/热升华/色彩真实/随身携带", "sales": "月销1.2万"}
    ],
    "三类打印机适合完全不同的场景，**不要选错**：\n\n## 📊 三类对比\n\n| 类型 | 代表 | 价格 | 打彩色 | 打黑白 | 打照片 | 月销 |\n|---|---|---|---|---|---|---|\n| 彩色喷墨 | 爱普生 L3253 | ¥1099 | ✅ | ✅ | 一般 | 1.8 万 |\n| 黑白激光 | 奔图 P2209 | ¥699 | ❌ | **快+便宜** | ❌ | **4.5 万** |\n| 照片打印 | 佳能 CP1500 | ¥699 | ✅ | ❌ | **最好** | 1.2 万 |\n\n## 🎯 按用途选\n\n### 学生/家庭作业 → 黑白激光 ¥699\n- 打作业/文档/快递单，**最高频**\n- 不堵头（喷墨长期不用会堵）\n- 碳粉便宜，单页 ¥0.05\n- **月销 4.5 万是家庭打印机的绝对销冠**\n\n### 需要彩色打印 → 爱普生 L3253 ¥1099\n- 彩色文档/孩子作业/PPT\n- 连供墨水单页仅 ¥0.03（远低于激光）\n- 打印+复印+扫描三合一\n\n### 想冲洗旅行照片 → 佳能 CP1500 ¥699\n- 热升华打印，色彩媲美照相馆\n- 随身便携，手机照片直接打\n- **只能打 4 寸照片，不能打文档**\n\n## 💡 90% 家庭的选择\n**黑白激光 ¥699**，理由：\n1. 打文档频率远高于打照片\n2. 激光不会堵头（喷墨长期闲置必堵）\n3. 价格最便宜",
    ["爱普生L3253彩色喷墨连供+单页0.03+月销1.8万，需要彩色打印的家庭首选", "奔图P2209黑白激光+快22页/min+不堵头+月销4.5万，90%家庭文档打印绝对销冠", "佳能CP1500照片打印机+热升华色彩真实+月销1.2万，专门打旅行照片首选"]
))

# 4. sku_comp - 充电方案
T.append(make_traj(
    "sft_skucomp_048", "sku_comp", "商品对比",
    "桌面充电方案：多口充电器 vs 充电站 vs 无线充电板",
    "桌面充电设备太多了，多口充电器/充电站/无线充电板怎么选",
    {"skus": ["Anker 100W 4口氮化镓充电器", "Baseus 充电站 6口桌面", "Belkin 15W 三合一无线充电板"], "mode": "use_case_comparison"},
    [
        {"product_id": "mock_charge_1", "title": "Anker 100W 4口氮化镓充电器 PD3.0", "price": 249, "is_platform_self": True, "rating": 4.9, "key_specs": "100W/4口/PD3.0/笔记本+手机同时充", "sales": "月销3.5万"},
        {"product_id": "mock_charge_2", "title": "倍思 桌面充电站 6口 65W", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "6口/65W总功率/USB-A+USB-C/适合家庭多设备", "sales": "月销2.2万"},
        {"product_id": "mock_charge_3", "title": "Belkin 三合一无线充电板 15W MagSafe", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "MagSafe/同时充iPhone+AirPods+Watch/月销4500", "sales": "月销4500"}
    ],
    "三种方案解决不同痛点：\n\n## 📊 三类充电方案对比\n\n| 维度 | 多口充电器 ¥249 | 充电站 ¥199 | 无线充电板 ¥599 |\n|---|---|---|---|\n| 接口 | 4 口 | **6 口** | 无线 3 设备 |\n| 功率 | **100W**（够笔记本）| 65W | 15W |\n| 出差携带 | ✅ 小巧 | ❌ 较重 | ❌ |\n| 价格 | ¥249 | **¥199** | ¥599 |\n| 需要数据线 | 是 | 是 | **不需要** |\n\n## 🎯 三类场景\n\n### 出差 + 有笔记本 → **Anker 4口氮化镓 ¥249**\n- 100W 够给 MacBook 满速充电\n- 体积小，出差装包不占地方\n- 4 口够手机+耳机+手表+笔记本同时充\n\n### 家庭多设备（不带出门）→ **倍思充电站 ¥199**\n- 6 口最多设备，家人各插各的\n- ¥199 是最便宜的解决方案\n- 总功率 65W（4 个手机同时充没问题）\n\n### 苹果全家桶用户 → **Belkin 三合一 ¥599**\n- 放枕头边一放，iPhone+Watch+AirPods 全部充\n- **不用找线**，睡觉时最方便\n- 贵 ¥400 但买的是「懒人仪式感」\n\n## 💡 真心建议\n\n- 宿舍/一个人 → **倍思充电站 ¥199 最划算**\n- 经常出差 → Anker 氮化镓（替代原来一堆充电头）\n- 苹果全家桶 → Belkin（贵但真的方便）",
    ["Anker 100W 4口氮化镓+PD3.0+月销3.5万，出差+有笔记本用户首选", "倍思充电站6口+65W+月销2.2万，家庭多设备最便宜方案", "Belkin三合一无线+MagSafe+月销4500，苹果全家桶睡前一放全充"]
))

# 5. matching - 居家瑜伽
T.append(make_traj(
    "sft_match_047", "matching_purchase", "搭配购物",
    "男士休闲穿搭（居家+轻通勤）",
    "周末休闲穿搭，配帽衫+休闲裤+小白鞋，要有点质感",
    {"query": "男士休闲穿搭 帽衫+休闲裤+小白鞋", "filters": {"style": "casual_quality", "gender": "male"}},
    [
        {"product_id": "mock_casual_1", "title": "优衣库 Premium Lamb 羊羔绒帽衫 米白", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "羊羔绒/米白/质感帽衫/月销8500", "sales": "月销8500"},
        {"product_id": "mock_casual_2", "title": "无印良品 法国亚麻休闲长裤 卡其", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "法国亚麻/卡其色/直筒/月销3500", "sales": "月销3500"},
        {"product_id": "mock_casual_3", "title": "Adidas Stan Smith 小白鞋 经典款", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "Stan Smith经典/小白鞋/30年不过时", "sales": "月销4500"}
    ],
    "男士休闲有质感穿搭 3 件 ¥1297：\n\n## 👕 完整方案\n\n| 单品 | 商品 | 价格 |\n|---|---|---|\n| 帽衫 | **优衣库羊羔绒帽衫 米白** | ¥399 |\n| 休闲裤 | MUJI 法国亚麻长裤 卡其 | ¥299 |\n| 鞋子 | Adidas Stan Smith 小白鞋 | ¥599 |\n\n## 🎨 配色公式\n\n**米白帽衫 + 卡其裤 + 白色小白鞋** = 莫兰迪暖色系男士休闲\n\n- 米白+卡其是同色系深浅搭配（永不出错）\n- 白色小白鞋提亮整体（任何场合百搭）\n- **比全黑/全灰高级 10 倍**\n\n## 💡 选品理由\n\n### 优衣库羊羔绒帽衫 ¥399\n普通棉帽衫显廉价，羊羔绒帽衫有**毛呢感**——同样的廓形，质感差距明显。\n\n### MUJI 亚麻裤 ¥299\n亚麻面料**夏天凉快冬天有型**，弹性好比牛仔裤舒服，卡其色百搭。\n\n### Stan Smith ¥599\n30 年不过时的经典款，**不管什么裤子都能配**。比普通帆布鞋显精致。\n\n## ⚠️ 男士休闲避雷\n- ❌ 衣服+裤子+鞋全用不同品牌 logo（土）\n- ❌ 紧身裤（除非健身肌肉型）\n- ❌ 运动帽衫配正装鞋（混搭失败）",
    ["优衣库羊羔绒帽衫米白+质感面料+月销8500，普通棉帽衫升级版", "MUJI法国亚麻长裤卡其+直筒+月销3500，夏凉冬型比牛仔裤舒服", "Adidas Stan Smith小白鞋+经典款+月销4500，30年不过时百搭"]
))

# 6. matching - 家庭影音布线
T.append(make_traj(
    "sft_match_048", "matching_purchase", "搭配购物",
    "孩子生日礼物整体搭配（8岁男孩）",
    "8岁男孩生日，配乐高+无线遥控车+探索类书籍",
    {"query": "8岁男孩生日礼物 乐高+遥控车+科普书", "filters": {"target_age": "boy_8", "category": "birthday_gift"}},
    [
        {"product_id": "mock_boy_1", "title": "乐高 Technic 机械组 科技系列 10+岁", "price": 499, "is_platform_self": True, "rating": 4.9, "key_specs": "乐高Technic/机械原理/500+颗粒/7-14岁", "sales": "月销2500"},
        {"product_id": "mock_boy_2", "title": "德国双鹰 C51030 高速无线遥控汽车", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "30km/h高速/2.4G控制/可越野/男孩最爱", "sales": "月销1.5万"},
        {"product_id": "mock_boy_3", "title": "少年读百科 科学实验100个 儿童版", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "100个科学实验/含实验材料/寓教于乐", "sales": "月销3500"}
    ],
    "8 岁男孩生日礼物 3 件套 ¥897，**智力+动手+探索全覆盖**：\n\n## 🎁 完整方案\n\n| 礼物 | 商品 | 价格 |\n|---|---|---|\n| 🥇 乐高 Technic | **机械组科技系列** | ¥499 |\n| 遥控车 | 德国双鹰高速越野 | ¥299 |\n| 书籍 | 少年读百科科学实验 | ¥99 |\n\n## 💡 选品逻辑\n\n### 乐高 Technic ¥499\n8 岁开始能理解机械原理——齿轮/连杆/差速器——这套**比普通积木难度升级**，男孩有挑战感。拼完还能理解「为什么转弯时轮子速度不同」。\n\n### 遥控车 ¥299\n**男孩最爱没有之一**。30km/h 高速+越野轮胎，充电 1 小时玩 40 分钟。德国双鹰品质稳定，月销 1.5 万。\n\n### 科学实验书 ¥99\n100 个实验含材料（小苏打+柠檬酸+颜料等），**动手做出来比看视频记得住**，送书不会显得「无聊」。\n\n## 🎂 送礼建议\n\n- 乐高当「主礼物」（最重，包装最好看）\n- 遥控车当「开门红」（先玩这个）\n- 书籍放在包里（压轴，告诉他里面有 100 个实验）\n\n## ⚠️ 8 岁男孩礼物避雷\n- ❌ 太幼稚（4 岁以下玩具）\n- ❌ 保健品/营养品（他会觉得不是礼物）\n- ❌ 超出年龄复杂度的（他会挫败感放弃）",
    ["乐高Technic机械组+500颗粒+月销2500，8岁男孩理解机械原理智力挑战", "德国双鹰高速遥控车30km/h越野+月销1.5万，男孩最爱开门红", "少年读百科100个科学实验含材料+月销3500，动手做实验压轴礼物"]
))

# 7. bundle - 健康监测
T.append(make_traj(
    "sft_bundle_045", "bundle_purchase", "组合购物",
    "3000 元新生儿摄影棚装备",
    "想给宝宝拍百天照，3000 自己布置摄影棚",
    {"query": "百天照摄影棚装备 补光灯+背景+服装", "max_price": 3200},
    [
        {"product_id": "mock_photo_1", "title": "南光 LED 摄影灯 双灯套装 柔光箱", "price": 899, "is_platform_self": True, "rating": 4.9, "key_specs": "双灯柔光箱/无影补光/3200-5600K色温/摄影专用", "sales": "月销1500"},
        {"product_id": "mock_photo_2", "title": "婴儿百天照拍摄道具套装 毛毯+篮子", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "百天照专用/含毛毯+藤编篮+枕头+小熊", "sales": "月销2500"},
        {"product_id": "mock_photo_3", "title": "宝宝百天照服装 5 套 不同主题", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "5套服装/不同主题/拍完可留念", "sales": "月销1800"},
        {"product_id": "mock_photo_4", "title": "纯色背景布 2.7×3m 3 色套装", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "纯白+米色+浅灰/3色/适合婴儿摄影", "sales": "月销3500"},
        {"product_id": "mock_photo_5", "title": "索尼 ZV-E10 II Vlog 相机 入门套机", "price": 4999, "is_platform_self": True, "rating": 4.9, "key_specs": "1英寸大底/4K/Vlog定位/入门摄影刚好", "sales": "月销4500"}
    ],
    "宝宝百天照自拍套装，**¥1796 配齐所有道具，不用 ¥5000 请摄影师**：\n\n## 📷 完整方案（不含相机）\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 补光灯 | 南光双灯柔光箱套装 | ¥899 |\n| 道具 | 百天照道具套装 | ¥399 |\n| 服装 | 5 套主题服装 | ¥299 |\n| 背景布 | 3 色 2.7×3m | ¥199 |\n| **道具合计** | | **¥1796** |\n\n## 💡 相机怎么解决\n\n**方案 A：用手机（免费）**\n现代旗舰手机（iPhone 15/小米 14）拍照完全够用，**配上好的灯光和布景**，手机也能拍出摄影棚效果。\n\n**方案 B：买相机（+¥4999）**\n索尼 ZV-E10 II 是摄影入门最佳，**但宝宝以后各种成长阶段都能用**（不只百天照），这笔钱值得。\n\n## 📸 百天照布置 SOP\n\n```\n1. 背景布铺地 + 挂墙（白色打底）\n2. 两盏柔光灯斜 45° 打主光+填充光\n3. 藤编篮+毛毯做「床」\n4. 宝宝睡着后抓拍（最自然）\n5. 5 套服装换来换去，每套 5-10 分钟\n```\n\n## 💰 对比请摄影师\n\n| 方案 | 成本 | 效果 |\n|---|---|---|\n| 请摄影师 | ¥2000-5000（只拍一次）| 专业 |\n| **自备道具** | **¥1796（可反复用）**| 自然真实 |\n| 差距 | **省 ¥200-3200** | 手机+好灯光效果不差 |",
    ["南光双灯柔光箱套装+3200-5600K色温+月销1500，摄影棚级别补光无阴影", "百天照专用道具+藤编篮+毛毯+月销2500，一套买齐省得单件凑", "5套婴儿百天照主题服装+月销1800，换套服装换场景", "纯色背景布3色2.7×3m+月销3500，专业摄影棚背景起步"]
))

# 8. bundle
T.append(make_traj(
    "sft_bundle_046", "bundle_purchase", "组合购物",
    "2500 元极简家庭监控系统",
    "家里老人独居，想装一套监控可以手机查看，2500 预算",
    {"query": "家庭监控系统 老人独居 手机查看", "max_price": 2800},
    [
        {"product_id": "mock_cam_1", "title": "海康威视 室内摄像头 4路 套装", "price": 1299, "is_platform_self": True, "rating": 4.9, "key_specs": "4路摄像头+硬盘录像机/手机远程/夜视/专业安防", "sales": "月销2500"},
        {"product_id": "mock_cam_2", "title": "萤石 C6W 双向通话摄像头 2K", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "2K/双向通话/AI人形检测/手机App/单个装", "sales": "月销4.5万"},
        {"product_id": "mock_cam_3", "title": "小米 室外摄像头 门口专用 防水", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "户外防水/门口摄像/米家App/夜视", "sales": "月销2.2万"},
        {"product_id": "mock_cam_4", "title": "智能门铃 可视 电池免布线款", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "可视门铃/电池款免布线/手机查看来访者", "sales": "月销3500"}
    ],
    "老人独居监控方案，**2500 预算配 3 个关键位置**：\n\n## 📹 推荐方案 ¥997（精简有效）\n\n| 位置 | 商品 | 价格 | 作用 |\n|---|---|---|---|\n| 客厅 | **萤石 C6W 2K** | ¥299 | 老人日常活动监测 |\n| 门口 | **小米室外防水** | ¥299 | 谁来访/老人进出 |\n| 大门 | **可视门铃电池款** | ¥399 | 老人不方便来开门时你能看到 |\n| **合计** | | **¥997** | |\n\n## 💡 为什么不推荐专业 4 路套装\n\n海康 4 路套装 ¥1299 需要**布线+打孔+专业安装**（加人工 ¥500+），操作复杂。**¥997 的方案无线安装，老人家 30 分钟装完**，效果完全够用。\n\n## 📱 手机查看体验\n\n- 萤石/小米都有 App，**随时查看实时画面**\n- 老人离开视野超过 X 分钟 → AI 自动报警推送\n- 双向通话（可以和老人说话）\n- 云存储 7 天录像（手机 App 随时回放）\n\n## 💰 余 ¥1503 干什么\n\n1. **智能手表（一键 SOS）¥599**：跌倒自动报警（比摄像头更主动）\n2. **智能燃气检测器 ¥199**：老人忘关燃气报警\n3. **门磁传感器 ¥79**：门没关自动提醒\n4. **存上备用**：有问题随时补充设备\n\n## ⚠️ 隐私注意\n\n安装前**一定告诉老人**有摄像头，避免老人感到被监视有心理压力。这些摄像头是「关心」不是「监视」——**和老人一起学会 App 查看，让他们也有安全感**。",
    ["萤石C6W 2K室内+双向通话+AI人形检测+月销4.5万，客厅老人活动监测首选", "小米室外防水摄像头+米家App+月销2.2万，门口来访记录", "可视门铃电池款免布线+手机查看+月销3500，大门远程查看来访者"]
))

# 9. place_order
T.append(make_traj(
    "sft_order_025", "place_order", "购物下单",
    "分期付款下单大件电器",
    "帮我下单那台 9999 的戴森吸尘器，用花呗分 12 期",
    {"product_id": "mock_dyson_v15", "payment_method": "installment_12", "address": "DEFAULT"},
    [
        {"product_id": "mock_dyson_v15", "title": "戴森 V15 Detect Complete 旗舰吸尘器", "price": 9999, "is_platform_self": True, "rating": 4.9, "key_specs": "订单[TRACKING_ID]-DYSON-2284/花呗12期/每期833元/手续费约1.5%", "sales": "—"}
    ],
    "✅ 下单成功，花呗 12 期已确认！\n\n## 📦 订单详情\n\n- **商品**：戴森 V15 Detect Complete 旗舰无线吸尘器\n- **总价**：¥9999\n- **订单号**：[TRACKING_ID]-DYSON-2284\n- **付款方式**：**花呗 12 期免息**（或 1.5% 手续费，取决于当前活动）\n\n## 💰 12 期还款计划\n\n| 每月还款 | 总期数 | 总支出 |\n|---|---|---|\n| **¥833** | 12 期 | ¥9999（免息）或 ¥10149（有息）|\n\n**注意**：\n- 购物平台免息活动每月不同，下单时看「费率说明」\n- 当前活动显示：**戴森产品 12 期免息**（0 手续费）\n- 确认支付页面显示「手续费 ¥0」才是免息\n\n## ⏰ 发货时间\n\n- 预计**明天发货**，后天送达\n- 戴森吸尘器**不含安装服务**（直接使用，无需安装）\n\n## 💡 分期使用建议\n\n### 什么时候分期值\n- 商品本身有**免息分期**活动（¥833×12=¥9999，一分不多花）\n- 短期现金流紧张但收入稳定\n\n### 什么时候分期不值\n- **有息分期**（1.5% = 多花 ¥150）\n- 你的理财收益 > 贷款利率（极少数情况）\n\n### 提前还款\n\n如果中途不想分期了，花呗支持**提前还清剩余本金**，不收违约金。\n\n## 🔧 收到戴森 V15 后\n\n1. **拆箱录视频**（大额商品保留凭证）\n2. 安装时看包装盒里的「快速安装指南」（2 分钟装好）\n3. 首次使用建议**充满电再用**\n4. 每次用完清空集尘桶（不要等满了再倒）",
    ["戴森V15 Detect Complete旗舰+花呗12期833元/月+订单[TRACKING_ID]-DYSON-2284，0手续费分期到手"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase
T.append(make_traj(
    "sft_repurchase_023", "repurchase", "复购召回",
    "复购婴儿辅食+阶段性升级提醒",
    "再买之前那个婴儿辅食米粉",
    {"category_keyword": "婴儿米粉", "time_range": "last_3_months", "check_stage_upgrade": True},
    [
        {"product_id": "mock_rice_old", "title": "嘉宝有机高铁米粉 一段 227g (2月前购买)", "price": 79, "is_platform_self": True, "rating": 4.9, "key_specs": "你2月前购买/一段(6月+)/月销2.8万", "sales": "月销2.8万"},
        {"product_id": "mock_rice_stage2", "title": "嘉宝有机米粉 二段 7种谷物 227g", "price": 79, "is_platform_self": True, "rating": 4.9, "key_specs": "二段(8月+)/7种谷物/更多营养/口感升级", "sales": "月销1.5万"},
        {"product_id": "mock_rice_varied", "title": "嘉宝 有机蔬菜米粉 多口味组合 6盒", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "多口味/胡萝卜+菠菜+南瓜/6盒组合", "sales": "月销4500"}
    ],
    "查到你 2 个月前买的是 **嘉宝有机高铁米粉一段 ¥79**。\n\n## 🍼 重要提醒：阶段升级！\n\n**一段米粉适合 6-8 个月宝宝**，你宝宝现在可能已经 **8 个月+**，应该升级到二段了：\n\n| 阶段 | 适用月龄 | 特点 |\n|---|---|---|\n| 一段 | 6-8 个月 | 单一谷物，最易消化 |\n| **二段** | **8-12 个月** | 多种谷物，更丰富营养 |\n| 三段 | 1 岁+ | 接近成人食物 |\n\n## 🛒 升级建议\n\n### 选项 A：二段米粉 ¥79（同价升级）\n**嘉宝二段 7 种谷物**：同品牌升级，宝宝口感接受度高。\n\n### 选项 B：多口味组合 ¥299 ⭐ 推荐\n**6 盒多口味组合**：胡萝卜+菠菜+南瓜……\n- 8 个月+ 宝宝可以开始接触不同食物味道\n- 培养不挑食习惯要从辅食开始\n- 6 盒约 2 个月用量，单盒 ¥49.8（比单买便宜）\n\n### 选项 C：继续复购一段\n如果宝宝月龄确认还不到 8 个月，继续买一段没问题。\n\n## 💡 我的建议\n\n**先告诉我宝宝现在多大了**——我帮你判断该买一段还是升级二段。\n\n如果是 8 个月+，**直接选多口味组合 ¥299**：\n- 接触多种食物味道是这阶段发育关键\n- 同品牌宝宝接受度最高\n- 6 盒够用 2 个月，省去下次复购麻烦\n\n你宝宝现在多大？",
    ["嘉宝一段米粉你2月前购买+月销2.8万，继续复购仅限宝宝6-8月内", "嘉宝二段7种谷物米粉+月销1.5万，8月+宝宝阶段升级首选", "嘉宝多口味蔬菜米粉6盒组合+月销4500，培养不挑食习惯8月+推荐"],
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
