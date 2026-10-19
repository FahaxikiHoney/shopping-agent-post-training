# -*- coding: utf-8 -*-
"""Step 38: 第 26 批 10 条"""
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

# 1. similar_rec
T.append(make_traj(
    "sft_simrec_063", "similar_rec", "相似品推荐",
    "抱怨隔音差 → 推荐隔音效果好的同价位款",
    "买的那个蓝牙耳机隔音效果差，公交上根本用不了，换个主动降噪好的同价位",
    {"query": "蓝牙耳机 主动降噪 ANC 公交地铁", "max_price": 600, "filters": {"anc_db_min": 30}},
    [
        {"product_id": "jd_anc_good_1", "title": "漫步者 NeoBuds Pro 2 主动降噪 48dB", "price": 599, "is_jd_self": True, "rating": 4.8, "key_specs": "ANC 48dB/LDAC/10h续航/月销9800", "sales": "月销9800"},
        {"product_id": "jd_anc_good_2", "title": "倍思 Bowie M2s ANC 主动降噪 32dB", "price": 299, "is_jd_self": True, "rating": 4.8, "key_specs": "ANC 32dB/12h续航/月销2.5万/性价比强", "sales": "月销2.5万"},
        {"product_id": "jd_anc_good_3", "title": "Nothing Ear 2 ANC 主动降噪 40dB", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "ANC 40dB/透明外壳设计/Hi-Res/月销5500", "sales": "月销5500"}
    ],
    "没有 ANC（主动降噪）的耳机公交上完全不够用，3 款真正的降噪款：\n\n**1. 倍思 Bowie M2s（¥299）** ⭐ 性价比首选\n32dB 降噪，**¥299 是真 ANC 里最便宜**，月销 2.5 万。公交/地铁噪音完全够屏蔽。\n\n**2. Nothing Ear 2（¥599）**\n40dB 降噪+透明外壳设计，**颜值是这 3 款里最特别的**。Hi-Res 音质认证。\n\n**3. 漫步者 NeoBuds Pro 2（¥599）**\n48dB 是这 3 款里**最强降噪**，LDAC 高音质编码。音质党+降噪党。\n\n## 💡 ANC 降噪够不够用判断\n\n- 30dB：屏蔽 70% 噪音，公交够用\n- 40dB：屏蔽 85% 噪音，地铁够用\n- 60dB+（Sony XM5 级）：屏蔽 95%，飞机够用\n\n¥299 倍思的 32dB 已经够公交用，更高要求再升级。",
    ["漫步者NeoBuds Pro 2 ANC 48dB最强+LDAC+月销9800，音质降噪双优", "倍思Bowie M2s ANC 32dB+月销2.5万，¥299最便宜真降噪公交够用", "Nothing Ear 2 ANC 40dB+透明外壳+月销5500，颜值音质降噪三合一"]
))

# 2. similar_rec
T.append(make_traj(
    "sft_simrec_064", "similar_rec", "相似品推荐",
    "抱怨充电速度慢 → 推荐快充版",
    "手机充电太慢了，充一晚上才满，换快充款",
    {"query": "手机充电器 超快充 120W", "max_price": 150, "filters": {"charging_w_min": 65}},
    [
        {"product_id": "jd_fast_chg_1", "title": "小米 100W 氮化镓充电器 单口", "price": 99, "is_jd_self": True, "rating": 4.9, "key_specs": "100W/单口PD/25分钟充满小米/月销4.5万", "sales": "月销4.5万"},
        {"product_id": "jd_fast_chg_2", "title": "Anker 65W 超薄氮化镓 双口 USB-C", "price": 129, "is_jd_self": True, "rating": 4.9, "key_specs": "65W/超薄/双口/Anker安全/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "jd_fast_chg_3", "title": "紫米 120W 氮化镓 单口 秒充", "price": 129, "is_jd_self": True, "rating": 4.8, "key_specs": "120W/最快充/支持苹果安卓/月销1.5万", "sales": "月销1.5万"}
    ],
    "充一晚上是旧充电头问题，换快充头直接起飞：\n\n**1. 小米 100W 单口（¥99）** ⭐ 性价比最高\n月销 4.5 万断档，100W 给小米手机 25 分钟充满，给 iPhone 也快。**¥99 是快充里最实惠的**。\n\n**2. 紫米 120W（¥129）**\n**最高功率**，支持小米/华为/苹果/三星全系快充协议，适合换手机频繁的人。\n\n**3. Anker 65W 双口（¥129）**\n65W+双口，**手机+iPad 或手机+笔记本同时充**，出差党刚需。\n\n## 💡 快充为什么有用\n\n你的手机如果支持 65W+快充：\n- 原装充电头 5-20W：充满 **1.5-3 小时**\n- 65W 快充头：充满 **30-50 分钟**\n- 100W+：**20-30 分钟**\n\n**换一个充电头，每天节省 1-2 小时充电等待**。\n\n## ⚠️ 注意\n\n充电头功率要匹配手机支持的快充协议：\n- 华为 SuperCharge → 买小米/华为快充头\n- 苹果 PD 协议 → 买 USB-C PD 充电头\n- 安卓通用 → QC3.0/4.0 或 PD 协议",
    ["小米100W氮化镓单口+25分钟充满+月销4.5万断档，¥99最实惠快充", "紫米120W最高功率+支持全协议+月销1.5万，换机频繁全协议兼容", "Anker 65W超薄双口+手机+iPad同充+月销2.5万，出差双设备首选"]
))

# 3. sku_comp
T.append(make_traj(
    "sft_skucomp_061", "sku_comp", "商品对比",
    "传统健身 vs 智能健身镜 vs 健身 App",
    "想在家健身，智能健身镜/健身App/传统器材哪个效果好",
    {"skus": ["智能健身镜FITURE", "Keep健身App会员", "哑铃+瑜伽垫传统器材"], "mode": "solution_comparison"},
    [
        {"product_id": "jd_mirror_fitness", "title": "FITURE 魔镜 智能健身镜 年费套餐", "price": 5999, "is_jd_self": True, "rating": 4.8, "key_specs": "AI纠姿/上千课程/互动健身/5年内容订阅", "sales": "月销1200"},
        {"product_id": "jd_keep_vip", "title": "Keep 健身 App SVIP 12个月", "price": 199, "is_jd_self": True, "rating": 4.8, "key_specs": "2000+课程/手机端/任何地点都能用/月销10万", "sales": "月销10万"},
        {"product_id": "jd_traditional", "title": "哑铃5-25kg可调+迪卡侬瑜伽垫+弹力带套装", "price": 968, "is_jd_self": True, "rating": 4.9, "key_specs": "可调哑铃+瑜伽垫+弹力带/家庭健身基础三件", "sales": "月销8000"}
    ],
    "三种方案**本质是不同的健身理念**，不是单纯比价格：\n\n## 📊 三种方案对比\n\n| 维度 | 健身镜 ¥5999 | Keep App ¥199 | 传统器材 ¥968 |\n|---|---|---|---|\n| 成本 | **最贵** | **最便宜** | 中等 |\n| 动作纠正 | **AI 实时纠姿** | 无 | 无 |\n| 课程丰富度 | 多 | **最多（2000+）**| 无课程 |\n| 使用门槛 | 低 | 低 | **需要自律** |\n| 适合人 | 愿意花钱的懒人 | 有自律/手机随时用 | 有训练基础 |\n\n## 🎯 三种适合的人\n\n### 健身镜 ¥5999（不差钱的懒人）\n- AI 纠姿让动作更标准\n- **¥5999 = 私教 10 节**，价值对比需要考虑\n- 适合：健身新手+预算宽裕+喜欢高科技感\n\n### Keep App ¥199（性价比之王）⭐\n- **月销 10 万是健身类 App 绝对销冠**\n- ¥199/年 = ¥0.55/天，几乎零门槛\n- 2000+ 课程覆盖所有需求\n- 缺点：需要自律，没有实时纠姿\n\n### 传统器材 ¥968（进阶选择）\n- **有了器材不一定会用**（没有课程指导）\n- 适合已经懂训练的人（不需要指导）\n- 长期最省（器材买一次用多年）\n\n## 💡 真心建议\n\n**先买 Keep App ¥199 试 3 个月**：\n- 0 门槛验证自己能不能坚持\n- 课程够丰富，从瑜伽/有氧到力量全有\n- 3 个月后：还在坚持 → 买器材；不坚持 → 只损失 ¥199\n\n**不要一开始就买 ¥5999 健身镜** = 大概率吃灰",
    ["FITURE魔镜+AI纠姿+5年内容+月销1200，不差钱健身新手懒人首选", "Keep App SVIP年卡199元+2000+课程+月销10万，性价比之王先试坚持再升级", "哑铃+瑜伽垫+弹力带基础三件968元+月销8000，有训练基础自律人最省"]
))

# 4. sku_comp
T.append(make_traj(
    "sft_skucomp_062", "sku_comp", "商品对比",
    "冰箱容量档次选购对比",
    "买冰箱，200L/350L/500L 三档怎么选，家里 3 口人",
    {"skus": ["海尔200L双门", "海尔350L三门", "海尔500L十字四门"], "mode": "capacity_comparison"},
    [
        {"product_id": "jd_fridge_200", "title": "海尔 BCD-200TMPT 200L 双门小冰箱", "price": 1299, "is_jd_self": True, "rating": 4.8, "key_specs": "200L/双门/小户型/2人以下", "sales": "月销2.5万"},
        {"product_id": "jd_fridge_350", "title": "海尔 BCD-350WLHFD9D 350L 三门风冷", "price": 2299, "is_jd_self": True, "rating": 4.9, "key_specs": "350L/三门风冷/3-4口家庭标准/月销3.5万", "sales": "月销3.5万"},
        {"product_id": "jd_fridge_500", "title": "海尔 BCD-500WLHTD79D9U1 500L 十字四门", "price": 3999, "is_jd_self": True, "rating": 4.9, "key_specs": "500L/十字四门/独立变温区/5口以上家庭", "sales": "月销1.8万"}
    ],
    "**3 口之家标准选 350L**，这是行业公认的 3-4 口最优解：\n\n## 📊 三档容量对比\n\n| 容量 | 价格 | 适合家庭 | 月销 |\n|---|---|---|---|\n| 200L | ¥1299 | 1-2 人 | 2.5 万 |\n| **350L** | **¥2299** | **3-4 口（你家）** | **3.5 万**（销冠）|\n| 500L | ¥3999 | 5 口以上 | 1.8 万 |\n\n## 💡 350L 为什么是 3 口家庭标准\n\n**3 口家庭冰箱内容量估算**：\n- 蔬菜水果：50L\n- 肉类海鲜：40L\n- 饮料/水：30L\n- 调味料/酱料：20L\n- 零食/熟食：30L\n- **共计约 170L，加余量需要 320-380L**\n\n200L 会满，350L 不会满，500L 会有空置。\n\n## 💰 价差分析\n\n### 200L → 350L（+¥1000）值\n- 150L 的差距是有感知的（买菜多了就满）\n- **买了大一号不会后悔，买了小的每次买菜要抠着用**\n\n### 350L → 500L（+¥1700）不值（3 口家庭）\n- 500L 对你家来说有 30-40% 空置\n- 空冰箱更耗电（热交换效率低）\n- ¥1700 买不来家庭实际需要的容量\n\n## 🎯 我的建议\n\n3 口家庭**直接选 350L ¥2299**，月销 3.5 万件是市场投票的结果。三门风冷（不结冰，不用除霜）是这个价位标配。",
    ["海尔200L双门+1-2人量+月销2.5万，单身独居小户型首选", "海尔350L三门风冷+3-4口家庭标准+月销3.5万销冠，3口家庭最优解", "海尔500L十字四门+独立变温区+月销1.8万，5口以上大家庭或常备大量食材"]
))

# 5. matching
T.append(make_traj(
    "sft_match_061", "matching_purchase", "搭配购物",
    "家庭影音室软装搭配",
    "客厅要做电影观影角，配遮光窗帘+豆袋沙发+爆米花机+零食桌",
    {"query": "家庭观影角布置 遮光窗帘+豆袋+爆米花机", "filters": {"style": "home_cinema_corner"}},
    [
        {"product_id": "jd_cinema_1", "title": "南极人 99% 遮光窗帘 深灰色 2.5m", "price": 399, "is_jd_self": True, "rating": 4.9, "key_specs": "99%遮光/深灰/投影效果好/2.5m高", "sales": "月销3500"},
        {"product_id": "jd_cinema_2", "title": "懒人豆袋沙发 成人大号 可折叠", "price": 299, "is_jd_self": True, "rating": 4.9, "key_specs": "成人大号/懒人坐/可折叠收纳/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "jd_cinema_3", "title": "家用微型爆米花机 热风式 无油", "price": 99, "is_jd_self": True, "rating": 4.9, "key_specs": "热风无油/3分钟出锅/观影仪式感/月销1.8万", "sales": "月销1.8万"},
        {"product_id": "jd_cinema_4", "title": "小型折叠边桌 沙发旁零食桌", "price": 79, "is_jd_self": True, "rating": 4.8, "key_specs": "折叠/沙发旁放零食/懒人必备", "sales": "月销3.5万"}
    ],
    "家庭观影角 4 件套 ¥876，**¥876 打造电影院体验**：\n\n## 🎬 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 遮光窗帘 | 南极人 99% 遮光深灰 | ¥399 |\n| 豆袋沙发 | 懒人大号可折叠 | ¥299 |\n| 爆米花机 | 热风无油 3 分钟 | ¥99 |\n| 零食边桌 | 折叠沙发旁桌 | ¥79 |\n\n## 🎨 观影角配置逻辑\n\n### 遮光窗帘是投影效果的关键\n- 普通窗帘白天遮光率 70-80%，**投影画面发灰**\n- 99% 遮光帘白天也能达到接近暗室效果\n- **深灰色吸光**，比黑色看起来不压抑\n\n### 豆袋沙发 vs 普通沙发\n豆袋沙发观影时的优势：\n- **随意调整坐姿**（沙发有固定形状）\n- 躺着看不难受\n- ¥299 比买一套新沙发便宜 10 倍\n\n### 爆米花机的仪式感价值\n¥99 买的不是爆米花，**是每次看电影前 3 分钟的仪式感**：\n- 爆米花香气弥漫\n- 孩子特别喜欢参与\n- 热风无油比微波炉更健康\n\n## 💎 进阶升级（+¥500）\n\n- 氛围灯（RGB 灯带）¥150\n- 毯子+抱枕套装 ¥200\n- 零食桶组合 ¥80\n- HDMI2.1 线（4K 信号）¥60",
    ["南极人99%遮光窗帘深灰2.5m+月销3500，投影关键白天接近暗室", "懒人豆袋沙发成人大号可折叠+月销2.5万，随意调姿势观影更舒服", "热风无油爆米花机3分钟+月销1.8万，99元买观影仪式感", "折叠零食边桌+月销3.5万，懒人沙发旁放爆米花水杯必备"]
))

# 6. matching
T.append(make_traj(
    "sft_match_062", "matching_purchase", "搭配购物",
    "男士商务礼品整套",
    "给老板送节日礼物，5000 预算，要有档次不失礼",
    {"query": "商务送礼 领导 高端 实用", "max_price": 5500, "filters": {"recipient": "boss", "category": "premium_gift"}},
    [
        {"product_id": "jd_boss_1", "title": "Montblanc 万宝龙 名片夹 商务款 皮质", "price": 1699, "is_jd_self": True, "rating": 4.9, "key_specs": "万宝龙/头层牛皮/商务名片夹/送礼有面子", "sales": "月销850"},
        {"product_id": "jd_boss_2", "title": "酒鬼 芙蓉王 50年陈酿 礼盒装 500ml", "price": 1599, "is_jd_self": True, "rating": 4.9, "key_specs": "50年陈酿/礼盒/高端商务酒礼/不失礼", "sales": "月销1200"},
        {"product_id": "jd_boss_3", "title": "天猫超市 大闸蟹礼盒 母5两公4两 16只", "price": 899, "is_jd_self": True, "rating": 4.9, "key_specs": "阳澄湖/母5两公4两/16只礼盒/应季送礼", "sales": "月销2500"},
        {"product_id": "jd_boss_4", "title": "保时捷 设计 钢笔 商务套装 礼盒", "price": 1299, "is_jd_self": True, "rating": 4.8, "key_specs": "保时捷设计/钢笔+笔记本/商务礼品套装", "sales": "月销680"}
    ],
    "给领导送礼 5000 预算，核心原则：**实用但不俗气、高档但不显眼**。\n\n## 💼 5000 预算方案\n\n### 方案 A：食品+商务用品（¥2498）⭐ 最稳\n\n| 礼物 | 商品 | 价格 |\n|---|---|---|\n| 商务酒 | 酒鬼 50 年陈酿礼盒 | ¥1599 |\n| 大闸蟹 | 阳澄湖 16 只礼盒 | ¥899 |\n| **合计** | | **¥2498** |\n\n**理由**：\n- 食品食用完不留痕（不引人注意）\n- 酒 + 蟹是最受欢迎的商务组合\n- 剩余 ¥2500 留备用\n\n### 方案 B：高端文具（¥2998）奢华感\n\n| 礼物 | 商品 | 价格 |\n|---|---|---|\n| 万宝龙名片夹 | 皮质 | ¥1699 |\n| 保时捷设计钢笔套装 | | ¥1299 |\n| **合计** | | **¥2998** |\n\n**理由**：\n- 万宝龙是商务礼品的最高规格之一\n- 但**领导已有同款的可能性大**，可能显得寒酸\n\n## 💡 送礼的真正智慧\n\n**礼物价值 ≠ 金额**：\n1. 了解领导的喜好（爱喝茶/爱高尔夫/爱收藏）\n2. 针对性的中档礼物 > 标准化的豪华礼物\n\n例如：\n- 领导爱喝茶 → ¥2000 的好茶比 ¥5000 的酒更有心意\n- 领导有孩子 → 孩子的礼物比领导的礼物更感人\n\n## ⚠️ 送礼禁忌\n\n- ❌ 钟（谐音「送终」）\n- ❌ 绿帽、绿色领带\n- ❌ 超 ¥10000 的礼物（有行贿风险）\n- ❌ 太私人（香水/内衣）\n- ✅ 食品饮品：最安全，用完不留据",
    ["酒鬼50年陈酿礼盒500ml+月销1200，商务场合送酒最受欢迎不失礼", "阳澄湖大闸蟹16只礼盒+月销2500，食品应季送礼不留痕最稳", "万宝龙皮质名片夹+月销850，高端文具送礼彰显档次", "保时捷设计钢笔+笔记本礼盒+月销680，商务文具套装有仪式感"]
))

# 7. bundle
T.append(make_traj(
    "sft_bundle_059", "bundle_purchase", "组合购物",
    "5000 元写字楼白领午休装备",
    "在写字楼上班，5000 配齐午休神器：颈枕+眼罩+白噪音+折叠凳",
    {"query": "写字楼午休装备 颈枕+眼罩+白噪音+折叠床", "max_price": 5500},
    [
        {"product_id": "jd_nap_1", "title": "Ostrich 鸵鸟枕 午睡神器 趴睡款", "price": 299, "is_jd_self": True, "rating": 4.9, "key_specs": "趴睡/遮光/可拆洗/办公室午睡必备", "sales": "月销1.5万"},
        {"product_id": "jd_nap_2", "title": "Manta 3D 立体遮光睡眠眼罩", "price": 299, "is_jd_self": True, "rating": 4.9, "key_specs": "3D立体不压眼球/完全遮光/可调", "sales": "月销2.2万"},
        {"product_id": "jd_nap_3", "title": "LectroFan 白噪音机 12种音效", "price": 499, "is_jd_self": True, "rating": 4.9, "key_specs": "12种白噪音/精准定时/午睡专用", "sales": "月销3500"},
        {"product_id": "jd_nap_4", "title": "办公室午休折叠躺椅 轻量便携", "price": 399, "is_jd_self": True, "rating": 4.8, "key_specs": "折叠收纳/躺椅/小型携带/压缩颈椎", "sales": "月销1.2万"},
        {"product_id": "jd_nap_5", "title": "眼部热敷蒸汽眼罩 发热款 20片装", "price": 99, "is_jd_self": True, "rating": 4.9, "key_specs": "蒸汽发热/眼周保暖/午睡眼疲劳/20片", "sales": "月销4.5万"}
    ],
    "写字楼午休装备 5 件套 ¥1595，**20 分钟高质量午睡下午精力翻倍**：\n\n## 😴 完整方案\n\n| 装备 | 商品 | 价格 | 作用 |\n|---|---|---|---|\n| 颈枕 | Ostrich 鸵鸟枕 | ¥299 | 趴桌上睡+遮光 |\n| 眼罩 | Manta 3D 立体 | ¥299 | 完全遮光不压眼 |\n| 白噪音 | LectroFan 12 音 | ¥499 | 屏蔽办公室杂音 |\n| 折叠椅 | 午休躺椅 | ¥399 | 拒绝趴桌伤颈椎 |\n| 热敷眼罩 | 蒸汽 20 片 | ¥99 | 眼睛疲劳缓解 |\n\n## 💡 写字楼午睡难点\n\n**3 大问题**：\n1. **光线刺眼**（天花板大灯+窗户）→ 3D 眼罩解决\n2. **杂音干扰**（键盘声/电话声）→ 白噪音遮蔽\n3. **趴桌伤颈椎**（趴 20 分钟颈椎酸）→ 鸵鸟枕或折叠椅\n\n## 💡 20 分钟午睡的科学\n\n**20 分钟是午睡黄金时长**：\n- 进入浅睡眠阶段（还没进入深睡眠）\n- 醒来**没有睡眠惰性**（不会比睡前更困）\n- 下午工作效率提升 34%（斯坦福研究数据）\n\n超过 30 分钟容易进入深睡眠，醒来会更困。\n\n## 💰 预算剩 ¥3405\n\n你说 5000 预算配午休装备，实际上 ¥1595 已经配齐了。余下 ¥3405 可以用于：\n- 升级人体工学椅（长期更重要）¥1499\n- 办公桌护颈托架 ¥299\n- 升降显示器架 ¥399\n- 留备用",
    ["Ostrich鸵鸟枕趴睡遮光+月销1.5万，趴桌午睡颈椎保护解决方案", "Manta 3D立体眼罩+完全遮光不压眼球+月销2.2万，写字楼遮光首选", "LectroFan白噪音12种+精准定时+月销3500，屏蔽键盘电话午睡专用", "午休折叠躺椅+月销1.2万，拒绝趴桌躺睡保护颈椎", "蒸汽热敷眼罩20片+月销4.5万，午睡前缓解眼疲劳"]
))

# 8. bundle
T.append(make_traj(
    "sft_bundle_060", "bundle_purchase", "组合购物",
    "2500 元家用急救 AED + 常用药",
    "想备个家庭急救包，专注心脏急救，2500 预算",
    {"query": "家庭心脏急救装备 AED+CPR面罩+急救包", "max_price": 2800},
    [
        {"product_id": "jd_first_aid_1", "title": "迪伽 家用 AED 除颤仪 全自动", "price": 1399, "is_jd_self": True, "rating": 4.8, "key_specs": "全自动/语音指导/家庭版/心脏骤停救命", "sales": "月销380"},
        {"product_id": "jd_first_aid_2", "title": "CPR 急救面罩 防感染 成人款", "price": 49, "is_jd_self": True, "rating": 4.9, "key_specs": "防感染/单向阀/随手包装/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "jd_first_aid_3", "title": "急救包 60件套 家庭版 含说明书", "price": 299, "is_jd_self": True, "rating": 4.9, "key_specs": "60件急救用品/含外伤/包扎/月销1.5万", "sales": "月销1.5万"},
        {"product_id": "jd_first_aid_4", "title": "急救知识挂图 心肺复苏 A2 防水", "price": 39, "is_jd_self": True, "rating": 4.8, "key_specs": "A2挂图/心肺复苏步骤/防水贴墙/快速查阅", "sales": "月销3500"}
    ],
    "家庭心脏急救 4 件套 ¥1786，余 ¥714：\n\n## ❤️ 完整方案\n\n| 装备 | 商品 | 价格 | 重要性 |\n|---|---|---|---|\n| 🥇 AED 除颤仪 | 迪伽家用全自动 | ¥1399 | ⭐⭐⭐⭐⭐ |\n| 急救包 60 件 | 外伤/包扎 | ¥299 | ⭐⭐⭐⭐ |\n| CPR 急救面罩 | 防感染单向阀 | ¥49 | ⭐⭐⭐⭐ |\n| 急救知识挂图 | A2 心肺复苏步骤 | ¥39 | ⭐⭐⭐ |\n\n## 💡 为什么 AED 最重要\n\n**心脏骤停的 4 分钟法则**：\n- 0-4 分钟：脑损伤概率低\n- 4-10 分钟：脑损伤概率大幅上升\n- >10 分钟：死亡/植物人概率极高\n- 救护车平均到达 **15 分钟**\n\n**AED 在 4 分钟内使用，复苏成功率 70%**\n**不使用 AED 等救护车，复苏成功率 < 5%**\n\n## 💡 家用 AED 操作简单\n\n迪伽家用版：\n1. 打开电源\n2. **语音提示「贴电极板」**\n3. 按照语音指导操作\n4. **全自动分析，自动决定是否放电**\n5. 不需要任何医学知识\n\n## 🧑‍⚕️ 还需要做\n\n**光买 AED 不够**，建议：\n1. 家人一起看 **CPR+AED 教学视频**（B 站搜「AED 使用方法」30 分钟学会）\n2. 急救挂图贴在显眼位置（每个人都知道在哪）\n3. AED **定期自检**（机器有自动自检功能）\n\n## 💰 余 ¥714 加\n\n- 血压计（欧姆龙）¥269\n- 血糖仪 ¥199\n- 急救常备药 ¥150",
    ["迪伽家用AED全自动+语音指导+月销380，4分钟内复苏率70%最重要投资", "急救包60件套+外伤包扎+月销1.5万，日常意外处理全覆盖", "CPR急救面罩+防感染单向阀+月销2.5万，人工呼吸防感染保护", "心肺复苏急救挂图A2防水+月销3500，全家快速查阅应急步骤"]
))

# 9. place_order
T.append(make_traj(
    "sft_order_032", "place_order", "购物下单",
    "订单支付失败处理",
    "刚下的单支付一直失败，一直提示支付超时，怎么办",
    {"order_id": "[TRACKING_ID]-PENDING-2284", "issue_type": "payment_failed"},
    [
        {"product_id": "jd_payment_help", "title": "支付失败订单 [TRACKING_ID]-PENDING-2284 — 处理中", "price": 0, "is_jd_self": True, "rating": 5.0, "key_specs": "订单待支付状态/30分钟内完成支付有效/超时自动取消退回", "sales": "—"}
    ],
    "支付失败很常见，**不用慌，订单还在**。几个解决方案：\n\n## 🔄 订单状态\n\n- 订单 [TRACKING_ID]-PENDING-2284 目前处于「**待支付**」状态\n- 京东订单**30 分钟内有效**（还没超时的话）\n- 超时后订单自动取消，重新下单即可（商品不会涨价）\n\n## 💳 支付失败原因 + 解决方案\n\n### 原因 1：银行卡/微信/支付宝余额不足\n→ 换一种支付方式\n→ 微信 → 支付宝 → 银行卡换着试\n\n### 原因 2：网络问题\n→ **换 4G/5G 网络**（WiFi 有时候支付接口慢）\n→ 等 10 秒重试\n\n### 原因 3：系统繁忙（高峰期/活动期）\n→ **等 5 分钟再试**\n→ 或换 App 重新进入支付页\n\n### 原因 4：银行卡当日交易限额\n→ 换其他银行卡\n→ 或开通京东白条分期\n\n## ✅ 最简单的操作\n\n1. 关闭 App，**重新打开**\n2. 进入「我的订单」→ 找到该订单\n3. 点「**立即付款**」重新发起支付\n4. **换一种支付方式**（如从微信换支付宝）\n\n## ⚠️ 超时了怎么办\n\n如果 30 分钟已经过了，订单会**自动取消**：\n- 不用担心钱被扣（没支付成功就没有扣款）\n- **重新下单**，价格和库存会实时更新\n- 重新下单选**余额/白条**更稳定（不依赖外部支付）\n\n## 💡 下次预防\n\n大额订单建议：\n1. 提前确认支付方式余额\n2. 绑定多种支付方式（备选）\n3. 促销活动期间**提前 5 分钟进入支付页**（服务器压力小）",
    ["支付失败订单待支付状态+30分钟内有效+换支付方式重试处理中"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase
T.append(make_traj(
    "sft_repurchase_030", "repurchase", "复购召回",
    "复购+推荐同品牌系列扩充",
    "再买之前那款果集乳液，顺便问问同牌有没有配套精华",
    {"category_keyword": "乳液", "time_range": "last_5_months", "show_same_brand": True},
    [
        {"product_id": "jd_lotion_old", "title": "科颜氏 焦油清爽保湿乳液 125ml (3月前)", "price": 210, "is_jd_self": True, "rating": 4.9, "key_specs": "3月前购买/订单[ORDER_ID]/125ml", "sales": "月销3.5万"},
        {"product_id": "jd_lotion_serum", "title": "科颜氏 高保湿精华 100ml 同系列", "price": 380, "is_jd_self": True, "rating": 4.9, "key_specs": "科颜氏同系列/保湿精华/前导精华/月销2.2万", "sales": "月销2.2万"},
        {"product_id": "jd_lotion_set", "title": "科颜氏 高保湿套装 精华+乳液 组合", "price": 549, "is_jd_self": True, "rating": 4.9, "key_specs": "精华100ml+乳液125ml套装/省41元", "sales": "月销4500"}
    ],
    "你 3 个月前买的是 **科颜氏焦油清爽保湿乳液 ¥210**（订单 [ORDER_ID]）。\n\n## 🧴 配套精华推荐\n\n科颜氏确实有同系列精华：**科颜氏高保湿精华 100ml ¥380**\n\n### 和乳液的搭配逻辑\n\n护肤步骤：洁面 → **精华（渗透）** → **乳液（锁水）**\n\n精华负责**活性成分渗透**，乳液负责**封锁保湿**。\n两者搭配效果比单用乳液**好 40%**。\n\n## 💰 三种购买方式对比\n\n| 方案 | 价格 | 省多少 |\n|---|---|---|\n| 单买乳液 ¥210 + 精华 ¥380 | ¥590 | 基准 |\n| **套装（精华+乳液）** | **¥549** | **省 ¥41** |\n| 只复购乳液 | ¥210 | — |\n\n## 🎯 我的建议\n\n**看你目前的护肤诉求**：\n\n### 你说效果不错 → 继续单买乳液 ¥210\n- 不需要改变\n- 省 ¥380\n\n### 你想要更好保湿效果 → 直接买套装 ¥549\n- 精华+乳液双效\n- 比分开买省 ¥41\n- 同系列成分协同效果最好\n\n### 你皮肤开始出现细纹/暗沉 → 换雅诗兰黛小棕瓶精华+科颜氏乳液\n- 乳液够用继续用科颜氏\n- 精华升级到抗老功效更强的款\n\n你目前皮肤状态如何？告诉我，我给针对性建议。",
    ["科颜氏乳液125ml你3月前购买+月销3.5万，继续复购同款最稳", "科颜氏高保湿精华100ml+同系列+月销2.2万，精华渗透+乳液锁水效果+40%", "科颜氏精华+乳液套装+省41元+月销4500，两件都想要套装最划算"],
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
