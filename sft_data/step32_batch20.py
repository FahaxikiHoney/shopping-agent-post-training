# -*- coding: utf-8 -*-
"""Step 32: 第 20 批 10 条"""
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
    "sft_simrec_051", "similar_rec", "相似品推荐",
    "抱怨连接不稳定 → 推荐 Wi-Fi 6E/信号更强款",
    "家里网络老掉线，上次买的路由器信号弱，要信号覆盖好的同价位款",
    {"query": "路由器 强信号 大户型覆盖 Wi-Fi 6", "max_price": 800, "filters": {"coverage_sqm_min": 120}},
    [
        {"product_id": "jd_router_cov_1", "title": "华为 AX6 Pro Wi-Fi 6 全屋覆盖 12天线", "price": 799, "is_jd_self": True, "rating": 4.9, "key_specs": "Wi-Fi 6/12天线/信号覆盖200㎡/穿墙强", "sales": "月销1.5万"},
        {"product_id": "jd_router_cov_2", "title": "小米 Redmi AX6 Wi-Fi 6 4×4 MIMO", "price": 349, "is_jd_self": True, "rating": 4.8, "key_specs": "Wi-Fi 6/4×4 MIMO/穿墙/月销3万", "sales": "月销3万"},
        {"product_id": "jd_router_cov_3", "title": "TP-Link 子母路由器套装 Mesh 组网", "price": 699, "is_jd_self": True, "rating": 4.9, "key_specs": "Mesh组网/两台路由器/信号无缝切换/适合复式", "sales": "月销1.2万"}
    ],
    "信号差主要是两个原因：**路由器功率弱** 或 **房子格局障碍多**。3 款对应不同情况：\n\n**1. 小米 Redmi AX6（¥349）** ⭐ 性价比首选\n4×4 MIMO 天线+Wi-Fi 6，**普通 3 居室完全够覆盖**。月销 3 万件是家用路由器销量王。\n\n**2. 华为 AX6 Pro（¥799）**\n12 天线大功率，**200㎡ 大户型/别墅穿墙必选**。华为信号算法优化在大户型优势明显。\n\n**3. TP-Link Mesh 套装（¥699）**\n两台路由器组 Mesh 网，**复式楼/多层别墅最佳方案**——一楼放一台，二楼放一台，信号无缝切换。\n\n## 💡 选哪个\n- 普通 3 居室 → 小米 AX6 ¥349（够用省钱）\n- 100-200㎡ 大户型 → 华为 AX6 Pro ¥799\n- 复式/多层/超大户型 → TP-Link Mesh ¥699",
    ["小米Redmi AX6 Wi-Fi 6+4×4 MIMO+月销3万，普通3居室性价比首选", "华为AX6 Pro 12天线+200㎡覆盖+月销1.5万，大户型穿墙强信号", "TP-Link Mesh两台套装+无缝切换+月销1.2万，复式多层楼最佳方案"]
))

# 2. similar_rec
T.append(make_traj(
    "sft_simrec_052", "similar_rec", "相似品推荐",
    "抱怨续航不足（智能手表）→ 推荐续航长款",
    "之前那款手表 Apple Watch 每天充电太麻烦了，有续航长的同功能款吗",
    {"query": "智能手表 续航长 健康监测 GPS", "min_price": 1000, "max_price": 2000, "filters": {"battery_days_min": 7}},
    [
        {"product_id": "jd_watch_bat_1", "title": "华为 Watch GT4 46mm 蓝牙版 14天续航", "price": 1488, "is_jd_self": True, "rating": 4.9, "key_specs": "14天续航/双频GPS/心率血氧/月销2.1万", "sales": "月销2.1万"},
        {"product_id": "jd_watch_bat_2", "title": "Garmin Venu 3 运动健康手表 10天", "price": 1999, "is_jd_self": True, "rating": 4.9, "key_specs": "10天续航/Garmin精准GPS/专业运动模式", "sales": "月销4500"},
        {"product_id": "jd_watch_bat_3", "title": "荣耀 Watch 4 Pro 21天续航 续航王", "price": 1299, "is_jd_self": True, "rating": 4.8, "key_specs": "21天续航/GPS/健康监测/月销1.5万", "sales": "月销1.5万"}
    ],
    "Apple Watch 每天充电是它的硬伤，国产长续航手表可以解决：\n\n**1. 荣耀 Watch 4 Pro（¥1299）** ⭐ 续航最长性价比最高\n**21 天续航**是这个价位天花板，比 Apple Watch 长 14 倍。月销 1.5 万。\n\n**2. 华为 Watch GT4（¥1488）**\n14 天续航+双频 GPS（精度最高），**运动外出不担心电量**。月销 2.1 万断档。\n\n**3. Garmin Venu 3（¥1999）**\n运动功能最专业，**跑步骑行游泳三项跟踪最准**，10 天续航够一周不充。\n\n## 📊 和 Apple Watch 的续航对比\n\n| 手表 | 续航 | 相比 AW SE（1.5 天）|\n|---|---|---|\n| 荣耀 Watch 4 Pro | **21 天** | 14 倍长 |\n| 华为 GT4 | 14 天 | 9 倍长 |\n| Garmin Venu 3 | 10 天 | 6 倍长 |\n\n## 💡 选哪个\n- 纯续航优先 → 荣耀 Watch 4 Pro ¥1299\n- 续航+精准 GPS → 华为 GT4 ¥1488\n- 专业运动员/健身党 → Garmin Venu 3 ¥1999",
    ["荣耀Watch 4 Pro 21天续航+GPS+月销1.5万，Apple Watch续航14倍最省心", "华为Watch GT4 14天+双频GPS精准+月销2.1万断档，运动续航双优", "Garmin Venu 3 10天续航+专业运动模式+月销4500，跑步骑行游泳专业党"]
))

# 3. sku_comp
T.append(make_traj(
    "sft_skucomp_049", "sku_comp", "商品对比",
    "三种床垫材质对比（乳胶/弹簧/记忆棉）",
    "买床垫纠结乳胶/弹簧/记忆棉，各有什么优缺点",
    {"categories": ["乳胶床垫", "独立袋装弹簧床垫", "记忆棉床垫"], "max_price": 5000, "topk_per_category": 1},
    [
        {"product_id": "jd_mat_latex", "title": "雅兰 泰国天然乳胶床垫 180×200×10cm", "price": 2999, "is_jd_self": True, "rating": 4.9, "key_specs": "天然乳胶/弹性好/透气防螨/不适合腰不好者", "sales": "月销1500"},
        {"product_id": "jd_mat_spring", "title": "慕思 独立袋装弹簧床垫 D-三度假日", "price": 3999, "is_jd_self": True, "rating": 4.9, "key_specs": "独立袋装弹簧/护腰/可平均承压/最大众选择", "sales": "月销2200"},
        {"product_id": "jd_mat_memory", "title": "宜家 记忆棉床垫 180×200cm 8cm", "price": 1499, "is_jd_self": True, "rating": 4.8, "key_specs": "记忆棉/低反弹/侧睡友好/价格最低", "sales": "月销1800"}
    ],
    "三种材质**各有适合人群**，没有绝对最好：\n\n## 📊 三种材质对比\n\n| 维度 | 乳胶 ¥2999 | 弹簧 ¥3999 | 记忆棉 ¥1499 |\n|---|---|---|---|\n| 弹性回弹 | **高（弹跳感）** | 中 | **低（包裹感）**|\n| 护腰支撑 | 一般 | **最好** | 差 |\n| 透气散热 | **好** | 好 | **差（闷热）**|\n| 防螨抗菌 | **天然防螨** | 一般 | 一般 |\n| 翻身噪音 | 无 | 微弱 | 无 |\n| 价格 | ¥2999 | ¥3999 | **¥1499** |\n\n## 🎯 按人群选\n\n### 腰不好/肩颈痛 → **独立弹簧 ¥3999**\n弹簧可以均匀承压，**护腰支撑是弹簧床垫最大优势**。乳胶/记忆棉都偏软，长期用腰会更不舒服。\n\n### 侧睡/怕热/过敏体质 → **乳胶 ¥2999**\n- 侧睡：乳胶弹性好，肩部/髋部不会受压\n- 怕热：乳胶比记忆棉凉爽得多\n- 过敏：天然乳胶有防螨属性\n\n### 预算紧/年轻人试用 → **记忆棉 ¥1499**\n- 价格最便宜\n- 包裹感强（但夏天闷热）\n- **不适合腰有问题的人**\n\n## 💡 真心建议\n\n**80% 成年人选独立弹簧床垫**（护腰是刚需），¥3999 慕思是中档信得过品牌。乳胶作为「功能性升级」，可以在弹簧垫上铺 5cm 乳胶床垫（¥1000 左右）——**两种材质结合**是最佳方案。",
    ["雅兰天然乳胶床垫+弹性透气防螨+月销1500，侧睡/怕热/过敏体质首选", "慕思独立袋装弹簧床垫+护腰支撑+月销2200，腰不好/肩颈痛必选", "宜家记忆棉床垫+低反弹包裹感+月销1800，预算紧年轻人试水"]
))

# 4. sku_comp
T.append(make_traj(
    "sft_skucomp_050", "sku_comp", "商品对比",
    "国货护肤 vs 日系护肤 vs 欧美护肤对比",
    "护肤品买国货/日系/欧美哪个更合适，各有什么优势",
    {"skus": ["薇诺娜修护精华水国货敏感肌", "资生堂肌源精华液日系", "雅诗兰黛小棕瓶精华欧美"], "mode": "origin_comparison"},
    [
        {"product_id": "jd_skin_cn", "title": "薇诺娜 修护精华水 120ml 国货敏感肌", "price": 239, "is_jd_self": True, "rating": 4.9, "key_specs": "国货医学护肤/马齿苋+玻尿酸/敏感肌首选/月销2万", "sales": "月销2万"},
        {"product_id": "jd_skin_jp", "title": "资生堂 肌源精华液 50ml 日系经典", "price": 799, "is_jd_self": True, "rating": 4.9, "key_specs": "日系精华/渗透肌底/润泽感强/温和月销5000", "sales": "月销5000"},
        {"product_id": "jd_skin_eu", "title": "雅诗兰黛 小棕瓶精华 30ml 抗老", "price": 749, "is_jd_self": True, "rating": 4.9, "key_specs": "二裂酵母/抗老修护/30+适合/月销1.2万", "sales": "月销1.2万"}
    ],
    "**护肤品没有绝对的「哪国最好」，关键看肤质和需求**：\n\n## 📊 三类产品对比\n\n| 维度 | 国货 ¥239 | 日系 ¥799 | 欧美 ¥749 |\n|---|---|---|---|\n| 成分透明度 | **最高** | 中 | 中 |\n| 配方方向 | **敏感修护** | 润泽温和 | **抗老功效** |\n| 适合人群 | 敏感/红血丝 | 干皮/温和需求 | **30+ 抗老** |\n| 性价比 | **最高** | 中偏低 | 中 |\n| 品牌历史 | 短 | 百年 | 数十年 |\n\n## 🎯 按需求选\n\n### 敏感肌/红肌/刚修复皮肤 → **薇诺娜 ¥239** ⭐\n- 国货医学护肤先行者\n- **马齿苋舒缓+玻尿酸保湿**，成分表清晰\n- ¥239 性价比碾压同档位进口品\n- 月销 2 万是国货护肤销冠\n\n### 干皮/想要润泽感/肤质稳定 → **资生堂 ¥799**\n- 日系百年品牌，温和无刺激\n- 渗透感强，干皮特别喜欢\n- 适合已知肤质稳定、想要**更好滋润感**的人\n\n### 25-40 岁、主要诉求抗老 → **雅诗兰黛小棕瓶 ¥749**\n- 二裂酵母是经过临床验证的抗老活性成分\n- 30+ 开始出现细纹、松弛的人最有效果\n- 月销 1.2 万是奢牌精华销冠\n\n## 💡 真心建议\n\n不要因为「贵=好」选护肤品——**国货薇诺娜对敏感肌的效果比很多进口品更好**。先判断自己的核心诉求（修护/润泽/抗老），再选对应品类，不要盲目跟风。",
    ["薇诺娜修护精华水+马齿苋+月销2万，国货敏感肌医学护肤性价比首选", "资生堂肌源精华液50ml+渗透润泽+月销5000，干皮温和需求日系经典", "雅诗兰黛小棕瓶精华30ml+二裂酵母抗老+月销1.2万，30+抗老需求首选"]
))

# 5. matching
T.append(make_traj(
    "sft_match_049", "matching_purchase", "搭配购物",
    "网红下午茶整套布置",
    "想在家布置一个拍照好看的下午茶角，配茶杯+点心架+桌布+装饰",
    {"query": "下午茶拍照布置 茶杯+点心架+桌布", "filters": {"style": "afternoon_tea_aesthetic"}},
    [
        {"product_id": "jd_tea_1", "title": "Emma Bridgewater 英式花卉茶杯套装 4件", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "英式花卉/杯碟套装4件/ins下午茶标配", "sales": "月销850"},
        {"product_id": "jd_tea_2", "title": "三层点心架 铁艺复古 银色款", "price": 199, "is_jd_self": True, "rating": 4.9, "key_specs": "三层铁艺/银色/复古下午茶/摆点心用", "sales": "月销2500"},
        {"product_id": "jd_tea_3", "title": "亚麻桌布 米白色 120×60cm", "price": 89, "is_jd_self": True, "rating": 4.9, "key_specs": "亚麻/米白色/防水/下午茶桌布标配", "sales": "月销4500"},
        {"product_id": "jd_tea_4", "title": "鲜花花束 混搭小花束 24支", "price": 59, "is_jd_self": True, "rating": 4.8, "key_specs": "混搭鲜花/24支/插瓶即用/拍照氛围感", "sales": "月销3500"}
    ],
    "下午茶拍照角 4 件套 ¥946，**15 分钟搭出 ins 风**：\n\n## ☕ 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 🥇 茶杯 | **Emma Bridgewater 英式花卉 4 件套** | ¥599 |\n| 点心架 | 三层铁艺银色 | ¥199 |\n| 桌布 | 亚麻米白 120×60 | ¥89 |\n| 鲜花 | 混搭花束 24 支 | ¥59 |\n\n## 🎨 下午茶拍照构图\n\n```\n基础构图（小红书爆款）：\n- 亚麻米白桌布打底\n- 三层点心架居中\n- 英式花卉茶杯放两侧\n- 鲜花插小瓶散落角落\n- 自然光+稍微侧窗\n```\n\n## 💡 选品理由\n\n### Emma Bridgewater ¥599\n英国品牌，花卉图案是下午茶的「灵魂单品」。杯碟套装 4 件够 2-4 人聚会用。\n\n### 三层点心架 ¥199\n**立体摆盘**让下午茶照片有层次感，放马卡龙/司康/小蛋糕，比平铺好看 10 倍。\n\n### 亚麻桌布 ¥89\n米白色亚麻是拍照背景最百搭的颜色，防水好打理。\n\n## 📸 一定要准备的\n\n**实体点心**（拍完要吃的）：\n- 司康 ¥30（手作/烘焙坊）\n- 马卡龙 ¥50\n- 草莓 ¥20\n\n**鲜花 ¥59 每次换一束**——鲜花是下午茶氛围感的 50%。",
    ["Emma Bridgewater英式花卉茶杯碟套装4件+月销850，下午茶ins灵魂单品", "三层铁艺银色点心架+月销2500，立体摆盘层次感拍照关键", "亚麻米白桌布120×60+防水+月销4500，下午茶拍照百搭背景", "混搭鲜花24支+月销3500，氛围感50%来自鲜花每次换"]
))

# 6. matching
T.append(make_traj(
    "sft_match_050", "matching_purchase", "搭配购物",
    "轻户外通勤穿搭男女通用",
    "骑行上班，需要配自行车头盔+骑行手套+防晒衣+骑行包",
    {"query": "骑行通勤装备 头盔+手套+防晒衣+包", "filters": {"category": "cycling_commute"}},
    [
        {"product_id": "jd_bike_1", "title": "JBM 骑行头盔 轻量透气 通勤款", "price": 199, "is_jd_self": True, "rating": 4.9, "key_specs": "CE认证/轻量透气/城市通勤/月销3500", "sales": "月销3500"},
        {"product_id": "jd_bike_2", "title": "迪卡侬 骑行手套 半指 透气防震", "price": 99, "is_jd_self": True, "rating": 4.9, "key_specs": "半指透气/掌心硅胶防震/城市骑行/月销4500", "sales": "月销4500"},
        {"product_id": "jd_bike_3", "title": "安踏 UPF50+ 骑行防晒衣 速干", "price": 199, "is_jd_self": True, "rating": 4.8, "key_specs": "UPF50+防晒/速干/骑行专用版型", "sales": "月销2200"},
        {"product_id": "jd_bike_4", "title": "迪卡侬 骑行背包 15L 防雨", "price": 249, "is_jd_self": True, "rating": 4.9, "key_specs": "15L/防雨/透气背板/电脑仓/月销2500", "sales": "月销2500"}
    ],
    "骑行通勤 4 件套 ¥746，**安全+防晒+实用三全**：\n\n## 🚴 完整方案\n\n| 装备 | 商品 | 价格 | 重要性 |\n|---|---|---|---|\n| 🥇 头盔 | JBM 轻量透气通勤款 | ¥199 | ⭐⭐⭐⭐⭐ |\n| 防晒衣 | 安踏 UPF50+ 速干 | ¥199 | ⭐⭐⭐⭐ |\n| 骑行包 | 迪卡侬 15L 防雨 | ¥249 | ⭐⭐⭐⭐ |\n| 手套 | 迪卡侬半指防震 | ¥99 | ⭐⭐⭐ |\n\n## 💡 头盔是唯一不能省的\n\n城市骑行**最常见事故是与机动车碰撞**，没有头盔的后果不敢想象。JBM 头盔 ¥199 通过 CE 国际认证，轻量透气夏天戴着不热。\n\n## 💡 防晒衣比防晒霜更实际\n\n骑行会出汗，**防晒霜出汗会化掉**，防晒衣 UPF50+ 是物理防晒，任何天气都有效。速干版型不影响骑行动作。\n\n## 💡 骑行包选 15L\n\n- **透气背板**：夏天背包不出一背汗\n- 防雨设计：下班遇到阵雨不用担心电脑进水\n- 15L 装电脑+换洗衣物+工作物品刚好\n\n## 🚴 骑行通勤 Tips\n\n1. **提前查天气**：下雨备折叠雨衣\n2. **骑行灯必备**：尾灯让后方机动车看到你\n3. **锁止装置**：到公司一定锁车（加码锁）\n4. **汗湿换衣**：包里备一件换洗衬衫",
    ["JBM轻量透气头盔CE认证+月销3500，骑行唯一不能省的安全装备", "安踏UPF50+骑行防晒衣速干+月销2200，比防晒霜更实际", "迪卡侬骑行背包15L防雨透气背板+月销2500，到公司不湿背不进水", "迪卡侬半指骑行手套防震+月销4500，掌心保护防路面震动"]
))

# 7. bundle
T.append(make_traj(
    "sft_bundle_047", "bundle_purchase", "组合购物",
    "5000 元新居保洁套装（家政+工具）",
    "新房收房了，5000 预算配齐保洁工具自己打扫",
    {"query": "新房保洁工具 吸尘器+拖地+清洁剂", "max_price": 5500},
    [
        {"product_id": "jd_clean_1", "title": "追觅 V12s Pro 双电池无线吸尘器", "price": 1899, "is_jd_self": True, "rating": 4.9, "key_specs": "185AW大吸力/双电池总120min/地板+地毯通用", "sales": "月销1.5万"},
        {"product_id": "jd_clean_2", "title": "添可芙万 2.0 洗地机 双滚刷热风", "price": 1999, "is_jd_self": True, "rating": 4.9, "key_specs": "双滚刷/热风烘干/边扫边洗/新房深度清洁", "sales": "月销9800"},
        {"product_id": "jd_clean_3", "title": "甲醛清除剂 2kg×3桶 空气净化", "price": 299, "is_jd_self": True, "rating": 4.8, "key_specs": "新房甲醛清除/2kg大桶/喷涂家具用", "sales": "月销4500"},
        {"product_id": "jd_clean_4", "title": "家政保洁工具套装 拖把+扫帚+水桶+擦玻璃", "price": 299, "is_jd_self": True, "rating": 4.9, "key_specs": "基础工具套装/拖把+扫+擦窗/新居必备", "sales": "月销2.5万"}
    ],
    "新房保洁 4 件套 ¥4496，**一次彻底搞定**：\n\n## 🏠 完整方案\n\n| 工具 | 商品 | 价格 | 用途 |\n|---|---|---|---|\n| 吸尘器 | 追觅 V12s Pro 双电池 | ¥1899 | 地板+沙发+床缝吸灰尘 |\n| 洗地机 | 添可芙万 2.0 | ¥1999 | 地板深度清洗 |\n| 甲醛清除 | 3 桶套装 | ¥299 | 新房家具柜子去醛 |\n| 工具套装 | 拖+扫+擦窗 | ¥299 | 基础工具 |\n\n## 💡 新房保洁顺序\n\n```\n第 1 天：\n1. 开窗通风\n2. 喷甲醛清除剂（家具+柜子内壁）\n3. 干拖把清灰尘\n\n第 2 天（等甲醛清除剂干后）：\n1. 吸尘器吸细灰（缝隙/地脚线）\n2. 洗地机湿洗地板\n3. 擦窗户/玻璃\n\n每周维护：\n- 洗地机日常清洁\n- 吸尘器每周 1 次\n```\n\n## 💡 为什么买洗地机而不是拖把\n\n新房施工残留的**细砂/石灰**普通拖把推来推去扫不干净，洗地机滚刷强力摩擦+边吸边洗**一遍搞定**。\n\n## ⚠️ 新房甲醛注意\n\n甲醛清除剂喷完需要**24 小时后再住人**。不要急，等等更安全。",
    ["追觅V12s Pro双电池+185AW+月销1.5万，新房全屋吸灰尘地板地毯通用", "添可芙万2.0洗地机双滚刷热风+月销9800，新房地板深度清洁一遍搞定", "甲醛清除剂3桶套装+月销4500，新房家具柜子喷涂去醛必备", "家政保洁工具套装+月销2.5万，拖扫擦窗基础工具一次配齐"]
))

# 8. bundle
T.append(make_traj(
    "sft_bundle_048", "bundle_purchase", "组合购物",
    "2000 元宠物狗体检+保健套装",
    "狗狗 5 岁了想做个健康检查，2000 预算配齐体检+日常保健",
    {"query": "宠物狗健康检查 体检+保健品", "max_price": 2200},
    [
        {"product_id": "jd_dog_health_1", "title": "宠物血常规+生化检查套餐 上门取血", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "上门取血/血常规+肝肾功能+血糖/3天出报告", "sales": "月销1500"},
        {"product_id": "jd_dog_health_2", "title": "宠物鱼油 Omega-3 180粒 关节护理", "price": 199, "is_jd_self": True, "rating": 4.9, "key_specs": "Omega-3/关节护理/皮毛光亮/5岁以上适合", "sales": "月销4500"},
        {"product_id": "jd_dog_health_3", "title": "宠物益生菌 30包 肠胃调理", "price": 99, "is_jd_self": True, "rating": 4.9, "key_specs": "益生菌/肠胃健康/减少呕吐/月销3500", "sales": "月销3500"},
        {"product_id": "jd_dog_health_4", "title": "宠物驱虫药 内外同驱 体重10-20kg", "price": 199, "is_jd_self": True, "rating": 4.9, "key_specs": "内外同驱/10-20kg体重/每3个月一次", "sales": "月销2200"},
        {"product_id": "jd_dog_health_5", "title": "宠物牙齿清洁 牙膏+牙刷套装", "price": 69, "is_jd_self": True, "rating": 4.8, "key_specs": "宠物专用牙膏/牙刷/日常护理牙结石", "sales": "月销5500"}
    ],
    "宠物 5 岁中年期健康套装 ¥1165，余 ¥835：\n\n## 🐶 完整方案\n\n| 项目 | 商品 | 价格 | 频次 |\n|---|---|---|---|\n| 🥇 体检 | 血常规+生化上门套餐 | ¥599 | 每年 1-2 次 |\n| 鱼油保健 | Omega-3 180 粒 | ¥199 | 每天 1 粒 |\n| 益生菌 | 30 包肠胃调理 | ¥99 | 每天 1 包 |\n| 驱虫 | 内外同驱（10-20kg）| ¥199 | 每 3 个月 |\n| 牙齿护理 | 牙膏+牙刷套装 | ¥69 | 每周 2-3 次 |\n\n## 💡 5 岁狗狗的健康重点\n\n### 体检 ¥599 最重要\n5 岁是犬类「中年」，很多疾病（心脏病/肾病/糖尿病）**这个阶段开始悄悄发展**。血常规+生化指标能早期发现 80% 的内脏问题，**早发现比晚发现便宜 10 倍**。\n\n### 鱼油 ¥199\n5 岁+犬关节开始磨损，Omega-3 对**关节润滑+皮毛光亮+心脏保护**有明确效果。\n\n### 驱虫 ¥199\n每 3 个月**内外同驱**：体内寄生虫（蛔虫/绦虫）+体外（跳蚤/蜱虫），**不做驱虫的狗活不长**。\n\n### 牙齿护理 ¥69\n5 岁后牙结石是大问题，轻则口臭，重则细菌入血影响心脏。**每周刷 2 次牙**能延缓牙结石 3-5 年。\n\n## 💰 余 ¥835 加\n\n- 宠物保险（首年 ¥500-800）：意外/手术报销\n- 关节保健零食 ¥150\n- 宠物医院备用费 ¥500",
    ["宠物上门取血体检+血常规+肝肾功能+月销1500，5岁中年犬年检早发现问题", "宠物鱼油Omega-3+关节护理皮毛光亮+月销4500，5岁以上必备", "宠物益生菌30包+月销3500，肠胃调理减少呕吐日常维护", "宠物内外同驱驱虫药+月销2200，每3个月必做不能省", "宠物牙膏+牙刷套装+月销5500，每周2次刷牙延缓牙结石"]
))

# 9. place_order
T.append(make_traj(
    "sft_order_026", "place_order", "购物下单",
    "节日限时秒杀下单",
    "双十一零点那款限量秒杀的 ¥399 戴森吹风机要抢，怎么操作",
    {"product_id": "jd_dyson_hair_sale", "action": "seckill_reserve", "scheduled_time": "00:00"},
    [
        {"product_id": "jd_dyson_hair_sale", "title": "戴森 Supersonic 吹风机 双十一秒杀价 ¥399", "price": 399, "is_jd_self": True, "rating": 4.9, "key_specs": "限时秒杀/原价2899/限量1000台/00:00开始/已帮你预约", "sales": "—"}
    ],
    "✅ 已帮你**预约双十一零点秒杀**，成功概率最大化操作如下：\n\n## ⏰ 预约状态\n\n- **商品**：戴森 Supersonic 吹风机（秒杀价 ¥399）\n- **预约状态**：已预约（系统自动提醒你）\n- **开抢时间**：双十一 **00:00:00**\n- **库存**：限量 1000 台（竞争激烈）\n\n## 🎯 抢到的 5 个关键操作\n\n### 提前 30 分钟（23:30）做\n1. **加入购物车**（直接下单比加购快）\n2. **填好收货地址**（不要临时填）\n3. **绑定支付方式**（首选京东白条/余额，比微信/银行卡快）\n4. **切到 5G/优质 Wi-Fi**\n5. **关掉其他耗电 App**\n\n### 00:00:00 时\n1. **提前 1 分钟进入商品页**\n2. 看到「立即抢购」按钮变亮**立刻点击**\n3. **不要犹豫**（0.3 秒内完成）\n4. 进入支付页面**立即付款**（不要改地址）\n\n## 💡 抢不到怎么办\n\n戴森双十一期间会有**多场秒杀**：\n- 11 月 1 日预售（通常价格最低）\n- 11 月 11 日 00:00\n- 11 月 11 日 12:00\n- 最终尾款日\n\n同时关注**京东超市/京东家电**两个频道，秒杀库存不一样。\n\n## ⚠️ 秒杀防坑\n\n- ❌ **不要在 APP 跳出付款时关掉**（会释放库存）\n- ❌ **不要多窗口同时打开**（容易卡）\n- ✅ **只用一个设备**（手机比电脑更稳）\n- ✅ **提前检查余额/白条额度够不够**",
    ["戴森Supersonic限量秒杀价399+限量1000台+已帮你预约，零点开抢操作指南"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase
T.append(make_traj(
    "sft_repurchase_024", "repurchase", "复购召回",
    "复购+最优时机建议（价格低点）",
    "再买一袋之前那个蛋白粉，现在是不是最低价",
    {"category_keyword": "蛋白粉", "time_range": "last_4_months", "check_price_history": True},
    [
        {"product_id": "jd_protein_old", "title": "MyProtein 乳清蛋白粉 1kg 巧克力味 (你3月前购买¥269)", "price": 269, "is_jd_self": True, "rating": 4.9, "key_specs": "你3月前购买¥269/订单[ORDER_ID]", "sales": "月销1.8万"},
        {"product_id": "jd_protein_now", "title": "MyProtein 乳清蛋白粉 1kg 巧克力味 (当前¥249)", "price": 249, "is_jd_self": True, "rating": 4.9, "key_specs": "当前价¥249/比你上次低20/历史最低¥219(618)", "sales": "月销1.8万"},
        {"product_id": "jd_protein_2p", "title": "MyProtein 乳清蛋白粉 2.5kg 超值装 (¥569)", "price": 569, "is_jd_self": True, "rating": 4.9, "key_specs": "2.5kg大包/单kg价228/比1kg更划算", "sales": "月销5500"}
    ],
    "你 3 个月前买的 **MyProtein 乳清蛋白粉 ¥269**，现在有些变化：\n\n## 📊 价格趋势\n\n| 时间 | 价格 |\n|---|---|\n| 你上次购买（3 月）| ¥269 |\n| **当前价** | **¥249**（比上次低 ¥20）|\n| 618 历史最低 | ¥219 |\n| 双十一历史最低 | ¥229 |\n\n**当前价不是历史最低，但比你上次买的时候便宜了 ¥20**。\n\n## 💡 3 个选择\n\n### 选项 A：现在直接买 1kg ¥249\n- 比上次省 ¥20\n- 随时想喝随时有货\n- **如果不差那 ¥30 可以现在入手**\n\n### 选项 B：等双十一 ¥229 ⭐ 省最多\n- 距今约 4 个月（10 月左右）\n- 最低可能到 ¥219-229\n- 省 ¥20-50 元\n- **前提：你的存货撑得到双十一**\n\n### 选项 C：升级 2.5kg 大包 ¥569 ⭐ 单 kg 最划算\n- 单 kg 价格 ¥228（比 1kg 款还便宜 ¥21）\n- **3 个月用量一次买完，省 ¥63**\n- 保质期 18 个月，2.5kg 约 4-5 个月用完\n- 只有仓储空间够才推荐\n\n## 🎯 我的建议\n\n**如果你快用完了**（剩不到 1 周）：\n- 马上买 1kg ¥249，¥249 已经比上次低\n\n**如果还有 1 个月库存**：\n- 考虑等双十一（最多再省 ¥30）\n\n**如果储存空间够**：\n- 直接 2.5kg ¥569，长期省钱最合算\n\n你蛋白粉现在还剩多少？",
    ["MyProtein乳清蛋白粉1kg你3月前购买¥269，当前¥249比上次低20元", "MyProtein当前价249+历史最低219(618/双十一)+等4个月再省20-30", "MyProtein 2.5kg超值装+单kg价228比1kg便宜+月销5500，长期用大包更划算"],
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
