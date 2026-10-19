# -*- coding: utf-8 -*-
"""Step 26: 第 14 批 10 条"""
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

# 1. similar_rec - 抱怨清洗复杂
T.append(make_traj(
    "sft_simrec_039", "similar_rec", "相似品推荐",
    "抱怨清洁麻烦 → 可机洗款",
    "之前买的电火锅清洗太麻烦，有能整个拆下放洗碗机的同价位款吗",
    {"query": "电火锅 可机洗 整体拆卸", "max_price": 500, "filters": {"dishwasher_safe": True}},
    [
        {"product_id": "mock_hot_1", "title": "美的 MC-DH40Q1 电火锅 锅体可拆 可机洗", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "锅体可拆+可放洗碗机/4L容量", "sales": "月销1.5万"},
        {"product_id": "mock_hot_2", "title": "苏泊尔 SHC23A 多功能锅 全模块拆卸", "price": 459, "is_platform_self": True, "rating": 4.9, "key_specs": "全模块化/3.5L+蒸笼/可机洗", "sales": "月销8500"},
        {"product_id": "mock_hot_3", "title": "九阳 JK-32H62 不粘电火锅 简易拆卸", "price": 199, "is_platform_self": True, "rating": 4.8, "key_specs": "3.2L/不粘涂层+底盘可拆", "sales": "月销4500"}
    ],
    "懂，电火锅清洗最大的痛点是「**电路部分不能水洗**」。3 款都解决了：\n\n**1. 美的可拆款 ¥299** ⭐ 性价比\n锅体整体拆下放洗碗机，**电路部分独立**。月销 1.5 万。\n\n**2. 苏泊尔全模块化 ¥459**\n所有部件可拆+多功能（火锅+蒸+煎），**机洗最彻底**。\n\n**3. 九阳简易拆卸 ¥199** 最便宜\n底盘可拆但内胆不能机洗，**手动好洗即可**。\n\n建议选**美的可拆款 ¥299**——可拆+可机洗+大容量平衡最好。",
    ["美的MC-DH40Q1可拆款+整体放洗碗机+月销1.5万，电火锅清洁性价比", "苏泊尔SHC23A全模块化+多功能+月销8500，清洁最彻底", "九阳JK-32H62底盘可拆+月销4500，最便宜手动好洗"]
))

# 2. similar_rec - 抱怨电池寿命
T.append(make_traj(
    "sft_simrec_040", "similar_rec", "相似品推荐",
    "抱怨电池衰减 → 大电池/可换电",
    "用了 2 年的吸尘器电池续航就一半了，新买的要电池耐用的",
    {"query": "无线吸尘器 大电池 耐用", "min_price": 1500, "max_price": 2500, "filters": {"battery_replaceable": True, "battery_cycles_min": 1000}},
    [
        {"product_id": "mock_vac_bat_1", "title": "戴森 V12 Detect Slim 可换电款", "price": 2299, "is_platform_self": True, "rating": 4.9, "key_specs": "可换电池/续航60min/电池可单买换", "sales": "月销4500"},
        {"product_id": "mock_vac_bat_2", "title": "追觅 V12s Pro 双电池版", "price": 1899, "is_platform_self": True, "rating": 4.9, "key_specs": "双电池(总120min)/可热插拔", "sales": "月销1800"},
        {"product_id": "mock_vac_bat_3", "title": "莱克 巨浪 M12R 高循环电池", "price": 1599, "is_platform_self": True, "rating": 4.8, "key_specs": "电池循环1500次/5年衰减<20%", "sales": "月销1200"}
    ],
    "电池衰减是无线吸尘器的硬伤。3 款解决方案：\n\n**1. 追觅 V12s Pro 双电池 ¥1899** ⭐ 最实用\n**双电池总续航 120min**+可热插拔，1 个充电时用另 1 个。**这套配置最实用**。\n\n**2. 戴森 V12 可换电款 ¥2299**\n电池可拆下来单买换新（原厂电池 ¥600），**戴森做工耐用**。\n\n**3. 莱克 M12R ¥1599** 最便宜\n标称**电池循环 1500 次+5 年衰减 <20%**，性价比首选。\n\n选追觅 ¥1899 —— 双电池 = **告别充电焦虑**。",
    ["追觅V12s Pro双电池版+120min总续航+可热插拔+月销1800，告别充电焦虑", "戴森V12可换电款+电池单买换+月销4500，做工耐用品牌党", "莱克M12R电池循环1500次+5年衰减<20%+月销1200，性价比首选"]
))

# 3. sku_comp - 性能版本三档对比
T.append(make_traj(
    "sft_skucomp_037", "sku_comp", "商品对比",
    "GPU 显卡 4060 vs 4070 vs 4080 对比",
    "买游戏本 RTX4060/4070/4080 性能差多少",
    {"skus": ["RTX 4060 游戏本", "RTX 4070 游戏本", "RTX 4080 游戏本"], "mode": "performance_tier_comparison"},
    [
        {"product_id": "mock_4060_laptop", "title": "联想拯救者 R7000 RTX4060 游戏本", "price": 6999, "is_platform_self": True, "rating": 4.9, "key_specs": "RTX4060 8G/原神高画质80帧/2K中等画质", "sales": "月销8500"},
        {"product_id": "mock_4070_laptop", "title": "联想拯救者 Y7000P RTX4070 游戏本", "price": 9499, "is_platform_self": True, "rating": 4.9, "key_specs": "RTX4070 8G/原神极高画质100帧/2K全特效", "sales": "月销4500"},
        {"product_id": "mock_4080_laptop", "title": "ROG 魔霸 RTX4080 游戏本旗舰", "price": 13999, "is_platform_self": True, "rating": 4.9, "key_specs": "RTX4080 12G/4K中等画质/3A大作天花板", "sales": "月销1200"}
    ],
    "**结论：拐点在 4070，4080 仅顶级 3A 党值得**。\n\n## 📊 三档性能对比\n\n| 维度 | 4060 ¥6999 | 4070 ¥9499 | 4080 ¥13999 |\n|---|---|---|---|\n| 显存 | 8G | 8G | **12G** |\n| 原神高画质 | 80 帧 | **100 帧** | 144 帧 |\n| 2K 全特效 | 中等 | **流畅** | 极致 |\n| 4K | 不行 | 中等 | **流畅** |\n| 月销 | **8500** | 4500 | 1200 |\n\n## 💰 性价比拆解\n\n### 4060 → 4070（+¥2500）值\n- 原神极高画质 100 帧（4060 仅 80）\n- **2K 屏全特效可玩**\n- 性价比拐点\n\n### 4070 → 4080（+¥4500）不值（90% 用户）\n- 仅 4K/144Hz 游戏才用得到\n- 笔记本 4K 屏本身贵\n- **4080 笔记本 ¥14000 起，台式机更划算**\n\n## 🎯 怎么选\n\n- **预算紧+原神够** → 4060 ¥6999\n- **2K 屏想全特效** → **4070 ¥9499**（拐点）\n- **4K 游戏发烧** → 4080 ¥13999",
    ["联想拯救者R7000 RTX4060+8G显存+原神高80帧+月销8500，预算紧主流游戏", "联想拯救者Y7000P RTX4070+原神极高100帧+2K全特效+月销4500，性价比拐点", "ROG魔霸RTX4080+12G显存+4K中等画质+月销1200，4K发烧顶配"]
))

# 4. sku_comp - 不同存储方案
T.append(make_traj(
    "sft_skucomp_038", "sku_comp", "商品对比",
    "笔记本 SSD 512G vs 1T vs 2T",
    "笔记本 SSD 选 512G 还是 1T 还是 2T",
    {"skus": ["三星 SSD 512G", "三星 SSD 1TB", "三星 SSD 2TB"], "mode": "storage_comparison"},
    [
        {"product_id": "mock_ssd_512", "title": "三星 980 NVMe SSD 512G", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "512G/NVMe 7000MB/s", "sales": "月销4.5万"},
        {"product_id": "mock_ssd_1t", "title": "三星 980 NVMe SSD 1TB", "price": 699, "is_platform_self": True, "rating": 4.9, "key_specs": "1TB/NVMe 7000MB/s", "sales": "月销2.5万"},
        {"product_id": "mock_ssd_2t", "title": "三星 980 NVMe SSD 2TB", "price": 1399, "is_platform_self": True, "rating": 4.9, "key_specs": "2TB/NVMe 7000MB/s", "sales": "月销850"}
    ],
    "**结论：1TB 是甜点，单 GB 价格最低**：\n\n## 📊 三档对比\n\n| 容量 | 价格 | 单 GB 价 | 适合 |\n|---|---|---|---|\n| 512G | ¥399 | **¥0.78** | 学生/纯办公 |\n| **1TB** | **¥699** | **¥0.68** ⭐ | 主流用户 |\n| 2TB | ¥1399 | ¥0.70 | 游戏+设计 |\n\n**1TB 单 GB 最便宜**（¥0.68 vs 512G 的 ¥0.78）。\n\n## 🎯 怎么选\n\n### 512G ¥399（学生）\n- 系统 50G + 软件 100G + 文件 200G = **剩 150G** 够用\n- 适合：上网课/文档/不存大文件\n\n### 1TB ¥699 ⭐ 推荐\n- **主流用户最佳**\n- 装系统+游戏+图片+视频\n- 单 GB 最便宜\n\n### 2TB ¥1399\n- 4K 视频素材\n- 游戏库 10+ 大作\n- 设计师/视频剪辑党",
    ["三星980 NVMe SSD 512G+月销4.5万，学生/纯办公够用", "三星980 NVMe SSD 1TB+月销2.5万，主流用户甜点单GB最便宜", "三星980 NVMe SSD 2TB+月销850，4K视频/设计师存储党"]
))

# 5. matching - 滑雪整套
T.append(make_traj(
    "sft_match_037", "matching_purchase", "搭配购物",
    "滑雪整体装备",
    "下个月去滑雪，配齐外套+裤子+护目镜+头盔+手套",
    {"query": "滑雪装备 外套+裤子+护具", "filters": {"sport": "skiing", "level": "beginner"}},
    [
        {"product_id": "mock_ski_1", "title": "Burton 滑雪服外套 防水透气", "price": 1899, "is_platform_self": True, "rating": 4.9, "key_specs": "Burton/防水15000mm/透气15000g", "sales": "月销850"},
        {"product_id": "mock_ski_2", "title": "Burton 滑雪裤 防水保暖款", "price": 1299, "is_platform_self": True, "rating": 4.9, "key_specs": "Burton同系列/搭配外套", "sales": "月销680"},
        {"product_id": "mock_ski_3", "title": "OAKLEY 滑雪护目镜 防雾防紫外", "price": 999, "is_platform_self": True, "rating": 4.9, "key_specs": "OAKLEY/防雾/100% UV", "sales": "月销1500"},
        {"product_id": "mock_ski_4", "title": "Smith 滑雪头盔 ABS+EPS 防撞", "price": 1099, "is_platform_self": True, "rating": 4.9, "key_specs": "Smith/ABS外壳+EPS吸震/CE认证", "sales": "月销1200"},
        {"product_id": "mock_ski_5", "title": "Burton 滑雪手套 防水保暖", "price": 399, "is_platform_self": True, "rating": 4.8, "key_specs": "Burton/Gore-Tex/触屏指尖", "sales": "月销2200"}
    ],
    "滑雪入门 5 件套 ¥5695，**安全第一**：\n\n## ⛷️ 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 🥇 头盔 | **Smith ABS+EPS（必须）** | ¥1099 |\n| 护目镜 | OAKLEY 防雾 | ¥999 |\n| 外套 | Burton 防水 15000mm | ¥1899 |\n| 雪裤 | Burton 防水保暖 | ¥1299 |\n| 手套 | Burton Gore-Tex | ¥399 |\n| **合计** | | **¥5695** |\n\n## 💡 滑雪安全要点\n\n### 1️⃣ 头盔不能省\n**滑雪 95% 死亡是脑损伤**：\n- 头盔必须 CE 认证（Smith 是雪盔顶级）\n- 不要图便宜买 ¥200 假货\n- **¥1099 救命级投资**\n\n### 2️⃣ 护目镜防雪盲\n雪地反光强 + 紫外线**致雪盲**（眼角膜灼伤）：\n- OAKLEY 是雪镜业内标杆\n- 防雾涂层（出汗不模糊）\n- 100% UV 防护\n\n### 3️⃣ 外套防水 15000mm 是入门\n- 5000mm：小雨可挡\n- 10000mm：中雨\n- **15000mm：暴雪（滑雪需要）**\n- 30000mm：专业级\n\n## 💰 进阶方案（高级滑雪党 ¥10000+）\n\n- 雪板+固定器 ¥3000-5000\n- 雪靴 ¥2000\n- 防摔短裤 ¥300\n- 护膝护肘 ¥500\n\n## ⚠️ 入门避坑\n\n- ❌ **租装备**（性价比低，1 周租金=买）\n- ❌ **棉服当滑雪服**（湿了不保暖）\n- ❌ **普通墨镜代护目镜**（紫外线伤眼）\n- ❌ **裸戴牛仔裤**（摔倒擦破皮）\n\n## 🎯 真心建议\n\n滑雪是**装备依赖型运动**，¥5695 投资值得：\n- 5 年不淘汰\n- 关键时刻保命\n- **租装备 5 次就值这套价**",
    ["Smith ABS+EPS头盔+CE认证+月销1200，滑雪95%死亡防护救命级", "OAKLEY护目镜+防雾+100% UV+月销1500，防雪盲业内标杆", "Burton滑雪外套+防水15000mm+透气+月销850，暴雪级防护", "Burton滑雪裤+同系列+月销680，搭配外套防水保暖", "Burton Gore-Tex手套+触屏指尖+月销2200，雪地保暖必备"]
))

# 6. matching - 钓鱼整套
T.append(make_traj(
    "sft_match_038", "matching_purchase", "搭配购物",
    "钓鱼新手装备组合",
    "想入门钓鱼，配齐鱼竿+鱼线+鱼饵+鱼护+椅子",
    {"query": "钓鱼新手装备 鱼竿+鱼线+鱼饵", "filters": {"sport": "fishing", "level": "beginner"}},
    [
        {"product_id": "mock_fish_1", "title": "光威 战神 4.5米台钓竿 新手入门", "price": 269, "is_platform_self": True, "rating": 4.9, "key_specs": "光威新手款/4.5米台钓竿+月销3500", "sales": "月销3500"},
        {"product_id": "mock_fish_2", "title": "钓鱼新手套装(鱼线+鱼钩+浮漂)", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "鱼线+10个鱼钩+5个浮漂", "sales": "月销1.2万"},
        {"product_id": "mock_fish_3", "title": "通用鱼饵套装 含商品饵+蚯蚓", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "5种鱼饵+蚯蚓1盒/适合所有淡水鱼", "sales": "月销8500"},
        {"product_id": "mock_fish_4", "title": "折叠鱼护 不锈钢框架 防溃逃", "price": 159, "is_platform_self": True, "rating": 4.8, "key_specs": "不锈钢框架+防溃逃设计", "sales": "月销2500"},
        {"product_id": "mock_fish_5", "title": "钓鱼折叠椅 带遮阳伞", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "折叠椅+遮阳伞+置物袋", "sales": "月销4500"}
    ],
    "钓鱼新手 5 件套 ¥815，**全套入门刚好**：\n\n## 🎣 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 🥇 鱼竿 | 光威 4.5 米台钓竿 | ¥269 |\n| 配件 | 鱼线+钩+浮漂 | ¥99 |\n| 鱼饵 | 5 种鱼饵+蚯蚓 | ¥89 |\n| 鱼护 | 折叠不锈钢 | ¥159 |\n| 椅子 | 折叠+遮阳伞 | ¥199 |\n| **合计** | | **¥815** |\n\n## 💡 钓鱼新手 3 个关键\n\n### 1️⃣ 鱼竿不要太贵\n新手会摔/会断/会缠线，**¥269 是性价比起步**。专业竿 ¥1000+ 等你钓 1 年再升级。\n\n### 2️⃣ 鱼饵要多种试\n不同鱼吃不同饵：\n- 鲫鱼 → 蚯蚓/红虫\n- 鲤鱼 → 玉米/商品饵\n- 草鱼 → 嫩玉米/草\n\n5 种套装让你**1 次试出当地鱼吃什么**。\n\n### 3️⃣ 椅子+遮阳伞防晒\n钓鱼经常**晒 4-6 小时**：\n- 防晒（避免黑成炭）\n- 久坐舒服（鱼咬钩前可能等 1 小时）\n\n## 💰 进阶（+¥500）\n\n- 探鱼器 ¥200\n- 抄网 ¥80\n- 鱼线轮（小海竿）¥300\n- 头巾防晒帽 ¥80\n- 防水雨衣 ¥100\n\n## ⚠️ 钓鱼避雷\n\n- ❌ **去禁渔区**（罚款 + 没收装备）\n- ❌ **不带渔证**（部分地区需要）\n- ❌ **野塘私自钓**（可能被骂偷鱼）\n- ❌ **冬天不穿够保暖**（钓鱼坐着冷得快）\n\n## 🎯 真心建议\n\n¥815 这套**够你钓 1 年**——之后想升级再投资。钓鱼是**禅修运动**，享受过程不只是钓到鱼。",
    ["光威战神4.5米台钓竿+新手入门+月销3500，性价比起步首选", "钓鱼新手套装+鱼线+10鱼钩+5浮漂+月销1.2万，配件一次配齐", "通用鱼饵+5种+蚯蚓+月销8500，1次试出当地鱼吃什么", "折叠鱼护不锈钢框架+防溃逃+月销2500，钓到的鱼保活", "钓鱼折叠椅+遮阳伞+月销4500，4-6小时防晒久坐舒适"]
))

# 7. bundle - 5000 抗衰组合
T.append(make_traj(
    "sft_bundle_035", "bundle_purchase", "组合购物",
    "5000 元 30 岁抗衰套装",
    "30 岁要开始抗衰了，5000 配齐护肤+保健品+科技小家电",
    {"query": "30岁抗衰套装 护肤+保健+科技", "max_price": 5500, "filters": {"target_age": "30_plus_anti_aging"}},
    [
        {"product_id": "mock_anti_1", "title": "雅诗兰黛小棕瓶眼霜+精华 30+礼盒", "price": 1680, "is_platform_self": True, "rating": 4.9, "key_specs": "30+抗老/二裂酵母+ChronoluxCB专利/月销4500", "sales": "月销4500"},
        {"product_id": "mock_anti_2", "title": "兰蔻菁纯眼霜+小黑瓶精华套装", "price": 2199, "is_platform_self": True, "rating": 4.9, "key_specs": "玫瑰精粹+视黄醇/抗老经典+保湿满分", "sales": "月销2200"},
        {"product_id": "mock_anti_3", "title": "Swisse 胶原蛋白肽 60 片+鱼油 60 粒", "price": 599, "is_platform_self": True, "rating": 4.9, "key_specs": "胶原蛋白肽内服+鱼油双套装", "sales": "月销1.5万"},
        {"product_id": "mock_anti_4", "title": "Notime 美容仪 RF 射频+光子嫩肤", "price": 1299, "is_platform_self": True, "rating": 4.8, "key_specs": "RF射频+光子嫩肤+EMS提拉一机三能", "sales": "月销1200"}
    ],
    "30+抗衰 4 件套 ¥5777，**超 ¥277 但都值**：\n\n## 💄 完整方案\n\n| 类别 | 商品 | 价格 |\n|---|---|---|\n| 🥇 抗衰眼霜+精华 | **雅诗兰黛小棕瓶礼盒** | ¥1680 |\n| 抗老精华套装 | 兰蔻菁纯+小黑瓶 | ¥2199 |\n| 美容仪 | Notime RF+光子+EMS | ¥1299 |\n| 内服 | Swisse 胶原+鱼油 | ¥599 |\n| **合计** | | **¥5777** |\n\n## 💡 30+ 抗衰 4 大体系\n\n### 1️⃣ 眼周（最先衰老）\n**雅诗兰黛小棕瓶眼霜**：\n- 二裂酵母（抗老黄金成分）\n- ChronoluxCB 专利\n- **30+ 必须开始用**（晚了细纹固定）\n\n### 2️⃣ 面部精华（核心）\n**兰蔻小黑瓶**：\n- 二裂酵母同款（升级版）\n- 修复屏障+抗老双效\n- **早晚用各 2 滴**\n\n### 3️⃣ 美容仪（外部刺激）\n**Notime 三合一**：\n- **RF 射频**：促进胶原蛋白生成\n- 光子嫩肤：淡化色斑\n- EMS：提拉紧致\n- 每周 3-4 次 + 配合精华使用效果翻倍\n\n### 4️⃣ 内服（根本调理）\n**Swisse 胶原蛋白肽**：\n- 内服补充胶原（外用只补 20%）\n- 鱼油抗氧化\n- 30+ 内调比外抹更重要\n\n## 🎯 抗衰组合发挥逻辑\n\n```\n内服胶原 → 体内合成胶原蛋白\n     ↓\n精华渗透 → 表皮吸收抗老活性\n     ↓\n美容仪刺激 → 促进胶原生成 + 精华吸收翻倍\n     ↓\n眼霜重点 → 最薄部位精准防护\n```\n\n## 💰 5 年抗衰投资 ROI\n\n这套装备**用 5 年的总成本 ¥30000**（每月 ¥500），但：\n- 5 年后看起来年轻 5-10 岁\n- 避免医美项目 ¥10000+/次\n- 信心+气质值\n\n## ⚠️ 抗衰避坑\n\n- ❌ **40 岁才开始**（晚了，35 前是黄金期）\n- ❌ **只用便宜货**（廉价精华浓度不够）\n- ❌ **三天打鱼两天晒网**（抗衰 = 长期坚持）\n- ❌ **忽视防晒**（紫外线是衰老 80% 原因）\n\n## 🌟 加 ¥0 但重要的事\n\n比这 ¥5777 装备更重要的：\n1. **每天 SPF50+ 防晒**（≤¥200 但效果最大）\n2. **23 点前睡觉**（皮肤修复黄金时间）\n3. **戒糖+多喝水**\n4. **运动 3 次/周**（血液循环=皮肤光泽）\n\n护肤+生活习惯**双线作战**才是真抗衰。",
    ["雅诗兰黛小棕瓶眼霜+精华礼盒+二裂酵母+ChronoluxCB+月销4500，30+抗老首选", "兰蔻菁纯+小黑瓶精华套装+玫瑰精粹+视黄醇+月销2200，抗老经典", "Notime美容仪RF+光子+EMS三合一+月销1200，每周3-4次配合精华效果翻倍", "Swisse胶原蛋白肽60片+鱼油60粒+月销1.5万，内服比外抹重要"]
))

# 8. bundle - 1500 周末野餐
T.append(make_traj(
    "sft_bundle_036", "bundle_purchase", "组合购物",
    "1500 元周末野餐装备",
    "想买齐周末公园野餐装备，1500 预算",
    {"query": "野餐装备 防水垫+食物+保温+拍照", "max_price": 1700, "filters": {"category": "picnic_set"}},
    [
        {"product_id": "mock_picnic_1", "title": "Naturehike 野餐垫 200×180 防水防潮", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "Naturehike/200×180加大/防水防潮", "sales": "月销4500"},
        {"product_id": "mock_picnic_2", "title": "野餐保温篮 30L 含食品级保鲜内胆", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "30L+食品级保鲜+保温/冷藏8小时", "sales": "月销2500"},
        {"product_id": "mock_picnic_3", "title": "便携咖啡机 户外手压款", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "户外手压式+无需电源/野餐做咖啡", "sales": "月销850"},
        {"product_id": "mock_picnic_4", "title": "藤编野餐篮 复古ins风 大号", "price": 269, "is_platform_self": True, "rating": 4.9, "key_specs": "藤编大号/ins复古风/拍照神器", "sales": "月销1500"},
        {"product_id": "mock_picnic_5", "title": "野餐餐具套装 含杯盘+刀叉+开酒器 4 人份", "price": 199, "is_platform_self": True, "rating": 4.9, "key_specs": "4人份餐具/含开酒器/可水洗循环用", "sales": "月销1200"}
    ],
    "周末野餐装备 5 件套 ¥1265，**ins 风+实用兼顾**：\n\n## 🧺 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 🥇 野餐垫 | **Naturehike 200×180** | ¥199 |\n| 保温篮 | 30L 食品级保鲜 | ¥299 |\n| 藤编篮 | ins 复古风 | ¥269 |\n| 餐具 | 4 人份+开酒器 | ¥199 |\n| 咖啡机 | 户外手压款 | ¥299 |\n| **合计** | | **¥1265** | 余 ¥235 |\n\n## 🎨 ins 野餐 SOP\n\n### 1️⃣ 防水垫先铺\n- 200×180 是 3-4 人尺寸\n- Naturehike 防水（草地有露水也不渗）\n\n### 2️⃣ 藤编篮拍照\n- **ins 风野餐 80% 看篮子**\n- 复古风篮子比塑料篮高级 10 倍\n- 装面包/葡萄/水果\n\n### 3️⃣ 保温篮存饮料\n- 红酒/汽水/水果**冷藏 8 小时**\n- 食品级内胆\n\n### 4️⃣ 手压咖啡机做仪式感\n- 户外手动做咖啡\n- **拍照超出片**\n\n## 📸 野餐拍照 3 招\n\n1. **俯拍**：野餐垫+食物+人脚（小红书爆款机位）\n2. **斜 45°**：藤编篮+蓝天背景\n3. **特写**：咖啡机+面包+鲜花\n\n## 🍓 食物搭配（额外 ¥200-300）\n\n推荐组合：\n- **法棍+乳酪+蜂蜜**（高级感）\n- **新鲜葡萄+草莓+蓝莓**（颜色丰富）\n- **三明治+水果沙拉**（饱腹）\n- **红酒+起泡水**（仪式感）\n\n## 💰 余 ¥235 加\n\n- 折叠野餐桌 ¥150\n- 飞盘/羽毛球 ¥80\n- 一次性垃圾袋 ¥10\n- 防蚊液 ¥30\n\n## ⚠️ 野餐避雷\n\n- ❌ **白衬衫坐草地**（绿色草汁洗不掉）\n- ❌ **吃含汁水多的水果**（西瓜会染色野餐垫）\n- ❌ **垃圾留现场**（被举报+罚款）\n- ❌ **明火烤肉**（公园禁止）\n\n这套装备**一年用 10-15 次回本**——每次野餐 ¥126，比下馆子还便宜。",
    ["Naturehike野餐垫200×180+防水防潮+月销4500，3-4人尺寸基础", "30L野餐保温篮+食品级保鲜+冷藏8小时+月销2500，饮料水果保鲜", "户外手压咖啡机+无需电源+月销850，野餐仪式感拍照神器", "藤编大号野餐篮+ins复古风+月销1500，野餐拍照80%看篮子", "4人份餐具+含开酒器+月销1200，循环用低碳环保"]
))

# 9. place_order - 跨境购买
T.append(make_traj(
    "sft_order_020", "place_order", "购物下单",
    "海外直邮+海关清关",
    "看到日本亚马逊那款 ¥899 的鼻毛修剪器，购物平台国际能直邮吗",
    {"product_query": "鼻毛修剪器 日本品牌", "from_overseas": True, "country": "Japan"},
    [
        {"product_id": "mock_intl_001", "title": "松下 ER-GN30 鼻毛修剪器 日本直邮", "price": 899, "is_platform_self": True, "rating": 4.9, "key_specs": "购物平台日本馆直邮/7-10天到/订单[TRACKING_ID]-JP-2284", "sales": "—"}
    ],
    "✅ 已通过购物平台日本馆下单，**对应日亚同款日本直邮**：\n\n## 📦 订单详情\n\n- **商品**：松下 ER-GN30 鼻毛修剪器（日版）\n- **价格**：¥899（含税）\n- **订单号**：[TRACKING_ID]-JP-2284\n- **发货**：**日本直邮**（不是国内代购）\n- **到货时间**：**7-10 个工作日**\n\n## 🌐 跨境购物 4 大重点\n\n### 1️⃣ 价格已含税\n购物平台日本馆**价格已包含跨境综合税**：\n- 个人物品税率 11.9%（日用电器）\n- **¥899 是到手价**，海关入境时不另收\n\n### 2️⃣ 物流流程\n```\nDay 0: 购物平台日本馆下单\nDay 1-2: 日本仓发货\nDay 3-5: 国际段空运到中国\nDay 6-8: 中国海关清关\nDay 9-10: 国内派送到家\n```\n\n### 3️⃣ 海关验证身份\n- 购物平台已用你购物平台账户**自动实名申报**\n- 不需要你额外提供身份证照片\n- 如遇异常海关会通过购物平台客服联系你\n\n### 4️⃣ 售后政策\n- ✅ **未拆封 30 天可退**\n- ❌ **已拆封不可退**（跨境法规）\n- ⚠️ **质量问题**：购物平台国际客服走特殊通道\n\n## ⚠️ 跨境购物避坑\n\n### 1. **电压差异**（最重要）\n- 日本电压 100V，中国 220V\n- **松下 ER-GN30 是电池款**（不涉及电压）\n- 但如果是日本电饭煲/吹风机**直接插会烧**\n\n### 2. **保修不一样**\n- 日版保修在日本（你买不了日本保修）\n- 购物平台日本馆**自营保修 1 年**（替代）\n\n### 3. **说明书是日文**\n- 日本品牌中文说明书可下载 PDF（搜「松下 ER-GN30 中文说明书」）\n- 操作简单的小家电基本不需要看\n\n## 💡 购物平台日本馆 vs 国内自营\n\n如果你单纯想买**鼻毛修剪器**，国内也有：\n- 飞利浦 NT3650（国内）¥199\n- 飞科 FS800（国内）¥39\n\n你为什么选松下日版 ¥899 呢？\n\n### 可能原因\n1. **日本品质要求高**（确实，但贵 ¥700）\n2. **同事推荐**（请确认推荐的是这款）\n3. **小红书种草**（注意辨别广告）\n\n如果只是想试试日本品质，**¥899 偏贵**。国内 ¥199 飞利浦也够用。\n\n## 🎯 真心建议\n\n如果你已经下单了就等收货吧。\n\n**如果你能取消**，可以考虑：\n- 飞利浦 NT3650 国内 ¥199（**便宜 ¥700**）\n- 体验差不超过 10%\n\n但你已下单的话，**¥899 也不算亏**——松下日版小家电品质是真好。",
    ["松下ER-GN30鼻毛修剪器日本直邮+购物平台日本馆+7-10天到，跨境购物含税到手价"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase - 替代款
T.append(make_traj(
    "sft_repurchase_018", "repurchase", "复购召回",
    "复购+找平替建议",
    "再买之前那个 La Mer 面霜，今年涨价好多",
    {"category_keyword": "面霜", "time_range": "last_6_months", "show_alternatives": True},
    [
        {"product_id": "mock_lamer_old", "title": "La Mer 海蓝之谜面霜 30ml (你 4 月前 ¥1980)", "price": 1980, "is_platform_self": True, "rating": 4.9, "key_specs": "你4月前购买¥1980/订单[TRACKING_ID]", "sales": "—"},
        {"product_id": "mock_lamer_now", "title": "La Mer 面霜 30ml (当前价 ¥2280)", "price": 2280, "is_platform_self": True, "rating": 4.9, "key_specs": "当前价¥2280涨300/月销1500", "sales": "月销1500"},
        {"product_id": "mock_alt_1", "title": "雅诗兰黛白金面霜 50ml (类似配方)", "price": 1880, "is_platform_self": True, "rating": 4.9, "key_specs": "雅诗兰黛白金/容量50ml(大62%)/同档奢牌", "sales": "月销850"},
        {"product_id": "mock_alt_2", "title": "兰蔻菁纯面霜 50ml (玫瑰精粹)", "price": 1480, "is_platform_self": True, "rating": 4.9, "key_specs": "兰蔻菁纯/50ml+玫瑰精粹/性价比之王", "sales": "月销1500"}
    ],
    "查到你 4 个月前买的是 **La Mer 海蓝之谜面霜 ¥1980**（订单 [TRACKING_ID]）。\n\n## 📊 价格变化\n\n- 你买的时候：¥1980\n- **当前：¥2280**（涨 ¥300，**+15%**）\n- 历史最低：¥1880\n\n## 🆘 La Mer 涨价的应对方案\n\n### 选项 A：继续买 La Mer ¥2280\n- 信仰党\n- 已经认可效果不想换\n- **但建议等 618 末班车降到 ¥2080 左右**\n\n### 选项 B：换雅诗兰黛白金 ¥1880\n- **同档奢牌**\n- 50ml vs La Mer 30ml（**多 67% 容量**）\n- 单 ml 价格 ¥37.6 vs La Mer ¥76（**便宜一半**）\n- 二裂酵母配方（抗老经典）\n\n### 选项 C：兰蔻菁纯面霜 ¥1480 ⭐ 性价比之王\n- 玫瑰精粹（女性最爱）\n- 50ml 大容量\n- **比 La Mer 便宜 ¥800**\n- 月销 1500 件\n\n## 💰 价格对比表\n\n| 商品 | 价格 | 容量 | 单 ml |\n|---|---|---|---|\n| La Mer 当前 | ¥2280 | 30ml | ¥76 |\n| 雅诗兰黛白金 | ¥1880 | 50ml | **¥37.6** |\n| 兰蔻菁纯 | ¥1480 | 50ml | **¥29.6** |\n\n## 💡 真心建议\n\n**3 种用户的不同选择**：\n\n### 1️⃣ 你认 La Mer 信仰\n继续买 La Mer，但**等 618 降到 ¥2080 再买**。这是历史价位。\n\n### 2️⃣ 你想换性价比\n**直接换兰蔻菁纯 ¥1480**：\n- 同档奢牌\n- 单 ml 便宜 60%\n- 1 年省 ¥800（够买半个 La Mer）\n\n### 3️⃣ 你想温和过渡\n**雅诗兰黛白金 ¥1880**：\n- 价格接近 La Mer\n- 二裂酵母效果好\n- 50ml 用 6 个月（La Mer 30ml 用 3 个月）\n\n## ⚠️ La Mer 真相\n\n说点真心话：\n- La Mer 效果**没贵 ¥800 那么多**\n- 主要价值在**仪式感+奢华感**\n- 30ml 用 3 个月 = **每天 ¥25** 的面霜（贵）\n\n如果你愿意尝试，**兰蔻菁纯 ¥1480 是绝大多数 La Mer 用户的最佳过渡**——效果相当 + 容量翻倍。\n\n要直接帮你下单兰蔻 ¥1480 吗？还是等 La Mer 降价？",
    ["La Mer面霜你4月前购买¥1980+订单[TRACKING_ID]，当前涨到¥2280涨15%", "La Mer当前价¥2280+30ml+历史最低¥1880，信仰党等618末班车", "雅诗兰黛白金面霜50ml+二裂酵母+月销850，温和过渡奢牌平替", "兰蔻菁纯面霜50ml+玫瑰精粹+月销1500，性价比之王单ml便宜60%"],
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
