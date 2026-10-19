# -*- coding: utf-8 -*-
"""Step 41: 第 29 批 10 条"""
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

# 1. similar_rec - 抱怨锅太重
T.append(make_traj(
    "sft_simrec_069", "similar_rec", "相似品推荐",
    "抱怨铸铁锅太重 → 推荐轻量不粘款",
    "买的铸铁锅炒菜手太酸，要轻一点同价位的",
    {"query": "炒锅 轻量 不粘 1kg以内", "max_price": 400, "filters": {"weight_max_kg": 1.5}},
    [
        {"product_id": "mock_wok_lite_1", "title": "苏泊尔 钛系列 不粘炒锅 32cm 1.2kg", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "钛合金涂层/1.2kg轻量/32cm/不粘耐用/月销3.5万", "sales": "月销3.5万"},
        {"product_id": "mock_wok_lite_2", "title": "双立人 不粘炒锅 28cm 铝锅轻量款", "price": 369, "is_platform_self": True, "rating": 4.8, "key_specs": "德国品牌/铝制轻量/1.0kg/28cm", "sales": "月销1.5万"},
        {"product_id": "mock_wok_lite_3", "title": "特福 泰坦 30cm 钛+陶瓷 轻不粘", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "法国特福/钛+陶瓷涂层/1.3kg/月销1.2万", "sales": "月销1.2万"}
    ],
    "铸铁锅炒菜手酸是真实问题，3 款轻量不粘替代：\n\n**1. 苏泊尔钛系列（¥299）** ⭐ 性价比第一\n**1.2kg+钛合金不粘**，月销 3.5 万件是轻量不粘锅的销冠，价格最低。\n\n**2. 双立人铝锅（¥369）**\n德国品牌+铝制 1.0kg 最轻，适合追求品牌质感的厨房党。\n\n**3. 特福泰坦（¥399）**\n法国特福，钛+陶瓷双涂层，耐用性最强，**用 5 年不掉涂层**。\n\n## 💡 各材质重量参考\n- 铸铁锅：3-5kg（重但导热均匀）\n- 不锈钢：2-3kg\n- **钛合金/铝制**：**1-1.5kg**（轻便首选）\n\n如果追求长期耐用，特福钛锅虽贵 ¥100 但涂层寿命更长。",
    ["苏泊尔钛系列32cm+1.2kg+钛合金涂层+月销3.5万，轻量不粘性价比销冠", "双立人铝制28cm+1.0kg最轻+月销1.5万，德国品牌品质手感轻盈", "特福泰坦30cm钛+陶瓷双涂层+1.3kg+月销1.2万，耐用性最强用5年"]
))

# 2. similar_rec - 抱怨没法调光
T.append(make_traj(
    "sft_simrec_070", "similar_rec", "相似品推荐",
    "抱怨亮度不可调 → 推荐智能调光款",
    "之前买的台灯只有一档亮度，写作业时太亮，晚上看书太暗，要能调光的同价位",
    {"query": "台灯 多档调光 色温可调 护眼", "max_price": 300, "filters": {"dimming_levels": "continuous_or_multi"}},
    [
        {"product_id": "mock_lamp_dim_1", "title": "飞利浦 桌面台灯 无级调光 4档色温", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "无级调光/4档色温/触控/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "mock_lamp_dim_2", "title": "松下 台灯 3档亮度+2档色温 护眼", "price": 269, "is_platform_self": True, "rating": 4.9, "key_specs": "3档亮度×2档色温/日本松下/无频闪", "sales": "月销9500"},
        {"product_id": "mock_lamp_dim_3", "title": "小米 米家台灯 Pro App联动 无级调光", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "App无级调光/色温2700-6500K/手势控制", "sales": "月销1.2万"}
    ],
    "单档亮度是最影响体验的缺陷，3 款调光款：\n\n**1. 飞利浦无级调光（¥199）** ⭐ 性价比首选\n**无级调光**（不是几档跳变，是连续调节），触控方便，月销 2.5 万。\n\n**2. 松下 3×2 档（¥269）**\n日本松下品牌，3 档亮度×2 档色温，**无频闪对眼睛最友好**。\n\n**3. 小米米家 Pro（¥299）**\n**App 联动**，可以设置定时/自动调节亮度，手势挥手开关灯。米家生态首选。\n\n## 💡 色温怎么用\n\n- **白光（6500K）**：白天学习、写作业，精神集中\n- **暖白（4000K）**：晚间阅读，眼睛不疲劳\n- **暖光（2700K）**：睡前，促进褪黑素分泌助眠\n\n一盏能调色温的台灯 = 学习、阅读、助眠三场景全覆盖。",
    ["飞利浦台灯无级调光+4档色温+触控+月销2.5万，连续调节性价比首选", "松下台灯3档亮度2档色温+无频闪+月销9500，日本品牌眼睛最友好", "小米米家Pro App无级调光+色温2700-6500K+月销1.2万，米家生态定时自动调"]
))

# 3. sku_comp
T.append(make_traj(
    "sft_skucomp_067", "sku_comp", "商品对比",
    "国产手机四大品牌旗舰综合对比",
    "国产旗舰手机，小米/华为/OPPO/vivo 最新款各有什么优势",
    {"skus": ["小米15 Ultra", "华为Pura 80 Pro", "OPPO Find X8 Pro", "vivo X200 Pro"], "mode": "brand_flagship_comparison"},
    [
        {"product_id": "mock_mi15u", "title": "小米 15 Ultra 徕卡旗舰", "price": 6499, "is_platform_self": True, "rating": 4.9, "key_specs": "徕卡四摄+1英寸/骁龙8 Elite/影像天花板", "sales": "月销8500"},
        {"product_id": "mock_hw_p80", "title": "华为 Pura 80 Pro 麒麟旗舰", "price": 6988, "is_platform_self": True, "rating": 4.9, "key_specs": "麒麟9100/卫星通话/XMAGE影像/自主生态", "sales": "月销1.2万"},
        {"product_id": "mock_oppo_x8", "title": "OPPO Find X8 Pro 哈苏旗舰", "price": 5999, "is_platform_self": True, "rating": 4.9, "key_specs": "哈苏四摄/天玑9400/最快充100W/月销6500", "sales": "月销6500"},
        {"product_id": "mock_vivo_x200", "title": "vivo X200 Pro 蔡司旗舰", "price": 5999, "is_platform_self": True, "rating": 4.9, "key_specs": "蔡司APO超望远/天玑9400/6000mAh超大电池", "sales": "月销7500"}
    ],
    "四大国产旗舰各有招牌优势，按你最在意的维度选：\n\n## 📊 核心优势对比\n\n| 品牌 | 价格 | 最强点 | 月销 |\n|---|---|---|---|\n| 小米 15 Ultra | ¥6499 | **徕卡+1英寸主摄影像天花板** | 8500 |\n| 华为 Pura 80 Pro | ¥6988 | **自主麒麟+卫星通话+鸿蒙生态** | 1.2万 |\n| OPPO Find X8 Pro | ¥5999 | **100W最快充+哈苏调色** | 6500 |\n| vivo X200 Pro | ¥5999 | **蔡司APO超望远+6000mAh续航王** | 7500 |\n\n## 🎯 按需求选\n\n### 影像党（拍照最强）→ **小米 15 Ultra**\n1 英寸主摄是唯一做到的，徕卡调色，**发布即成为评测机构影像第一**。\n\n### 商务/国产生态党 → **华为 Pura 80 Pro**\n卫星通话+麒麟自研+鸿蒙生态闭环。月销 1.2 万说明**商务用户认可度最高**。\n\n### 充电党/性价比 → **OPPO/vivo 两款 ¥5999**\n比华为小米便宜 ¥500-1000，性能相差不大：\n- OPPO：100W 快充（20 分钟充满）\n- vivo：6000mAh 超大电池（两天不充）\n\n## 💡 真心建议\n\n**不要「机皇」情结**——6000 元以上的手机**日常使用体验差距极小**。建议按这个顺序想清楚：\n1. 用 iPhone 吗？（不用再比）\n2. 在乎卫星/鸿蒙吗？→ 华为\n3. 最在乎影像吗？→ 小米\n4. 要省 1000 块？→ OPPO/vivo 任选",
    ["小米15 Ultra徕卡+1英寸主摄+月销8500，影像党唯一选择", "华为Pura 80 Pro麒麟+卫星通话+月销1.2万，商务/国产生态闭环首选", "OPPO Find X8 Pro 100W快充+哈苏+月销6500，20分钟充满快充党", "vivo X200 Pro蔡司APO望远+6000mAh+月销7500，续航+长焦双优"]
))

# 4. sku_comp
T.append(make_traj(
    "sft_skucomp_068", "sku_comp", "商品对比",
    "不同档次洗碗机对比",
    "买洗碗机纠结，4000/6000/10000 三档差在哪",
    {"skus": ["方太嵌入式4000档", "西门子嵌入式6000档", "博世嵌入式10000旗舰"], "mode": "price_tier_comparison"},
    [
        {"product_id": "mock_dw_4k", "title": "方太 EW14H 13套嵌入式 智能洗", "price": 3999, "is_platform_self": True, "rating": 4.9, "key_specs": "13套/72℃高温杀菌/烘干/国产实惠", "sales": "月销3500"},
        {"product_id": "mock_dw_6k", "title": "西门子 SJ636X00JC 14套 全嵌 静音", "price": 5999, "is_platform_self": True, "rating": 4.9, "key_specs": "14套/43dB超静音/自动开门烘干/月销2500", "sales": "月销2500"},
        {"product_id": "mock_dw_10k", "title": "博世 SMS8ZCI00W 旗舰 抽屉式第三层", "price": 9999, "is_platform_self": True, "rating": 4.9, "key_specs": "14套+第三层/EcoSilence/家庭套装专用", "sales": "月销680"}
    ],
    "**结论：6000 元是家用洗碗机的性价比拐点**。\n\n## 📊 三档核心差异\n\n| 维度 | 方太 ¥3999 | 西门子 ¥5999 | 博世 ¥9999 |\n|---|---|---|---|\n| 容量 | 13 套 | 14 套 | **14 套+第三层** |\n| 噪音 | 45dB | **43dB（更静）** | 42dB |\n| 烘干 | 热风烘干 | **自动开门烘干** | 开门+分子筛 |\n| 适合 | 3 口普通家庭 | **3-5 口标准** | 追求极致 |\n\n## 💰 差价分析\n\n### ¥3999 → ¥5999（+¥2000）值\n- 13→14 套（多放碗筷）\n- **自动开门烘干**：关键升级（烘干彻底不留水）\n- 噪音降 2dB\n\n### ¥5999 → ¥9999（+¥4000）不值（90% 用户）\n- 第三层抽屉：放刀具/调料盖（大多数人装不满）\n- 分子筛烘干：比开门烘干略好\n- 品牌溢价\n\n## 🎯 我的建议\n\n**直接选西门子 ¥5999**，3-5 口家庭标准配置，月销 2500 件是洗碗机市场认可度最高的档位。",
    ["方太EW14H 13套+72℃高温杀菌+月销3500，国产实惠3口家庭入门", "西门子SJ636X00JC 14套+自动开门烘干+43dB+月销2500，家用性价比拐点甜点", "博世SMS8ZCI00W第三层+分子筛烘干+月销680，追求极致的旗舰配置"]
))

# 5. matching
T.append(make_traj(
    "sft_match_067", "matching_purchase", "搭配购物",
    "新生儿满月酒整体布置",
    "宝宝满月酒布置，配桌旗+气球+宝宝展示板+糖果袋",
    {"query": "满月酒布置 桌旗+气球+展示板+糖果", "filters": {"category": "baby_full_month_party"}},
    [
        {"product_id": "mock_month_1", "title": "满月宴桌旗套装 粉蓝双色 10件", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "桌旗+插花瓶+数字贴/满月宴专用/月销1.8万", "sales": "月销1.8万"},
        {"product_id": "mock_month_2", "title": "满月气球套装 宝宝主题 100个", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "满月主题/100个/含胎毛+出生日期字母", "sales": "月销1.2万"},
        {"product_id": "mock_month_3", "title": "宝宝成长展示板 A1 写真板定制", "price": 59, "is_platform_self": True, "rating": 4.9, "key_specs": "A1定制/宝宝照片+出生数据/满月展示核心", "sales": "月销3.5万"},
        {"product_id": "mock_month_4", "title": "满月糖果袋 100只 宝宝主题", "price": 49, "is_platform_self": True, "rating": 4.8, "key_specs": "100只/满月主题图案/装糖果伴手礼", "sales": "月销4.5万"}
    ],
    "满月酒布置 4 件套 ¥296，**温馨仪式感拉满**：\n\n## 👶 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 桌旗 | 满月宴双色 10 件套 | ¥89 |\n| 气球 | 满月主题 100 个 | ¥99 |\n| 展示板 | A1 宝宝成长写真板 | ¥59 |\n| 糖果袋 | 100 只满月主题 | ¥49 |\n\n## 💡 展示板是核心\n\n**A1 写真展示板**是满月酒的灵魂：\n- 宝宝照片+出生日期+体重+姓名\n- 摆在签到台前\n- **来宾第一眼会驻足看**\n- 定制款 ¥59 印刷精美，自己设计发给商家打印\n\n## 🎈 气球摆法\n\n满月酒气球建议：\n- 入口做「**气球门**」（两根立柱拱形）\n- 主桌后做「**气球墙**」（背景）\n- 100 个刚好够入口+2-3 桌装饰\n\n## 🍬 糖果袋用法\n\n装 8-10 颗糖/坚果/小饼干，**每位来宾离席时一袋**。100 只对应约 100 位来宾。\n\n## 💰 加 ¥200 升级\n\n- 宝宝百天胎毛笔定制（纪念品）¥300\n- 摄影跟拍（记录仪式）¥500-1000\n- 满月蛋糕定制 ¥300",
    ["满月宴桌旗套装双色10件+月销1.8万，桌面布置即买即用", "满月主题气球100个+月销1.2万，入口气球门+主桌背景", "A1宝宝成长展示板定制+月销3.5万，来宾驻足看布置灵魂", "满月糖果袋100只+月销4.5万，来宾离席伴手礼装糖果"]
))

# 6. matching
T.append(make_traj(
    "sft_match_068", "matching_purchase", "搭配购物",
    "极简主义清零整理术",
    "家里太乱想断舍离，配衣物整理袋+杂物箱+标签机+清洁套装",
    {"query": "断舍离整理收纳套装 衣物+杂物+标签", "filters": {"style": "minimalist_declutter"}},
    [
        {"product_id": "mock_decl_1", "title": "真空压缩袋 12张+电动抽气泵 整理套", "price": 159, "is_platform_self": True, "rating": 4.9, "key_specs": "12张+电动泵/被子衣物压缩/月销5万", "sales": "月销5万"},
        {"product_id": "mock_decl_2", "title": "可折叠储物箱 8个套装 布艺带盖", "price": 169, "is_platform_self": True, "rating": 4.9, "key_specs": "8个布艺箱/折叠带盖/标注物品/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "mock_decl_3", "title": "标签机 热敏打印 手持迷你", "price": 129, "is_platform_self": True, "rating": 4.9, "key_specs": "热敏/手持/打标签/整理神器/月销1.8万", "sales": "月销1.8万"},
        {"product_id": "mock_decl_4", "title": "衣架统一款 防滑 30个装 浅灰", "price": 79, "is_platform_self": True, "rating": 4.9, "key_specs": "防滑/统一颜色/30个/视觉整洁/月销3万", "sales": "月销3万"}
    ],
    "断舍离整理 4 件套 ¥536，**系统整理不反弹**：\n\n## 🗂️ 完整方案\n\n| 工具 | 商品 | 价格 |\n|---|---|---|\n| 压缩袋 | 12 张+电动泵 | ¥159 |\n| 储物箱 | 布艺 8 个套装 | ¥169 |\n| 标签机 | 热敏手持迷你 | ¥129 |\n| 衣架 | 统一浅灰 30 个 | ¥79 |\n\n## 💡 断舍离的 3 个步骤\n\n### 步骤 1：清出（压缩袋+储物箱）\n- 把所有东西拿出来摆地上\n- **超过 1 年没用的** → 扔/捐\n- 季节性物品 → 压缩袋+储物箱收起\n\n### 步骤 2：归位（标签机）\n- 每个储物箱贴标签\n- **标签是防止反弹的关键**——知道东西在哪，就不会乱放\n- 热敏标签机打出来**比手写好看且持久**\n\n### 步骤 3：统一（衣架）\n- 换成统一颜色衣架\n- **视觉整洁感直接翻倍**\n- 不同形状/颜色的衣架是视觉混乱的根源\n\n## 💡 断舍离的心理技巧\n\n问自己**3 个问题**：\n1. 最近 1 年用过吗？\n2. 将来 1 年会用吗？\n3. 如果再买，会买吗？\n\n三个都「不」→ 果断扔。",
    ["真空压缩袋12张+电动泵+月销5万，被子衣物压缩70%季节整理", "布艺储物箱8个带盖+月销2.5万，杂物分类归位断舍离后不反弹", "热敏标签机手持迷你+月销1.8万，每箱贴标签防止找不到东西乱放", "防滑衣架统一浅灰30个+月销3万，衣柜视觉整洁翻倍"]
))

# 7. bundle
T.append(make_traj(
    "sft_bundle_065", "bundle_purchase", "组合购物",
    "4000 元书法爱好者入门",
    "想学书法，4000 预算配齐毛笔+纸+墨+砚+临帖",
    {"query": "书法入门装备 毛笔+宣纸+墨汁+砚台+字帖", "max_price": 4500},
    [
        {"product_id": "mock_calligraphy_1", "title": "湖笔 善琏湖笔 入门套装 10支 大中小", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "浙江湖笔/大中小10支/楷隶行书全覆盖", "sales": "月销1200"},
        {"product_id": "mock_calligraphy_2", "title": "墨浓堂 宣纸 生宣 100张 四尺半生熟", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "安徽宣纸/四尺/生宣100张/书法标准", "sales": "月销3500"},
        {"product_id": "mock_calligraphy_3", "title": "一得阁 墨汁 500ml 碳素 浓厚款", "price": 49, "is_platform_self": True, "rating": 4.9, "key_specs": "一得阁经典/500ml/碳素黑/书法标配", "sales": "月销8万"},
        {"product_id": "mock_calligraphy_4", "title": "端砚 长方形 仿古 初学款 20cm", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "仿古端砚/20cm长/研墨用/初学适合", "sales": "月销1500"},
        {"product_id": "mock_calligraphy_5", "title": "欧阳询 九成宫 楷书字帖 翻印精品", "price": 39, "is_platform_self": True, "rating": 4.9, "key_specs": "欧阳询楷书/高清翻印/楷书入门标准帖", "sales": "月销2.5万"}
    ],
    "书法入门 5 件套 ¥1085，余 ¥2915：\n\n## 🖌️ 完整方案\n\n| 器材 | 商品 | 价格 |\n|---|---|---|\n| 毛笔 | 湖笔入门 10 支 | ¥399 |\n| 宣纸 | 安徽生宣 100 张 | ¥299 |\n| 墨汁 | 一得阁 500ml | ¥49 |\n| 砚台 | 仿古端砚 20cm | ¥299 |\n| 字帖 | 欧阳询九成宫 | ¥39 |\n\n## 💡 为什么选这些器材\n\n### 湖笔（浙江）是书法笔标准\n浙江湖州是中国毛笔之乡，**「湖笔」是优质毛笔的代名词**。10 支套装覆盖大楷/中楷/小楷/行书/草书全场景。\n\n### 宣纸选生宣\n生宣吸水性强，**写出来有墨晕效果**，是正统书法纸张。练习用生宣，精品书法作品才换熟宣。\n\n### 一得阁是书法圈的默认标准\n月销 8 万件，**书法老师人手一瓶**，碳素黑不脱色，墨迹持久。\n\n### 欧阳询楷书是入门首选\n书法界共识：**楷书是基础，从欧体开始**最标准。九成宫是欧阳询最著名的作品，无数书法家启蒙帖。\n\n## 💰 余 ¥2915 用于\n\n- **书法课学费**（线下/线上 ¥500-1500 入门）\n- 书法毡/文房用品 ¥200\n- 《书法入门》教材 ¥50\n- 作品装裱（练出作品后）¥300\n\n## 💡 书法练习 SOP\n\n1. **每天 30-60 分钟**（贵在坚持不在长）\n2. 先临帖（照着九成宫写）\n3. **3 个月后能背临**（不看帖写）\n4. 再学行书/草书",
    ["湖笔入门10支大中小楷隶行+月销1200，浙江湖州标准书法笔", "安徽生宣100张四尺+月销3500，书法正统纸张墨晕效果", "一得阁碳素墨汁500ml+月销8万，书法圈默认标准老师人手一瓶", "仿古端砚20cm+月销1500，研墨功夫也是书法仪式感", "欧阳询九成宫楷书字帖+月销2.5万，书法入门楷书标准帖"]
))

# 8. bundle
T.append(make_traj(
    "sft_bundle_066", "bundle_purchase", "组合购物",
    "5000 元家庭储粮应急备战套装",
    "看新闻想备点应急物资，5000 预算粮食水食品",
    {"query": "家庭应急物资储备 食品+水+能源", "max_price": 5500},
    [
        {"product_id": "mock_emergency_food_1", "title": "卫岗 纯牛奶 250ml×48 长期储存款 6个月", "price": 189, "is_platform_self": True, "rating": 4.9, "key_specs": "48盒/6个月保质/常温储存/蛋白补充", "sales": "月销5万"},
        {"product_id": "mock_emergency_food_2", "title": "稳健 自热米饭 整箱 20份 90天", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "20份/90天/不需要加热/即食", "sales": "月销1.5万"},
        {"product_id": "mock_emergency_food_3", "title": "应急饮用水 1.5L×24 五年保质", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "1.5L×24/5年保质/断水应急", "sales": "月销2.5万"},
        {"product_id": "mock_emergency_food_4", "title": "压缩饼干 整箱 720g×6包 7年保质", "price": 149, "is_platform_self": True, "rating": 4.8, "key_specs": "6包/7年保质/高热量/逃生携带", "sales": "月销3.5万"},
        {"product_id": "mock_emergency_food_5", "title": "太阳能手摇发电收音机 LED手电筒 多功能", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "太阳能+手摇/收音机+手电+充电宝/断电应急", "sales": "月销2.2万"}
    ],
    "家庭应急物资 5 件套 ¥1035，**3 口之家 30 天基础储备**：\n\n## 🆘 完整方案\n\n| 物资 | 商品 | 价格 | 储量 |\n|---|---|---|---|\n| 牛奶 | 卫岗 48 盒 6 月保质 | ¥189 | 蛋白来源 |\n| 自热米饭 | 20 份 90 天 | ¥299 | 主食 |\n| 应急水 | 1.5L×24 5 年保质 | ¥199 | 36L 饮水 |\n| 压缩饼干 | 6 包 7 年保质 | ¥149 | 高热量备用 |\n| 应急收音机 | 太阳能+手摇 | ¥199 | 断电信息获取 |\n\n## 💡 应急储备的科学逻辑\n\n**美国 FEMA 建议家庭备齐 2 周物资**，中国应急标准参考：\n- **饮水**：每人每天 2L × 3 人 × 7 天 = 42L（36L 基本够）\n- **食物**：每人每天 2000 卡 × 3 人 × 7 天\n- 自热米饭+压缩饼干可以维持 7-14 天\n\n## ⚠️ 应急储备注意\n\n1. **不要买「专业战备」昂贵套装**——日常食品轮换更实用\n2. **轮换法**：买完的当月，下次先吃旧的，补充新的\n3. **存放位置**：阴凉干燥，避开窗户（阳光加速过期）\n4. **记录保质期**：贴个标签注明最早过期日期\n\n## 💰 余 ¥3965 加\n\n**优先级顺序**：\n1. AED 除颤仪 ¥1399\n2. 急救包 ¥299\n3. 手机移动电源 ¥200\n4. 家庭药品箱 ¥300\n5. 多功能瑞士军刀 ¥100",
    ["卫岗纯牛奶48盒+6个月保质+月销5万，蛋白补充常温储存", "稳健自热米饭20份+90天保质+月销1.5万，不需加热主食应急", "应急饮用水1.5L×24+五年保质+月销2.5万，断水饮水基础储备", "压缩饼干720g×6包+7年保质+月销3.5万，高热量逃生携带", "太阳能手摇收音机+手电+充电+月销2.2万，断电信息获取救命"]
))

# 9. place_order
T.append(make_traj(
    "sft_order_035", "place_order", "购物下单",
    "消费金融分期+提前还款",
    "之前用白条买了台电脑分 12 期，现在有钱了想提前还清",
    {"order_id": "[TRACKING_ID]-BAITIAO-2284", "action": "early_payoff", "product": "笔记本电脑"},
    [
        {"product_id": "mock_baitiao_payoff", "title": "分期服务 提前还款 — 订单 [TRACKING_ID]-BAITIAO-2284", "price": 0, "is_platform_self": True, "rating": 5.0, "key_specs": "已查询剩余账单/可提前还款/无违约金/具体操作步骤", "sales": "—"}
    ],
    "好主意！提前还款可以省下后续利息，下面是操作步骤：\n\n## 💰 提前还款流程\n\n### 步骤 1：查询剩余账单\n1. 购物 App → **「我的」→「分期服务」**\n2. 找到该分期订单\n3. 查看「**剩余待还金额**」\n\n### 步骤 2：申请提前还款\n1. 进入白条账单 → 选择该笔分期\n2. 点「**提前还款**」\n3. 系统显示：本金 + 已产生利息\n4. 确认金额 → 支付\n\n### 步骤 3：确认还清\n\n还款后 **24 小时内**白条账户更新，该笔分期状态变为「已结清」。\n\n## 💡 提前还款省多少\n\n按 ¥6000 的电脑分 12 期，月利率约 0.5%（每月 ¥30）：\n\n| 剩余月数 | 可省利息 |\n|---|---|\n| 还剩 6 期 | 约 ¥180 |\n| 还剩 9 期 | 约 ¥270 |\n| 还剩 12 期（刚开始）| 约 ¥360 |\n\n**有闲钱就提前还，每省一分是一分**。\n\n## ⚠️ 注意事项\n\n1. **提前还款无违约金**（分期服务正常分期）\n2. 还款后**额度立刻恢复**（可再次使用白条）\n3. 如果是「白条免息活动」期间的分期，**提前还款不会返还免息优惠**（你本来就是 0 利率）\n4. **账单日**前还款影响当月账单，账单日后还款下月出账\n\n## 💡 理财建议\n\n如果你的闲钱放在**余额宝/货币基金（年化 2%+）**，而白条利率是 **年化 6%**：\n- 提前还白条 = 无风险 6% 回报\n- **高于所有低风险理财产品**\n- 所以有白条分期+有闲钱，**一定提前还**。",
    ["分期服务提前还款+无违约金+额度立刻恢复，有闲钱省利息无风险最优先"],
    tool_name="OrderQuerySkill"
))

# 10. repurchase
T.append(make_traj(
    "sft_repurchase_033", "repurchase", "复购召回",
    "复购彩妆+色号升级建议",
    "再买之前那支口红，不过想换个夏天更日常的色号",
    {"category_keyword": "口红", "time_range": "last_5_months", "suggest_seasonal_color": True},
    [
        {"product_id": "mock_lipstick_old", "title": "MAC 子弹头 306 玫红 (4月前购买)", "price": 179, "is_platform_self": True, "rating": 4.9, "key_specs": "你4月前购买/MAC 306玫红色/适合秋冬", "sales": "月销2.5万"},
        {"product_id": "mock_lipstick_summer1", "title": "MAC 子弹头 518 珊瑚粉 夏日款", "price": 179, "is_platform_self": True, "rating": 4.9, "key_specs": "珊瑚粉/夏天最日常/显白不出戏/月销4.5万", "sales": "月销4.5万"},
        {"product_id": "mock_lipstick_summer2", "title": "MAC 子弹头 578 裸橘色 夏天热门", "price": 179, "is_platform_self": True, "rating": 4.8, "key_specs": "裸橘色/夏日感强/混血妆必备/月销2.8万", "sales": "月销2.8万"}
    ],
    "你 4 个月前买的是 **MAC 306 玫红色**。玫红适合秋冬，夏天确实偏浓。推荐换色：\n\n## 🌸 夏日口红色号指南\n\n### 为什么秋冬色号夏天不适合\n- 玫红/深红：**夏天显浓妆**，日常偏老气\n- 夏天需要：**轻薄感+水润感+清爽色系**\n\n## 🛒 夏日推荐换色\n\n### MAC 518 珊瑚粉（¥179）⭐ 夏日首选\n- **珊瑚粉 = 夏天最日常**\n- 黄皮/白皮都显白\n- 不挑场合：上班/约会/逛街全能用\n- **月销 4.5 万件**，夏天口红销冠\n\n### MAC 578 裸橘色（¥179）时尚感强\n- 裸橘色是今年夏季「混血妆」核心\n- 配古铜肤色超好看\n- 适合：喜欢精致感/想要不同风格\n\n## 💊 色号选购表（按肤色）\n\n| 肤色 | 推荐夏日色 |\n|---|---|\n| 黄皮/暖肤 | **珊瑚粉/裸橘** |\n| 白皮/冷肤 | 玫粉/西柚红 |\n| 小麦肤色 | 砖红/赤褐 |\n\n## 🎯 建议\n\n**MAC 318 珊瑚粉 ¥179** 直接复购换色——同品牌同价格，夏天日常比 306 强 100%。\n\n你是什么肤色？告诉我，我可以给更精准的色号建议。",
    ["MAC 306玫红你4月前购买+秋冬色号夏天偏浓，同品牌换色最稳", "MAC 518珊瑚粉夏日日常+显白+月销4.5万，夏天口红销冠色", "MAC 578裸橘色混血妆+月销2.8万，夏日时尚感强不同风格"],
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
