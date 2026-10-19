# -*- coding: utf-8 -*-
"""Step 14: 第 2 批 - matching + bundle 共 14 条"""
import json
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "trajectories_final.jsonl"

def make_traj(tid, sc, cat, focus, query, tool_input, products, final_content, card_reasons, thinking="", multi_turn=False, history=None):
    cards = [{"card_id": p["product_id"], "display_price": p["price"], "reason": r} for p, r in zip(products, card_reasons)]
    return {
        "trajectory_id": tid, "scenario_type": sc, "category": cat, "quality_label": "good",
        "training_focus": focus, "is_multi_turn": multi_turn, "conversation_history": history or [],
        "user_query": query, "thinking": thinking or f"分析{focus}，调用工具召回 {len(products)} 款匹配项。",
        "steps": [
            {"step_id": 1, "step_type": "tool_call", "tool_name": "SkuRecallShopping", "tool_input": tool_input,
             "tool_output": {"status": "SUCCESS", "products": products}, "error_type": None},
            {"step_id": 2, "step_type": "final_response", "content": final_content, "product_cards": cards}
        ],
        "final_response": final_content, "eval_score": 1.0, "sft_source": "claude_local_v1"
    }


T = []

# ═══ matching_purchase (7 条) ═══
T.append(make_traj(
    "sft_match_010", "matching_purchase", "搭配购物",
    "服装搭配：黑色皮夹克配下装",
    "新买了一件黑色皮夹克，配什么裤子和鞋子帅气",
    {"query": "男士裤子 鞋子 配黑色皮夹克", "filters": {"style": "rock_streetwear"}, "match_with": "black_leather_jacket"},
    [
        {"product_id": "jd_pants_rock_001", "title": "Levi's 511 修身牛仔裤 深蓝水洗", "price": 599, "is_jd_self": True, "rating": 4.8, "key_specs": "修身/深蓝水洗/经典501升级", "sales": "月销1.5万"},
        {"product_id": "jd_pants_rock_002", "title": "工装直筒裤 黑色多袋款 oversize", "price": 399, "is_jd_self": True, "rating": 4.7, "key_specs": "黑色机能/直筒oversize", "sales": "月销3500"},
        {"product_id": "jd_shoes_rock", "title": "Dr.Martens 1460 黑色马丁靴 8孔", "price": 1499, "is_jd_self": True, "rating": 4.9, "key_specs": "经典8孔/真皮/摇滚标配", "sales": "月销2200"}
    ],
    "黑色皮夹克 = 摇滚/街头风的硬核单品。2 套方案：\n\n## 🔥 方案 A：经典摇滚风\n**Levi's 511 修身牛仔裤 ¥599 + Dr.Martens 1460 马丁靴 ¥1499**\n深蓝牛仔裤+黑皮衣+黑马丁靴是 50 年不变的摇滚铁三角。\n\n## 🔥 方案 B：街头机能风\n**黑色多袋工装裤 ¥399 + Dr.Martens ¥1499**\n全黑配色 + 机能感工装裤，**潮流博主最爱拍照组合**。\n\n## ⚠️ 避雷\n- ❌ 浅色西裤：完全风格冲突\n- ❌ 运动鞋（除非是 AJ1 黑红配）：休闲过头压不住皮衣\n- ❌ 紧身瘦腿裤：和皮衣的厚重不平衡",
    ["Levi's 511修身深蓝水洗+经典摇滚铁三角", "黑色机能工装裤oversize直筒+街头风潮博必备", "Dr.Martens 1460黑色8孔真皮+摇滚标配50年不过时"]
))

T.append(make_traj(
    "sft_match_011", "matching_purchase", "搭配购物",
    "家居搭配：客厅地毯配色",
    "客厅米色沙发+原木地板，配什么颜色的地毯",
    {"query": "客厅地毯 短毛 易打理", "filters": {"colors": ["米色", "驼色", "灰白", "藏蓝"], "size_cm": "200x300"}, "match_with": "beige_sofa_oak_floor"},
    [
        {"product_id": "jd_rug_001", "title": "无印良品 米色短毛地毯 200×300", "price": 899, "is_jd_self": True, "rating": 4.8, "key_specs": "米色同色系/短毛易吸尘/200×300适合大客厅", "sales": "月销1200"},
        {"product_id": "jd_rug_002", "title": "宜家 STOCKHOLM 灰白几何地毯 240×170", "price": 1299, "is_jd_self": True, "rating": 4.9, "key_specs": "灰白几何/手工编织/对比色提亮", "sales": "月销850"},
        {"product_id": "jd_rug_003", "title": "藏蓝色波斯风格地毯 200×280", "price": 1499, "is_jd_self": True, "rating": 4.7, "key_specs": "藏蓝色波斯纹/对比色制造焦点/200×280", "sales": "月销520"}
    ],
    "米色沙发+原木地板=暖色基调，地毯有 3 种思路：\n\n## 🎨 1. 同色系沉稳：MUJI 米色 ¥899 ⭐\n地毯+沙发同色，**空间整体感最强**。短毛易吸尘养宠/有娃家庭友好。\n\n## 🎨 2. 灰白提亮：宜家 STOCKHOLM ¥1299\n灰白几何纹**让暖色调不显闷**，最 ins 风的选择。\n\n## 🎨 3. 深色制造焦点：藏蓝波斯 ¥1499\n沙发地板都是浅色，**深色地毯是视觉焦点**，适合追求设计感的家。\n\n选 MUJI 同色系最稳；要打破单调选灰白；玩设计选藏蓝。",
    ["MUJI米色短毛同色系+200×300适合大客厅，整体感最强", "宜家灰白几何手工编织+对比色提亮，ins风最受欢迎", "藏蓝波斯纹深色焦点+对比制造视觉中心，设计感家庭首选"]
))

T.append(make_traj(
    "sft_match_012", "matching_purchase", "搭配购物",
    "服装搭配：连衣裙配外套",
    "夏天买的米白色雪纺连衣裙，过渡季配什么外套",
    {"query": "女士过渡季外套 雪纺裙搭配", "filters": {"colors": ["奶咖", "燕麦", "藏蓝", "黑色"], "season": "spring_autumn"}, "match_with": "white_chiffon_dress"},
    [
        {"product_id": "jd_jacket_001", "title": "ITS 奶咖色羊毛西装外套 oversize", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "奶咖色/oversize/同色系温柔", "sales": "月销3500"},
        {"product_id": "jd_jacket_002", "title": "三福 牛仔外套 浅蓝水洗 修身款", "price": 199, "is_jd_self": True, "rating": 4.7, "key_specs": "浅蓝/修身/经典百搭", "sales": "月销1.5万"},
        {"product_id": "jd_jacket_003", "title": "无印良品 黑色短款风衣 防水面料", "price": 899, "is_jd_self": True, "rating": 4.8, "key_specs": "黑色短款/防水/简约通勤", "sales": "月销1200"}
    ],
    "米白雪纺裙是温柔单品，外套决定整套风格走向：\n\n## 🎨 方案 1：温柔奶系（约会/拍照）\n**ITS 奶咖色羊毛西装 ¥599** ⭐\n奶咖×米白=温柔莫兰迪，oversize 西装+雪纺裙是当下最火的配方。\n\n## 🎨 方案 2：清新少女（日常）\n**三福浅蓝牛仔外套 ¥199**\n经典少女配色，价格最低，月销 1.5 万件人手一件。\n\n## 🎨 方案 3：干练通勤（上班）\n**MUJI 黑色短款风衣 ¥899**\n黑×米白对比制造干练感，适合周一到周五。",
    ["奶咖×米白温柔莫兰迪+oversize西装，约会拍照最火配方", "浅蓝牛仔×米白清新少女+月销1.5万，¥199人手一件", "黑×米白干练对比+防水风衣+简约通勤，工作日刚需"]
))

T.append(make_traj(
    "sft_match_013", "matching_purchase", "搭配购物",
    "家居搭配：餐厅吊灯",
    "餐厅刚装好北欧风，1.4米实木餐桌配什么吊灯",
    {"query": "餐厅吊灯 北欧风", "filters": {"style": "nordic", "materials": ["藤编", "白色金属", "木质"], "for_table_length_m": 1.4}, "match_with": "nordic_dining_room"},
    [
        {"product_id": "jd_lamp_001", "title": "无印良品 藤编吊灯 北欧手工 直径40cm", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "藤编手工/40cm/暖光2700K", "sales": "月销680"},
        {"product_id": "jd_lamp_002", "title": "Muuto 同款 白色金属吊灯 极简款", "price": 899, "is_jd_self": True, "rating": 4.8, "key_specs": "白色金属/极简北欧/可调高度", "sales": "月销380"},
        {"product_id": "jd_lamp_003", "title": "宜家 SINNERLIG 竹编吊灯 大号", "price": 399, "is_jd_self": True, "rating": 4.8, "key_specs": "竹编/大号45cm/¥399平价北欧", "sales": "月销1500"}
    ],
    "北欧餐厅吊灯=自然材质+柔和光线。1.4m 餐桌建议 1 盏大灯（直径 40-50cm）：\n\n## 🎨 风格 1：温暖手工感\n**MUJI 藤编吊灯 ¥599** ⭐\n藤编+暖光是北欧最经典的餐厅光源，光线透过藤条形成阴影氛围感。\n\n## 🎨 风格 2：极简设计感\n**Muuto 同款白色金属 ¥899**\n白色金属极简款，**适合工业风+北欧混搭**。\n\n## 🎨 风格 3：平价竹编\n**宜家 SINNERLIG ¥399**\n竹编效果接近藤编，**便宜 200 元**适合预算紧家庭。",
    ["MUJI藤编手工+暖光2700K+40cm，北欧餐厅最经典氛围灯", "Muuto白色金属极简+可调高度，工业+北欧混搭首选", "宜家竹编平价北欧+¥399大号45cm，预算紧家庭性价比"]
))

T.append(make_traj(
    "sft_match_014", "matching_purchase", "搭配购物",
    "电脑桌面整体配色",
    "我书房整体白色，电脑桌面想统一白色系，键盘鼠标显示器有什么推荐",
    {"query": "白色电脑配件套装 颜值党", "filters": {"colors": ["白色", "纯白"]}, "match_with": "white_desktop_setup"},
    [
        {"product_id": "jd_kb_white", "title": "ikbc 白色机械键盘 87键 樱桃轴", "price": 499, "is_jd_self": True, "rating": 4.9, "key_specs": "纯白配色/樱桃Cherry轴/87键紧凑", "sales": "月销4500"},
        {"product_id": "jd_mouse_white", "title": "罗技 M650 白色无线鼠标 静音版", "price": 199, "is_jd_self": True, "rating": 4.8, "key_specs": "纯白/静音点击/双模蓝牙", "sales": "月销1.5万"},
        {"product_id": "jd_disp_white", "title": "AOC U27N3 27寸 4K 白色显示器", "price": 1899, "is_jd_self": True, "rating": 4.8, "key_specs": "纯白机身+底座/27寸4K/Type-C", "sales": "月销1200"}
    ],
    "白色系桌面要点：**所有外设统一白色**（包括线材）。3 件配齐：\n\n## ⌨️ 键盘：ikbc 白色机械 ¥499\n樱桃 Cherry 轴+纯白配色，87键紧凑款不占地。月销 4500 件。\n\n## 🖱️ 鼠标：罗技 M650 白色 ¥199\n静音点击不扰邻，双模蓝牙+USB 接收器适配所有设备。\n\n## 🖥️ 显示器：AOC U27N3 ¥1899\n**白色机身的 4K 显示器不多，AOC 这款是少数**。Type-C 单线连接笔记本。\n\n**额外建议**：买白色编织线（数据线/电源线）¥30-50/根，整体颜值再升一档。",
    ["ikbc白色机械Cherry轴87键+月销4500，白色桌面键盘标配", "罗技M650白色静音+双模蓝牙，月销1.5万白色鼠标首选", "AOC白色4K显示器+Type-C单线，白色系少数派显示器"]
))

T.append(make_traj(
    "sft_match_015", "matching_purchase", "搭配购物",
    "运动套装：跑步全装备",
    "夏天开始跑步，配一身跑步装备，包含衣服鞋子袜子运动表",
    {"query": "夏季跑步装备 速干透气", "filters": {"category": "running_gear", "season": "summer"}, "match_with": "summer_running"},
    [
        {"product_id": "jd_run_top", "title": "Nike Dri-FIT 速干跑步T恤", "price": 199, "is_jd_self": True, "rating": 4.9, "key_specs": "Dri-FIT速干/反光条/夏季透气", "sales": "月销1.5万"},
        {"product_id": "jd_run_short", "title": "Adidas Run Icons 跑步短裤 内置内衬", "price": 259, "is_jd_self": True, "rating": 4.8, "key_specs": "内置内衬+侧袋/速干面料", "sales": "月销8500"},
        {"product_id": "jd_run_socks", "title": "Stance 专业跑步袜 3 双装", "price": 159, "is_jd_self": True, "rating": 4.9, "key_specs": "中筒/防滑垫/3双装", "sales": "月销4500"},
        {"product_id": "jd_run_shoes", "title": "Adidas Boston 12 男款跑步鞋 42码", "price": 1099, "is_jd_self": True, "rating": 4.9, "key_specs": "Lightstrike Pro中底/碳板/竞速训练", "sales": "月销3500"}
    ],
    "夏季跑步装备核心 = **速干 + 反光（安全）**。4 件齐：\n\n## 🏃 跑步全装备 ¥1716\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 上衣 | Nike Dri-FIT T恤（速干+反光条）| ¥199 |\n| 短裤 | Adidas Run Icons（内置内衬）| ¥259 |\n| 袜子 | Stance 跑步袜 3 双装 | ¥159 |\n| 鞋子 | **Adidas Boston 12 碳板跑鞋** | ¥1099 |\n\n## 💡 选品理由\n\n1. **Dri-FIT 速干 T**：纯棉跑步会吸汗发重，速干面料是夏季刚需\n2. **内置内衬短裤**：避免摩擦+不用单买内裤\n3. **3 双袜子轮换**：跑步袜防起水泡，必须专业款\n4. **Boston 12 碳板**：兼顾训练 + 半马，是跑步进阶天花板\n\n## 💎 加一件神器（可选）\n\n**佳明 Forerunner 165 运动表 ¥1499**：GPS+心率+配速，跑步数据可视化是坚持下来的关键。",
    ["Nike Dri-FIT速干+反光条夏季透气，安全跑步必备", "Adidas Run Icons内置内衬+侧袋+速干，免单买内裤", "Stance专业跑步袜3双装+防滑垫，跑步起水泡刚需", "Adidas Boston 12碳板跑鞋+Lightstrike Pro，训练半马进阶首选"]
))

T.append(make_traj(
    "sft_match_016", "matching_purchase", "搭配购物",
    "卫浴整体搭配",
    "卫生间装修白色调，配什么浴室柜、水龙头、毛巾架",
    {"query": "卫浴套装 白色现代风", "filters": {"colors": ["白色", "银色", "金色"], "style": "modern"}, "match_with": "white_bathroom"},
    [
        {"product_id": "jd_cab_001", "title": "九牧 白色实木浴室柜 90cm 含台盆", "price": 1899, "is_jd_self": True, "rating": 4.9, "key_specs": "白色实木+陶瓷台盆/90cm/防潮", "sales": "月销2200"},
        {"product_id": "jd_tap_001", "title": "汉斯格雅 白色+银色水龙头 抽拉式", "price": 999, "is_jd_self": True, "rating": 4.9, "key_specs": "白色+银色拼接/抽拉式/陶瓷阀芯10年", "sales": "月销1500"},
        {"product_id": "jd_rack_001", "title": "九牧 不锈钢毛巾架 太空铝拉丝白", "price": 299, "is_jd_self": True, "rating": 4.8, "key_specs": "拉丝白/304不锈钢/双层毛巾位", "sales": "月销4500"}
    ],
    "白色卫浴 3 件套配齐 ¥3197：\n\n## 🛁 完整方案\n\n| 用品 | 商品 | 价格 |\n|---|---|---|\n| 浴室柜 | **九牧白色实木 90cm 含台盆** | ¥1899 |\n| 水龙头 | **汉斯格雅白+银抽拉式** | ¥999 |\n| 毛巾架 | 九牧拉丝白双层 | ¥299 |\n| **合计** | | **¥3197** |\n\n## 💡 选品理由\n\n1. **九牧+汉斯格雅同体系**：白色色调统一，光泽度一致\n2. **白色实木≠普通柜**：实木+多层防潮处理，比 PVC 板贵但用 10 年不发霉\n3. **抽拉龙头**：洗头/清洁台面方便\n4. **太空铝毛巾架**：防锈+轻量+承重 30kg\n\n## ⚠️ 避雷\n\n- ❌ **白色搭配金色金属**（除非新中式风格）\n- ❌ 不同品牌混搭：白的色温会不一致，整体看着脏\n- ❌ 廉价 PVC 浴室柜：南方潮湿地区 2 年发霉",
    ["九牧白色实木浴室柜含台盆+90cm防潮，10年不发霉品质", "汉斯格雅白+银抽拉式陶瓷阀芯10年保修，洗头清洁方便", "九牧拉丝白304不锈钢双层毛巾架，防锈轻量承重30kg"]
))


# ═══ bundle_purchase (7 条) ═══
T.append(make_traj(
    "sft_bundle_008", "bundle_purchase", "组合购物",
    "6000 元全屋净水方案",
    "新房想做全屋净水，6000 预算从前置过滤到末端直饮",
    {"query": "全屋净水系统 前置+中央+末端", "max_price": 6500, "filters": {"category": "water_purification"}},
    [
        {"product_id": "jd_water_001", "title": "汉斯希尔 前置过滤器 反冲洗款", "price": 1099, "is_jd_self": True, "rating": 4.9, "key_specs": "前置/40微米/反冲洗/装在水表后", "sales": "月销1.5万"},
        {"product_id": "jd_water_002", "title": "3M 中央净水器 大流量 5年滤芯", "price": 2299, "is_jd_self": True, "rating": 4.8, "key_specs": "中央/活性炭+KDF/5年滤芯", "sales": "月销3500"},
        {"product_id": "jd_water_003", "title": "小米 RO 反渗透净水器 厨下式直饮", "price": 1999, "is_jd_self": True, "rating": 4.9, "key_specs": "末端RO反渗透/直饮级/智能APP", "sales": "月销2.2万"}
    ],
    "全屋净水 = **3 级过滤** 才完整。6000 预算刚好覆盖：\n\n## 💧 完整方案 ¥5397\n\n| 位置 | 商品 | 价格 | 作用 |\n|---|---|---|---|\n| 🥇 前置 | **汉斯希尔反冲洗款** | ¥1099 | 拦截泥沙铁锈（保护后续）|\n| 🥈 中央 | **3M 大流量 5 年滤芯** | ¥2299 | 全屋去除余氯异味 |\n| 🥉 末端 | **小米 RO 反渗透厨下** | ¥1999 | 直饮级（替代瓶装水）|\n| **合计** | | **¥5397**（余 603）|\n\n## 💡 为什么 3 级都要\n\n- **只装末端**：水管输送过程的余氯/铁锈进不到饮用水，但洗澡洗碗还是脏水\n- **只装前置**：粗过滤够不到饮用级别\n- **3 级齐**：洗澡、洗菜、直饮都达标，**才是真正全屋净水**\n\n## 💰 余 ¥603 可加\n\n- 软水机（南方水硬地区）¥500\n- 智能水监测器 ¥200\n\n## ⚠️ 装修时机\n\n**必须在水电改造时装前置和中央**，墙都封了就来不及了。末端可以后期装。",
    ["汉斯希尔前置反冲洗+40微米拦截泥沙铁锈，保护后续滤芯必备", "3M中央大流量+5年滤芯+全屋去氯，洗澡洗菜安全升级", "小米RO反渗透厨下式直饮级+智能APP，瓶装水替代月销2.2万"]
))

T.append(make_traj(
    "sft_bundle_009", "bundle_purchase", "组合购物",
    "3500 元程序员桌面",
    "程序员桌面升级 3500，键鼠+人体工学+护眼",
    {"query": "程序员桌面套装 机械键盘+人体工学椅+护眼台灯", "max_price": 3800},
    [
        {"product_id": "jd_dev_kb", "title": "HHKB Professional Hybrid 静电容键盘", "price": 1899, "is_jd_self": True, "rating": 4.9, "key_specs": "静电容Topre轴/60键紧凑/程序员神器", "sales": "月销680"},
        {"product_id": "jd_dev_mouse", "title": "罗技 MX Master 3S 旗舰办公鼠标", "price": 699, "is_jd_self": True, "rating": 4.9, "key_specs": "全键静音/3设备切换/70天续航", "sales": "月销1.5万"},
        {"product_id": "jd_dev_chair", "title": "西昊 Doro C300 人体工学椅", "price": 1499, "is_jd_self": True, "rating": 4.9, "key_specs": "4D扶手/腰托/网布透气/承重150kg", "sales": "月销1.8万"},
        {"product_id": "jd_dev_lamp", "title": "明基 ScreenBar Halo 屏幕挂灯", "price": 199, "is_jd_self": True, "rating": 4.9, "key_specs": "屏幕挂灯/前后双光源/无线遥控", "sales": "月销2200"}
    ],
    "程序员桌面要点：**键盘是吃饭工具，椅子是身体本钱**。4 件配齐 ¥4296，**超预算 ¥796**——但我不建议砍：\n\n## 💻 完整方案 ¥4296\n\n| 装备 | 商品 | 价格 | 程序员价值 |\n|---|---|---|---|\n| 🥇 键盘 | **HHKB 静电容** | ¥1899 | Topre 轴是码农圣杯，省手腕 |\n| 椅子 | **西昊 Doro C300** | ¥1499 | 8h+ 久坐刚需 |\n| 鼠标 | 罗技 MX Master 3S | ¥699 | 静音+横向滚轮 |\n| 屏幕挂灯 | 明基 ScreenBar Halo | ¥199 | 护眼必备 |\n\n## 🎯 砍预算方案 ¥3197\n\n如果硬要 3500 以内：\n- HHKB → **ikbc C87 樱桃轴 ¥499**（省 1400）\n- 其他不变\n- 总计 ¥2896（余 604）\n\n但 **HHKB 是码农神器**：60% 紧凑布局+Topre 轴手感无敌，写代码 5 年也不卷键，**只要你做这行就值这 ¥1899**。\n\n## 💡 我的建议\n\n如果你工作 3 年+确定继续做程序员，**超预算 ¥796 上 HHKB**，平均到 5 年每月 ¥15 买顶级码农工具。\n\n如果刚入行试试水，先 ikbc + 其他 3 件，**等加薪了再升级键盘**。",
    ["HHKB静电容Topre轴+60键紧凑+月销680小众神器，程序员圣杯", "西昊Doro C300 4D扶手+腰托+承重150kg，8h+久坐健康刚需", "罗技MX Master 3S全键静音+横向滚轮+70天续航，开会神器", "明基ScreenBar Halo屏幕挂灯+前后双光源+无线遥控，长期护眼"]
))

T.append(make_traj(
    "sft_bundle_010", "bundle_purchase", "组合购物",
    "2500 元化妆台基础套装",
    "搬新家化妆台空了，2500 预算配齐化妆镜+收纳+护肤套装",
    {"query": "化妆台套装 化妆镜+收纳+护肤", "max_price": 2800},
    [
        {"product_id": "jd_makeup_001", "title": "AMIRO 智能化妆镜 LED 三色光", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "三色光/可调亮度/无影补光", "sales": "月销1.2万"},
        {"product_id": "jd_makeup_002", "title": "亚克力化妆品收纳盒 大容量分层", "price": 199, "is_jd_self": True, "rating": 4.8, "key_specs": "亚克力透明/分层抽屉/口红格", "sales": "月销1.8万"},
        {"product_id": "jd_makeup_003", "title": "兰蔻 小黑瓶肌底液 50ml", "price": 1080, "is_jd_self": True, "rating": 4.9, "key_specs": "二裂酵母/抗老精华/明星单品", "sales": "月销4500"},
        {"product_id": "jd_makeup_004", "title": "雅诗兰黛 樱花水 200ml 化妆水", "price": 580, "is_jd_self": True, "rating": 4.8, "key_specs": "樱花调湿润/温和不刺激", "sales": "月销2200"}
    ],
    "化妆台 2500 预算分配：**镜子(20%)+收纳(10%)+护肤精华(70%)**。4 件 ¥2458 配齐：\n\n## 💄 完整方案\n\n| 用品 | 商品 | 价格 |\n|---|---|---|\n| 🔦 化妆镜 | **AMIRO 智能 LED 三色光** | ¥599 |\n| 📦 收纳 | 亚克力分层收纳盒 | ¥199 |\n| 💧 化妆水 | 雅诗兰黛樱花水 | ¥580 |\n| 💉 精华 | **兰蔻小黑瓶** | ¥1080 |\n| **合计** | | **¥2458** |\n\n## 💡 选品理由\n\n1. **AMIRO 三色光**：白光/暖光/自然光切换，化妆颜色不会偏差（普通灯下化妆出门变色）\n2. **亚克力收纳**：透明一眼找到，比抽屉收纳神器\n3. **兰蔻小黑瓶**：是抗老起手第一支精华\n4. **雅诗兰黛樱花水**：清爽不黏，所有肤质通用\n\n## ⚠️ 避坑\n\n- ❌ 不要先囤面膜：开封后保质期短，先打好基础\n- ❌ 不要买廉价化妆镜：补光不均化妆会偏色",
    ["AMIRO智能LED三色光+无影补光+月销1.2万，化妆颜色不偏差", "亚克力透明分层收纳+口红格，化妆台一目了然", "兰蔻小黑瓶二裂酵母抗老+明星单品，护肤起手第一支精华", "雅诗兰黛樱花水温润+全肤质通用，日常化妆水首选"]
))

T.append(make_traj(
    "sft_bundle_011", "bundle_purchase", "组合购物",
    "4500 元小厨房刚需家电",
    "新房 8 平米小厨房，4500 配齐微波炉/电饭煲/电水壶/料理机",
    {"query": "小厨房刚需家电套装", "max_price": 4800, "filters": {"size": "compact"}},
    [
        {"product_id": "jd_kit_001", "title": "美的 PG2310W 微蒸烤一体机 35L", "price": 2599, "is_jd_self": True, "rating": 4.8, "key_specs": "微+蒸+烤三合一/嵌入式不占台面", "sales": "月销5500"},
        {"product_id": "jd_kit_002", "title": "美的 SF40 智能电饭煲 4L IH加热", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "4L/IH电磁加热/24小时预约", "sales": "月销1.5万"},
        {"product_id": "jd_kit_003", "title": "苏泊尔 1.7L 304不锈钢电水壶 防干烧", "price": 159, "is_jd_self": True, "rating": 4.9, "key_specs": "1.7L/304不锈钢/防干烧+保温", "sales": "月销5万"},
        {"product_id": "jd_kit_004", "title": "美的 BL1572A Plus 自清洁破壁机", "price": 699, "is_jd_self": True, "rating": 4.7, "key_specs": "8叶钝刀/一键自洗/早餐豆浆", "sales": "月销9500"}
    ],
    "8 平米小厨房 = **省空间是核心**。4 件 ¥4056 配齐：\n\n## 🍳 完整方案\n\n| 家电 | 商品 | 价格 | 节省空间 |\n|---|---|---|---|\n| 🥇 微蒸烤 | **美的微蒸烤一体 35L** | ¥2599 | **嵌入式不占台面**（顶 3 台）|\n| 电饭煲 | 美的 IH 智能 4L | ¥599 | 标准 |\n| 电水壶 | 苏泊尔 1.7L 304 | ¥159 | 标准 |\n| 破壁机 | 美的自清洁 | ¥699 | 标准 |\n| **合计** | | **¥4056** | 余 ¥744 |\n\n## 💡 关键决策：微蒸烤 vs 单买\n\n如果你单买**微波炉 ¥600+蒸箱 ¥1500+烤箱 ¥1000 = ¥3100**，便宜 ¥500。但：\n- 占 3 个台面位置（小厨房灾难）\n- 同时用 3 台跳闸\n- 接 3 根插座\n\n**¥2599 微蒸烤一体是小厨房刚需**，多花 ¥500 买空间。\n\n## 💰 余 ¥744 可加\n\n- 油烟机+灶具升级款（¥500）\n- 净水器末端（¥300-500）\n- 早餐机/三明治机（¥200）",
    ["美的微蒸烤一体3合1+嵌入式不占台面+月销5500，小厨房省空间刚需", "美的IH电饭煲4L+24小时预约+月销1.5万，3-4口家庭刚需", "苏泊尔1.7L 304不锈钢电水壶+防干烧+月销5万，烧水标配", "美的破壁机8叶钝刀+一键自洗，早餐豆浆果汁全能"]
))

T.append(member_quick := make_traj(
    "sft_bundle_012", "bundle_purchase", "组合购物",
    "1000 元宝宝洗澡用品",
    "宝宝出生准备洗澡用品，1000 预算全套",
    {"query": "宝宝洗澡套装 浴盆+浴床+水温+沐浴露", "max_price": 1100, "filters": {"category": "baby_bath"}},
    [
        {"product_id": "jd_baby_001", "title": "蒂爱 婴儿浴盆 折叠款 0-3岁可用", "price": 299, "is_jd_self": True, "rating": 4.9, "key_specs": "折叠不占地/0-3岁通用/带水温显示", "sales": "月销1.2万"},
        {"product_id": "jd_baby_002", "title": "蒂爱 浴床防滑款 新生儿适用", "price": 169, "is_jd_self": True, "rating": 4.8, "key_specs": "防滑/0-6月新生儿/可拆洗", "sales": "月销8500"},
        {"product_id": "jd_baby_003", "title": "贝亲 婴儿沐浴露+洗发二合一 500ml", "price": 89, "is_jd_self": True, "rating": 4.9, "key_specs": "二合一/无泪配方/弱酸性", "sales": "月销4.5万"},
        {"product_id": "jd_baby_004", "title": "迪宝乐 智能水温计 浮水款", "price": 79, "is_jd_self": True, "rating": 4.8, "key_specs": "智能显示/防水浮水/超温警报", "sales": "月销1.8万"},
        {"product_id": "jd_baby_005", "title": "全棉时代 婴儿浴巾 110×110cm A类", "price": 159, "is_jd_self": True, "rating": 4.9, "key_specs": "A类纯棉/110×110cm/包裹宝宝", "sales": "月销2.2万"}
    ],
    "宝宝洗澡 5 件套 ¥795，余 ¥205 备用：\n\n## 🛁 完整方案\n\n| 用品 | 商品 | 价格 |\n|---|---|---|\n| 浴盆 | 蒂爱折叠浴盆（带水温显示）| ¥299 |\n| 浴床 | 蒂爱防滑浴床（0-6月）| ¥169 |\n| 浴巾 | 全棉时代 A 类纯棉 | ¥159 |\n| 沐浴露 | 贝亲二合一无泪 | ¥89 |\n| 水温计 | 智能浮水款 | ¥79 |\n| **合计** | | **¥795** |\n\n## 💡 必备 vs 可缓买\n\n**必备**：浴盆+浴床+沐浴露+浴巾（4 件）\n**可缓**：水温计（浴盆带显示其实够了）\n\n## ⚠️ 选品理由\n\n1. **折叠浴盆**：小户型救星，洗完挂墙节省 0.5㎡\n2. **浴床**：0-6 月宝宝软趴趴，浴床承托避免溺水\n3. **A 类纯棉浴巾**：婴儿皮肤接触必须 A 类（最高安全标准）\n4. **二合一沐浴**：宝宝洗发+沐浴不分开（婴儿头发少没必要分）\n\n## 💰 余 ¥205\n\n- 婴儿浴室椅（坐着洗，6 月+）¥80\n- 婴儿润肤油（洗澡后涂）¥80\n- 防滑垫 ¥30",
    ["蒂爱折叠浴盆+带水温显示+0-3岁通用，小户型挂墙节省空间", "蒂爱浴床防滑+0-6月新生儿专用，软趴趴宝宝承托防溺水", "全棉时代A类纯棉110×110cm+婴儿皮肤最高安全标准", "贝亲二合一无泪沐浴+弱酸性+月销4.5万，宝宝洗发沐浴一瓶搞定", "智能水温计浮水款+超温警报，避免烫伤宝宝"]
))

T.append(make_traj(
    "sft_bundle_013", "bundle_purchase", "组合购物",
    "7000 元自媒体拍摄装备",
    "想做自媒体，7000 预算配相机+稳定器+麦克风+灯光",
    {"query": "自媒体拍摄装备 vlog 相机+稳定器+灯", "max_price": 7500},
    [
        {"product_id": "jd_vlog_001", "title": "索尼 ZV-1F 4K Vlog 数码相机", "price": 3499, "is_jd_self": True, "rating": 4.9, "key_specs": "1英寸大底/4K视频/Vlog定位", "sales": "月销4500"},
        {"product_id": "jd_vlog_002", "title": "大疆 RS 3 Mini 稳定器", "price": 1899, "is_jd_self": True, "rating": 4.9, "key_specs": "1kg轻量/3轴稳定/无线蓝牙快门", "sales": "月销2200"},
        {"product_id": "jd_vlog_003", "title": "罗德 Wireless GO II 无线领夹麦", "price": 1499, "is_jd_self": True, "rating": 4.9, "key_specs": "双通道无线麦/收音之王", "sales": "月销1500"},
        {"product_id": "jd_vlog_004", "title": "南光 LED 双色温补光灯 圆形便携", "price": 269, "is_jd_self": True, "rating": 4.8, "key_specs": "双色温3200-6500K/便携可手持", "sales": "月销3500"}
    ],
    "自媒体新手 4 件套 ¥7166，**专业起步配置**：\n\n## 🎬 完整方案\n\n| 装备 | 商品 | 价格 | 自媒体价值 |\n|---|---|---|---|\n| 🥇 相机 | **索尼 ZV-1F 4K Vlog** | ¥3499 | 一英寸大底是 Vlog 画质门槛 |\n| 稳定器 | 大疆 RS 3 Mini | ¥1899 | 走路拍不抖刚需 |\n| 麦克风 | **罗德 Wireless GO II** | ¥1499 | 收音决定 50% 视频质感 |\n| 补光灯 | 南光 LED 双色温 | ¥269 | 室内拍摄必备 |\n| **合计** | | **¥7166** |\n\n## 💡 选品逻辑\n\n1. **画质 ≠ 流量**：观众更在意「**收音清晰 + 画面稳**」而不是 4K vs 8K\n2. **罗德 Wireless GO II 是行业标杆**：双通道可同时收 2 个人，访谈类必备\n3. **索尼 ZV-1F**：Vlog 专属定位，一键美颜+对焦人脸，**不需要后期就能直出**\n4. **稳定器+补光**：让画面专业度从「业余」直接跳到「准 KOL」\n\n## 🎯 这套适合\n\n- 美食 / 旅行 / 日常 Vlog\n- 知识分享 / 访谈\n- 探店 / 测评\n\n## ⚠️ 不适合\n\n- 风光摄影（需要单反+长焦镜头，预算 ¥15000+）\n- 短剧/电影（需要专业摄像机，¥30000+）\n\n## 💰 进阶可加\n\n用了 3 个月发现真有兴趣再加：\n- 全画幅相机（A7M4）¥15000\n- 提词器 ¥500\n- 蓝牙鼠标遥控 ¥100",
    ["索尼ZV-1F一英寸大底+4K Vlog定位+一键美颜，新手不需后期直出", "大疆RS 3 Mini稳定器1kg轻量+3轴稳定，走路拍不抖刚需", "罗德Wireless GO II双通道无线麦+访谈必备，收音决定50%质感", "南光LED双色温3200-6500K+便携可手持，室内补光准KOL水准"]
))

T.append(make_traj(
    "sft_bundle_014", "bundle_purchase", "组合购物",
    "5000 元父母全屋健康监测",
    "想给爸妈装一套家用健康监测设备，5000 预算",
    {"query": "老人健康监测套装 血压+血糖+体脂+心电", "max_price": 5500, "filters": {"category": "elder_health"}},
    [
        {"product_id": "jd_eld_001", "title": "欧姆龙 U10L 上臂式电子血压计 智能", "price": 269, "is_jd_self": True, "rating": 4.9, "key_specs": "医用级精准/语音播报/90组记忆", "sales": "月销4.2万"},
        {"product_id": "jd_eld_002", "title": "强生 OneTouch 血糖仪+50条试纸", "price": 399, "is_jd_self": True, "rating": 4.9, "key_specs": "5秒出值/含50条试纸/手机同步", "sales": "月销1.5万"},
        {"product_id": "jd_eld_003", "title": "华为体脂秤 3 Pro 心率+心电图", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "11项体成分+心率+心电图", "sales": "月销1.2万"},
        {"product_id": "jd_eld_004", "title": "鱼跃 制氧机 1L 家用静音款", "price": 1999, "is_jd_self": True, "rating": 4.8, "key_specs": "1L/min/医用级氧浓度/静音<45dB", "sales": "月销680"},
        {"product_id": "jd_eld_005", "title": "华为 Watch GT4 老人款 GPS定位+SOS", "price": 1488, "is_jd_self": True, "rating": 4.9, "key_specs": "GPS定位+一键SOS+跌倒检测", "sales": "月销1.8万"}
    ],
    "父母健康监测 5 件套 ¥4754，余 ¥246 备用：\n\n## ❤️ 完整方案\n\n| 监测项 | 商品 | 价格 | 频次 |\n|---|---|---|---|\n| 🥇 血压 | **欧姆龙 U10L 智能血压计** | ¥269 | 每天 |\n| 血糖 | 强生 OneTouch+50 条试纸 | ¥399 | 糖尿病/前期每天 |\n| 体脂心电 | 华为体脂秤 3 Pro | ¥599 | 每周 |\n| 制氧机 | **鱼跃 1L 静音制氧机** | ¥1999 | 心肺不好备用 |\n| 智能手表 | **华为 Watch GT4 老人款（SOS）** | ¥1488 | 全天佩戴 |\n| **合计** | | **¥4754** |\n\n## 💡 选品逻辑\n\n1. **欧姆龙血压计语音播报**：老人不用看屏幕，听数字\n2. **血糖仪**：高血压人群 30% 伴随糖尿病前期，建议常备\n3. **制氧机**：心衰/慢阻肺患者刚需，鱼跃是医用级国产标杆\n4. **GT4 老人款核心功能**：\n   - 一键 SOS 直拨子女电话\n   - 跌倒自动报警\n   - 实时定位（防走失）\n\n## ⚠️ 不需要的\n\n- ❌ 家用 CT 机 / 家用心电图（¥1万+，专业医院更准）\n- ❌ 颈椎按摩仪 / 足浴盆 / 老花镜：这些**不是健康监测，是日用保健**\n\n## 💰 余 ¥246 加\n\n- 雾化器（呼吸道用）¥180\n- 体温计耳温枪 ¥60",
    ["欧姆龙U10L上臂式医用级+语音播报+90组记忆+月销4.2万，老人血压每日必备", "强生OneTouch 5秒出值+含50条试纸+手机同步，糖尿病人群刚需", "华为体脂秤3 Pro 11项体成分+心电图，每周健康跟踪", "鱼跃1L制氧机医用级+静音<45dB，心肺疾病家庭刚需", "华为GT4老人款GPS+SOS+跌倒检测，全天佩戴防走失保命"]
))


print(f"准备追加 {len(T)} 条")
with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
    for t in T:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")
print(f"✅ 已追加 {len(T)} 条")

with open(OUTPUT_PATH) as f:
    total = sum(1 for _ in f)
print(f"   总条数: {total}")
