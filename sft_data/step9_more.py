# -*- coding: utf-8 -*-
"""Step 9: 10 条新数据（场景轮换）"""
import json
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "trajectories_final.jsonl"

T = [
    # 101. similar_rec - 抱怨重量
    {
        "trajectory_id": "sft_simrec_009",
        "scenario_type": "similar_rec",
        "category": "相似品推荐",
        "quality_label": "good",
        "training_focus": "抱怨重量过重 → weight_max 参数限制",
        "is_multi_turn": True,
        "user_query": "这台笔记本太重了，2.3kg 背着累，有没有更轻的同价位款",
        "conversation_history": [
            {"role": "user", "content": "推荐 5000 元游戏本"},
            {"role": "assistant", "content": "推荐机械革命极光 Pro ¥4999，2.3kg..."},
            {"role": "user", "content": "这台笔记本太重了，2.3kg 背着累，有没有更轻的同价位款"}
        ],
        "thinking": "抱怨重量。5000价位轻薄本核显能跑LOL，但游戏性能下降。需说明权衡。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "轻薄笔记本 1.5kg以下", "min_price": 4500, "max_price": 5500, "filters": {"weight_max_kg": 1.5}},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_lap_light_001", "title": "联想小新Pro14 2025 R7-8845H 1.46kg", "price": 4899.0, "is_platform_self": True, "rating": 4.8, "key_specs": "1.46kg/2.8K 120Hz屏/Radeon 780M核显", "sales": "月销1.8万"},
                        {"product_id": "mock_lap_light_002", "title": "华为 MateBook 14s 2024 i7-13700H 1.43kg", "price": 5299.0, "is_platform_self": True, "rating": 4.9, "key_specs": "1.43kg/2.5K触控屏/华为生态联动", "sales": "月销7500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "5000 价位 1.5kg 以下的轻薄本有这两款：\n\n**1. 联想小新 Pro14（¥4899）** ⭐ 性价比\n1.46kg 比游戏本轻 850g，R7-8845H + Radeon 780M 核显，**LOL/CSGO 流畅，但跑不了原神高画质**。\n\n**2. 华为 MateBook 14s（¥5299）**\n1.43kg 最轻，i7+触控屏，华为生态联动好。游戏能力和小新差不多。\n\n⚠️ **重要权衡**：轻薄本 = 牺牲游戏性能。如果你确定不玩 3A 大作，选轻薄本没问题；如果还想偶尔玩重度游戏，建议**留游戏本 + 买个 ¥150 的电脑包减负**更实在。",
                "product_cards": [
                    {"card_id": "mock_lap_light_001", "display_price": 4899.0, "reason": "1.46kg+R7-8845H+780M核显，LOL流畅性价比首选"},
                    {"card_id": "mock_lap_light_002", "display_price": 5299.0, "reason": "1.43kg最轻+触控屏+华为生态，办公党首选"}
                ]
            }
        ],
        "final_response": "5000 价位 1.5kg 以下的轻薄本有这两款：\n\n**1. 联想小新 Pro14（¥4899）** ⭐ 性价比\n1.46kg 比游戏本轻 850g，R7-8845H + Radeon 780M 核显，**LOL/CSGO 流畅，但跑不了原神高画质**。\n\n**2. 华为 MateBook 14s（¥5299）**\n1.43kg 最轻，i7+触控屏，华为生态联动好。游戏能力和小新差不多。\n\n⚠️ **重要权衡**：轻薄本 = 牺牲游戏性能。如果你确定不玩 3A 大作，选轻薄本没问题；如果还想偶尔玩重度游戏，建议**留游戏本 + 买个 ¥150 的电脑包减负**更实在。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # 102. similar_rec - 抱怨续航
    {
        "trajectory_id": "sft_simrec_010",
        "scenario_type": "similar_rec",
        "category": "相似品推荐",
        "quality_label": "good",
        "training_focus": "抱怨续航 → battery_hours_min 参数",
        "is_multi_turn": True,
        "user_query": "之前那款无线耳机续航只有6小时太短了，长一点的有什么推荐",
        "conversation_history": [
            {"role": "user", "content": "推荐 800 元内蓝牙耳机"},
            {"role": "assistant", "content": "推荐 Sony LinkBuds S ¥799，续航 6 小时..."},
            {"role": "user", "content": "之前那款无线耳机续航只有6小时太短了，长一点的有什么推荐"}
        ],
        "thinking": "抱怨续航。800价位真无线耳机续航 ≥ 8 小时（单次）的款。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "蓝牙耳机 长续航", "max_price": 800, "filters": {"battery_hours_min": 8}, "exclude_skus": ["Sony LinkBuds S"]},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_ear_long_001", "title": "华为 FreeBuds Pro 3 主动降噪", "price": 799.0, "is_platform_self": True, "rating": 4.9, "key_specs": "单次9h/带壳31h/主动降噪/华为生态", "sales": "月销1.5万"},
                        {"product_id": "mock_ear_long_002", "title": "漫步者 NeoBuds Pro 2 LDAC", "price": 599.0, "is_platform_self": True, "rating": 4.8, "key_specs": "单次10h/带壳40h/LDAC高音质/降噪", "sales": "月销9800"},
                        {"product_id": "mock_ear_long_003", "title": "倍思 Bowie M2s Pro 静噪 Pro 续航王", "price": 299.0, "is_platform_self": True, "rating": 4.7, "key_specs": "单次12h/带壳50h(续航天花板)/主动降噪", "sales": "月销2.5万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "800 内续航 ≥ 8 小时的真无线耳机，3 款给你选：\n\n**1. 倍思 Bowie M2s Pro（¥299）** ⭐ 续航王\n**单次 12h + 带壳 50h**，是这 3 款里最长的。价格仅 ¥299，对续航党无脑选。\n\n**2. 漫步者 NeoBuds Pro 2（¥599）**\n单次 10h + 带壳 40h，**多了 LDAC 高音质编码**（音质党刚需）。\n\n**3. 华为 FreeBuds Pro 3（¥799）**\n单次 9h + 带壳 31h，**主动降噪是 3 款里最强**。华为手机用户优选（双设备秒切）。\n\n**建议**：纯求续航选倍思（一半价 + 续航最长），求音质漫步者，求降噪+华为生态选 FreeBuds。",
                "product_cards": [
                    {"card_id": "mock_ear_long_003", "display_price": 299.0, "reason": "12h+50h续航天花板+主动降噪，299价格续航党无脑选"},
                    {"card_id": "mock_ear_long_002", "display_price": 599.0, "reason": "10h+40h续航+LDAC高音质编码，音质党刚需"},
                    {"card_id": "mock_ear_long_001", "display_price": 799.0, "reason": "9h+31h续航+最强降噪+华为生态秒切，华为用户优选"}
                ]
            }
        ],
        "final_response": "800 内续航 ≥ 8 小时的真无线耳机，3 款给你选：\n\n**1. 倍思 Bowie M2s Pro（¥299）** ⭐ 续航王\n**单次 12h + 带壳 50h**，是这 3 款里最长的。价格仅 ¥299，对续航党无脑选。\n\n**2. 漫步者 NeoBuds Pro 2（¥599）**\n单次 10h + 带壳 40h，**多了 LDAC 高音质编码**（音质党刚需）。\n\n**3. 华为 FreeBuds Pro 3（¥799）**\n单次 9h + 带壳 31h，**主动降噪是 3 款里最强**。华为手机用户优选（双设备秒切）。\n\n**建议**：纯求续航选倍思（一半价 + 续航最长），求音质漫步者，求降噪+华为生态选 FreeBuds。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # 103. sku_comp - 价格段对比
    {
        "trajectory_id": "sft_skucomp_007",
        "scenario_type": "sku_comp",
        "category": "商品对比",
        "quality_label": "good",
        "training_focus": "同品类高低价对比：贵 3 倍真的好 3 倍吗",
        "user_query": "戴森 V12（3299）和追觅 V12s Pro（1699）真有2倍差距吗，差在哪里",
        "thinking": "两款都是高端无线吸尘器，价差 ¥1600。要挖出真实差异：吸力/续航/智能/做工/品牌。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"skus": ["戴森V12 Detect Slim Absolute", "追觅 V12s Pro"], "mode": "parallel_exact_match", "fields": ["吸力", "续航", "智能", "刷头", "做工"]},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_v12d", "title": "戴森 V12 Detect Slim Absolute", "price": 3299.0, "is_platform_self": True, "rating": 4.9, "key_specs": "150AW/60min/激光除尘+LCD屏/4刷头/英国品牌", "sales": "月销6500"},
                        {"product_id": "mock_v12s", "title": "追觅 V12s Pro 旗舰款", "price": 1699.0, "is_platform_self": True, "rating": 4.8, "key_specs": "185AW(更强)/60min/激光除尘+OLED屏/5刷头/国产", "sales": "月销1.5万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "**直接说结论：戴森 V12 的 ¥1600 溢价主要买的是「品牌信任」**。性能上追觅 V12s Pro 几乎全面碾压：\n\n## 📊 5 维度对比\n\n| 维度 | 戴森 V12 ¥3299 | 追觅 V12s Pro ¥1699 |\n|---|---|---|\n| **吸力** | 150AW | **185AW（强 23%）**|\n| **续航** | 60min | 60min（持平）|\n| **智能屏** | LCD | **OLED（更清晰）**|\n| **刷头数** | 4 个 | **5 个**|\n| **做工** | **英国精密设计** | 国产精密接近 |\n| **品牌** | **戴森（保值率高）** | 追觅（口碑上升）|\n\n## 💰 ¥1600 溢价值不值\n\n**值的部分**：\n- ✅ 戴森做工细节（接缝/手感/转向）确实领先\n- ✅ 二手保值率高（戴森 V12 二手 ¥1800-2200，追觅二手 ¥800）\n- ✅ 售后网点更密（戴森全国 200+ 维修点）\n\n**不值的部分**：\n- ❌ 性能：追觅吸力更强、刷头更多\n- ❌ 故障率：两者差不多（追觅是原戴森中国团队创立）\n\n## 🎯 我的推荐\n\n- **2 年内大概率换/卖** → **戴森**（二手保值）\n- **用 5 年以上** → **追觅 V12s Pro**（同等体验省 ¥1600）\n- **送礼/家里人在意品牌** → 戴森\n\n90% 的家庭实用角度，追觅 V12s Pro 是更聪明的选择。",
                "product_cards": [
                    {"card_id": "mock_v12s", "display_price": 1699.0, "reason": "185AW吸力强23%+5刷头+OLED屏，性能碾压且省1600元家用首选"},
                    {"card_id": "mock_v12d", "display_price": 3299.0, "reason": "戴森做工+二手保值+售后网点密，仅推荐2年内换/卖或送礼场景"}
                ]
            }
        ],
        "final_response": "**直接说结论：戴森 V12 的 ¥1600 溢价主要买的是「品牌信任」**。性能上追觅 V12s Pro 几乎全面碾压：\n\n## 📊 5 维度对比\n\n| 维度 | 戴森 V12 ¥3299 | 追觅 V12s Pro ¥1699 |\n|---|---|---|\n| **吸力** | 150AW | **185AW（强 23%）**|\n| **续航** | 60min | 60min（持平）|\n| **智能屏** | LCD | **OLED（更清晰）**|\n| **刷头数** | 4 个 | **5 个**|\n| **做工** | **英国精密设计** | 国产精密接近 |\n| **品牌** | **戴森（保值率高）** | 追觅（口碑上升）|\n\n## 💰 ¥1600 溢价值不值\n\n**值的部分**：\n- ✅ 戴森做工细节（接缝/手感/转向）确实领先\n- ✅ 二手保值率高（戴森 V12 二手 ¥1800-2200，追觅二手 ¥800）\n- ✅ 售后网点更密（戴森全国 200+ 维修点）\n\n**不值的部分**：\n- ❌ 性能：追觅吸力更强、刷头更多\n- ❌ 故障率：两者差不多（追觅是原戴森中国团队创立）\n\n## 🎯 我的推荐\n\n- **2 年内大概率换/卖** → **戴森**（二手保值）\n- **用 5 年以上** → **追觅 V12s Pro**（同等体验省 ¥1600）\n- **送礼/家里人在意品牌** → 戴森\n\n90% 的家庭实用角度，追觅 V12s Pro 是更聪明的选择。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # 104. sku_comp - 配件 vs 主商品对比
    {
        "trajectory_id": "sft_skucomp_008",
        "scenario_type": "sku_comp",
        "category": "商品对比",
        "quality_label": "good",
        "training_focus": "对比主商品和配件方案：买套装还是单件加配件",
        "user_query": "iPad Pro 11寸单买 ¥6499，套装（含键盘+笔）¥8499，买套装划算吗",
        "thinking": "套装 vs 单件 + 单买配件 哪个更划算。需要分别查单买的键盘+笔价格。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "iPad Pro 11寸 妙控键盘 Apple Pencil", "show_all_skus": True},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_ipad_pro", "title": "iPad Pro 11寸 M4 256G 单机", "price": 6499.0, "is_platform_self": True, "rating": 4.9, "key_specs": "M4芯片/11寸/256G/官方单机价", "sales": "月销4500"},
                        {"product_id": "mock_ipad_bundle", "title": "iPad Pro 11寸 M4 256G 套装（含妙控键盘+Apple Pencil Pro）", "price": 8499.0, "is_platform_self": True, "rating": 4.9, "key_specs": "套装含妙控键盘+Pencil Pro/原装组合/省399", "sales": "月销1800"},
                        {"product_id": "mock_magic_kb", "title": "妙控键盘 iPad Pro 11寸 单买", "price": 2299.0, "is_platform_self": True, "rating": 4.8, "key_specs": "原装妙控键盘/单买价", "sales": "月销1200"},
                        {"product_id": "mock_pencil_pro", "title": "Apple Pencil Pro 单买", "price": 999.0, "is_platform_self": True, "rating": 4.9, "key_specs": "Pencil Pro/单买价", "sales": "月销3500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "PythonCalculator",
                "tool_input": {"code": "a = 6499 + 2299 + 999  # 单件凑\nb = 8499  # 套装\nsave = a - b\nprint(f'方案A 单件凑: iPad 6499 + 键盘 2299 + Pencil 999 = {a}')\nprint(f'方案B 套装价: {b}')\nprint(f'套装省 ¥{save}（约5%）')\nprint(f'\\n但... 如果只要其中一件配件:')\nprint(f'iPad + 仅键盘: {6499+2299} = 8798')\nprint(f'iPad + 仅Pencil: {6499+999} = 7498（比套装便宜1001）')"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [{"product_id": "calc_v9", "title": "方案对比", "price": 0.0, "is_platform_self": False, "rating": 5.0, "key_specs": "单件凑9797/套装8499/套装省1298/仅Pencil7498比套装便宜1001", "sales": "—"}]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "final_response",
                "content": "**结论：套装的省钱前提是「2 个配件都要」**。看你实际需求：\n\n## 💰 三种方案对比\n\n| 方案 | 价格 | 包含 |\n|---|---|---|\n| 🥇 套装 | **¥8499** | iPad + 键盘 + Pencil |\n| 单件全凑 | ¥9797 | iPad + 键盘 + Pencil |\n| iPad+仅 Pencil | **¥7498** | iPad + Pencil（无键盘）|\n| iPad+仅键盘 | ¥8798 | iPad + 键盘（无 Pencil）|\n\n## 🎯 怎么选\n\n### 1️⃣ 两个配件都要 → **买套装 ¥8499**（省 ¥1298）⭐\n这是最划算路径。妙控键盘+Pencil Pro 单买要凑到 ¥9797，套装直接省 13%。\n\n### 2️⃣ 只画画/记笔记，不打字 → **iPad + 仅 Pencil ¥7498**\n比套装便宜 ¥1001。等以后真要打字再买键盘也不迟。\n\n### 3️⃣ 只办公打字 → **iPad + 仅键盘 ¥8798**\n但说实话，**iPad 打字效率比不上笔记本**，如果纯办公更建议买 ¥5500 的 MacBook Air M3。\n\n## 💡 关键判断\n\n问自己 3 个问题：\n- ✅ 我会经常用 iPad 做笔记/画画吗？→ Pencil 必要\n- ✅ 我会用 iPad 替代笔记本写邮件/文档吗？→ 键盘必要\n- ❌ 我只刷视频/看电子书？→ 单买 iPad ¥6499 即可，别花冤枉钱\n\n## 📝 我的建议\n\n90% 的 iPad Pro 用户**只用上 Pencil，键盘很快吃灰**。建议先买 **iPad + Pencil（¥7498）** 用 2-3 个月，确认真的需要再加键盘。比直接套装更稳妥。",
                "product_cards": [
                    {"card_id": "mock_ipad_bundle", "display_price": 8499.0, "reason": "套装比单件凑省1298元约13%，键盘+Pencil都要时最划算"},
                    {"card_id": "mock_ipad_pro", "display_price": 6499.0, "reason": "单买iPad可灵活搭配配件，刷视频/看书纯日用足够"},
                    {"card_id": "mock_pencil_pro", "display_price": 999.0, "reason": "Pencil Pro是iPad最高使用率配件，画画/笔记党刚需"}
                ]
            }
        ],
        "final_response": "**结论：套装的省钱前提是「2 个配件都要」**。看你实际需求：\n\n## 💰 三种方案对比\n\n| 方案 | 价格 | 包含 |\n|---|---|---|\n| 🥇 套装 | **¥8499** | iPad + 键盘 + Pencil |\n| 单件全凑 | ¥9797 | iPad + 键盘 + Pencil |\n| iPad+仅 Pencil | **¥7498** | iPad + Pencil（无键盘）|\n| iPad+仅键盘 | ¥8798 | iPad + 键盘（无 Pencil）|\n\n## 🎯 怎么选\n\n### 1️⃣ 两个配件都要 → **买套装 ¥8499**（省 ¥1298）⭐\n这是最划算路径。妙控键盘+Pencil Pro 单买要凑到 ¥9797，套装直接省 13%。\n\n### 2️⃣ 只画画/记笔记，不打字 → **iPad + 仅 Pencil ¥7498**\n比套装便宜 ¥1001。等以后真要打字再买键盘也不迟。\n\n### 3️⃣ 只办公打字 → **iPad + 仅键盘 ¥8798**\n但说实话，**iPad 打字效率比不上笔记本**，如果纯办公更建议买 ¥5500 的 MacBook Air M3。\n\n## 💡 关键判断\n\n问自己 3 个问题：\n- ✅ 我会经常用 iPad 做笔记/画画吗？→ Pencil 必要\n- ✅ 我会用 iPad 替代笔记本写邮件/文档吗？→ 键盘必要\n- ❌ 我只刷视频/看电子书？→ 单买 iPad ¥6499 即可，别花冤枉钱\n\n## 📝 我的建议\n\n90% 的 iPad Pro 用户**只用上 Pencil，键盘很快吃灰**。建议先买 **iPad + Pencil（¥7498）** 用 2-3 个月，确认真的需要再加键盘。比直接套装更稳妥。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # 105. matching - 鞋子配袜子裤子
    {
        "trajectory_id": "sft_match_008",
        "scenario_type": "matching_purchase",
        "category": "搭配购物",
        "quality_label": "good",
        "training_focus": "运动鞋整体搭配：袜子+裤子风格统一",
        "user_query": "我新买了一双白色 AJ1，配什么袜子和裤子好看",
        "thinking": "白色 AJ1 是潮流单品。搭配方向：袜子(中筒/纯色/品牌logo) + 裤子(直筒/oversize/工装)。重点是潮流感统一。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "中筒袜 男士 潮流", "filters": {"style": ["sport", "trendy"], "colors": ["白色", "黑色", "灰色"]}, "match_with": "white_aj1_sneakers"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_socks_001", "title": "Nike Elite 中筒篮球袜 3双装 黑白配", "price": 159.0, "is_platform_self": True, "rating": 4.9, "key_specs": "Nike Elite/中筒/黑白配色/AJ1官配", "sales": "月销1.8万"},
                        {"product_id": "mock_socks_002", "title": "Stance 街头潮袜 印花款 单双", "price": 89.0, "is_platform_self": True, "rating": 4.7, "key_specs": "Stance潮牌/印花设计/中筒/潮流圈认可", "sales": "月销4500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "男士直筒裤 工装裤 oversize", "filters": {"style": "streetwear", "colors": ["卡其", "军绿", "黑色"]}, "match_with": "white_aj1_sneakers"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_pants_001", "title": "GAP 卡其工装直筒裤 oversize 美式街头", "price": 399.0, "is_platform_self": True, "rating": 4.8, "key_specs": "卡其色/直筒oversize/适合AJ1街头风", "sales": "月销6500"},
                        {"product_id": "mock_pants_002", "title": "Stussy 同款 黑色机能工装裤 多袋款", "price": 599.0, "is_platform_self": True, "rating": 4.7, "key_specs": "黑色/机能多袋/潮牌风格", "sales": "月销1500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "final_response",
                "content": "白色 AJ1 是经典潮流单品，整体搭配要走**街头/运动风**。给你 2 套方案：\n\n## 🔥 方案 A：经典美式街头（推荐）\n\n| 配件 | 商品 | 价格 |\n|---|---|---|\n| 袜子 | **Nike Elite 中筒袜 3 双装** | ¥159 |\n| 裤子 | **GAP 卡其工装直筒裤** | ¥399 |\n\n**风格亮点**：Nike 袜 + AJ1（都是 Nike 系），袜口露出黑白 logo 和 AJ1 形成呼应。卡其工装裤 + 白色 AJ1 是 90 年代美式街头的教科书。\n\n## 🔥 方案 B：潮牌机能风\n\n| 配件 | 商品 | 价格 |\n|---|---|---|\n| 袜子 | **Stance 印花潮袜** | ¥89 |\n| 裤子 | **Stussy 同款黑色机能工装裤** | ¥599 |\n\n**风格亮点**：Stance + Stussy 都是潮流圈认可的品牌，机能多袋裤 + 印花袜 + 白 AJ1 走的是「日系潮牌」路线，**适合拍照党/潮流博主**。\n\n## 💡 怎么选\n\n| 场景 | 推荐 |\n|---|---|\n| 日常通勤+周末逛街 | **方案 A（GAP + Nike 袜）** |\n| 拍照/潮流活动/玩配饰 | **方案 B（Stussy + Stance）** |\n\n## ⚠️ 避雷\n\n- ❌ **黑色西裤 + AJ1**：完全风格冲突\n- ❌ **白色船袜（隐形袜）**：露脚踝穿 AJ1 显得别扭，**中筒袜才是 AJ1 的灵魂**\n- ❌ **紧身瘦腿裤**：AJ1 鞋头偏宽，搭瘦腿裤显头重脚轻，**直筒/oversize 才合适**\n\n## 🎯 关键铁律\n\nAJ1 = 中筒袜 + 直筒/oversize 裤。这套公式 30 年都不会过时。",
                "product_cards": [
                    {"card_id": "mock_socks_001", "display_price": 159.0, "reason": "Nike Elite中筒袜AJ1官配，3双装黑白配色经典美式街头"},
                    {"card_id": "mock_pants_001", "display_price": 399.0, "reason": "GAP卡其工装直筒oversize，90年代美式街头AJ1教科书搭配"},
                    {"card_id": "mock_socks_002", "display_price": 89.0, "reason": "Stance潮牌印花中筒袜，潮流圈认可拍照党首选"},
                    {"card_id": "mock_pants_002", "display_price": 599.0, "reason": "Stussy黑色机能多袋工装裤，日系潮牌路线适合潮流博主"}
                ]
            }
        ],
        "final_response": "白色 AJ1 是经典潮流单品，整体搭配要走**街头/运动风**。给你 2 套方案：\n\n## 🔥 方案 A：经典美式街头（推荐）\n\n| 配件 | 商品 | 价格 |\n|---|---|---|\n| 袜子 | **Nike Elite 中筒袜 3 双装** | ¥159 |\n| 裤子 | **GAP 卡其工装直筒裤** | ¥399 |\n\n**风格亮点**：Nike 袜 + AJ1（都是 Nike 系），袜口露出黑白 logo 和 AJ1 形成呼应。卡其工装裤 + 白色 AJ1 是 90 年代美式街头的教科书。\n\n## 🔥 方案 B：潮牌机能风\n\n| 配件 | 商品 | 价格 |\n|---|---|---|\n| 袜子 | **Stance 印花潮袜** | ¥89 |\n| 裤子 | **Stussy 同款黑色机能工装裤** | ¥599 |\n\n**风格亮点**：Stance + Stussy 都是潮流圈认可的品牌，机能多袋裤 + 印花袜 + 白 AJ1 走的是「日系潮牌」路线，**适合拍照党/潮流博主**。\n\n## 💡 怎么选\n\n| 场景 | 推荐 |\n|---|---|\n| 日常通勤+周末逛街 | **方案 A（GAP + Nike 袜）** |\n| 拍照/潮流活动/玩配饰 | **方案 B（Stussy + Stance）** |\n\n## ⚠️ 避雷\n\n- ❌ **黑色西裤 + AJ1**：完全风格冲突\n- ❌ **白色船袜（隐形袜）**：露脚踝穿 AJ1 显得别扭，**中筒袜才是 AJ1 的灵魂**\n- ❌ **紧身瘦腿裤**：AJ1 鞋头偏宽，搭瘦腿裤显头重脚轻，**直筒/oversize 才合适**\n\n## 🎯 关键铁律\n\nAJ1 = 中筒袜 + 直筒/oversize 裤。这套公式 30 年都不会过时。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # 106. matching - 包包配饰
    {
        "trajectory_id": "sft_match_009",
        "scenario_type": "matching_purchase",
        "category": "搭配购物",
        "quality_label": "good",
        "training_focus": "包包+丝巾+挂件三件套搭配",
        "user_query": "新买的香芋紫 LV Speedy 包包，配什么丝巾和挂件好看",
        "thinking": "香芋紫=粉紫色调。丝巾(同色系/浅紫/米白)+挂件(银金属/毛绒小物)。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "丝巾 包配饰 真丝", "filters": {"colors": ["浅紫", "米白", "燕麦"], "material": "silk"}, "match_with": "taro_purple_LV_Speedy"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_scarf_001", "title": "上海故事 真丝丝巾 浅紫提花 同色系", "price": 159.0, "is_platform_self": True, "rating": 4.8, "key_specs": "100%桑蚕丝/浅紫色/提花纹/55cm方巾", "sales": "月销2500"},
                        {"product_id": "mock_scarf_002", "title": "Hermès 同款 米白丝巾 90cm 大方巾", "price": 599.0, "is_platform_self": True, "rating": 4.7, "key_specs": "100%真丝/米白色/90cm大方巾/对比色提亮", "sales": "月销680"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "包挂件 包配饰 金属", "filters": {"colors": ["银色", "金色", "粉色"], "style": "luxury_charm"}},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_charm_001", "title": "施华洛世奇 水晶蝴蝶包挂件 粉紫色", "price": 469.0, "is_platform_self": True, "rating": 4.9, "key_specs": "施华洛世奇水晶/粉紫色/同色系蝴蝶造型", "sales": "月销1200"},
                        {"product_id": "mock_charm_002", "title": "Jellycat 兔子毛绒包挂 经典款 米色", "price": 199.0, "is_platform_self": True, "rating": 4.9, "key_specs": "Jellycat官方/米色/毛绒可爱风", "sales": "月销1.8万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "final_response",
                "content": "香芋紫 LV Speedy 是温柔系包包，配饰要呼应这个调性。2 套方案：\n\n## 💜 方案 A：高级同色系（贵妇风）\n\n| 配件 | 商品 | 价格 |\n|---|---|---|\n| 丝巾 | **上海故事浅紫真丝丝巾** | ¥159 |\n| 挂件 | **施华洛世奇粉紫水晶蝴蝶挂件** | ¥469 |\n\n**风格**：3 件全部粉紫色系，**深浅渐变层次**。丝巾系在包柄上、挂件挂侧边，整套有「高级珠宝级」精致感。**适合 25-40 岁通勤/约会**。\n\n## 🤍 方案 B：温柔对比（少女风）\n\n| 配件 | 商品 | 价格 |\n|---|---|---|\n| 丝巾 | **米白 90cm 大方巾** | ¥599 |\n| 挂件 | **Jellycat 兔子毛绒挂件 米色** | ¥199 |\n\n**风格**：米白 × 香芋紫 = 温柔莫兰迪。Jellycat 是当下最火的毛绒挂件，**少女感拉满**。**适合 20-30 岁日常出街/拍照**。\n\n## 💡 怎么选\n\n| 你是 | 推荐 |\n|---|---|\n| 通勤/约会党 | **方案 A 同色系** |\n| 拍照/网红风 | **方案 B 温柔对比** |\n| 都想要不想花太多 | 上海故事丝巾 ¥159 + Jellycat ¥199 = ¥358 也是经典 |\n\n## ⚠️ 配色避雷\n\n- ❌ **黑色丝巾**：会压住香芋紫的温柔感\n- ❌ **大红色挂件**：色相冲突\n- ❌ **荧光色任何配件**：让奢侈品看起来掉价\n\n## 🎯 系法建议\n\n丝巾系在包柄根部（不要全包柄缠绕，太复杂），打个简单的「双叶结」最有气质。",
                "product_cards": [
                    {"card_id": "mock_scarf_001", "display_price": 159.0, "reason": "上海故事浅紫真丝同色系深浅渐变，贵妇风通勤约会党首选"},
                    {"card_id": "mock_charm_001", "display_price": 469.0, "reason": "施华洛世奇粉紫水晶蝴蝶+同色系珠宝级精致感"},
                    {"card_id": "mock_scarf_002", "display_price": 599.0, "reason": "米白90cm大方巾温柔莫兰迪对比，少女风拍照党"},
                    {"card_id": "mock_charm_002", "display_price": 199.0, "reason": "Jellycat兔子毛绒挂件少女感拉满，月销1.8万网红首选"}
                ]
            }
        ],
        "final_response": "香芋紫 LV Speedy 是温柔系包包，配饰要呼应这个调性。2 套方案：\n\n## 💜 方案 A：高级同色系（贵妇风）\n\n| 配件 | 商品 | 价格 |\n|---|---|---|\n| 丝巾 | **上海故事浅紫真丝丝巾** | ¥159 |\n| 挂件 | **施华洛世奇粉紫水晶蝴蝶挂件** | ¥469 |\n\n**风格**：3 件全部粉紫色系，**深浅渐变层次**。丝巾系在包柄上、挂件挂侧边，整套有「高级珠宝级」精致感。**适合 25-40 岁通勤/约会**。\n\n## 🤍 方案 B：温柔对比（少女风）\n\n| 配件 | 商品 | 价格 |\n|---|---|---|\n| 丝巾 | **米白 90cm 大方巾** | ¥599 |\n| 挂件 | **Jellycat 兔子毛绒挂件 米色** | ¥199 |\n\n**风格**：米白 × 香芋紫 = 温柔莫兰迪。Jellycat 是当下最火的毛绒挂件，**少女感拉满**。**适合 20-30 岁日常出街/拍照**。\n\n## 💡 怎么选\n\n| 你是 | 推荐 |\n|---|---|\n| 通勤/约会党 | **方案 A 同色系** |\n| 拍照/网红风 | **方案 B 温柔对比** |\n| 都想要不想花太多 | 上海故事丝巾 ¥159 + Jellycat ¥199 = ¥358 也是经典 |\n\n## ⚠️ 配色避雷\n\n- ❌ **黑色丝巾**：会压住香芋紫的温柔感\n- ❌ **大红色挂件**：色相冲突\n- ❌ **荧光色任何配件**：让奢侈品看起来掉价\n\n## 🎯 系法建议\n\n丝巾系在包柄根部（不要全包柄缠绕，太复杂），打个简单的「双叶结」最有气质。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # 107. bundle - 4000元露营装备
    {
        "trajectory_id": "sft_bundle_006",
        "scenario_type": "bundle_purchase",
        "category": "组合购物",
        "quality_label": "good",
        "training_focus": "4000预算分配到帐篷/天幕/桌椅/灯/炉具",
        "user_query": "想配一套露营装备，4000 预算够 2 人用就行",
        "thinking": "4000 露营入门：帐篷40%(1600)+天幕15%(600)+桌椅20%(800)+灯具10%(400)+炉具15%(600)。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "露营帐篷 2-3人 自动", "min_price": 1000, "max_price": 1800},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_camp_001", "title": "Naturehike 云尚 2-3人帐篷 自动速开", "price": 1299.0, "is_platform_self": True, "rating": 4.9, "key_specs": "2-3人/自动速开/银胶防水/4kg", "sales": "月销1.5万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "天幕 露营 防晒", "max_price": 700},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_camp_002", "title": "牧高笛 蝶形天幕 UPF50+ 防晒", "price": 599.0, "is_platform_self": True, "rating": 4.8, "key_specs": "UPF50+防晒/4×4米/赠杆+绳", "sales": "月销4500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "露营桌椅套装 折叠", "max_price": 900},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_camp_003", "title": "黑鹿 蛋卷桌+月亮椅×2 套装", "price": 769.0, "is_platform_self": True, "rating": 4.9, "key_specs": "蛋卷桌1+月亮椅2/铝合金/可折叠", "sales": "月销6800"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 4,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "露营灯 氛围灯", "max_price": 500},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_camp_004", "title": "歌乐 LED 营地灯+氛围灯+头灯3件套", "price": 389.0, "is_platform_self": True, "rating": 4.8, "key_specs": "营地灯+氛围串灯+头灯/USB充电", "sales": "月销1.2万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 5,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "卡式炉 户外 锅具", "max_price": 700},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_camp_005", "title": "Iwatani 岩谷 卡式炉+锅具4件套", "price": 599.0, "is_platform_self": True, "rating": 4.9, "key_specs": "日本岩谷卡式炉+锅具4件套", "sales": "月销3500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 6,
                "step_type": "tool_call",
                "tool_name": "PythonCalculator",
                "tool_input": {"code": "items = {'帐篷':1299,'天幕':599,'桌椅':769,'灯具':389,'卡炉':599}\ntotal = sum(items.values())\nfor k,v in items.items():\n    print(f'{k}: ¥{v}  ({v/total*100:.0f}%)')\nprint(f'合计: ¥{total}, 余 ¥{4000-total}')"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [{"product_id": "calc_b6", "title": "预算分配", "price": 0.0, "is_platform_self": False, "rating": 5.0, "key_specs": "合计3655元/余345/帐篷36%桌椅21%卡炉16%天幕16%灯具11%", "sales": "—"}]
                },
                "error_type": None
            },
            {
                "step_id": 7,
                "step_type": "final_response",
                "content": "2 人露营入门套装，**5 件齐了 ¥3655，余 ¥345 留备用**：\n\n## 🏕️ 完整方案\n\n| 类别 | 商品 | 价格 |\n|---|---|---|\n| 🥇 帐篷 | **Naturehike 云尚 2-3人自动速开** | ¥1299 |\n| 天幕 | **牧高笛蝶形天幕 UPF50+** | ¥599 |\n| 桌椅 | **黑鹿 蛋卷桌+月亮椅×2 套装** | ¥769 |\n| 卡炉 | **Iwatani 岩谷卡炉+锅具 4 件套** | ¥599 |\n| 灯具 | **歌乐 LED 三件套（营地+氛围+头灯）** | ¥389 |\n| **合计** | | **¥3655**（余 345）|\n\n## 💰 余 ¥345 怎么花\n\n按必要性：\n1. **充气垫×2**（¥150-200）：睡帐篷里硬地面，没气垫=没法睡\n2. **野餐垫**（¥80-150）：摆桌椅前打底\n3. **保温箱**（¥100-200）：冷藏饮料食材\n4. **湿巾+垃圾袋**（¥50）：必备\n\n## ⚠️ 新手避坑\n\n- ❌ **不要买便宜的「3 季帐」**：防雨防风性能差，第一次下雨就崩溃\n- ❌ **不要买电锅/电磁炉**：户外没电，卡式炉才是唯一解\n- ❌ **不要买太重的天幕（>3kg）**：搬运累，UPF50+ 的轻量化天幕够用\n\n## 🎯 选品理由\n\n- **Naturehike 云尚**：露营圈口碑天花板，2-3 人帐篷月销 1.5 万\n- **岩谷卡炉**：日本品牌，户外炉具行业标杆，二手保值\n- **黑鹿桌椅**：蛋卷桌+月亮椅是露营网红标配，颜值在线\n\n这套装备**用 3 年没问题**，比临时凑齐合算多了。",
                "product_cards": [
                    {"card_id": "mock_camp_001", "display_price": 1299.0, "reason": "Naturehike云尚2-3人自动速开+银胶防水+月销1.5万露营圈口碑天花板"},
                    {"card_id": "mock_camp_002", "display_price": 599.0, "reason": "牧高笛蝶形天幕UPF50+防晒+4×4米，赠杆+绳一站式"},
                    {"card_id": "mock_camp_003", "display_price": 769.0, "reason": "黑鹿蛋卷桌+2个月亮椅套装+铝合金可折叠，露营网红标配"},
                    {"card_id": "mock_camp_005", "display_price": 599.0, "reason": "岩谷卡炉+锅具4件套日本品牌，户外炉具行业标杆"},
                    {"card_id": "mock_camp_004", "display_price": 389.0, "reason": "歌乐LED营地灯+氛围串灯+头灯3件套USB充电一次配齐"}
                ]
            }
        ],
        "final_response": "2 人露营入门套装，**5 件齐了 ¥3655，余 ¥345 留备用**：\n\n## 🏕️ 完整方案\n\n| 类别 | 商品 | 价格 |\n|---|---|---|\n| 🥇 帐篷 | **Naturehike 云尚 2-3人自动速开** | ¥1299 |\n| 天幕 | **牧高笛蝶形天幕 UPF50+** | ¥599 |\n| 桌椅 | **黑鹿 蛋卷桌+月亮椅×2 套装** | ¥769 |\n| 卡炉 | **Iwatani 岩谷卡炉+锅具 4 件套** | ¥599 |\n| 灯具 | **歌乐 LED 三件套（营地+氛围+头灯）** | ¥389 |\n| **合计** | | **¥3655**（余 345）|\n\n## 💰 余 ¥345 怎么花\n\n按必要性：\n1. **充气垫×2**（¥150-200）：睡帐篷里硬地面，没气垫=没法睡\n2. **野餐垫**（¥80-150）：摆桌椅前打底\n3. **保温箱**（¥100-200）：冷藏饮料食材\n4. **湿巾+垃圾袋**（¥50）：必备\n\n## ⚠️ 新手避坑\n\n- ❌ **不要买便宜的「3 季帐」**：防雨防风性能差，第一次下雨就崩溃\n- ❌ **不要买电锅/电磁炉**：户外没电，卡式炉才是唯一解\n- ❌ **不要买太重的天幕（>3kg）**：搬运累，UPF50+ 的轻量化天幕够用\n\n## 🎯 选品理由\n\n- **Naturehike 云尚**：露营圈口碑天花板，2-3 人帐篷月销 1.5 万\n- **岩谷卡炉**：日本品牌，户外炉具行业标杆，二手保值\n- **黑鹿桌椅**：蛋卷桌+月亮椅是露营网红标配，颜值在线\n\n这套装备**用 3 年没问题**，比临时凑齐合算多了。",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # 108. bundle - 8000元相机摄影入门
    {
        "trajectory_id": "sft_bundle_007",
        "scenario_type": "bundle_purchase",
        "category": "组合购物",
        "quality_label": "good",
        "training_focus": "8000预算分相机+镜头+三脚架+SD卡+包",
        "user_query": "想入门摄影，预算 8000 给一套设备",
        "thinking": "8000摄影入门：机身+套头60%(4800)+定焦头20%(1600)+三脚架/SD/包20%(1600)。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "微单相机 入门套机 24-50mm", "min_price": 4000, "max_price": 5500},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_cam_001", "title": "索尼 ZV-E10 II 套机（含 16-50mm 镜头）", "price": 4999.0, "is_platform_self": True, "rating": 4.9, "key_specs": "APS-C/Vlog定位/含套头/4K视频", "sales": "月销1.8万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "索尼 50mm F1.8 定焦镜头", "max_price": 1700},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_cam_002", "title": "索尼 SEL50F18F E50mm F1.8 OSS 定焦", "price": 1599.0, "is_platform_self": True, "rating": 4.9, "key_specs": "E卡口/50mm F1.8/人像定焦/虚化神器", "sales": "月销5500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 3,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "三脚架 碳纤维 轻量", "max_price": 600},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_cam_003", "title": "思锐 AM-225+B-00K 碳纤维三脚架", "price": 469.0, "is_platform_self": True, "rating": 4.8, "key_specs": "碳纤维/1.2kg轻量/最高1.5m", "sales": "月销2500"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 4,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "SD卡 128G 高速", "max_price": 200},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_cam_004", "title": "闪迪 Extreme Pro SD卡 128G V30", "price": 159.0, "is_platform_self": True, "rating": 4.9, "key_specs": "128G/V30高速/4K连拍", "sales": "月销1.5万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 5,
                "step_type": "tool_call",
                "tool_name": "SkuRecallShopping",
                "tool_input": {"query": "摄影包 单肩 防水", "max_price": 400},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_cam_005", "title": "国家地理 NG W2161 单肩摄影包", "price": 369.0, "is_platform_self": True, "rating": 4.8, "key_specs": "防水帆布/装1机2镜+13寸笔记本", "sales": "月销1200"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 6,
                "step_type": "tool_call",
                "tool_name": "PythonCalculator",
                "tool_input": {"code": "items = {'机身+套头':4999,'50mm定焦':1599,'三脚架':469,'SD卡':159,'摄影包':369}\ntotal = sum(items.values())\nfor k,v in items.items(): print(f'{k}: ¥{v}')\nprint(f'\\n合计: ¥{total}, 余 ¥{8000-total}')"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [{"product_id": "calc_b7", "title": "预算分配", "price": 0.0, "is_platform_self": False, "rating": 5.0, "key_specs": "合计7595/余405", "sales": "—"}]
                },
                "error_type": None
            },
            {
                "step_id": 7,
                "step_type": "final_response",
                "content": "8000 摄影入门最优配置，**5 件 ¥7595，余 ¥405**：\n\n## 📷 完整方案\n\n| 类别 | 商品 | 价格 |\n|---|---|---|\n| 🥇 机身+套头 | **索尼 ZV-E10 II（含 16-50mm 套头）** | ¥4999 |\n| 定焦镜头 | **索尼 50mm F1.8 OSS（人像虚化）** | ¥1599 |\n| 三脚架 | **思锐碳纤维三脚架（1.2kg）** | ¥469 |\n| 存储卡 | **闪迪 Extreme Pro 128G V30** | ¥159 |\n| 摄影包 | **国家地理 NG W2161 单肩包** | ¥369 |\n| **合计** | | **¥7595**（余 405）|\n\n## 💡 为什么这样配\n\n### 1️⃣ 机身选 ZV-E10 II 而非全画幅入门 A7C\n¥4999 vs ¥10000+，APS-C 画质对入门完全够用，**省下的钱买定焦头才是真正的画质提升**。\n\n### 2️⃣ 必须加 50mm F1.8 定焦\n套头 16-50mm 是变焦头，**光圈 F3.5-5.6 拍不出虚化**。50mm F1.8 是「人像虚化神器」，¥1599 性价比之王。\n\n### 3️⃣ 三脚架碳纤维不要铝合金\n碳纤维 1.2kg vs 铝合金 2kg，外出携带差距巨大。\n\n## 💰 余 ¥405 可加\n\n按优先级：\n1. **UV 镜+CPL 偏振镜**（¥150-300）：保护镜头 + 拍风景压反光\n2. **快门遥控器**（¥80）：长曝光/自拍刚需\n3. **清洁套装**（¥50）：擦镜布+气吹+清洁笔\n\n## ⚠️ 新手避坑\n\n- ❌ **不要买二手镜头**：可能有霉斑入灰（看不出来）\n- ❌ **不要买 35mm 1.8 而不是 50mm**：35mm 街拍可以，**人像没 50mm 好看**\n- ❌ **不要买廉价 SD 卡**：4K 视频卡顿掉帧，必须 V30 以上\n\n## 🎯 6 个月后再加\n\n如果你拍出兴趣，半年后可加：\n1. 70-200mm 长焦（¥3000-5000）→ 演唱会/运动\n2. 闪光灯（¥500-1000）→ 室内人像\n3. 灯架+反光板（¥300）→ 棚拍",
                "product_cards": [
                    {"card_id": "mock_cam_001", "display_price": 4999.0, "reason": "索尼ZV-E10 II含16-50套头+APS-C+Vlog定位，摄影入门最优起点"},
                    {"card_id": "mock_cam_002", "display_price": 1599.0, "reason": "50mm F1.8人像虚化神器，套头无法替代的画质升级"},
                    {"card_id": "mock_cam_003", "display_price": 469.0, "reason": "思锐碳纤维1.2kg轻量+最高1.5m，外出携带降维打击铝合金"},
                    {"card_id": "mock_cam_004", "display_price": 159.0, "reason": "闪迪V30高速SD卡支持4K连拍不掉帧"},
                    {"card_id": "mock_cam_005", "display_price": 369.0, "reason": "国家地理单肩+防水帆布+装1机2镜+13寸笔记本"}
                ]
            }
        ],
        "final_response": "8000 摄影入门最优配置，**5 件 ¥7595，余 ¥405**：\n\n## 📷 完整方案\n\n| 类别 | 商品 | 价格 |\n|---|---|---|\n| 🥇 机身+套头 | **索尼 ZV-E10 II（含 16-50mm 套头）** | ¥4999 |\n| 定焦镜头 | **索尼 50mm F1.8 OSS（人像虚化）** | ¥1599 |\n| 三脚架 | **思锐碳纤维三脚架（1.2kg）** | ¥469 |\n| 存储卡 | **闪迪 Extreme Pro 128G V30** | ¥159 |\n| 摄影包 | **国家地理 NG W2161 单肩包** | ¥369 |\n| **合计** | | **¥7595**（余 405）|\n\n## 💡 为什么这样配\n\n### 1️⃣ 机身选 ZV-E10 II 而非全画幅入门 A7C\n¥4999 vs ¥10000+，APS-C 画质对入门完全够用，**省下的钱买定焦头才是真正的画质提升**。\n\n### 2️⃣ 必须加 50mm F1.8 定焦\n套头 16-50mm 是变焦头，**光圈 F3.5-5.6 拍不出虚化**。50mm F1.8 是「人像虚化神器」，¥1599 性价比之王。\n\n### 3️⃣ 三脚架碳纤维不要铝合金\n碳纤维 1.2kg vs 铝合金 2kg，外出携带差距巨大。\n\n## 💰 余 ¥405 可加\n\n按优先级：\n1. **UV 镜+CPL 偏振镜**（¥150-300）：保护镜头 + 拍风景压反光\n2. **快门遥控器**（¥80）：长曝光/自拍刚需\n3. **清洁套装**（¥50）：擦镜布+气吹+清洁笔\n\n## ⚠️ 新手避坑\n\n- ❌ **不要买二手镜头**：可能有霉斑入灰（看不出来）\n- ❌ **不要买 35mm 1.8 而不是 50mm**：35mm 街拍可以，**人像没 50mm 好看**\n- ❌ **不要买廉价 SD 卡**：4K 视频卡顿掉帧，必须 V30 以上\n\n## 🎯 6 个月后再加\n\n如果你拍出兴趣，半年后可加：\n1. 70-200mm 长焦（¥3000-5000）→ 演唱会/运动\n2. 闪光灯（¥500-1000）→ 室内人像\n3. 灯架+反光板（¥300）→ 棚拍",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # 109. repurchase - 复购化妆品+换季提醒
    {
        "trajectory_id": "sft_repurchase_004",
        "scenario_type": "repurchase",
        "category": "复购召回",
        "quality_label": "good",
        "training_focus": "复购防晒霜+换季产品升级建议",
        "user_query": "夏天到了，去年的防晒霜还能用吗，要不要再买一支",
        "thinking": "防晒霜复购：化妆品有保质期+夏季是高使用期。先查历史购买记录+判断保质期+推荐复购或升级。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "SkuRepurchaseRecall",
                "tool_input": {"category_keyword": "防晒霜", "time_range": "last_18_months"},
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_rep_004", "title": "安热沙金瓶 SPF50+ PA++++ 60ml (去年5月购买)", "price": 199.0, "is_platform_self": True, "rating": 4.9, "key_specs": "购买:2025-05-12/订单[ORDER_ID]/开封后12月保质期/已过期", "sales": "月销4.5万"},
                        {"product_id": "mock_rep_005", "title": "安热沙金瓶升级版 智能感肌 PA++++ 60ml(新款)", "price": 219.0, "is_platform_self": True, "rating": 4.9, "key_specs": "2026新款/智能感肌技术/同品牌升级版", "sales": "月销2.8万"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "**重要提醒：你去年 5 月买的防晒霜已经过保质期，必须扔掉**！\n\n## ⚠️ 保质期判断\n\n- **购买时间**：2025-05-12（订单 [ORDER_ID]）\n- **产品**：安热沙金瓶 60ml\n- **开封后保质期**：12 个月\n- **当前已使用**：约 13 个月 → **已过期 1 个月+**\n\n## 🚨 为什么必须扔\n\n过期防晒霜会**失效**：\n- SPF 防护值衰减 50% 以上\n- 化学防晒剂分解产生刺激物（可能引发过敏）\n- 油脂氧化变质（导致闷痘）\n\n## 🛒 推荐复购\n\n### 🥇 同款经典：**安热沙金瓶 ¥199**\n你已经用过 1 年没敏感，复购最稳。\n\n### 🥈 同品牌升级：**安热沙金瓶 2026 智能感肌版 ¥219**\n多 ¥20 升级到 2026 新款，**新增「智能感肌」技术**：遇汗水/油脂会变成更强防晒膜（户外党推荐）。\n\n## 💡 怎么选\n\n| 你的使用场景 | 推荐 |\n|---|---|\n| 日常上班通勤 | **经典款 ¥199**（够用） |\n| 户外/运动/海边度假 | **2026 升级款 ¥219**（出汗也防晒）|\n\n## 📝 这次买完记住\n\n1. **开封后写日期在瓶身**（防忘）\n2. **明年这个时候必须换新**\n3. 夏季 60ml 用 3-4 个月用完，**建议常备 2 瓶**（家里 + 包里各一）\n\n要直接帮你下单经典款还是升级款？",
                "product_cards": [
                    {"card_id": "mock_rep_005", "display_price": 219.0, "reason": "安热沙2026智能感肌升级版+多20元换新技术，户外党升级首选"},
                    {"card_id": "mock_rep_004", "display_price": 199.0, "reason": "安热沙金瓶经典款，你用过1年无敏感，日常通勤复购最稳"}
                ]
            }
        ],
        "final_response": "**重要提醒：你去年 5 月买的防晒霜已经过保质期，必须扔掉**！\n\n## ⚠️ 保质期判断\n\n- **购买时间**：2025-05-12（订单 [ORDER_ID]）\n- **产品**：安热沙金瓶 60ml\n- **开封后保质期**：12 个月\n- **当前已使用**：约 13 个月 → **已过期 1 个月+**\n\n## 🚨 为什么必须扔\n\n过期防晒霜会**失效**：\n- SPF 防护值衰减 50% 以上\n- 化学防晒剂分解产生刺激物（可能引发过敏）\n- 油脂氧化变质（导致闷痘）\n\n## 🛒 推荐复购\n\n### 🥇 同款经典：**安热沙金瓶 ¥199**\n你已经用过 1 年没敏感，复购最稳。\n\n### 🥈 同品牌升级：**安热沙金瓶 2026 智能感肌版 ¥219**\n多 ¥20 升级到 2026 新款，**新增「智能感肌」技术**：遇汗水/油脂会变成更强防晒膜（户外党推荐）。\n\n## 💡 怎么选\n\n| 你的使用场景 | 推荐 |\n|---|---|\n| 日常上班通勤 | **经典款 ¥199**（够用） |\n| 户外/运动/海边度假 | **2026 升级款 ¥219**（出汗也防晒）|\n\n## 📝 这次买完记住\n\n1. **开封后写日期在瓶身**（防忘）\n2. **明年这个时候必须换新**\n3. 夏季 60ml 用 3-4 个月用完，**建议常备 2 瓶**（家里 + 包里各一）\n\n要直接帮你下单经典款还是升级款？",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },

    # 110. place_order - 礼品下单+附加服务
    {
        "trajectory_id": "sft_order_005",
        "scenario_type": "place_order",
        "category": "购物下单",
        "quality_label": "good",
        "training_focus": "礼品下单：礼品包装+不放价签+发卡片+发到第三方地址",
        "user_query": "下单那个雅诗兰黛眼霜，送朋友的，要礼品包装别放价签，发到朋友家",
        "thinking": "礼品场景下单：4个附加要求(礼品包装/不放价签/送贺卡/送货到第三方)。逐个传给 ShoppingPlaceOrderTool。",
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": "ShoppingPlaceOrderTool",
                "tool_input": {
                    "product_id": "mock_eye_001",
                    "quantity": 1,
                    "address": "FRIEND_ADDRESS",
                    "gift_options": {
                        "gift_wrap": True,
                        "hide_price_tag": True,
                        "include_card": True,
                        "card_message": "（待用户回复）"
                    }
                },
                "tool_output": {
                    "status": "SUCCESS",
                    "products": [
                        {"product_id": "mock_eye_001", "title": "雅诗兰黛小棕瓶眼霜 15ml", "price": 499.0, "is_platform_self": True, "rating": 4.9, "key_specs": "订单[ORDER_ID]/已勾选礼品包装+隐藏价签+附贺卡+寄朋友地址", "sales": "—"}
                    ]
                },
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": "✅ 礼品订单已下，但**贺卡内容还需要你提供**：\n\n## 📦 订单详情\n\n- **订单号**：[ORDER_ID]\n- **商品**：雅诗兰黛小棕瓶眼霜 15ml ¥499\n- **收货人**：朋友地址（请确认朋友姓名+手机+地址正确）\n\n## 🎁 礼品服务（已勾选）\n\n- ✅ **礼品包装**：购物平台官方礼盒+丝带（免费）\n- ✅ **隐藏价签**：商品发票寄到你本人邮箱，朋友收到的包装内**不含价格信息**\n- ✅ **附赠贺卡**：购物平台精美贺卡 1 张（免费）\n- ✅ **寄送至朋友地址**：购物平台物流直送，不经你转交\n\n## ✍️ 还差贺卡内容\n\n请回复你想写的贺卡话（系统会**手写体打印**在贺卡上）：\n\n**模板可选**：\n1. **生日类**：「生日快乐，祝你眼角永远年轻 ❤️」\n2. **节日类**：「妇女节快乐，请你做永远的少女」\n3. **感谢类**：「谢谢你一直以来的陪伴，这份心意请收下」\n4. **自由发挥**：你直接告诉我想写啥\n\n回复贺卡内容后，订单自动进入打包流程，**明天朋友就能收到**。\n\n## 💡 贴心提醒\n\n- 朋友收到后**不会知道价格**\n- 如果朋友想退货，需要联系**购物平台客服**（不是你处理）\n- 平台自营礼品包装不收费，第三方店铺一般会收 ¥5-15 包装费",
                "product_cards": [
                    {"card_id": "mock_eye_001", "display_price": 499.0, "reason": "已下单+礼品包装+隐藏价签+附贺卡，购物平台物流直送朋友地址明日达"}
                ]
            }
        ],
        "final_response": "✅ 礼品订单已下，但**贺卡内容还需要你提供**：\n\n## 📦 订单详情\n\n- **订单号**：[ORDER_ID]\n- **商品**：雅诗兰黛小棕瓶眼霜 15ml ¥499\n- **收货人**：朋友地址（请确认朋友姓名+手机+地址正确）\n\n## 🎁 礼品服务（已勾选）\n\n- ✅ **礼品包装**：购物平台官方礼盒+丝带（免费）\n- ✅ **隐藏价签**：商品发票寄到你本人邮箱，朋友收到的包装内**不含价格信息**\n- ✅ **附赠贺卡**：购物平台精美贺卡 1 张（免费）\n- ✅ **寄送至朋友地址**：购物平台物流直送，不经你转交\n\n## ✍️ 还差贺卡内容\n\n请回复你想写的贺卡话（系统会**手写体打印**在贺卡上）：\n\n**模板可选**：\n1. **生日类**：「生日快乐，祝你眼角永远年轻 ❤️」\n2. **节日类**：「妇女节快乐，请你做永远的少女」\n3. **感谢类**：「谢谢你一直以来的陪伴，这份心意请收下」\n4. **自由发挥**：你直接告诉我想写啥\n\n回复贺卡内容后，订单自动进入打包流程，**明天朋友就能收到**。\n\n## 💡 贴心提醒\n\n- 朋友收到后**不会知道价格**\n- 如果朋友想退货，需要联系**购物平台客服**（不是你处理）\n- 平台自营礼品包装不收费，第三方店铺一般会收 ¥5-15 包装费",
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    },
]


def main():
    print(f"准备追加 {len(T)} 条到 {OUTPUT_PATH}...")
    from collections import Counter
    sc = Counter(t["scenario_type"] for t in T)
    for t in T:
        print(f"  ✨ {t['trajectory_id']:<22} [{t['scenario_type']}] {t.get('training_focus','')[:55]}")
    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for t in T:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"\n✅ 追加 {len(T)} 条 | 分布: {dict(sc)}")
    with open(OUTPUT_PATH) as f:
        total = sum(1 for _ in f)
    print(f"   总计: {total} 条")


if __name__ == "__main__":
    main()
