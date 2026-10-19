# -*- coding: utf-8 -*-
"""
Step 6: 造 5 条组合购物 (bundle_purchase) 正样本
训练目标：预算拆分 + 多次工具调用 + PythonCalculator 算账 + 多方案对比
与搭配购物的区别：核心是【价格分配】而非【风格匹配】
"""
import json
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "trajectories_v2_renamed.jsonl"

T = [
    # ── 86. 5000元客厅音响系统 ──
    {
        "trajectory_id": "sft_bundle_001",
        "scenario_type": "bundle_purchase",
        "category": "组合购物",
        "quality_label": "good",
        "training_focus": "5000预算拆分到3个品类（音箱/功放/线材），多次工具调用+算账",
        "user_query": "我有5000块，想给客厅配一套音响系统",
        "thinking": "客厅音响系统=音箱+功放(可选)+线材。5000预算分配：音箱70%(3500)+功放25%(1250)+线材5%(250)。或一体式(soundbar 5000)。两套方案对比。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "客厅书架音箱 hifi", "min_price": 2500, "max_price": 4000, "is_platform_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_001a", "title": "JBL Stage A170 落地式音箱 一对", "price": 3499.0, "is_platform_self": True, "rating": 4.8, "key_specs": "落地式/双6.5寸低音/适合15-25㎡客厅", "sales": "月销680"},
                        {"product_id": "mock_bundle_001b", "title": "惠威 D3.2HT 5.1家庭影院主箱+环绕(套装)", "price": 3899.0, "is_platform_self": True, "rating": 4.7, "key_specs": "5.1声道套装/含主箱+中置+环绕/无功放需另配", "sales": "月销420"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "功放 蓝牙HiFi 客厅", "min_price": 800, "max_price": 1500},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_001c", "title": "天逸 AD-86D 高保真合并功放", "price": 1180.0, "is_platform_self": True, "rating": 4.8, "key_specs": "2×120W/蓝牙5.0/4-8Ω通用/适合JBL Stage", "sales": "月销380"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "Soundbar 一体回音壁 5.1", "min_price": 4000, "max_price": 5500},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_001d", "title": "Sony HT-A5000 7.1.2 Soundbar 一体回音壁", "price": 4999.0, "is_platform_self": True, "rating": 4.9, "key_specs": "杜比全景声/无需功放/支持环绕模拟/壁挂", "sales": "月销850"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 4,
                "step_type": "tool_call",
                "tool_name": "PythonCalculator",
                "tool_input": {"code": "a = 3499 + 1180 + 200  # JBL+功放+线\nb = 4999  # 一体Soundbar\nprint(f'方案A 分体派: JBL落地{3499}+天逸功放{1180}+线材{200} = {a}元, 余{5000-a}')\nprint(f'方案B 一体派: Sony HT-A5000 = {b}元, 余{5000-b}')\nprint(f'差价: {abs(a-b)}元')"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [{"product_id": "calc_b1", "title": "预算分配", "price": 0.0, "is_platform_self": False, "rating": 5.0, "key_specs": "方案A:4879元(余121)/方案B:4999元(余1)/差120", "sales": "—"}]
                },
                "error_type": None
            },
            {
                "step_id": 5,
                "step_type": "final_response",
                "content": "5000 预算客厅音响，**核心是选「分体派」还是「一体派」**。两套方案算给你看：\n\n## 🎵 方案 A：分体派（音质优先）¥4879\n\n| 配件 | 商品 | 价格 |\n|---|---|---|\n| 音箱 | **JBL Stage A170 落地式（一对）** | ¥3499 |\n| 功放 | **天逸 AD-86D 合并功放** | ¥1180 |\n| 线材 | 发烧友音箱线+RCA信号线 | ¥200 |\n| **合计** | | **¥4879**（余 121）|\n\n**优点**：\n- **音质天花板**——同价位分体系统比一体 Soundbar 高 1-2 个档次\n- 后期可单独升级功放/音箱，玩性高\n- JBL Stage A170 是 4000 内落地音箱评分最高的\n\n**缺点**：\n- 占地大（落地音箱+功放）\n- 接线复杂（音箱线/电源线/信号线一堆）\n- 需要一定调试经验\n\n## 🎵 方案 B：一体派（颜值+省心）¥4999\n\n**Sony HT-A5000 7.1.2 Soundbar ¥4999**\n\n**优点**：\n- **无需功放**——通电即用，连电视一条 HDMI 线\n- 颜值高（条形+壁挂），不破坏装修\n- **杜比全景声 7.1.2 声道**模拟，看电影体验秒杀传统 5.1\n- 月销 850 件是 5000 价位 Soundbar 销冠\n\n**缺点**：\n- 纯听音乐音质不如分体 JBL（适合电影>音乐）\n- 不可升级\n\n## 💡 怎么选\n\n| 你的情况 | 推荐 |\n|---|---|\n| 客厅 15㎡+ / 主要听音乐 / 想发烧 | **方案 A 分体**（音质天花板）|\n| 客厅 10-15㎡ / 主要看电影 / 想省心 | **方案 B Sony Soundbar**（颜值+杜比全景声）|\n| 不确定 / 第一次配音响 | **方案 B**（试错成本低）|\n\n## 💎 重要提醒\n\n- 分体派**必须配功放**（音箱不能直接接电视），千万别买了 JBL 落地却没买功放\n- 客厅 > 30㎡ 建议直接加预算到 8000+ 上 5.1 真分体（家庭影院），5000 在大客厅就是凑合\n- Soundbar 一定要看电视的 **HDMI eARC** 接口（不是普通 HDMI，否则杜比全景声出不来）",
                "product_cards": [
                    {"card_id": "mock_bundle_001a", "display_price": 3499.0, "reason": "JBL Stage A170落地音箱4000内评分最高，分体派音质天花板"},
                    {"card_id": "mock_bundle_001c", "display_price": 1180.0, "reason": "天逸AD-86D 2×120W蓝牙合并功放，分体派必备"},
                    {"card_id": "mock_bundle_001d", "display_price": 4999.0, "reason": "Sony HT-A5000 杜比全景声7.1.2 Soundbar，一体派颜值+省心首选"}
                ]
            }
        ],
        "final_response": "5000 预算客厅音响，**核心是选「分体派」还是「一体派」**。两套方案算给你看：\n\n## 🎵 方案 A：分体派（音质优先）¥4879\n\n| 配件 | 商品 | 价格 |\n|---|---|---|\n| 音箱 | **JBL Stage A170 落地式（一对）** | ¥3499 |\n| 功放 | **天逸 AD-86D 合并功放** | ¥1180 |\n| 线材 | 发烧友音箱线+RCA信号线 | ¥200 |\n| **合计** | | **¥4879**（余 121）|\n\n**优点**：\n- **音质天花板**——同价位分体系统比一体 Soundbar 高 1-2 个档次\n- 后期可单独升级功放/音箱，玩性高\n- JBL Stage A170 是 4000 内落地音箱评分最高的\n\n**缺点**：\n- 占地大（落地音箱+功放）\n- 接线复杂（音箱线/电源线/信号线一堆）\n- 需要一定调试经验\n\n## 🎵 方案 B：一体派（颜值+省心）¥4999\n\n**Sony HT-A5000 7.1.2 Soundbar ¥4999**\n\n**优点**：\n- **无需功放**——通电即用，连电视一条 HDMI 线\n- 颜值高（条形+壁挂），不破坏装修\n- **杜比全景声 7.1.2 声道**模拟，看电影体验秒杀传统 5.1\n- 月销 850 件是 5000 价位 Soundbar 销冠\n\n**缺点**：\n- 纯听音乐音质不如分体 JBL（适合电影>音乐）\n- 不可升级\n\n## 💡 怎么选\n\n| 你的情况 | 推荐 |\n|---|---|\n| 客厅 15㎡+ / 主要听音乐 / 想发烧 | **方案 A 分体**（音质天花板）|\n| 客厅 10-15㎡ / 主要看电影 / 想省心 | **方案 B Sony Soundbar**（颜值+杜比全景声）|\n| 不确定 / 第一次配音响 | **方案 B**（试错成本低）|\n\n## 💎 重要提醒\n\n- 分体派**必须配功放**（音箱不能直接接电视），千万别买了 JBL 落地却没买功放\n- 客厅 > 30㎡ 建议直接加预算到 8000+ 上 5.1 真分体（家庭影院），5000 在大客厅就是凑合\n- Soundbar 一定要看电视的 **HDMI eARC** 接口（不是普通 HDMI，否则杜比全景声出不来）",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ── 87. 2000元厨房刀具锅具组合 ──
    {
        "trajectory_id": "sft_bundle_002",
        "scenario_type": "bundle_purchase",
        "category": "组合购物",
        "quality_label": "good",
        "training_focus": "2000预算厨房刀具+锅具组合，按使用频率分配预算",
        "user_query": "我有2000元，想给家里换一套厨房刀具和锅具",
        "thinking": "2000预算厨具组合。按使用频率：炒锅(每天用)45% > 刀具(每天用)30% > 汤锅(2-3次/周)15% > 平底锅(1-2次/周)10%。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "炒锅 不粘锅 麦饭石/钛合金", "max_price": 900, "is_platform_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_002a", "title": "苏泊尔 钛系列不粘炒锅 32cm 适合明火/电磁", "price": 459.0, "is_platform_self": True, "rating": 4.8, "key_specs": "钛合金不粘/32cm/明火电磁通用/送锅盖+硅胶铲", "sales": "月销3.5万"},
                        {"product_id": "mock_bundle_002b", "title": "炊大皇 麦饭石不粘炒锅 30cm", "price": 199.0, "is_platform_self": True, "rating": 4.7, "key_specs": "麦饭石涂层/30cm/性价比款", "sales": "月销5万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "厨房刀具套装 不锈钢", "min_price": 400, "max_price": 800},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_002c", "title": "双立人 Now S 5件套 主厨+水果+剪+磨刀器+刀架", "price": 699.0, "is_platform_self": True, "rating": 4.9, "key_specs": "德国双立人/5件套/含主厨刀+水果刀+剪+磨刀器+刀架", "sales": "月销1500"},
                        {"product_id": "mock_bundle_002d", "title": "十八子作 厨房刀具7件套 国产经典款", "price": 459.0, "is_platform_self": True, "rating": 4.7, "key_specs": "国产经典/7件套/含全套切片/砍骨刀", "sales": "月销1.2万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "汤锅 不锈钢 304", "max_price": 400, "is_platform_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_002e", "title": "WMF 福腾宝 24cm 304不锈钢汤锅", "price": 369.0, "is_platform_self": True, "rating": 4.8, "key_specs": "德国WMF/304不锈钢/24cm/明火电磁通用", "sales": "月销850"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 4,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "平底煎锅 不粘 24cm", "max_price": 300},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_002f", "title": "Tefal 特福 24cm 钛系列不粘煎锅 红点款", "price": 269.0, "is_platform_self": True, "rating": 4.9, "key_specs": "法国Tefal/钛+陶瓷不粘/24cm/红点温控", "sales": "月销2200"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 5,
                "step_type": "tool_call",
                "tool_name": "PythonCalculator",
                "tool_input": {"code": "a = 459 + 699 + 369 + 269   # 升级派\nb = 459 + 459 + 369 + 269   # 实用派\nc = 199 + 459 + 369 + 269   # 性价比派\nprint(f'方案A 升级派(苏泊尔钛+双立人+WMF+Tefal): {a}, 余{2000-a}')\nprint(f'方案B 实用派(苏泊尔钛+十八子作+WMF+Tefal): {b}, 余{2000-b}')\nprint(f'方案C 性价比派(炊大皇+十八子作+WMF+Tefal): {c}, 余{2000-c}')"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [{"product_id": "calc_b2", "title": "预算分配", "price": 0.0, "is_platform_self": False, "rating": 5.0, "key_specs": "A升级派1796(余204)/B实用派1556(余444)/C性价比1296(余704)", "sales": "—"}]
                },
                "error_type": None
            },
            {
                "step_id": 6,
                "step_type": "final_response",
                "content": "2000 预算厨具组合，按 **使用频率分配预算** 最合理：炒锅(每天)≥30% / 刀具(每天)≥25% / 汤锅(每周3次)15% / 煎锅(每周1-2次)10%。\n\n三套方案给你选：\n\n## 🍳 方案 A：升级派（推荐）¥1796\n\n| 用品 | 商品 | 价格 |\n|---|---|---|\n| 炒锅 | 苏泊尔钛系列 32cm 不粘锅 | ¥459 |\n| 刀具 | **双立人 Now S 5件套**（含磨刀器+刀架）| ¥699 |\n| 汤锅 | WMF 福腾宝 24cm 304 不锈钢 | ¥369 |\n| 煎锅 | Tefal 特福 24cm 钛+陶瓷不粘 | ¥269 |\n| **合计** | | **¥1796**（余 204）|\n\n**优势**：\n- 刀具用 10 年起步（双立人锋利度衰减最慢）\n- 4 件全部品牌货，颜值统一\n- 余 ¥204 可以加 1 把日式三德刀或一套硅胶铲\n\n## 🍳 方案 B：实用派 ¥1556\n\n炒锅+汤锅+煎锅同方案 A，刀具换成 **十八子作 7 件套 ¥459**（更多刀型，国产顶尖）。**省 ¥240**，但刀具锋利度衰减比双立人快。\n\n## 🍳 方案 C：性价比派 ¥1296\n\n炒锅换成 **炊大皇麦饭石 ¥199**（涂层易磨损，1-2 年要换），其余同方案 B。**省 ¥500** 但炒锅 2 年内可能要再买一个。\n\n## 💡 我的建议\n\n**直接选方案 A（¥1796）**，理由：\n1. **炒锅和刀具是每天都用**的——这两样必须买好的，否则用 1 年就嫌弃想换\n2. 苏泊尔钛系列是 ¥500 内炒锅 NO.1（月销 3.5 万），不粘性能比麦饭石强 2-3 倍\n3. 双立人刀具的真正价值在「**10 年不卷刃**」，平均 ¥70/年完全划算\n4. 余 ¥204 可以买点小件（硅胶铲/木砧板/收纳架），不浪费\n\n## ⚠️ 避免组合误区\n\n- ❌ 不要买**全套日系厨具**——刀具用日式（轻薄锋利）但炒锅用厚重铁锅是错配\n- ❌ 不要买**多功能合一锅**（炒锅+煎锅+汤锅一体），样样通样样松\n- ❌ 不要买**全套铸铁锅**——重 3-5kg 长期用伤手腕\n\n选 4 件专用具是最优解。",
                "product_cards": [
                    {"card_id": "mock_bundle_002a", "display_price": 459.0, "reason": "苏泊尔钛系列32cm不粘炒锅+月销3.5万，每日炒菜必备核心"},
                    {"card_id": "mock_bundle_002c", "display_price": 699.0, "reason": "双立人Now S 5件套含磨刀器+刀架，10年不卷刃日常用刀党"},
                    {"card_id": "mock_bundle_002e", "display_price": 369.0, "reason": "WMF 24cm 304不锈钢汤锅，德国品质明火电磁通用"},
                    {"card_id": "mock_bundle_002f", "display_price": 269.0, "reason": "Tefal特福24cm红点钛系列煎锅，温控显示煎牛排首选"}
                ]
            }
        ],
        "final_response": "2000 预算厨具组合，按 **使用频率分配预算** 最合理：炒锅(每天)≥30% / 刀具(每天)≥25% / 汤锅(每周3次)15% / 煎锅(每周1-2次)10%。\n\n三套方案给你选：\n\n## 🍳 方案 A：升级派（推荐）¥1796\n\n| 用品 | 商品 | 价格 |\n|---|---|---|\n| 炒锅 | 苏泊尔钛系列 32cm 不粘锅 | ¥459 |\n| 刀具 | **双立人 Now S 5件套**（含磨刀器+刀架）| ¥699 |\n| 汤锅 | WMF 福腾宝 24cm 304 不锈钢 | ¥369 |\n| 煎锅 | Tefal 特福 24cm 钛+陶瓷不粘 | ¥269 |\n| **合计** | | **¥1796**（余 204）|\n\n**优势**：\n- 刀具用 10 年起步（双立人锋利度衰减最慢）\n- 4 件全部品牌货，颜值统一\n- 余 ¥204 可以加 1 把日式三德刀或一套硅胶铲\n\n## 🍳 方案 B：实用派 ¥1556\n\n炒锅+汤锅+煎锅同方案 A，刀具换成 **十八子作 7 件套 ¥459**（更多刀型，国产顶尖）。**省 ¥240**，但刀具锋利度衰减比双立人快。\n\n## 🍳 方案 C：性价比派 ¥1296\n\n炒锅换成 **炊大皇麦饭石 ¥199**（涂层易磨损，1-2 年要换），其余同方案 B。**省 ¥500** 但炒锅 2 年内可能要再买一个。\n\n## 💡 我的建议\n\n**直接选方案 A（¥1796）**，理由：\n1. **炒锅和刀具是每天都用**的——这两样必须买好的，否则用 1 年就嫌弃想换\n2. 苏泊尔钛系列是 ¥500 内炒锅 NO.1（月销 3.5 万），不粘性能比麦饭石强 2-3 倍\n3. 双立人刀具的真正价值在「**10 年不卷刃**」，平均 ¥70/年完全划算\n4. 余 ¥204 可以买点小件（硅胶铲/木砧板/收纳架），不浪费\n\n## ⚠️ 避免组合误区\n\n- ❌ 不要买**全套日系厨具**——刀具用日式（轻薄锋利）但炒锅用厚重铁锅是错配\n- ❌ 不要买**多功能合一锅**（炒锅+煎锅+汤锅一体），样样通样样松\n- ❌ 不要买**全套铸铁锅**——重 3-5kg 长期用伤手腕\n\n选 4 件专用具是最优解。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ── 88. 1500元健身入门套装 ──
    {
        "trajectory_id": "sft_bundle_003",
        "scenario_type": "bundle_purchase",
        "category": "组合购物",
        "quality_label": "good",
        "training_focus": "1500预算覆盖4-5件健身入门装备，按训练频率分配",
        "user_query": "我想开始健身，家里空间不大，预算1500想配一套入门装备",
        "thinking": "1500预算居家健身入门。哑铃50% > 瑜伽垫15% > 弹力带10% > 跳绳5% > 其他配件20%余量。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "可调节哑铃 家用 占地小", "min_price": 500, "max_price": 900},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_003a", "title": "海德 HEAD 可调节哑铃 5-25kg 一对 静音胶包", "price": 759.0, "is_platform_self": True, "rating": 4.8, "key_specs": "可调5-25kg/占地0.3㎡/胶包静音/送收纳架", "sales": "月销2.1万"},
                        {"product_id": "mock_bundle_003b", "title": "李宁 哑铃 5-15kg 一对 入门款", "price": 429.0, "is_platform_self": True, "rating": 4.7, "key_specs": "可调5-15kg/适合入门/不带收纳架", "sales": "月销1.5万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "瑜伽垫 加厚 10mm", "max_price": 200},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_003c", "title": "迪卡侬 NBR 瑜伽垫 加厚 10mm 183×61cm", "price": 89.0, "is_platform_self": True, "rating": 4.9, "key_specs": "10mm加厚/NBR防滑/183×61cm/送绑带背包", "sales": "月销5.8万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "弹力带 训练 多档", "max_price": 150},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_003d", "title": "Keep 弹力带 5档训练套装 10-35磅", "price": 79.0, "is_platform_self": True, "rating": 4.7, "key_specs": "5档阻力10-35磅/Keep APP同步课程", "sales": "月销1.5万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 4,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "智能跳绳 计数", "max_price": 80},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_003e", "title": "李宁 智能跳绳 蓝牙计数 计卡路里", "price": 49.0, "is_platform_self": True, "rating": 4.8, "key_specs": "蓝牙计数+卡路里/可换钢丝/送1.4kg负重", "sales": "月销3.2万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 5,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "蛋白粉 健身 入门", "max_price": 350},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_003f", "title": "MyProtein 乳清蛋白粉 1kg 巧克力味 入门款", "price": 269.0, "is_platform_self": True, "rating": 4.8, "key_specs": "英国MyProtein/乳清蛋白80%/1kg约33份", "sales": "月销1.8万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 6,
                "step_type": "tool_call",
                "tool_name": "PythonCalculator",
                "tool_input": {"code": "core = 759 + 89 + 79 + 49  # 核心4件\nfull = core + 269  # 含蛋白粉\nprint(f'核心4件(哑铃+垫+带+跳绳): {core}元, 余{1500-core}')\nprint(f'完整5件(+蛋白粉): {full}元, 余{1500-full}')\nprint(f'仅哑铃占核心: {759/core*100:.0f}%')"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [{"product_id": "calc_b3", "title": "预算分配", "price": 0.0, "is_platform_self": False, "rating": 5.0, "key_specs": "核心4件976元(余524)/完整5件1245元(余255)/哑铃占核心78%", "sales": "—"}]
                },
                "error_type": None
            },
            {
                "step_id": 7,
                "step_type": "final_response",
                "content": "1500 预算居家健身入门，**5 件装备完美覆盖 90% 训练动作**，还能余 ¥255 给你买点衣物。\n\n## 🏋️ 完整方案 ¥1245（推荐）\n\n| 装备 | 商品 | 价格 | 用途 |\n|---|---|---|---|\n| 🥇 哑铃（核心）| **海德可调节哑铃 5-25kg** | ¥759 | 增肌主力（肩推/卧推/划船/二头弯举）|\n| 瑜伽垫 | 迪卡侬 NBR 10mm 加厚 | ¥89 | 核心训练/HIIT/拉伸 |\n| 弹力带 | Keep 5 档训练套装 | ¥79 | 练背/肩/臀，孤立动作 |\n| 跳绳 | 李宁智能跳绳 | ¥49 | 热身+有氧（10min=跑步 20min）|\n| 蛋白粉 | MyProtein 乳清 1kg | ¥269 | 增肌必备（训练后补充）|\n| **合计** | | **¥1245**（余 255）|\n\n## 📊 为什么这样分配预算？\n\n哑铃占了 **60%（¥759）**，因为：\n1. **居家健身 80% 动作靠哑铃**——肩推/卧推/划船/二头/三头/臀桥都能做\n2. **可调节 5-25kg** 覆盖新手到中级所有重量，不用买不同重量的固定哑铃\n3. 海德是占地最小的款（0.3㎡），租房友好\n\n## 💡 余 ¥255 加什么？\n\n按优先级：\n1. **运动衣鞋**（¥150-250）：训练专用速干衣 + 室内训练鞋\n2. **健身镜或健身APP会员**（¥150-300）：能看动作纠正，新手最容易练废\n3. **简易引体向上杆**（¥100-200）：练背的最佳器械\n\n## ⚠️ 避坑\n\n- ❌ 不要买**全套固定重量哑铃**（5kg+10kg+15kg各一对）——占地大+换重量麻烦+总价更贵\n- ❌ 不要买**跑步机/椭圆机**（占地大+噪音扰邻+ 90% 用户 3 个月后吃灰）\n- ❌ 不要买**便宜的杂牌哑铃**（涂层易脱+不静音，凌晨练扰邻）\n\n这套配置能让你**前 6 个月足够练出明显效果**，到时再决定要不要加深蹲架/卧推凳。\n\n## 🎯 如果只买 3 件最精简（¥898）\n\n哑铃 + 瑜伽垫 + 蛋白粉 = ¥759 + ¥89 + ¥269 = **¥1117**（余 383）。如果你想试水后期再加件，这是最最最低门槛。但 80% 新手会半途而废，**先全套买齐反而能逼自己坚持**。",
                "product_cards": [
                    {"card_id": "mock_bundle_003a", "display_price": 759.0, "reason": "海德可调5-25kg哑铃占地0.3㎡静音胶包，居家健身80%动作主力"},
                    {"card_id": "mock_bundle_003c", "display_price": 89.0, "reason": "迪卡侬10mm加厚NBR瑜伽垫月销5.8万，护膝防滑核心训练必备"},
                    {"card_id": "mock_bundle_003d", "display_price": 79.0, "reason": "Keep 5档弹力带+APP同步课程，练背肩臀孤立动作首选"},
                    {"card_id": "mock_bundle_003e", "display_price": 49.0, "reason": "李宁智能跳绳蓝牙计数，10min有氧=跑步20min最高效热身"},
                    {"card_id": "mock_bundle_003f", "display_price": 269.0, "reason": "MyProtein乳清蛋白粉1kg约33份，训练后补充增肌必备"}
                ]
            }
        ],
        "final_response": "1500 预算居家健身入门，**5 件装备完美覆盖 90% 训练动作**，还能余 ¥255 给你买点衣物。\n\n## 🏋️ 完整方案 ¥1245（推荐）\n\n| 装备 | 商品 | 价格 | 用途 |\n|---|---|---|---|\n| 🥇 哑铃（核心）| **海德可调节哑铃 5-25kg** | ¥759 | 增肌主力（肩推/卧推/划船/二头弯举）|\n| 瑜伽垫 | 迪卡侬 NBR 10mm 加厚 | ¥89 | 核心训练/HIIT/拉伸 |\n| 弹力带 | Keep 5 档训练套装 | ¥79 | 练背/肩/臀，孤立动作 |\n| 跳绳 | 李宁智能跳绳 | ¥49 | 热身+有氧（10min=跑步 20min）|\n| 蛋白粉 | MyProtein 乳清 1kg | ¥269 | 增肌必备（训练后补充）|\n| **合计** | | **¥1245**（余 255）|\n\n## 📊 为什么这样分配预算？\n\n哑铃占了 **60%（¥759）**，因为：\n1. **居家健身 80% 动作靠哑铃**——肩推/卧推/划船/二头/三头/臀桥都能做\n2. **可调节 5-25kg** 覆盖新手到中级所有重量，不用买不同重量的固定哑铃\n3. 海德是占地最小的款（0.3㎡），租房友好\n\n## 💡 余 ¥255 加什么？\n\n按优先级：\n1. **运动衣鞋**（¥150-250）：训练专用速干衣 + 室内训练鞋\n2. **健身镜或健身APP会员**（¥150-300）：能看动作纠正，新手最容易练废\n3. **简易引体向上杆**（¥100-200）：练背的最佳器械\n\n## ⚠️ 避坑\n\n- ❌ 不要买**全套固定重量哑铃**（5kg+10kg+15kg各一对）——占地大+换重量麻烦+总价更贵\n- ❌ 不要买**跑步机/椭圆机**（占地大+噪音扰邻+ 90% 用户 3 个月后吃灰）\n- ❌ 不要买**便宜的杂牌哑铃**（涂层易脱+不静音，凌晨练扰邻）\n\n这套配置能让你**前 6 个月足够练出明显效果**，到时再决定要不要加深蹲架/卧推凳。\n\n## 🎯 如果只买 3 件最精简（¥898）\n\n哑铃 + 瑜伽垫 + 蛋白粉 = ¥759 + ¥89 + ¥269 = **¥1117**（余 383）。如果你想试水后期再加件，这是最最最低门槛。但 80% 新手会半途而废，**先全套买齐反而能逼自己坚持**。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ── 89. 3000元桌面办公升级套装 ──
    {
        "trajectory_id": "sft_bundle_004",
        "scenario_type": "bundle_purchase",
        "category": "组合购物",
        "quality_label": "good",
        "training_focus": "3000预算桌面办公套装：显示器+椅子+键鼠+周边",
        "user_query": "想给居家办公升级一下桌面，3000预算配显示器+椅子+键盘鼠标",
        "thinking": "3000居家办公升级。椅子50%(1500)+显示器30%(900)+键鼠15%(450)+台灯/收纳5%(150)。健康优先椅子。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "人体工学椅 办公椅", "min_price": 1200, "max_price": 1800, "is_platform_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_004a", "title": "西昊 Doro C300 人体工学椅 4D扶手", "price": 1499.0, "is_platform_self": True, "rating": 4.9, "key_specs": "4D扶手/腰托/网布透气/可躺/承重150kg", "sales": "月销1.8万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "显示器 27寸 2K IPS 办公", "max_price": 1200, "is_platform_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_004b", "title": "DELL 戴尔 S2722DC 27寸 2K Type-C 90W反向供电", "price": 1099.0, "is_platform_self": True, "rating": 4.8, "key_specs": "27寸2K/IPS广色域/Type-C 90W反向给笔记本供电/USB Hub", "sales": "月销4500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "罗技 MX 键鼠套装", "max_price": 800, "is_platform_self": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_004c", "title": "罗技 MX Master 3S + MX Keys S 键鼠套装", "price": 699.0, "is_platform_self": True, "rating": 4.9, "key_specs": "MX Master 3S+MX Keys S/3设备切换/全键静音/双系统", "sales": "月销3500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 4,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "屏幕挂灯 智能", "max_price": 250},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_004d", "title": "明基 ScreenBar Halo 智能屏幕挂灯", "price": 199.0, "is_platform_self": True, "rating": 4.9, "key_specs": "屏幕挂灯/前后双光源/无线遥控/护眼", "sales": "月销2200"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 5,
                "step_type": "tool_call",
                "tool_name": "PythonCalculator",
                "tool_input": {"code": "core = 1499 + 1099 + 699  # 椅+显+键鼠\nfull = core + 199  # 加挂灯\nprint(f'核心3件: 椅{1499}+显{1099}+键鼠{699} = {core}元, 余{3000-core}')\nprint(f'完整4件(+屏幕挂灯): {full}元, 余{3000-full}')\nprint(f'椅子占比 {1499/full*100:.0f}% / 显示器 {1099/full*100:.0f}% / 键鼠 {699/full*100:.0f}% / 挂灯 {199/full*100:.0f}%')"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [{"product_id": "calc_b4", "title": "预算分配", "price": 0.0, "is_platform_self": False, "rating": 5.0, "key_specs": "核心3件3297超50元/完整4件3496超496元", "sales": "—"}]
                },
                "error_type": None
            },
            {
                "step_id": 6,
                "step_type": "final_response",
                "content": "桌面办公升级是「投资健康+效率」，**3000 内最优配置是 4 件套**——但**超预算 ¥496**，我先给你看正配置，再给压预算方案。\n\n## 💼 标准方案（超预算 ¥496）\n\n| 装备 | 商品 | 价格 | 占比 |\n|---|---|---|---|\n| 🥇 椅子（投资健康）| **西昊 Doro C300 人体工学椅** | ¥1499 | 43% |\n| 显示器 | DELL S2722DC 27寸 2K Type-C | ¥1099 | 31% |\n| 键鼠 | 罗技 MX Master 3S + MX Keys S | ¥699 | 20% |\n| 屏幕挂灯 | 明基 ScreenBar Halo | ¥199 | 6% |\n| **合计** | | **¥3496** | (超 ¥496)|\n\n## 🎯 压预算 ¥3000 方案\n\n**砍掉屏幕挂灯**（最低优先级，后期可加）：\n\n¥1499 + ¥1099 + ¥699 = **¥3297**（还超 ¥297）\n\n再砍：把椅子换成 **西昊 M57**（¥1099，少了 4D 扶手但腰托和透气保留）：\n\n¥1099 + ¥1099 + ¥699 = **¥2897**（余 ¥103）✅\n\n## 💡 我的建议\n\n**直接超预算 ¥496 上 4 件套**——理由：\n1. **椅子是 8 小时坐姿伴侣**，¥1499 比 ¥1099 多的「4D 扶手」直接决定肩颈健康，几年里少看 1 次理疗师就回本\n2. DELL S2722DC 的 **Type-C 90W 反向供电**对笔记本用户是降维打击（一根线连显示器=充电+扩展屏幕+USB Hub）\n3. 罗技 MX 系列**静音键鼠**是开会神器，省得敲键盘吵到家人\n4. 屏幕挂灯长期看是护眼必需，多花 ¥199 值\n\n## 📐 桌面布局建议\n\n```\n         [屏幕挂灯]\n         ┌──────┐\n         │ 27寸  │\n         │  显   │← 摆在桌子中央，正对你\n         │  示   │\n         └──────┘\n   [键盘─────────]\n              [鼠标]\n         [人体工学椅]\n```\n\n## ⚠️ 避坑\n\n- ❌ **不要先省椅子钱**——人体工学椅是 4 件里**唯一直接影响健康的**\n- ❌ **不要买曲面显示器办公用**——文字阅读会有畸变，曲面只适合游戏\n- ❌ **不要买无线充电板这类「桌面玩具」**——3000 预算应该全花在 4 个核心件上\n\n## 🌟 未来升级路径\n\n6 个月后用得舒服，可以加：\n1. 升降桌（¥800-2000）→ 站立办公\n2. 第二台显示器（¥800-1500）→ 双屏\n3. NAS 存储（¥1500+）→ 远程文件",
                "product_cards": [
                    {"card_id": "mock_bundle_004a", "display_price": 1499.0, "reason": "西昊Doro C300 4D扶手+腰托+月销1.8万，8小时办公直接决定肩颈健康"},
                    {"card_id": "mock_bundle_004b", "display_price": 1099.0, "reason": "DELL S2722DC 27寸2K+Type-C 90W反向供电一根线降维打击"},
                    {"card_id": "mock_bundle_004c", "display_price": 699.0, "reason": "罗技MX Master 3S+MX Keys S键鼠套装，3设备切换+全键静音开会神器"},
                    {"card_id": "mock_bundle_004d", "display_price": 199.0, "reason": "明基ScreenBar Halo前后双光源+无线遥控，长期护眼最高优先升级"}
                ]
            }
        ],
        "final_response": "桌面办公升级是「投资健康+效率」，**3000 内最优配置是 4 件套**——但**超预算 ¥496**，我先给你看正配置，再给压预算方案。\n\n## 💼 标准方案（超预算 ¥496）\n\n| 装备 | 商品 | 价格 | 占比 |\n|---|---|---|---|\n| 🥇 椅子（投资健康）| **西昊 Doro C300 人体工学椅** | ¥1499 | 43% |\n| 显示器 | DELL S2722DC 27寸 2K Type-C | ¥1099 | 31% |\n| 键鼠 | 罗技 MX Master 3S + MX Keys S | ¥699 | 20% |\n| 屏幕挂灯 | 明基 ScreenBar Halo | ¥199 | 6% |\n| **合计** | | **¥3496** | (超 ¥496)|\n\n## 🎯 压预算 ¥3000 方案\n\n**砍掉屏幕挂灯**（最低优先级，后期可加）：\n\n¥1499 + ¥1099 + ¥699 = **¥3297**（还超 ¥297）\n\n再砍：把椅子换成 **西昊 M57**（¥1099，少了 4D 扶手但腰托和透气保留）：\n\n¥1099 + ¥1099 + ¥699 = **¥2897**（余 ¥103）✅\n\n## 💡 我的建议\n\n**直接超预算 ¥496 上 4 件套**——理由：\n1. **椅子是 8 小时坐姿伴侣**，¥1499 比 ¥1099 多的「4D 扶手」直接决定肩颈健康，几年里少看 1 次理疗师就回本\n2. DELL S2722DC 的 **Type-C 90W 反向供电**对笔记本用户是降维打击（一根线连显示器=充电+扩展屏幕+USB Hub）\n3. 罗技 MX 系列**静音键鼠**是开会神器，省得敲键盘吵到家人\n4. 屏幕挂灯长期看是护眼必需，多花 ¥199 值\n\n## ⚠️ 避坑\n\n- ❌ **不要先省椅子钱**——人体工学椅是 4 件里**唯一直接影响健康的**\n- ❌ **不要买曲面显示器办公用**——文字阅读会有畸变，曲面只适合游戏\n- ❌ **不要买无线充电板这类「桌面玩具」**——3000 预算应该全花在 4 个核心件上\n\n## 🌟 未来升级路径\n\n6 个月后用得舒服，可以加：\n1. 升降桌（¥800-2000）→ 站立办公\n2. 第二台显示器（¥800-1500）→ 双屏\n3. NAS 存储（¥1500+）→ 远程文件",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # ── 90. 5000元新生儿月子包 ──
    {
        "trajectory_id": "sft_bundle_005",
        "scenario_type": "bundle_purchase",
        "category": "组合购物",
        "quality_label": "good",
        "training_focus": "5000预算多品类母婴组合：奶粉/纸尿裤/衣物/床品/喂养用品",
        "user_query": "宝宝快出生了，5000预算给新生儿配齐第一个月的用品",
        "thinking": "新生儿月子包。核心刚需：奶粉(30%)+纸尿裤(15%)+衣物洗护(20%)+床品(20%)+喂养用品(15%)。所有品类必须够用1个月。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "新生儿奶粉 0-6月 一段", "max_price": 1800, "filters": {"safety_cert": "国标A2"}},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_005a", "title": "飞鹤 星飞帆 一段奶粉 700g×2罐 0-6月", "price": 778.0, "is_platform_self": True, "rating": 4.9, "key_specs": "新国标/A2牛奶蛋白/2罐够吃1个月/月销4.5万", "sales": "月销4.5万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "新生儿纸尿裤 NB码", "max_price": 800},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_005b", "title": "大王 GOO.N 维E NB 144片×2包 新生儿适用", "price": 599.0, "is_platform_self": True, "rating": 4.9, "key_specs": "日本大王/NB码288片/适合0-5kg/新生儿1月用量", "sales": "月销1.5万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "新生儿衣物套装 纯棉 A类", "max_price": 800},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_005c", "title": "全棉时代 新生儿和尚服+连体衣套装 7件 A类", "price": 569.0, "is_platform_self": True, "rating": 4.9, "key_specs": "A类纯棉/3件和尚服+4件连体衣/0-3月", "sales": "月销1.2万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 4,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "婴儿床 实木 含床垫", "max_price": 1200},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_005d", "title": "BABYBJÖRN 折叠婴儿床+椰棕床垫套装", "price": 1099.0, "is_platform_self": True, "rating": 4.8, "key_specs": "实木+椰棕床垫/可折叠/适合0-3岁/防夹手设计", "sales": "月销380"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 5,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "新生儿奶瓶 玻璃 防胀气", "max_price": 600},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_005e", "title": "贝亲 玻璃奶瓶 防胀气 160ml×2 + 240ml×1 套装", "price": 459.0, "is_platform_self": True, "rating": 4.9, "key_specs": "日本贝亲/防胀气/玻璃材质/3只装+0-3月奶嘴", "sales": "月销8500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 6,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "新生儿洗护套装 沐浴露", "max_price": 500},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_bundle_005f", "title": "贝亲 婴儿洗护5件套（沐浴露+洗发+润肤+爽身+棉签）", "price": 359.0, "is_platform_self": True, "rating": 4.8, "key_specs": "5件洗护全套+棉柔巾100抽×6包", "sales": "月销1.1万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 7,
                "step_type": "tool_call",
                "tool_name": "PythonCalculator",
                "tool_input": {"code": "items = {'飞鹤奶粉':778, '大王纸尿裤':599, '全棉衣物':569, '婴儿床':1099, '贝亲奶瓶':459, '洗护套装':359}\ntotal = sum(items.values())\nbudget = 5000\nfor k, v in items.items():\n    print(f'{k:<12} ¥{v}  占比 {v/total*100:.0f}%')\nprint(f'\\n合计: ¥{total}, 余 ¥{budget-total}')\n# 余额可加奶粉提前备1月\nprint(f'余额建议: 加1罐奶粉(¥389) + 备用湿巾(¥100) + 体温计(¥80) = ¥569')"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [{"product_id": "calc_b5", "title": "月子包预算分配", "price": 0.0, "is_platform_self": False, "rating": 5.0, "key_specs": "合计3863元/余1137元/奶粉20%纸尿裤16%衣物15%床29%奶瓶12%洗护9%", "sales": "—"}]
                },
                "error_type": None
            },
            {
                "step_id": 8,
                "step_type": "final_response",
                "content": "5000 预算新生儿月子包，**6 大件先配齐，第 1 个月够用，余 ¥1137 留备用**：\n\n## 👶 月子包完整配置 ¥3863\n\n| 用品 | 商品 | 价格 | 用量 |\n|---|---|---|---|\n| 婴儿床 | BABYBJÖRN 实木+椰棕床垫 | ¥1099 | 用 3 年 |\n| 奶粉 | 飞鹤星飞帆一段 700g×2 罐 | ¥778 | 1 个月 |\n| 纸尿裤 | 大王 GOO.N NB 288 片 | ¥599 | 1 个月 |\n| 衣物 | 全棉时代和尚服+连体衣 7 件 | ¥569 | 0-3 月 |\n| 奶瓶 | 贝亲玻璃防胀气 3 只装 | ¥459 | 用 6 月 |\n| 洗护 | 贝亲 5 件套+棉柔巾 | ¥359 | 1-2 月 |\n| **合计** | | **¥3863** | |\n\n## 💰 余 ¥1137 怎么花\n\n**强烈建议提前备货**（生完去医院+月子里没空网购）：\n\n| 项目 | 价格 | 必要性 |\n|---|---|---|\n| 加备 1 罐奶粉（怕换粉过敏）| ¥389 | ⭐⭐⭐ |\n| 湿巾 6 大包 | ¥100 | ⭐⭐⭐ |\n| 电子体温计（耳温/额温）| ¥150 | ⭐⭐⭐ |\n| 鼻塞吸鼻器 | ¥80 | ⭐⭐ |\n| 婴儿指甲剪套装 | ¥50 | ⭐⭐ |\n| 婴儿监护器（晚上看睡眠）| ¥350 | ⭐⭐ |\n| **合计** | **¥1119** | 余 ¥18 应急 |\n\n## 💡 选购理由\n\n1. **飞鹤一段**：国产新国标 A2 蛋白，月销 4.5 万件，0-6 月小宝宝最稳的选择\n2. **大王 NB 码**：纸尿裤评价最稳的品牌之一，新生儿皮肤娇嫩首选\n3. **BABYBJÖRN 床**：北欧品牌，无甲醛+椰棕床垫（婴儿不能用记忆棉/海绵）\n4. **贝亲玻璃奶瓶**：玻璃比塑料安全（无塑化剂），用 6 个月再换塑料便携款\n\n## ⚠️ 重要提醒\n\n- ❌ **不要买全套电动玩具/早教机**——0-3 月宝宝只需要妈妈的脸\n- ❌ **不要买婴儿枕头**——0-1 岁宝宝不需要枕头（易窒息）\n- ❌ **不要囤太多 NB 纸尿裤**——宝宝长得快，2 个月就升 S 码了\n\n## 🎯 后续准备\n\n第 2 个月开始要加：\n1. 婴儿背带 / 推车（¥300-1500）\n2. 抚触油 + 益生菌（¥150-300）\n3. 玩具：黑白卡 / 摇铃（¥100 内）\n\n月子里安心带娃，其他东西宝宝长一点再买不迟。",
                "product_cards": [
                    {"card_id": "mock_bundle_005d", "display_price": 1099.0, "reason": "BABYBJÖRN实木婴儿床+椰棕床垫+防夹手设计，0-3岁安全床品最大件"},
                    {"card_id": "mock_bundle_005a", "display_price": 778.0, "reason": "飞鹤星飞帆新国标A2蛋白+月销4.5万，0-6月新生儿奶粉首选1个月用量"},
                    {"card_id": "mock_bundle_005b", "display_price": 599.0, "reason": "大王GOO.N NB码288片日本品牌，新生儿1个月用量皮肤娇嫩首选"},
                    {"card_id": "mock_bundle_005c", "display_price": 569.0, "reason": "全棉时代A类纯棉7件套+和尚服+连体衣，0-3月新生儿衣物全配"},
                    {"card_id": "mock_bundle_005e", "display_price": 459.0, "reason": "贝亲玻璃防胀气奶瓶3只装+0-3月奶嘴，无塑化剂用6个月"},
                    {"card_id": "mock_bundle_005f", "display_price": 359.0, "reason": "贝亲5件洗护全套+棉柔巾100抽×6包，新生儿日常清洁全覆盖"}
                ]
            }
        ],
        "final_response": "5000 预算新生儿月子包，**6 大件先配齐，第 1 个月够用，余 ¥1137 留备用**：\n\n## 👶 月子包完整配置 ¥3863\n\n| 用品 | 商品 | 价格 | 用量 |\n|---|---|---|---|\n| 婴儿床 | BABYBJÖRN 实木+椰棕床垫 | ¥1099 | 用 3 年 |\n| 奶粉 | 飞鹤星飞帆一段 700g×2 罐 | ¥778 | 1 个月 |\n| 纸尿裤 | 大王 GOO.N NB 288 片 | ¥599 | 1 个月 |\n| 衣物 | 全棉时代和尚服+连体衣 7 件 | ¥569 | 0-3 月 |\n| 奶瓶 | 贝亲玻璃防胀气 3 只装 | ¥459 | 用 6 月 |\n| 洗护 | 贝亲 5 件套+棉柔巾 | ¥359 | 1-2 月 |\n| **合计** | | **¥3863** | |\n\n## 💰 余 ¥1137 怎么花\n\n**强烈建议提前备货**（生完去医院+月子里没空网购）：\n\n| 项目 | 价格 | 必要性 |\n|---|---|---|\n| 加备 1 罐奶粉（怕换粉过敏）| ¥389 | ⭐⭐⭐ |\n| 湿巾 6 大包 | ¥100 | ⭐⭐⭐ |\n| 电子体温计（耳温/额温）| ¥150 | ⭐⭐⭐ |\n| 鼻塞吸鼻器 | ¥80 | ⭐⭐ |\n| 婴儿指甲剪套装 | ¥50 | ⭐⭐ |\n| 婴儿监护器（晚上看睡眠）| ¥350 | ⭐⭐ |\n| **合计** | **¥1119** | 余 ¥18 应急 |\n\n## 💡 选购理由\n\n1. **飞鹤一段**：国产新国标 A2 蛋白，月销 4.5 万件，0-6 月小宝宝最稳的选择\n2. **大王 NB 码**：纸尿裤评价最稳的品牌之一，新生儿皮肤娇嫩首选\n3. **BABYBJÖRN 床**：北欧品牌，无甲醛+椰棕床垫（婴儿不能用记忆棉/海绵）\n4. **贝亲玻璃奶瓶**：玻璃比塑料安全（无塑化剂），用 6 个月再换塑料便携款\n\n## ⚠️ 重要提醒\n\n- ❌ **不要买全套电动玩具/早教机**——0-3 月宝宝只需要妈妈的脸\n- ❌ **不要买婴儿枕头**——0-1 岁宝宝不需要枕头（易窒息）\n- ❌ **不要囤太多 NB 纸尿裤**——宝宝长得快，2 个月就升 S 码了\n\n## 🎯 后续准备\n\n第 2 个月开始要加：\n1. 婴儿背带 / 推车（¥300-1500）\n2. 抚触油 + 益生菌（¥150-300）\n3. 玩具：黑白卡 / 摇铃（¥100 内）\n\n月子里安心带娃，其他东西宝宝长一点再买不迟。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },
]


def main():
    print(f"准备追加 {len(T)} 条组合购物到 {OUTPUT_PATH}...")
    print()
    for t in T:
        print(f"  ✨ {t['trajectory_id']:<22} {t.get('training_focus','')[:55]}")
    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for t in T:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"\n✅ 已追加 {len(T)} 条")
    with open(OUTPUT_PATH) as f:
        total = sum(1 for _ in f)
    print(f"   文件总条数：{total}")


if __name__ == "__main__":
    main()
