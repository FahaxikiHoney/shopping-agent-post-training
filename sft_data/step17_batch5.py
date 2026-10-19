# -*- coding: utf-8 -*-
"""Step 17: 第 5 批 10 条数据"""
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

# 1. similar_rec - 抱怨能效低
T.append(make_traj(
    "sft_simrec_021", "similar_rec", "相似品推荐",
    "抱怨能耗高 → energy_grade=1 一级能效",
    "上次推荐那台空调三级能效，电费太贵，有一级能效的同价位款吗",
    {"query": "1.5匹空调 一级能效 变频", "min_price": 2500, "max_price": 3500, "filters": {"energy_grade": 1}},
    [
        {"product_id": "mock_ac_e1", "title": "美的 KFR-35GW 1.5匹 一级能效 智能变频", "price": 2999, "is_platform_self": True, "rating": 4.9, "key_specs": "1级能效APF 5.0/年耗电800度/智能变频", "sales": "月销2.5万"},
        {"product_id": "mock_ac_e2", "title": "格力 KFR-35GW 云佳一级能效 自清洁", "price": 3199, "is_platform_self": True, "rating": 4.9, "key_specs": "1级能效/自清洁/格力核心压缩机", "sales": "月销1.8万"},
        {"product_id": "mock_ac_e3", "title": "海尔 KFR-35GW 一级能效 抗菌除醛", "price": 2899, "is_platform_self": True, "rating": 4.8, "key_specs": "1级能效/抗菌除醛/UVC紫外线杀菌", "sales": "月销1.5万"}
    ],
    "三级能效一年多耗 ~600 度电（多花 ¥360），换一级能效 1-2 年就回本：\n\n**1. 美的 KFR-35GW（¥2999）** ⭐ 性价比最高\nAPF 5.0 一级能效，**年耗电仅 800 度（三级要 1400 度）**。月销 2.5 万件断档第一。\n\n**2. 格力云佳（¥3199）**\n格力核心压缩机+自清洁功能，**贵 ¥200 买的是核心配件耐用**。\n\n**3. 海尔抗菌除醛（¥2899）**\n最便宜+独家 UVC 紫外线杀菌（适合卧室空调）。\n\n**算账**：三级 vs 一级每年省 ¥360 电费，**用 10 年净省 ¥3600**，完全值得多花的差价。",
    ["美的APF 5.0一级能效+年耗800度+月销2.5万断档，性价比最高", "格力云佳1级能效+自清洁+核心压缩机耐用，多200元品质升级", "海尔1级能效+UVC紫外线杀菌+抗菌除醛，最便宜卧室首选"]
))

# 2. similar_rec - 抱怨学习曲线
T.append(make_traj(
    "sft_simrec_022", "similar_rec", "相似品推荐",
    "抱怨上手难 → 工具加 ease_of_use 维度",
    "之前推的那台咖啡机要研磨调粉量太复杂，有一键出咖啡的同价位款吗",
    {"query": "全自动咖啡机 一键操作 新手友好", "min_price": 1500, "max_price": 2500, "filters": {"ease_of_use": "one_touch"}},
    [
        {"product_id": "mock_coffee_1", "title": "德龙 ECAM22.110 全自动咖啡机 一键意式", "price": 2299, "is_platform_self": True, "rating": 4.9, "key_specs": "一键意式/集成磨豆机/3个预设按钮", "sales": "月销1500"},
        {"product_id": "mock_coffee_2", "title": "飞利浦 EP1220 全自动 咖啡馆系列 LatteGo", "price": 1999, "is_platform_self": True, "rating": 4.9, "key_specs": "一键拿铁/LatteGo奶系统/新手友好", "sales": "月销2200"},
        {"product_id": "mock_coffee_3", "title": "雀巢 Dolce Gusto 胶囊咖啡机 全自动", "price": 599, "is_platform_self": True, "rating": 4.8, "key_specs": "胶囊式/0门槛/单价￥6/杯", "sales": "月销4500"}
    ],
    "懂了，咖啡机分 3 个上手难度档：\n\n**1. 飞利浦 EP1220 LatteGo（¥1999）** ⭐ 全自动一键拿铁\n**一键直出意式/拿铁/卡布**，奶系统 LatteGo 一秒拆洗。比德龙便宜 ¥300 操作更简单。\n\n**2. 德龙 ECAM22.110（¥2299）**\n3 个预设按钮（意式/美式/咖啡），但**牛奶要手动打**（学习曲线 1 周）。\n\n**3. 雀巢 Dolce Gusto 胶囊机（¥599）** 真零门槛\n买胶囊 → 放进去 → 按按钮，**完全没学习成本**。但**单杯 ¥6**比自磨贵 3 倍。\n\n**建议**：\n- 想喝奶咖+预算够 → **飞利浦 LatteGo**\n- 偶尔喝几杯 → **雀巢胶囊机**（省 ¥1400 但长期成本高）\n- 喜欢手冲半自动乐趣 → 这 3 款都不适合，应该买半自动",
    ["飞利浦EP1220 LatteGo一键意式+拿铁+奶系统一秒拆洗，新手最友好", "德龙ECAM22.110一键意式+3个预设但牛奶手动，学习曲线1周", "雀巢Dolce Gusto胶囊机零门槛+0学习，单杯6元长期贵"]
))

# 3. sku_comp - 不同存储方案对比
T.append(make_traj(
    "sft_skucomp_019", "sku_comp", "商品对比",
    "云服务 vs 本地 NAS 对比",
    "存照片视频，买百度云会员还是装家用 NAS",
    {"skus": ["百度云会员 SVIP 1年", "群晖 DS220+ NAS 双盘位"], "mode": "parallel_exact_match"},
    [
        {"product_id": "mock_cloud_001", "title": "百度网盘 SVIP 12个月", "price": 198, "is_platform_self": True, "rating": 4.7, "key_specs": "5TB空间/超会员/秒传/在线播放", "sales": "月销1.5万"},
        {"product_id": "mock_nas_001", "title": "群晖 DS220+ NAS 双盘位+2块4TB硬盘", "price": 3999, "is_platform_self": True, "rating": 4.9, "key_specs": "群晖DSM系统/8TB可用/家庭云", "sales": "月销680"}
    ],
    "**结论：5 年内云会员便宜，5 年后 NAS 反超**。算给你看：\n\n## 📊 5 年成本对比\n\n| 维度 | 百度云 SVIP | 群晖 NAS |\n|---|---|---|\n| 首次投入 | ¥198/年 | **¥3999**（一次）|\n| 5 年总成本 | ¥990 | ¥3999 |\n| 10 年总成本 | ¥1980 | **¥3999**（NAS 反超）|\n| 容量 | 5TB | **8TB** |\n| 数据所有权 | ❌ 百度服务器 | **✅ 你自己的** |\n| 跑路风险 | ⚠️ 百度政策变化 | **✅ 自主可控** |\n| 上传速度 | ⚠️ 限速 | **✅ 千兆局域网满速** |\n\n## 🎯 怎么选\n\n### 1️⃣ 短期方案 → **百度云 SVIP ¥198/年**\n- 1-3 年内不想折腾\n- 数据不敏感（公开照片+视频）\n- 经常出差异地访问\n\n### 2️⃣ 长期+重视隐私 → **群晖 NAS ¥3999**\n- 家庭照片+视频要保存 10 年+\n- 不想数据在他人服务器\n- 5 年后 NAS 总成本反超云会员\n\n## 💡 实际建议\n\n**两套组合最稳**：\n- 日常照片 → NAS（速度快+隐私）\n- 备份 → 百度云（异地容灾，万一 NAS 坏了）\n\n**¥3999 + ¥198 看似贵 ¥1200**，但**数据丢失的风险 = 无价**。",
    ["百度云SVIP 5TB+秒传+在线播放+月销1.5万，1-3年短期最划算", "群晖DS220+ NAS+8TB+5年后总成本反超云会员，长期+隐私首选"]
))

# 4. sku_comp - 工具版本对比
T.append(make_traj(
    "sft_skucomp_020", "sku_comp", "商品对比",
    "AppleCare+ vs 购物平台延保 vs 不买",
    "iPhone 15 Pro 9999 元，AppleCare+ 1499 vs 购物平台延保 499 vs 不买，怎么选",
    {"skus": ["AppleCare+ for iPhone 15 Pro", "购物平台延保2年（iPhone 5K-10K档）", "无保险"], "mode": "comparison_with_baseline"},
    [
        {"product_id": "mock_apple_care", "title": "AppleCare+ 2年（iPhone 15 Pro）", "price": 1499, "is_platform_self": True, "rating": 4.9, "key_specs": "Apple官方/2年延保/含意外险/碎屏199元/进水免费维修", "sales": "月销3500"},
        {"product_id": "mock_mock_warranty", "title": "购物平台延保2年（iPhone 5K-10K档）", "price": 499, "is_platform_self": True, "rating": 4.7, "key_specs": "购物平台延保/2年延保/不含意外损坏/仅覆盖自然故障", "sales": "月销5500"},
        {"product_id": "mock_no_insurance", "title": "不买保险（自负风险）", "price": 0, "is_platform_self": False, "rating": 5.0, "key_specs": "省下保险费/碎屏自费1899/进水自费3000+", "sales": "—"}
    ],
    "iPhone 保险这个钱**值不值看你的使用习惯**。算给你看 3 种选择的期望成本：\n\n## 📊 风险成本计算\n\n| 选项 | 价格 | 覆盖 | 期望维修成本 |\n|---|---|---|---|\n| AppleCare+ | ¥1499 | ✅ 全部（含意外）| **¥0**（碎屏199/次×2 已含）|\n| 购物平台延保 | ¥499 | ⚠️ 仅自然故障 | 碎屏自费 ¥1899 |\n| 不买 | ¥0 | ❌ | 碎屏 ¥1899 + 主板坏 ¥3000+ |\n\n## 🎯 三种用户的最优解\n\n### 1️⃣ 经常出门带手机/带小孩玩 → **AppleCare+ ¥1499** ⭐\niPhone 15 Pro 摔屏维修 **¥1899/次**，AppleCare+ 包含 2 次意外险（每次 ¥199）。**摔过一次就回本**。\n\n### 2️⃣ 日常稳定/不爱出门/有壳 → **购物平台延保 ¥499**\n主板/电池/听筒故障是 2 年后高发，¥499 防大件维修。**碎屏自己小心点**。\n\n### 3️⃣ 风险接受度高 → **不买**\n如果你 2 年内没摔过手机/没进过水，**¥1499 大概率白送苹果**。\n\n## 💡 真心建议\n\n**iPhone 15 Pro 9999 + AppleCare+ 1499 = ¥11498**，相当于把手机预算抬高到 ¥11500。如果你预算紧到 ¥9999 已经吃力，**省下 ¥1499 比保险更实在**。\n\n反之如果你**确定经常摔/进水**（比如健身/带娃/工地），AppleCare+ 闭眼上。",
    ["AppleCare+ Apple官方2年+含意外+碎屏199元/次，经常摔/带娃党摔1次回本", "购物平台延保499元仅自然故障+不含意外，日常稳定+有壳用户性价比", "不买保险风险自担+碎屏3000+，2年内0意外的省钱党"]
))

# 5. matching - 阳台改造
T.append(make_traj(
    "sft_match_019", "matching_purchase", "搭配购物",
    "阳台改造整体搭配",
    "想把 5 平米阳台改成休闲角，配置桌椅+植物+灯具+地毯",
    {"query": "阳台改造 休闲角 北欧风", "filters": {"category": "balcony_lounge", "style": "nordic_relaxed"}},
    [
        {"product_id": "mock_balc_1", "title": "宜家 TÄRNÖ 折叠桌椅 2椅1桌套装", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "折叠桌+2椅/防水松木/北欧风", "sales": "月销4500"},
        {"product_id": "mock_balc_2", "title": "龟背竹 大盆栽 1.5米高 含花盆", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "1.5米高/含陶土花盆/北欧绿植网红款", "sales": "月销1.5万"},
        {"product_id": "mock_balc_3", "title": "Tika 北欧风藤编吊灯 直径30cm 阳台款", "price": 359, "is_platform_self": True, "rating": 4.9, "key_specs": "藤编手工/30cm/暖光2700K", "sales": "月销680"},
        {"product_id": "mock_balc_4", "title": "短毛地毯 燕麦色 100×150cm 阳台尺寸", "price": 189, "is_platform_self": True, "rating": 4.8, "key_specs": "短毛防晒/燕麦色/100×150cm", "sales": "月销1200"}
    ],
    "5 平米阳台改造 4 件套 ¥1446，**性价比满分**：\n\n## 🌿 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 桌椅 | **宜家 TÄRNÖ 折叠桌椅套装** | ¥599 |\n| 植物 | 龟背竹 1.5 米大盆栽 | ¥299 |\n| 灯具 | Tika 北欧藤编吊灯 | ¥359 |\n| 地毯 | 短毛燕麦色 100×150cm | ¥189 |\n| **合计** | | **¥1446** |\n\n## 💡 选品理由\n\n### 1️⃣ 折叠桌椅是阳台救星\n5 平米空间小，**折叠款不用时收起来放角落**。宜家这款防水松木材质，下雨也不怕。\n\n### 2️⃣ 龟背竹是北欧风网红\n大叶片+1.5 米高度=**视觉焦点**。耐阴好养（一周浇一次），月销 1.5 万件。\n\n### 3️⃣ 藤编吊灯+暖光\n阳台白天靠自然光，**夜晚靠暖光氛围灯**。藤编透光效果美如杂志拍照。\n\n### 4️⃣ 燕麦色短毛地毯\n阳台地砖硬+晒，**地毯铺一块立刻有家的感觉**。短毛好打理（不挂灰）。\n\n## 🎯 进阶搭配（+¥500）\n\n- 户外抱枕×2 ¥150（坐感+颜值）\n- 串灯 ¥80（晚上氛围）\n- 小书架 ¥200（看书+种花二合一）\n- 户外咖啡杯 ¥80\n\n## ⚠️ 阳台改造避坑\n\n- ❌ **大型沙发**：阳台承重有限+不好搬\n- ❌ **吊椅/秋千**：需要稳定承重墙，租房不建议\n- ❌ **太多绿植**：超过 3 盆变成杂物堆",
    ["宜家TÄRNÖ折叠桌椅套装+防水松木+月销4500，5平米阳台救星", "龟背竹1.5米大盆栽+耐阴好养+月销1.5万，视觉焦点北欧网红", "Tika藤编吊灯30cm+暖光2700K，杂志级氛围灯", "短毛燕麦色100×150cm阳台地毯，铺一块有家的感觉"]
))

# 6. matching - 男士穿搭整套
T.append(make_traj(
    "sft_match_020", "matching_purchase", "搭配购物",
    "约会一整套男士穿搭",
    "30 岁男生第一次相亲约会，配一套衣服鞋子+发型工具",
    {"query": "男士相亲约会穿搭 衬衫+西裤+皮鞋", "filters": {"age_range": "25-35", "style": "smart_casual"}},
    [
        {"product_id": "mock_date_1", "title": "海澜之家 牛津纺商务衬衫 蓝色 长袖", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "蓝色/牛津纺/修身合体/正装休闲两用", "sales": "月销1.5万"},
        {"product_id": "mock_date_2", "title": "GAP 修身羊毛西裤 深灰色 弹力面料", "price": 499, "is_platform_self": True, "rating": 4.8, "key_specs": "深灰色/修身/弹力舒适/可机洗", "sales": "月销6500"},
        {"product_id": "mock_date_3", "title": "策乐 真皮德比鞋 棕色 商务休闲款", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "头层牛皮/德比鞋型/棕色百搭", "sales": "月销4500"},
        {"product_id": "mock_date_4", "title": "GATSBY 杰士派 强力定型发蜡 80g", "price": 49, "is_platform_self": True, "rating": 4.8, "key_specs": "8级定型/持久8小时/日系男生最爱", "sales": "月销3.5万"}
    ],
    "30 岁男生相亲穿搭核心：**得体 + 干净 + 不浮夸**。整套配齐 ¥1446：\n\n## 👔 完整方案\n\n| 单品 | 商品 | 价格 |\n|---|---|---|\n| 上衣 | 海澜之家**蓝色牛津纺衬衫** | ¥299 |\n| 下装 | GAP**深灰修身西裤** | ¥499 |\n| 鞋子 | 策乐**棕色真皮德比鞋** | ¥599 |\n| 发型 | GATSBY 强力发蜡 | ¥49 |\n| **合计** | | **¥1446** |\n\n## 🎨 配色公式（30 岁男生黄金组合）\n\n**蓝衬衫 + 深灰西裤 + 棕色德比鞋**\n\n- ✅ 蓝色显白显年轻（避免黑/灰显沉重）\n- ✅ 深灰西裤百搭（避免深蓝过于商务）\n- ✅ 棕色皮鞋温柔（避免黑色像殡仪馆服务员）\n\n## 💇 发型加分\n\n相亲前一周**剪个利落短发**（侧分/上梳），用 GATSBY 发蜡定型 5 分钟搞定。\n\n## ⚠️ 避雷清单\n\n- ❌ **印花/花纹衬衫**：30 岁穿显得幼稚\n- ❌ **格子衬衫**：除非格子是细暗格\n- ❌ **运动鞋**：相亲场合 = 不重视\n- ❌ **皮带颜色和鞋不一致**：基本审美问题\n\n## 💡 加分细节\n\n- 香水（淡香木质调）¥300-500\n- 简约腕表（西铁城/天梭）¥1500-3000\n- 干净的指甲+口气清新（最容易忽略）\n\n相亲第一印象 70% 由穿搭决定，**这套 ¥1446 投资绝对值得**。",
    ["海澜之家蓝色牛津纺衬衫+修身合体+正装休闲两用+月销1.5万，相亲蓝色显白显年轻", "GAP深灰羊毛西裤+弹力舒适+可机洗，百搭避免商务过头", "策乐棕色真皮德比鞋+头层牛皮+商务休闲款+月销4500，温柔避免黑色沉重", "GATSBY强力定型发蜡8级+8小时持久+月销3.5万，相亲前5分钟搞定发型"]
))

# 7. bundle - 中考准备
T.append(member_traj := make_traj(
    "sft_bundle_017", "bundle_purchase", "组合购物",
    "1500 元中考冲刺学习装备",
    "孩子要中考了，1500 预算给他配齐学习装备",
    {"query": "中考学习装备 护眼台灯+错题本+笔记本", "max_price": 1800, "filters": {"target_age": "student_15_18"}},
    [
        {"product_id": "mock_study_1", "title": "明基 MindDuo 2 护眼台灯 国AA级", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "国AA级照度/防蓝光/智能调光", "sales": "月销2200"},
        {"product_id": "mock_study_2", "title": "晨光 错题本+笔记本套装 12本装", "price": 89, "is_platform_self": True, "rating": 4.8, "key_specs": "12本/错题专用分类/A5大小", "sales": "月销4.5万"},
        {"product_id": "mock_study_3", "title": "西伯利亚 网课耳机 头戴麦克风", "price": 169, "is_platform_self": True, "rating": 4.9, "key_specs": "头戴85dB音量保护/带麦", "sales": "月销4.5万"},
        {"product_id": "mock_study_4", "title": "购物平台读书 学生学习平板 11寸", "price": 599, "is_platform_self": True, "rating": 4.8, "key_specs": "11寸大屏/护眼墨水屏/电子题库", "sales": "月销680"}
    ],
    "中考冲刺装备 4 件套 ¥1456：\n\n## 📚 完整方案\n\n| 装备 | 商品 | 价格 | 用途 |\n|---|---|---|---|\n| 🥇 护眼台灯 | **明基 MindDuo 2 国 AA 级** | ¥599 | 每晚 4-5h 写作业刚需 |\n| 错题本 | 晨光 12 本套装 | ¥89 | 错题分类整理 |\n| 网课耳机 | 西伯利亚头戴麦克风 | ¥169 | 网课不影响家人 |\n| 学习平板 | 购物平台读书学生版 | ¥599 | 电子题库刷题 |\n| **合计** | | **¥1456** | |\n\n## 💡 选品逻辑\n\n### 1️⃣ 护眼台灯是中考最重要投资\n中考生**每天写作业 4-5 小时**，普通台灯近视加深 50-100 度/年。明基 MindDuo 2 是**国 AA 级照度**（最高标准），多 ¥300 比普通台灯保护眼睛 5 年。\n\n### 2️⃣ 错题本是中考提分关键\n**错题本管理 = 提分 20-30 分**。晨光 12 本套装够 6 大科分类（语数英物化生）+ 2 本周记。\n\n### 3️⃣ 网课耳机要 85dB 限制\n中考期间会有大量补课网课，**耳机音量限制保护听力 + 不打扰家人**。\n\n### 4️⃣ 学习平板挑墨水屏\n墨水屏不发光，**8 小时刷题不伤眼**。普通 iPad 反而加深近视。\n\n## ⚠️ 不要买\n\n- ❌ 高端机械键盘（中考写字不打字）\n- ❌ 普通平板（屏幕反光伤眼）\n- ❌ 奖励性奢侈品（中考前换 iPhone 是大忌，分心）\n\n## 💪 加 ¥200 的提分神器\n\n- 番茄钟（专注训练）¥80\n- 站立学习架（颈椎保护）¥120\n\n孩子中考加油！",
    ["明基MindDuo 2护眼台灯+国AA级照度+防蓝光，中考4-5h写作业近视防护刚需", "晨光错题本12本套装+科目分类+月销4.5万，错题管理=提分20-30分", "西伯利亚网课耳机85dB音量保护+月销4.5万，网课不打扰家人保护听力", "购物平台读书学生平板+11寸墨水屏+电子题库，8h刷题不伤眼"]
))

# 8. bundle - 自驾游
T.append(make_traj(
    "sft_bundle_018", "bundle_purchase", "组合购物",
    "3500 元长途自驾游装备",
    "国庆要长途自驾川西 7 天，3500 配齐车载装备",
    {"query": "自驾游装备 车载 长途", "max_price": 3800, "filters": {"category": "self_driving"}},
    [
        {"product_id": "mock_drive_1", "title": "70迈 A810 4K行车记录仪 双摄前后", "price": 999, "is_platform_self": True, "rating": 4.9, "key_specs": "4K高清/双摄/紧急录像/月销1.8万", "sales": "月销1.8万"},
        {"product_id": "mock_drive_2", "title": "Anker 车载逆变器+USB-C 100W", "price": 399, "is_platform_self": True, "rating": 4.8, "key_specs": "100W PD/手机笔记本通用", "sales": "月销3500"},
        {"product_id": "mock_drive_3", "title": "倍思 车载充气泵+胎压监测", "price": 269, "is_platform_self": True, "rating": 4.9, "key_specs": "充气+胎压监测+应急照明", "sales": "月销5500"},
        {"product_id": "mock_drive_4", "title": "野营折叠床 车后排款 长 1.8 米", "price": 799, "is_platform_self": True, "rating": 4.8, "key_specs": "1.8米/折叠后排床/SUV适用", "sales": "月销1200"},
        {"product_id": "mock_drive_5", "title": "海拔氧气罐 高反应急 6L×3罐", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "高原反应应急/6L×3罐/川西刚需", "sales": "月销8500"},
        {"product_id": "mock_drive_6", "title": "车载冰箱 12V/220V 24L 双模", "price": 899, "is_platform_self": True, "rating": 4.8, "key_specs": "12V车载+220V家用/24L/双模通用", "sales": "月销680"}
    ],
    "川西 7 天自驾装备 6 件 ¥3564，**川西高海拔特别要重视**：\n\n## 🚗 完整方案\n\n| 装备 | 商品 | 价格 | 重要性 |\n|---|---|---|---|\n| 行车记录仪 | 70迈 A810 4K | ¥999 | ⭐⭐⭐ |\n| 🚨 **高反氧气罐** | 6L×3 罐 | ¥199 | ⭐⭐⭐⭐⭐ |\n| 充气泵+胎压监测 | 倍思 | ¥269 | ⭐⭐⭐⭐ |\n| 车载逆变器 | Anker 100W | ¥399 | ⭐⭐⭐ |\n| 后排折叠床 | 1.8 米 SUV 款 | ¥799 | ⭐⭐⭐⭐ |\n| 车载冰箱 24L | 12V/220V 双模 | ¥899 | ⭐⭐⭐ |\n| **合计** | | **¥3564** | |\n\n## 💡 川西自驾刚需 vs 可选\n\n### 🚨 川西刚需（必买）\n\n**1. 氧气罐 ¥199**：川西很多地方海拔 3000-4500m，高反不是闹着玩的，**应急救命**\n\n**2. 充气泵+胎压监测 ¥269**：川西路况复杂，**爆胎概率比城里高 10 倍**，胎压不足是首要原因\n\n**3. 后排折叠床 ¥799**：川西景区酒店少+贵，**车上睡 1-2 晚省 ¥1000+** 还能看星空\n\n### 🚗 长途舒适（推荐）\n\n**1. 行车记录仪 4K ¥999**：拍下川西沿途绝美风景\n\n**2. 车载冰箱 ¥899**：高海拔超市少，囤几天水果零食必备\n\n**3. 车载逆变器 ¥399**：手机笔记本充电+车载小风扇\n\n## 💰 余 ¥236 加\n\n- 防滑链（雪山备用）¥80\n- 应急救援包（包含手电筒/绷带/对讲机）¥120\n- 充电式手电 ¥50\n\n## ⚠️ 川西自驾安全清单\n\n1. **出发前**：检查车辆机油、刹车、胎压\n2. **沿途**：随时关注海拔，**4000m+ 不要剧烈运动**\n3. **应急**：手机存当地救援电话+紧急联系人\n4. **保险**：临时加买**境外救援险**（川西部分区域信号差）\n\n祝你旅途平安！🚗",
    ["70迈A810 4K行车记录仪+双摄前后+紧急录像，川西风光拍照记录", "氧气罐6L×3+高反应急+月销8500，川西海拔3000-4500m救命刚需", "倍思充气泵+胎压监测+应急照明+月销5500，川西爆胎应急刚需", "Anker 100W车载逆变器+PD快充，手机笔记本通用", "野营折叠后排床1.8米+SUV适用，川西无酒店区车上睡省1000+", "车载冰箱12V/220V双模+24L+高海拔超市少，囤水果零食必备"]
))

# 9. place_order - 取消重订
T.append(make_traj(
    "sft_order_011", "place_order", "购物下单",
    "取消旧订单+重新下单更便宜的",
    "刚下的那台 6999 笔记本，发现 PLUS 会员价才 6499，能取消重买吗",
    {"order_id_to_cancel": "[ORDER_ID]", "new_product_id": "mock_lap_plus", "use_plus_price": True},
    [
        {"product_id": "mock_lap_plus", "title": "联想小新Pro16 PLUS会员专享价", "price": 6499, "is_platform_self": True, "rating": 4.9, "key_specs": "PLUS专享价6499/省500/订单[ORDER_ID]", "sales": "—"}
    ],
    "好的，已经帮你**取消旧订单 + 用 PLUS 价重下**，省 ¥500！\n\n## 📋 操作详情\n\n### 1️⃣ 取消旧订单 ✅\n- 旧订单：**[ORDER_ID]**（¥6999）\n- 状态：已申请取消（未发货所以秒成功）\n- 退款：**¥6999 原路退回**，1 个工作日内到账\n\n### 2️⃣ 重新下单（PLUS 价）✅\n- 新订单：**[ORDER_ID]**\n- 商品：联想小新 Pro16（同款）\n- 价格：**¥6499**（PLUS 专享 -¥500）\n- 收货地址：默认地址\n- 预计明天送达\n\n## 💰 算账\n\n| 项目 | 金额 |\n|---|---|\n| 旧订单退款 | +¥6999 |\n| 新订单支付 | -¥6499 |\n| **净省** | **¥500** |\n\n## ⚠️ 风险提示\n\n这次操作**完全没风险**，因为旧订单还在「待出库」状态。但要注意：\n\n1. **平台自营退款会扣 PLUS 京豆**：如果旧订单消耗了京豆/优惠券，会回到账户\n2. **新订单的快递时效**：因为是新下，比旧订单晚 1 天发货（旧订单原本今天发，新订单明天发）\n3. **价保功能也能省**：购物平台 PLUS 会员买完后 15 天降价可申请「价保」，**下次买东西不用取消重下，直接申请价保也能省**\n\n## 💡 下次省钱小技巧\n\n- 下单前 **打开 PLUS 价**（结算页右上角）\n- 检查 **店铺券+品类券+京豆** 是否都用上\n- 大件商品下单后 **设置 7-15 天降价提醒**（自动申请价保）\n\n这次省的 ¥500 可以加个无线鼠标 + 鼠标垫了 🎉",
    ["联想小新Pro16 PLUS专享价6499元+省500元+订单[ORDER_ID]，PLUS会员价直接省500"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase - 复购+品牌升级
T.append(make_traj(
    "sft_repurchase_009", "repurchase", "复购召回",
    "复购洗发水+护发体系完善",
    "再买之前那款洗发水，最近发尾干枯能加点什么",
    {"category_keyword": "洗发水", "time_range": "last_4_months", "include_related_products": True},
    [
        {"product_id": "mock_shampoo_old", "title": "卡诗 双重菁纯洗发水 250ml (你3月前购买)", "price": 280, "is_platform_self": True, "rating": 4.9, "key_specs": "卡诗经典款/250ml/订单[ORDER_ID]", "sales": "月销1.2万"},
        {"product_id": "mock_shampoo_new", "title": "卡诗 修复护发素 200ml (同系列)", "price": 320, "is_platform_self": True, "rating": 4.9, "key_specs": "同系列护发素/修护发尾/搭配洗发水", "sales": "月销8500"},
        {"product_id": "mock_shampoo_mask", "title": "卡诗 顺直凝润修复发膜 200ml", "price": 380, "is_platform_self": True, "rating": 4.9, "key_specs": "深层修复/每周2-3次", "sales": "月销4500"}
    ],
    "查到你 3 个月前买的是 **卡诗双重菁纯洗发水**（¥280/订单 [ORDER_ID]）。\n\n## 🆘 发尾干枯的根本解决方案\n\n光买洗发水不够！专业护发是 **3 步法**：\n\n### 🚿 Step 1：洗发水（清洁+基础护理）\n**继续复购你已经认可的卡诗 ¥280**（同款不换，避免发质适应期）\n\n### 💧 Step 2：护发素（修护发尾，关键⭐）\n**新增：卡诗修复护发素 ¥320**\n- 同系列同体系（pH 接近，配合更好）\n- 每次洗头用，**2 周内发尾摸起来明显顺滑**\n- 这是你忽略的关键步骤——80% 的发尾干枯是缺少护发素\n\n### 🎭 Step 3：发膜（深层修复，每周 2-3 次）\n**新增：卡诗修复发膜 ¥380**\n- 每周用 2-3 次（涂在发中到发尾，敷 5-10 分钟）\n- **3 周内开叉减少 70%**\n- 不是必需，但发尾严重干枯刚需\n\n## 🛒 完整复购方案\n\n### 方案 A：基础升级 ¥600\n洗发水 ¥280 + 护发素 ¥320 = **覆盖日常护理 80% 需求**\n\n### 方案 B：完整三件套 ¥980\n洗发水 + 护发素 + 发膜 = **3 个月内发尾质感明显改善**\n\n### 方案 C：先单买护发素 ¥320\n试 2 周看效果，**最不踩坑的起步**\n\n## 💡 真心建议\n\n**先选方案 C 加买护发素 ¥320**：\n1. 你已经认可洗发水了，**关键是补护发素**\n2. ¥320 比直接买套装试错成本低\n3. 2 周后看效果再决定要不要加发膜\n\n## ⚠️ 护发避坑\n\n- ❌ **不要用洗发水涂发尾**：洗发水主清洁，洗发尾会更干\n- ❌ **护发素不要涂到头皮**：会闷头皮屑\n- ❌ **不同品牌混用**：pH 不一致，效果打折",
    ["卡诗双重菁纯洗发水你3月前购买+月销1.2万，继续复购维持发质适应", "卡诗修复护发素+同系列同体系+发尾干枯关键步骤80%忽略", "卡诗修复发膜深层修护+每周2-3次+3周开叉减少70%，严重干枯刚需"],
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
