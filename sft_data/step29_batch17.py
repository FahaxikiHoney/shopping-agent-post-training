# -*- coding: utf-8 -*-
"""Step 29: 第 17 批 10 条"""
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

# 1. similar_rec - 抱怨没有夜间模式
T.append(make_traj(
    "sft_simrec_045", "similar_rec", "相似品推荐",
    "抱怨功能缺失(夜间/护眼) → 推荐有该功能的同价位",
    "之前那台路由器没有夜间定时断网功能，孩子熬夜玩手机控制不了，有同价位的能设置的吗",
    {"query": "路由器 定时断网 家长控制 儿童管控", "max_price": 600, "filters": {"parental_control": True}},
    [
        {"product_id": "mock_router_pc_1", "title": "华为路由 AX3 Pro 家长管控版 Wi-Fi 6", "price": 499, "is_platform_self": True, "rating": 4.9, "key_specs": "Wi-Fi 6/家长管控+定时断网/华为生态/月销2万", "sales": "月销2万"},
        {"product_id": "mock_router_pc_2", "title": "小米 AX3000T 路由器 家长控制定时", "price": 369, "is_platform_self": True, "rating": 4.8, "key_specs": "AX3000/家长控制+定时管理/米家App控制", "sales": "月销4.5万"},
        {"product_id": "mock_router_pc_3", "title": "TP-Link XDR 3010 家庭管控路由", "price": 449, "is_platform_self": True, "rating": 4.8, "key_specs": "Wi-Fi 6/儿童保护+作业时间/精细化管控", "sales": "月销1.5万"}
    ],
    "控制孩子上网时间是真实需求，3 款都有定时断网+家长管控：\n\n**1. 小米 AX3000T（¥369）** ⭐ 性价比首选\n**米家 App 直接管**：指定设备+时间段+一键断网，还能看孩子今天上网几小时。月销 4.5 万件断档第一。\n\n**2. TP-Link XDR 3010（¥449）**\n**最细化**的家长管控——可按「作业时间/睡觉时间」分时段管，还能过滤少儿不宜内容。\n\n**3. 华为路由 AX3 Pro（¥499）**\n华为生态联动最顺滑，配华为手机家长用着最方便，Wi-Fi 6 性能也最强。\n\n## 💡 选择逻辑\n- **家里是小米生态** → 小米 AX3000T（¥369 最便宜）\n- **想要精细控制内容** → TP-Link XDR 3010\n- **家里用华为手机** → 华为 AX3 Pro\n\n## ⚠️ 避坑\n断网功能必须在路由器上设置（不是手机 App 那种），孩子换 VPN 会绕过 App，但绕不过**路由器层面的断网**。",
    ["小米AX3000T+米家App定时断网+月销4.5万断档，米家生态家长管控首选", "TP-Link XDR 3010分时段管控+内容过滤+月销1.5万，精细管控首选", "华为AX3 Pro+Wi-Fi 6+华为生态联动+月销2万，华为手机用户首选"]
))

# 2. similar_rec - 抱怨安装麻烦
T.append(make_traj(
    "sft_simrec_046", "similar_rec", "相似品推荐",
    "抱怨安装复杂 → 推荐免打孔/免安装款",
    "上次买的窗帘杆要打孔太麻烦了，租房不能打孔，有免打孔的同款吗",
    {"query": "窗帘杆 免打孔 伸缩 租房", "filters": {"no_drilling": True}},
    [
        {"product_id": "mock_rod_1", "title": "梦诗达 免打孔伸缩窗帘杆 不锈钢", "price": 49, "is_platform_self": True, "rating": 4.9, "key_specs": "免打孔/伸缩1.2-2.1m/304不锈钢/承重8kg", "sales": "月销8万"},
        {"product_id": "mock_rod_2", "title": "罗马杆 免打孔 加厚铝合金 1.5-2.5m", "price": 89, "is_platform_self": True, "rating": 4.8, "key_specs": "加厚铝合金/免打孔/1.5-2.5m可伸缩", "sales": "月销3.5万"},
        {"product_id": "mock_rod_3", "title": "天丽 顶装免打孔窗帘杆 双杆款", "price": 129, "is_platform_self": True, "rating": 4.8, "key_specs": "顶装免打孔/双杆/内外帘分离/稳固", "sales": "月销1.2万"}
    ],
    "租房神器，3 款都不用打孔：\n\n**1. 梦诗达免打孔伸缩杆 ¥49** ⭐ 月销 8 万断档\n顶在窗框两侧靠弹力固定，**¥49 真的够用**，承重 8kg，普通窗帘没问题。\n\n**2. 加厚铝合金伸缩罗马杆 ¥89**\n铝合金比钢杆更轻，**颜值好看**，适合看起来要高级一点的窗帘款式。\n\n**3. 天丽双杆款 ¥129**\n**双杆设计**可以挂两层（纱帘+遮光帘），功能最全，适合想要内外双层窗帘的租客。\n\n## 💡 选哪个\n- 普通单层窗帘 → 梦诗达 ¥49（够用省钱）\n- 想要颜值好看 → 铝合金 ¥89\n- 要双层遮光+纱帘 → 天丽双杆 ¥129",
    ["梦诗达免打孔伸缩杆+弹力固定+承重8kg+月销8万断档，租房最省钱", "加厚铝合金免打孔+颜值好看+月销3.5万，追求颜值的租客", "天丽双杆免打孔+内外帘分离+月销1.2万，要双层遮光+纱帘的刚需"]
))

# 3. sku_comp
T.append(make_traj(
    "sft_skucomp_043", "sku_comp", "商品对比",
    "同价位不同品牌净化器对比（3款）",
    "米家、352、IAM 三款净水器都在 1500-2000 左右，有什么区别",
    {"skus": ["小米米家空气净化器4 Pro", "352 X83C", "IAM KJ900F"], "mode": "parallel_exact_match"},
    [
        {"product_id": "mock_air_mi", "title": "小米米家空气净化器 4 Pro 除甲醛", "price": 1599, "is_platform_self": True, "rating": 4.9, "key_specs": "CADR颗粒500/甲醛300/米家App/月销4.1万", "sales": "月销4.1万"},
        {"product_id": "mock_air_352", "title": "352 X83C 大客厅净化器", "price": 1999, "is_platform_self": True, "rating": 4.9, "key_specs": "CADR颗粒750/甲醛400/双侧进风/CCM F4", "sales": "月销1.2万"},
        {"product_id": "mock_air_iam", "title": "IAM KJ900F 全能除醛 母婴款", "price": 1799, "is_platform_self": True, "rating": 4.8, "key_specs": "CADR颗粒900/甲醛450/醛霾双滤芯", "sales": "月销8500"}
    ],
    "三款都是主流选择，**核心差异在适用面积和生态**：\n\n## 📊 关键参数\n\n| 维度 | 米家 ¥1599 | 352 X83C ¥1999 | IAM ¥1799 |\n|---|---|---|---|\n| 颗粒 CADR | 500 | **750** | 900 |\n| 甲醛 CADR | 300 | **400** | **450** |\n| 适用面积 | 60-80㎡ | **90㎡** | 100㎡ |\n| App 生态 | **米家** | 独立 App | 独立 App |\n| 月销 | **4.1 万** | 1.2 万 | 8500 |\n\n## 🎯 怎么选\n\n### 米家 ¥1599（60-80㎡，米家生态用户）\n- 日常用最便宜\n- 米家全家联动（和小米电器一起控制）\n- 月销 4.1 万是大众选择\n\n### 352 X83C ¥1999（80-100㎡大客厅）\n- **双侧进风净化更快**\n- CCM 滤网等级 F4 顶配（寿命更长）\n- 适合大客厅，性能最均衡\n\n### IAM KJ900F ¥1799（母婴/新装修）\n- CADR 数据最大\n- **醛霾双独立滤芯**（新装修推荐）\n- 适合家有婴幼儿\n\n## 💡 真心建议\n- 60-80㎡普通卧室 → 米家省 400\n- 大客厅/开放厅 → 352 X83C\n- 刚装修/有孕妇婴儿 → IAM KJ900F",
    ["米家4 Pro CADR 500+米家App+月销4.1万，60-80㎡普通家庭性价比首选", "352 X83C CADR 750+双侧进风+CCM F4+月销1.2万，80-100㎡大客厅最均衡", "IAM KJ900F CADR 900+醛霾双滤芯+月销8500，新装修/母婴场景首选"]
))

# 4. sku_comp
T.append(make_traj(
    "sft_skucomp_044", "sku_comp", "商品对比",
    "跑步机 vs 椭圆机 vs 划船机 居家有氧选哪个",
    "居家有氧训练买跑步机/椭圆机/划船机哪个好，预算 3000",
    {"categories": ["跑步机", "椭圆机", "划船机"], "max_price": 3500, "topk_per_category": 1},
    [
        {"product_id": "mock_treadmill", "title": "迈宝赫 走步机 折叠静音 家用", "price": 2999, "is_platform_self": True, "rating": 4.8, "key_specs": "折叠/静音/最高10km/h/适合走步慢跑", "sales": "月销3500"},
        {"product_id": "mock_elliptical", "title": "舒华 椭圆机 家用磁控静音 SH-E0001", "price": 2599, "is_platform_self": True, "rating": 4.9, "key_specs": "磁控静音/全身有氧/膝盖零冲击/月销2200", "sales": "月销2200"},
        {"product_id": "mock_rowing", "title": "concept2 划船机 RowErg 标准款", "price": 8500, "is_platform_self": True, "rating": 4.9, "key_specs": "Concept2专业款/全身86%肌肉/有氧无氧双效", "sales": "月销680"}
    ],
    "**3000 预算内推荐椭圆机**，理由如下：\n\n## 📊 三种器械对比\n\n| 维度 | 跑步机 ¥2999 | 椭圆机 ¥2599 | 划船机 ¥8500 |\n|---|---|---|---|\n| 价格（预算内）| ✅ | ✅ | ❌（超预算）|\n| 噪音 | ⚠️ 中等 | **低（静音）** | 低 |\n| 膝盖冲击 | ❌ 有冲击 | **零冲击** | 低 |\n| 占地 | 大 | 中等 | **可竖放** |\n| 减脂效率 | 中 | 中偏高 | **最高** |\n| 上手难度 | 易 | 易 | 需要学姿势 |\n\n## 🎯 我的推荐：椭圆机 ¥2599\n\n**理由**：\n1. **比跑步机便宜 ¥400** 还更静音\n2. 椭圆运动零冲击——**膝盖不好、体重偏大的人刚需**\n3. 全身有氧，比只练腿的跑步机更全面\n\n## 💡 什么情况选跑步机\n- 你有跑步习惯，想在家继续\n- 膝盖没有问题\n- 家里楼上/楼下不怕吵（跑步机震动明显）\n\n## 💡 划船机 ¥8500 超预算\n- 减脂效果最好但贵 3 倍\n- Concept2 是专业级，先买椭圆机试试，2 年后再升级也不迟",
    ["迈宝赫走步机折叠静音+最高10km/h+月销3500，有跑步习惯膝盖没问题", "舒华椭圆机磁控静音+零冲击+月销2200，膝盖有问题/体重偏大/怕吵邻居推荐", "Concept2 RowErg划船机+86%肌肉+超预算8500，预算充足最高效有氧"]
))

# 5. matching
T.append(make_traj(
    "sft_match_043", "matching_purchase", "搭配购物",
    "手冲咖啡整套器具搭配",
    "想入门手冲咖啡，配齐咖啡壶+滤杯+磨豆机+分享壶",
    {"query": "手冲咖啡器具 入门套装", "filters": {"category": "pour_over_coffee"}},
    [
        {"product_id": "mock_po_1", "title": "Hario V60 02 陶瓷滤杯 白色", "price": 129, "is_platform_self": True, "rating": 4.9, "key_specs": "Hario经典/陶瓷/02号适合1-4人/手冲标配", "sales": "月销1.5万"},
        {"product_id": "mock_po_2", "title": "Fellow Stagg EKG+ 电热手冲壶 600ml", "price": 999, "is_platform_self": True, "rating": 4.9, "key_specs": "1°精准控温/鹅颈壶口/Fellow旗舰", "sales": "月销2200"},
        {"product_id": "mock_po_3", "title": "Comandante C40 手动磨豆机", "price": 1099, "is_platform_self": True, "rating": 4.9, "key_specs": "德国Comandante/N66钢刀/手冲磨盘天花板", "sales": "月销850"},
        {"product_id": "mock_po_4", "title": "Hario V60 分享壶 600ml 玻璃", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "Hario玻璃分享壶/600ml/带刻度", "sales": "月销3500"}
    ],
    "手冲咖啡 4 件套 ¥2316，**专业入门配置**：\n\n## ☕ 完整方案\n\n| 器具 | 商品 | 价格 |\n|---|---|---|\n| 🥇 磨豆机 | **Comandante C40** | ¥1099 |\n| 手冲壶 | Fellow Stagg EKG+ | ¥999 |\n| 滤杯 | Hario V60 02 陶瓷 | ¥129 |\n| 分享壶 | Hario 玻璃分享壶 | ¥89 |\n\n## 💡 为什么把磨豆机排第一\n\n**手冲咖啡 80% 的味道来自研磨**——一台好磨豆机比贵 10 倍的咖啡壶更有价值。Comandante C40 是手动磨豆机的天花板，N66 钢刀研磨均匀度专业级。\n\n## 💡 入门可以降价的选择\n\n如果 ¥2316 太贵，可以替换：\n- 磨豆机 → 1Zpresso JX（¥499）省 ¥600\n- 手冲壶 → Bonavita（¥299）省 ¥700\n- **总价降到 ¥1000 内**\n\n但 Hario 滤杯+分享壶不建议换——本来就便宜，且是行业标准。",
    ["Hario V60 02陶瓷滤杯+手冲标配+月销1.5万，滤杯首选不用换", "Fellow Stagg EKG+ 1°精准控温+鹅颈壶口+月销2200，手冲壶旗舰", "Comandante C40 N66钢刀+德国品质+月销850，手动磨豆机天花板", "Hario玻璃分享壶600ml+带刻度+月销3500，分享壶标配不用换"]
))

# 6. matching
T.append(make_traj(
    "sft_match_044", "matching_purchase", "搭配购物",
    "国风旗袍整体穿搭",
    "买了一件改良旗袍参加婚宴，配什么包包+鞋子+发饰",
    {"query": "旗袍婚宴搭配 包包+鞋子", "filters": {"style": "qipao_banquet"}, "match_with": "improved_qipao"},
    [
        {"product_id": "mock_qp_1", "title": "国风刺绣小包 单肩宴会款 金色", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "刺绣工艺/金色/宴会专用/月销1200", "sales": "月销1200"},
        {"product_id": "mock_qp_2", "title": "旗袍专用绣花高跟鞋 5cm 包头", "price": 349, "is_platform_self": True, "rating": 4.8, "key_specs": "5cm包头跟/绣花/国风设计/站8h不累", "sales": "月销850"},
        {"product_id": "mock_qp_3", "title": "复古珍珠发簪 发钗 4件套", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "珍珠发簪+发钗/4件套/适合盘发", "sales": "月销4500"}
    ],
    "改良旗袍婚宴搭配 3 件套 ¥737，**国风仪式感拉满**：\n\n## 👗 完整方案\n\n| 单品 | 商品 | 价格 |\n|---|---|---|\n| 包包 | **国风刺绣小包 金色** | ¥299 |\n| 鞋子 | **旗袍专用绣花高跟鞋** | ¥349 |\n| 发饰 | 复古珍珠发簪 4 件套 | ¥89 |\n\n## 🎨 配色逻辑\n\n**旗袍颜色决定配件走向**：\n- **红色旗袍** → 金色包+金色鞋+珍珠白发簪（最经典）\n- **墨绿/藏蓝旗袍** → 金色包+黑色绣花鞋+珍珠发簪（高级感）\n- **粉色旗袍** → 粉金色包+裸色鞋+金色发簪（温柔感）\n\n## 💡 选品理由\n\n### 绣花高跟鞋必选 5cm 包头款\n婚宴站立和走动时间长，5cm 是最舒服的高跟高度；包头款比尖头耐穿更久。\n\n### 金色包比黑色更正确\n旗袍搭黑色包容易显沉，**金色和旗袍刺绣呼应**，1cm 的黄金比例配色。\n\n### 珍珠发饰是国风仪式感关键\n改良旗袍建议盘发+珍珠发簪，不要披发（显正式度不够）。",
    ["国风刺绣小包金色+宴会专用+月销1200，旗袍配金色包颜色最呼应", "旗袍专用绣花高跟鞋5cm包头+站8h不累+月销850，婚宴旗袍专用", "复古珍珠发簪4件套+月销4500，盘发必备仪式感翻倍"]
))

# 7. bundle
T.append(make_traj(
    "sft_bundle_041", "bundle_purchase", "组合购物",
    "2000 元大学生考研装备",
    "备考考研，2000 预算配齐学习装备",
    {"query": "考研学习装备 台灯+白噪音+平板+笔记本", "max_price": 2200},
    [
        {"product_id": "mock_kaoyan_1", "title": "明基 MindDuo 2 护眼台灯 国AA级", "price": 999, "is_platform_self": True, "rating": 4.9, "key_specs": "国AA级照度/防蓝光/智能调光/月销2200", "sales": "月销2200"},
        {"product_id": "mock_kaoyan_2", "title": "三福 考研错题本套装 12本 学科分类", "price": 69, "is_platform_self": True, "rating": 4.9, "key_specs": "12本/学科分类/错题管理/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "mock_kaoyan_3", "title": "大耳朵白噪音机 睡眠专注两用", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "白噪音/睡眠+专注两用/宿舍图书馆都能用", "sales": "月销3500"},
        {"product_id": "mock_kaoyan_4", "title": "番茄钟 物理计时 25分钟专注", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "物理番茄钟/无需充电/培养专注习惯", "sales": "月销1.5万"},
        {"product_id": "mock_kaoyan_5", "title": "考研专用真题全年笔记本 A5 12本", "price": 99, "is_platform_self": True, "rating": 4.8, "key_specs": "A5/考研专用/按科目分类/全年用量", "sales": "月销1.8万"}
    ],
    "考研学习装备 5 件套 ¥1455，余 ¥545：\n\n## 📚 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 🥇 台灯 | **明基 MindDuo 2 护眼台灯** | ¥999 |\n| 错题本 | 三福考研 12 本 | ¥69 |\n| 笔记本 | 考研专用 A5 12 本 | ¥99 |\n| 白噪音机 | 睡眠+专注两用 | ¥199 |\n| 番茄钟 | 物理计时 | ¥89 |\n\n## 💡 为什么护眼台灯是最重要的投资\n\n考研备考**每天 10+ 小时看书**，普通台灯近视加深 100-150 度/年。明基国 AA 级是最高标准，¥999 看起来贵，但**平均到备考 1 年每天 ¥2.7**，保护视力 1 年收益远大于成本。\n\n## 💡 白噪音机解决的两个问题\n\n1. **宿舍熄灯后** 还想多学 1 小时 → 戴耳机放白噪音不影响室友\n2. **图书馆人多嘈杂** → 白噪音覆盖周围声音提高专注\n\n## 💰 余 ¥545 加\n\n- 考研历年真题（¥100-300/科）\n- 护眼防蓝光眼镜 ¥80\n- 能量棒/营养品 ¥150\n- 打印机（用学校或打印店）",
    ["明基MindDuo 2护眼台灯+国AA级+防蓝光+月销2200，考研每天10h看书视力保护", "三福考研错题本12本+学科分类+月销2.5万，错题整理提分关键", "大耳朵白噪音机+睡眠专注两用+月销3500，宿舍/图书馆专注神器", "物理番茄钟25分钟+月销1.5万，培养考研专注习惯", "考研专用A5笔记本12本+月销1.8万，全年按科目分类够用"]
))

# 8. bundle
T.append(make_traj(
    "sft_bundle_042", "bundle_purchase", "组合购物",
    "6000 元新婚卧室家电套装",
    "新婚卧室家电，6000 配齐空调+除湿机+智能灯+音箱",
    {"query": "新婚卧室家电套装 空调+除湿+灯+音箱", "max_price": 6500},
    [
        {"product_id": "mock_marry_1", "title": "格力 KFR-26GW 1匹变频壁挂空调 一级能效", "price": 2399, "is_platform_self": True, "rating": 4.9, "key_specs": "1匹一级能效/15平米适用/静音22dB", "sales": "月销1.5万"},
        {"product_id": "mock_marry_2", "title": "美的 DH50 除湿机 50L/日 家用", "price": 1599, "is_platform_self": True, "rating": 4.8, "key_specs": "50L日除湿量/适合35-50㎡/南方梅雨必备", "sales": "月销4500"},
        {"product_id": "mock_marry_3", "title": "飞利浦智能卧室灯 可调色温 床头款", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "2700-6500K可调/助眠+起床模式/App控制", "sales": "月销6500"},
        {"product_id": "mock_marry_4", "title": "Sonos Era 100 卧室智能音箱", "price": 1799, "is_platform_self": True, "rating": 4.9, "key_specs": "Sonos品质/立体声/Trueplay自适应/月销1200", "sales": "月销1200"}
    ],
    "新婚卧室家电 4 件套 ¥6196，**超 ¥196 但配置合理**：\n\n## 🛏️ 完整方案\n\n| 家电 | 商品 | 价格 |\n|---|---|---|\n| 空调 | 格力 1 匹一级能效 | ¥2399 |\n| 除湿机 | 美的 50L | ¥1599 |\n| 智能灯 | 飞利浦可调色温 | ¥399 |\n| 音箱 | Sonos Era 100 | ¥1799 |\n| **合计** | | **¥6196** |\n\n## 💡 新婚卧室为什么要除湿机\n\n南方（江苏/浙江/广东/湖南）梅雨季卧室湿度 80%+，**被子湿哒哒、衣服晾不干**——除湿机是刚需，不是奢侈品。50L 除湿量覆盖 35-50㎡ 卧室。\n\n## 💡 可调色温灯是助眠关键\n\n- 晚上 2700K 暖光 → 促进褪黑素分泌 → 更快入睡\n- 早上 6500K 冷光 → 唤醒精神 → 不靠闹钟自然醒\n- **两口子睡前看书/刷手机的卧室氛围感**\n\n## 💰 压预算到 ¥6000\n\n- 砍掉 Sonos 换小爱音箱 ¥249 → 省 ¥1550，总 ¥4646\n- 但 Sonos 卧室音质是质的差别（睡前音乐/白噪音专用）\n- 建议两人商量：**音质敏感选 Sonos，省钱选小爱**",
    ["格力KFR-26GW 1匹一级能效+静音22dB+月销1.5万，卧室空调性价比首选", "美的DH50除湿机50L+月销4500，南方梅雨季卧室刚需", "飞利浦可调色温智能灯+助眠起床模式+月销6500，新婚卧室氛围感", "Sonos Era 100卧室智能音箱+Trueplay自适应+月销1200，睡前音乐/白噪音品质"]
))

# 9. place_order
T.append(make_traj(
    "sft_order_023", "place_order", "购物下单",
    "下单时选错规格+立刻修改",
    "刚下的那台空调选成 1.5 匹了，我要 1 匹，能改吗",
    {"action": "modify_spec", "original_order": "[ORDER_ID]", "new_spec": "1匹"},
    [
        {"product_id": "mock_ac_1p", "title": "格力 KFR-26GW 1匹 变频壁挂（已替换）", "price": 2399, "is_platform_self": True, "rating": 4.9, "key_specs": "订单已改为1匹款/原1.5匹退款/新订单[ORDER_ID]", "sales": "—"}
    ],
    "✅ 已帮你**取消原订单+下单 1 匹新款**！\n\n## 📋 操作详情\n\n### 原订单（1.5 匹）已取消\n- 订单号：[ORDER_ID]\n- 状态：**待出库 → 已取消**\n- 退款：¥2999 原路退回，1 个工作日到账\n\n### 新订单（1 匹）已下\n- 订单号：**[ORDER_ID]**\n- 商品：格力 KFR-26GW **1 匹**变频空调\n- 价格：¥2399\n- 比原 1.5 匹**便宜 ¥600**\n- 预计明天发货\n\n## 💡 1 匹 vs 1.5 匹选择参考\n\n| 房间面积 | 建议匹数 |\n|---|---|\n| 10-15㎡（小卧室）| **1 匹** ✅ |\n| 15-22㎡（主卧/次卧）| **1.5 匹** |\n| 22-30㎡（大卧室/书房）| 2 匹 |\n| 30-50㎡（客厅）| 3 匹 |\n\n**1 匹刚好适合 15㎡ 以内的小卧室**——如果你的房间是这个范围，选择完全正确。\n\n## ⚠️ 空调匹数选错的后果\n\n- **太小（1 匹配 25㎡）**：制冷/制热能力不足，一直高负荷运转→更耗电+寿命短\n- **太大（2 匹配 10㎡）**：频繁启停→不舒适+也耗电\n- 精准匹配才省电。",
    ["格力KFR-26GW 1匹变频壁挂+新订单[ORDER_ID]+比1.5匹省600元，10-15㎡刚好"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase
T.append(make_traj(
    "sft_repurchase_021", "repurchase", "复购召回",
    "复购+包装升级（替代送礼场景）",
    "上次买的那款红酒朋友很喜欢，想再买两瓶送朋友，要礼盒装的",
    {"category_keyword": "红酒", "time_range": "last_6_months", "gift_packaging": True},
    [
        {"product_id": "mock_wine_old", "title": "拉菲传奇波尔多 750ml (你3月前购买普通装)", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "你3月前购买/订单[ORDER_ID]/普通装", "sales": "月销1.5万"},
        {"product_id": "mock_wine_gift", "title": "拉菲传奇波尔多 2支礼盒装 含木盒", "price": 499, "is_platform_self": True, "rating": 4.9, "key_specs": "同款2支+实木礼盒/送礼标配/精美包装", "sales": "月销2500"},
        {"product_id": "mock_wine_single", "title": "拉菲传奇波尔多 750ml 单支礼盒", "price": 269, "is_platform_self": True, "rating": 4.9, "key_specs": "单支礼盒/精美礼盒包装/自带礼袋", "sales": "月销4500"}
    ],
    "查到你 3 个月前买的是 **拉菲传奇波尔多普通装 ¥199**（订单 [ORDER_ID]）。\n\n## 🍷 送礼方案\n\n### 方案 A：2 支礼盒套装 ¥499 ⭐ 推荐\n- 同款酒 × 2 支 + **实木礼盒**\n- 精美包装，直接送\n- 单支 ¥249.5（比单买 ¥199 贵 ¥50，差价全买包装和仪式感）\n\n### 方案 B：单支礼盒 × 2 ¥538\n- 每人送一支\n- 单支礼盒包装\n- 比 2 支套装贵 ¥39\n\n### 方案 C：普通装 × 2 ¥398\n- 最便宜\n- 包装平平，**送礼不好看**\n\n## 💡 我的建议\n\n**直接选 2 支礼盒套装 ¥499**：\n1. 送 1 个朋友更有仪式感（实木礼盒配精美礼袋）\n2. 比单买 2 支 ¥398 贵 ¥101，买的是包装溢价\n3. 你朋友喜欢这款味道，**同款更有诚意**\n\n要帮你直接下单 ¥499 礼盒套装吗？还是分开买 2 个单支礼盒？",
    ["拉菲传奇普通装你3月前购买+订单[TRACKING_ID]，同款口味已确认", "拉菲传奇2支实木礼盒套装+单支249.5+月销2500，送1个朋友最有仪式感", "拉菲传奇单支礼盒+精美礼袋+月销4500，分别送2个朋友首选"],
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
