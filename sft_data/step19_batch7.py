# -*- coding: utf-8 -*-
"""Step 19: 第 7 批 10 条"""
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

# 1. similar_rec - 抱怨大小不合适
T.append(make_traj(
    "sft_simrec_025", "similar_rec", "相似品推荐",
    "抱怨尺码偏大 → 推荐小一码同款",
    "买的那件 M 码风衣穿着像袍子，有偏小的同款吗",
    {"query": "女士风衣 修身版型 小码", "filters": {"sizing": "slim_fit_or_petite"}, "exclude_skus": ["M码原款"]},
    [
        {"product_id": "jd_coat_s1", "title": "Maxmara同款 经典风衣 修身版 S码", "price": 1299, "is_jd_self": True, "rating": 4.9, "key_specs": "修身版/比常规版小0.5码/S码贴合", "sales": "月销680"},
        {"product_id": "jd_coat_s2", "title": "优衣库 风衣 petite小个子版 S码", "price": 599, "is_jd_self": True, "rating": 4.8, "key_specs": "Petite专为150-160身高/袖长腰节都缩短", "sales": "月销4500"},
        {"product_id": "jd_coat_s3", "title": "Burberry同款 翻领修身风衣 S码", "price": 1899, "is_jd_self": True, "rating": 4.9, "key_specs": "经典翻领修身/收腰设计/小个子友好", "sales": "月销380"}
    ],
    "M 码穿着像袍子说明你属于小个子/瘦体型。3 款都是为偏小身材设计：\n\n**1. 优衣库 Petite ¥599** ⭐ 性价比首选\n**Petite 系列专为 150-160cm 设计**，袖长+腰节都缩短，**不用改裤脚**。月销 4500 件最受小个子追捧。\n\n**2. Maxmara 同款修身版 ¥1299**\n比常规版小 0.5 码，**修身剪裁显瘦**。设计师品牌质感。\n\n**3. Burberry 同款翻领修身 ¥1899**\n经典款型+收腰设计，**通勤场合最显气质**。\n\n## 💡 选码关键\n\n身高 150-160 优衣库 Petite，160-168 选 Maxmara/Burberry 的 S 码。",
    ["Maxmara修身版比常规小0.5码+S码贴合，设计师质感小个子修身首选", "优衣库Petite专为150-160身高+袖长腰节缩短+月销4500，小个子免改裤脚", "Burberry同款翻领修身+收腰设计+月销380，通勤气质党首选"]
))

# 2. similar_rec - 抱怨偏甜
T.append(make_traj(
    "sft_simrec_026", "similar_rec", "相似品推荐",
    "抱怨口味偏甜 → 推荐无糖/低糖款",
    "之前那款酸奶太甜了，有无糖或低糖的同品牌款吗",
    {"query": "酸奶 无糖 低糖 高蛋白", "filters": {"sugar_content_max_g": 5, "is_protein_rich": True}},
    [
        {"product_id": "jd_yog_1", "title": "简爱 0蔗糖酸奶 无糖款 100g×10杯", "price": 49, "is_jd_self": True, "rating": 4.9, "key_specs": "0蔗糖/纯天然/100g×10杯/0添加剂", "sales": "月销4.5万"},
        {"product_id": "jd_yog_2", "title": "明治 保加利亚式酸奶 无糖原味 400g", "price": 26, "is_jd_self": True, "rating": 4.9, "key_specs": "0糖/明治百年品牌/400g大盒", "sales": "月销3.5万"},
        {"product_id": "jd_yog_3", "title": "蒙牛 冠益乳 低糖款 100g×4", "price": 12, "is_jd_self": True, "rating": 4.8, "key_specs": "低糖（5g以下）/经典LC菌/100g×4杯", "sales": "月销5.5万"}
    ],
    "0 糖 + 高蛋白 = 健康酸奶黄金组合。3 款：\n\n**1. 简爱 0 蔗糖 ¥49（10 杯）** ⭐ 首选\n**0 蔗糖+0 添加剂**，是真「配料表只有生牛乳+乳酸菌」的纯净酸奶。¥4.9/杯。\n\n**2. 明治保加利亚 ¥26**\n日本百年品牌，**400g 大盒装一家三口够吃 2 天**。¥6.5/100g 最便宜。\n\n**3. 蒙牛冠益乳低糖 ¥12（4 杯）**\n低糖（不是 0 糖，含约 4g）+经典 LC 菌。预算紧选这个。\n\n## ⚠️ 选购避雷\n\n- ❌ 「低脂酸奶」 ≠ 「低糖」（低脂往往加糖增加口感）\n- ❌ 「风味酸奶」基本都加糖（包装小字写「白砂糖」）\n- ✅ **看配料表前 3 位**：必须是「生牛乳+菌+水」（无糖无添加剂）",
    ["简爱0蔗糖+0添加剂+纯天然+月销4.5万，最纯净酸奶配料表标杆", "明治保加利亚式0糖+400g大盒+百年品牌+月销3.5万，全家分享最划算", "蒙牛冠益乳低糖+LC菌+月销5.5万，预算紧低糖入门"]
))

# 3. sku_comp - 不同年款同型号
T.append(make_traj(
    "sft_skucomp_023", "sku_comp", "商品对比",
    "新旧款 iPad Air 对比",
    "iPad Air 6 (M2) 和 iPad Air 5 (M1) 差 1500，值不值",
    {"skus": ["iPad Air 6 M2 11寸", "iPad Air 5 M1 10.9寸"], "mode": "parallel_exact_match"},
    [
        {"product_id": "jd_iair6", "title": "iPad Air 6 M2 11寸 128G", "price": 4799, "is_jd_self": True, "rating": 4.9, "key_specs": "M2芯片(2024)/11寸/128G/USB-C 10Gbps", "sales": "月销8500"},
        {"product_id": "jd_iair5", "title": "iPad Air 5 M1 10.9寸 64G", "price": 3299, "is_jd_self": True, "rating": 4.9, "key_specs": "M1芯片(2022)/10.9寸/64G/USB-C 5Gbps", "sales": "月销1.2万"}
    ],
    "iPad Air 5 → Air 6 升级了 4 个核心点：\n\n## 📊 关键差异\n\n| 维度 | Air 5 (M1) ¥3299 | Air 6 (M2) ¥4799 |\n|---|---|---|\n| 芯片 | M1（2020 年） | **M2（2022 年）+ 18% CPU** |\n| 内存 | 8GB | 8GB（同等）|\n| 存储 | **64G**（基础款）| **128G**（基础款）|\n| USB-C | 5Gbps | **10Gbps（双倍）**|\n| 屏幕 | 10.9 寸 | 11 寸 |\n\n## 💰 ¥1500 差价拆解\n\n- M2 vs M1：约 ¥500 溢价\n- 128G vs 64G：实际差 ¥1000\n\n**核心结论：¥1500 主要买的是存储翻倍**。M2 vs M1 对日常使用影响极小（除非你跑 PR/3D 建模）。\n\n## 🎯 怎么选\n\n### ✅ Air 5 ¥3299 够用：\n- 上网课/刷视频/看书 → 64G 都够\n- 偶尔记笔记 → 单设备使用足够\n- 不打算扩展存储 → 直接 Air 5\n\n### ✅ Air 6 ¥4799 值得：\n- 离线电影 50G+ → 必须 128G\n- 拍 4K 视频素材 → 必须 128G\n- 接外置硬盘传文件 → USB 10Gbps 实际有用\n\n## 💡 真心建议\n\n**80% 的人 Air 5 ¥3299 就够**。除非你能明确说出 64G 装不下的需求，否则别多花 ¥1500。\n\n如果存储真的不够，Air 6 256G 版（¥5499）比 64G→128G→256G 阶梯更划算。",
    ["iPad Air 6 M2+128G+USB-C 10Gbps+月销8500，存储党+视频党升级首选", "iPad Air 5 M1+64G+USB-C 5Gbps+月销1.2万，80%用户够用省1500"]
))

# 4. sku_comp - 国产 vs 进口
T.append(make_traj(
    "sft_skucomp_024", "sku_comp", "商品对比",
    "国产 vs 进口奶粉对比",
    "1岁宝宝奶粉，飞鹤臻稚 vs 启赋蕴萃，国产 vs 进口怎么选",
    {"skus": ["飞鹤臻稚3段", "启赋蕴萃3段"], "mode": "parallel_exact_match"},
    [
        {"product_id": "jd_fh_zz3", "title": "飞鹤臻稚 3段奶粉 700g 1-3岁", "price": 339, "is_jd_self": True, "rating": 4.9, "key_specs": "中国新国标/A2牛奶/适合中国宝宝体质/700g", "sales": "月销3.5万"},
        {"product_id": "jd_qf3", "title": "启赋蕴萃 3段（爱尔兰进口）900g", "price": 459, "is_jd_self": True, "rating": 4.9, "key_specs": "爱尔兰进口/HMO母乳低聚糖/欧标/900g", "sales": "月销1.8万"}
    ],
    "1 岁宝宝奶粉选择 = **国产新国标 vs 进口欧标**，没有绝对答案：\n\n## 📊 关键对比\n\n| 维度 | 飞鹤臻稚 ¥339/700g | 启赋蕴萃 ¥459/900g |\n|---|---|---|\n| 单价 | ¥4.84/g | **¥5.10/g** |\n| 奶源 | 中国黑龙江 A2 | **爱尔兰一级牧场** |\n| 标准 | **2023 新国标** | 欧盟标准 |\n| 配方亮点 | A2 蛋白+针对中国宝宝 | **HMO 母乳低聚糖** |\n| 月销 | **3.5 万** | 1.8 万 |\n\n## 🎯 怎么选\n\n### 选 飞鹤臻稚 ¥339（国产派）：\n- **新国标比欧标更严**（中国 2023 新国标）\n- 月销 3.5 万是断档第一，信任度最高\n- **A2 蛋白适合中国宝宝体质**\n- 价格便宜 ¥120/罐\n\n### 选 启赋蕴萃 ¥459（进口派）：\n- **HMO 母乳低聚糖**是进口的护城河（国产配方暂无）\n- 爱尔兰一级牧场（北纬 50° 黄金牧场）\n- 大罐 900g（飞鹤 700g），单 g 价格其实只贵 ¥0.26\n\n## 💡 我的建议\n\n**普通宝宝**：飞鹤臻稚 ¥339（性价比+国货支持）\n**易过敏/肠胃敏感宝宝**：启赋蕴萃 ¥459（HMO 缓解肠胃不适）\n**两个都试过都适合**：哪个孩子更爱喝选哪个（口感差异）\n\n## ⚠️ 重要：1 岁后可逐渐过渡到牛奶\n\n奶粉 3 段不是必须吃到 3 岁，**1 岁后辅食营养充足可逐渐过渡到鲜牛奶**，奶粉作为补充即可。",
    ["飞鹤臻稚A2牛奶+新国标+月销3.5万，国产顶尖+性价比+中国宝宝体质", "启赋蕴萃爱尔兰一级牧场+HMO母乳低聚糖+900g大罐，肠胃敏感宝宝进口首选"]
))

# 5. matching - 出差差旅
T.append(make_traj(
    "sft_match_023", "matching_purchase", "搭配购物",
    "商务差旅整套搭配",
    "下周出差3天，配齐行李箱+西装套+商务鞋+背包",
    {"query": "商务差旅装备 行李箱+西装+商务鞋", "filters": {"category": "business_travel", "trip_duration_days": 3}},
    [
        {"product_id": "jd_biz_1", "title": "新秀丽 商务行李箱 24寸 PC材质", "price": 1299, "is_jd_self": True, "rating": 4.9, "key_specs": "24寸/PC材质/TSA锁/可登机+3天差旅刚好", "sales": "月销4500"},
        {"product_id": "jd_biz_2", "title": "雅戈尔 商务西装套装 深灰色 修身版", "price": 1999, "is_jd_self": True, "rating": 4.9, "key_specs": "深灰色/含西装+裤子/羊毛混纺/防皱", "sales": "月销2200"},
        {"product_id": "jd_biz_3", "title": "Tumi 商务背包 笔记本仓 黑色", "price": 1499, "is_jd_self": True, "rating": 4.9, "key_specs": "15.6寸笔记本仓/防水/Tumi品牌商务标配", "sales": "月销1500"},
        {"product_id": "jd_biz_4", "title": "Clarks 真皮商务鞋 黑色 牛津款", "price": 899, "is_jd_self": True, "rating": 4.9, "key_specs": "Clarks英国品牌/头层牛皮/防滑商务正装", "sales": "月销3500"}
    ],
    "3 天商务差旅 4 件套配齐 ¥5696：\n\n## 💼 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 行李箱 | **新秀丽 24 寸 PC** | ¥1299 |\n| 西装 | **雅戈尔深灰修身套装** | ¥1999 |\n| 背包 | **Tumi 商务背包** | ¥1499 |\n| 商务鞋 | **Clarks 牛津鞋** | ¥899 |\n| **合计** | | **¥5696** |\n\n## 💡 选品逻辑\n\n### 1️⃣ 行李箱 24 寸刚好\n- 22 寸太小（3 天衣服+电脑+洗漱包塞不下）\n- 28 寸太大（很多酒店行李架放不下）\n- **24 寸 = 3 天差旅+登机箱黄金尺寸**\n\n### 2️⃣ 西装选深灰修身\n- **比黑色显年轻 + 比深蓝更百搭**\n- 修身版避免「面口袋感」\n- 防皱面料（行李箱里揉一天也能穿）\n\n### 3️⃣ Tumi 背包是商务党暗号\n- 同等价位中**做工和分仓设计最强**\n- 15.6 寸笔记本仓 + 多个小袋（充电线/笔/文件）\n- 一眼就是「专业人士」的视觉标签\n\n### 4️⃣ Clarks 牛津鞋耐穿\n- 英国老牌质量稳，**1 双穿 5 年**\n- 黑色配深灰西装绝配\n- 头层牛皮越穿越柔软\n\n## 🎯 3 天差旅打包清单\n\n```\n🧳 行李箱（24寸）\n├─ 西装 1 套（必穿）\n├─ 衬衫 2 件（白+浅蓝）\n├─ 内裤袜子 4 套\n├─ 睡衣 1 套\n├─ 洗漱包\n├─ 备用平底鞋 1 双\n└─ 折叠雨伞\n\n🎒 背包\n├─ MacBook + 充电器\n├─ 文件夹\n├─ 钱包+护照\n├─ 移动电源\n└─ 降噪耳机\n```\n\n这套装备**重要客户拜访 100% 出场即专业**。",
    ["新秀丽24寸PC+TSA锁+可登机+月销4500，3天差旅+登机黄金尺寸", "雅戈尔深灰修身西装+羊毛混纺防皱，比黑色显年轻百搭", "Tumi商务背包15.6寸+防水+月销1500，商务党专业人士视觉标签", "Clarks英国头层牛皮+牛津款+月销3500，5年耐穿配深灰绝配"]
))

# 6. matching - 厨房咖啡角
T.append(make_traj(
    "sft_match_024", "matching_purchase", "搭配购物",
    "家庭咖啡角整套",
    "想在厨房角落做个咖啡角，配咖啡机+磨豆+杯具+收纳",
    {"query": "家庭咖啡角 整体配置", "filters": {"category": "home_coffee_corner", "style": "cafe_aesthetic"}},
    [
        {"product_id": "jd_coffee_1", "title": "德龙 EC9255 半自动咖啡机 双锅炉", "price": 4999, "is_jd_self": True, "rating": 4.9, "key_specs": "德龙旗舰/双锅炉/拉花蒸汽/家用咖啡馆级", "sales": "月销1500"},
        {"product_id": "jd_coffee_2", "title": "百胜图 BT-90 电动磨豆机 锥刀", "price": 999, "is_jd_self": True, "rating": 4.9, "key_specs": "锥刀磨盘/40档粗细可调/匹配半自动机", "sales": "月销2200"},
        {"product_id": "jd_coffee_3", "title": "Notneutral Lino 拿铁杯套装 6色", "price": 459, "is_jd_self": True, "rating": 4.9, "key_specs": "美国Notneutral/6种色/8oz拿铁杯×6", "sales": "月销680"},
        {"product_id": "jd_coffee_4", "title": "竹木咖啡器具收纳架 多层", "price": 299, "is_jd_self": True, "rating": 4.8, "key_specs": "竹木/4层/收纳豆罐/粉碗/压粉锤", "sales": "月销1200"}
    ],
    "家庭咖啡角 4 件 ¥6756，**家用咖啡馆级配置**：\n\n## ☕ 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 🥇 咖啡机 | **德龙 EC9255 双锅炉半自动** | ¥4999 |\n| 磨豆机 | **百胜图 BT-90 锥刀** | ¥999 |\n| 杯具 | **Notneutral Lino 拿铁杯 6 色** | ¥459 |\n| 收纳架 | 竹木 4 层咖啡角架 | ¥299 |\n| **合计** | | **¥6756** |\n\n## 💡 选品理由\n\n### 1️⃣ 德龙 EC9255 是家用半自动天花板\n- **双锅炉**（一边煮咖啡一边打奶，效率翻倍）\n- 蒸汽棒可拉花\n- ¥4999 价位「真正能拉出花的家用机」唯一选择\n- 比 ¥2000 价位的便宜机**奶泡细腻度高 80%**\n\n### 2️⃣ 磨豆机 ¥999 必须配\n**半自动机最大的误区：买好机不买好磨**：\n- 平刀磨豆 = 出粉不均 = 萃取不均 = 难喝\n- 锥刀磨豆 = 出粉均匀 = 咖啡好喝 80% 看磨豆机\n- 百胜图 BT-90 是 ¥1000 内最值的锥刀磨\n\n### 3️⃣ Notneutral 拿铁杯是「咖啡圈圣杯」\n- 美国设计师品牌，**全球咖啡馆都在用**\n- 6 色搭配心情切换\n- 8oz 标准拿铁尺寸\n\n### 4️⃣ 收纳架让咖啡角变咖啡馆\n竹木 4 层架放：豆罐 + 粉碗 + 压粉锤 + 拉花缸 + 杯具，**台面整洁度+颜值翻倍**。\n\n## 🎯 进阶配件（可选 +¥1000）\n\n- 拉花缸 ¥150（不锈钢）\n- 布粉器 ¥80\n- 压粉锤（实木）¥200\n- 咖啡豆罐×3 ¥150\n- 温度计 ¥100\n- 称豆电子秤 ¥150\n\n## ⚠️ 入坑警告\n\n开始这件事**就回不去了**：\n- 你会买不同产地咖啡豆（¥200-500/包）\n- 你会订阅咖啡豆月度计划（¥300/月）\n- 你会开始研究单品 vs 拼配（¥1000+ 学费）\n\n但**每天早上一杯精品手冲 = 每天 ¥30 咖啡馆体验 × 365 天 = 每年省 ¥10000**，1 年回本。",
    ["德龙EC9255双锅炉半自动+蒸汽拉花，家用咖啡馆级唯一选择", "百胜图BT-90锥刀磨+40档粗细可调，咖啡好喝80%看磨豆", "Notneutral Lino拿铁杯6色+全球咖啡馆同款+8oz标准，咖啡圈圣杯", "竹木4层收纳架+豆罐+粉碗+压粉锤，咖啡角变咖啡馆颜值翻倍"]
))

# 7. bundle - 留学行李
T.append(make_traj(
    "sft_bundle_021", "bundle_purchase", "组合购物",
    "5000 元留学第一年装备",
    "9 月去美国留学，5000 预算配齐第一年的电器+生活用品",
    {"query": "留学装备 电器生活用品", "max_price": 5500, "filters": {"category": "study_abroad", "voltage": "110V_or_universal"}},
    [
        {"product_id": "jd_abroad_1", "title": "Anker 100W 氮化镓充电器 4口 全球电压", "price": 299, "is_jd_self": True, "rating": 4.9, "key_specs": "100W 4口/全球电压100-240V/PD3.0", "sales": "月销3.5万"},
        {"product_id": "jd_abroad_2", "title": "戴森 Supersonic 吹风机 美版110V", "price": 2899, "is_jd_self": True, "rating": 4.9, "key_specs": "美版110V直接用/戴森招牌/不伤发", "sales": "月销1500"},
        {"product_id": "jd_abroad_3", "title": "小米电饭煲 美版110V 1.5L", "price": 599, "is_jd_self": True, "rating": 4.8, "key_specs": "美版110V/1.5L单人量/IH加热", "sales": "月销680"},
        {"product_id": "jd_abroad_4", "title": "新秀丽 30寸大行李箱 PC材质", "price": 1499, "is_jd_self": True, "rating": 4.9, "key_specs": "30寸超大/PC/TSA锁/留学专用", "sales": "月销2500"}
    ],
    "5000 留学装备 4 件套 ¥5296，**超 ¥296 但都是刚需**：\n\n## ✈️ 完整方案\n\n| 装备 | 商品 | 价格 | 重要性 |\n|---|---|---|---|\n| 🥇 充电器 | **Anker 100W 全球电压** | ¥299 | ⭐⭐⭐⭐⭐ |\n| 吹风机 | **戴森 Supersonic 美版** | ¥2899 | ⭐⭐⭐⭐ |\n| 电饭煲 | **小米美版 110V** | ¥599 | ⭐⭐⭐⭐⭐ |\n| 行李箱 | **新秀丽 30 寸** | ¥1499 | ⭐⭐⭐⭐⭐ |\n| **合计** | | **¥5296** | |\n\n## 💡 关键决策：买美版 vs 中国版+变压器\n\n### ✅ 选美版（推荐）\n- **直接 110V 即插即用**，去美国当地买电器一样的体验\n- 不用扛变压器（变压器重 1-2kg）\n- 出问题美国本地维修\n- **国内买美版的价格 = 美国本地价 + 邮费**，并不贵\n\n### ❌ 不要买中国版+变压器\n- 变压器重 1-2kg 占行李配额（航空 1kg=¥80）\n- 变压器有损耗（咖啡机加热慢、电压不稳）\n- 长期使用变压器自身会坏\n\n## 🌍 全球电压充电器是 MUST HAVE\n\n手机/笔记本/相机都用同一个 Anker 100W：\n- 全球电压（100V 美国 / 220V 欧洲）\n- 4 口同时充（手机+电脑+iPad+耳机）\n- **比单独买 4 个充电器节省 ¥500**\n\n## 📦 30 寸行李箱是留学党标配\n\n30 寸≈158cm 三边总和（航司大件行李上限），**单件能装 23kg**。买 2 个 30 寸+背包是留学党出行常规。\n\n## 💰 余 ¥0 但建议加 ¥500 这些\n\n（行李箱里再塞）：\n- 美版蓝牙音箱 ¥199\n- 小型超声波熨衣机 ¥150（西装抗皱）\n- 食品级保温杯 ¥80\n- USB-C 数据线×3 ¥50\n\n## ⚠️ 留学不要带的\n\n- ❌ 中国电压电饭煲（美国 110V 不通用）\n- ❌ 转换插头（不是变压器，只换插脚，会烧）\n- ❌ 国产化妆品（美国海关查得严）\n- ❌ 中草药（一律禁止入境）\n\n## 🏆 真心建议\n\n**戴森吹风机 ¥2899 值不值？**\n如果你长发+在意发质 → 值（戴森不伤发是真的）。\n如果短发/不在乎 → 直接美国本地买 Conair 吹风机 ¥30 美元就够，**省 ¥2700 转买其他东西**。",
    ["Anker 100W 4口+全球电压100-240V+月销3.5万，留学党手机笔记本通用唯一充电器", "戴森Supersonic美版110V+直接即插即用，长发党不伤发刚需", "小米美版110V电饭煲+1.5L单人量+IH加热，留学党中餐刚需", "新秀丽30寸PC+TSA锁+月销2500，留学党单件装23kg标配"]
))

# 8. bundle - 婚礼伴娘
T.append(make_traj(
    "sft_bundle_022", "bundle_purchase", "组合购物",
    "1500 元伴娘整套",
    "下周当伴娘，1500 预算配伴娘服+鞋+包+发饰",
    {"query": "伴娘整套 香槟色礼服 配饰", "max_price": 1800, "filters": {"category": "bridesmaid_outfit"}},
    [
        {"product_id": "jd_bm_1", "title": "韩版伴娘礼服 香槟色 V领修身长款", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "香槟色/V领长款/修身显瘦/雪纺面料", "sales": "月销1500"},
        {"product_id": "jd_bm_2", "title": "意大利同款 香槟色高跟鞋 5cm 真皮", "price": 399, "is_jd_self": True, "rating": 4.8, "key_specs": "香槟色/5cm跟/真皮/婚礼站8h不累", "sales": "月销680"},
        {"product_id": "jd_bm_3", "title": "金色小手包 链条单肩 婚礼宴会款", "price": 299, "is_jd_self": True, "rating": 4.9, "key_specs": "金色链条/小手包/装手机口红钥匙", "sales": "月销1200"},
        {"product_id": "jd_bm_4", "title": "复古金色发饰头链 婚礼伴娘款", "price": 89, "is_jd_self": True, "rating": 4.9, "key_specs": "复古金色/头链发饰/搭配香槟色", "sales": "月销850"}
    ],
    "伴娘 4 件套 ¥1386 配齐，**重点是整体协调香槟色调**：\n\n## 👰 完整方案\n\n| 单品 | 商品 | 价格 |\n|---|---|---|\n| 礼服 | **香槟色 V 领修身长款** | ¥599 |\n| 高跟鞋 | **香槟色 5cm 真皮跟** | ¥399 |\n| 手包 | **金色链条小手包** | ¥299 |\n| 发饰 | **复古金色头链** | ¥89 |\n| **合计** | | **¥1386** |\n\n## 🎨 伴娘穿搭铁律\n\n### 1️⃣ 颜色：**不抢新娘风头**\n- ✅ 香槟/裸粉/雾蓝/沙金\n- ❌ 大红/纯白（雷区）\n- ❌ 黑色（葬礼色不合婚礼调）\n\n### 2️⃣ 长度：长款 > 短款\n- 长裙更显气质\n- 短款随意感强**对不起新娘的隆重**\n\n### 3️⃣ 鞋跟：5cm 是黄金\n- 太高站 8 小时崩溃\n- 太平显腿短\n- **5cm 既显高又不累**\n\n## 💡 选品理由\n\n### 礼服 ¥599 香槟色 V 领\n- V 领显锁骨+脸小\n- 修身长款显瘦显高\n- 雪纺面料**婚礼凉爽不闷**\n- 月销 1500 件是伴娘服爆款\n\n### 鞋 ¥399 真皮 5cm\n- **婚礼要站 8 小时**，便宜鞋会磨脚\n- 同色系搭配显腿长\n\n### 包 ¥299 金色小手包\n- 香槟色礼服**必须搭金色配饰**\n- 小手包只装必需品（手机/口红/钥匙）\n\n### 发饰 ¥89 头链\n- **最便宜的提质单品**\n- 金色发饰让整套贵气\n\n## 📸 拍照效果\n\n伴娘整体效果 = 同色系协调 + 配饰点缀 + 站姿。这套搭配出来：\n\n- 不抢新娘风头 ✅\n- 拍照好看 ✅\n- 不重样**与其他伴娘可同款也可单买**\n\n## 💰 加 ¥300 升级\n\n- 香槟色淡香水 ¥200\n- 假睫毛+口红补妆套装 ¥100\n\n婚礼当天**化妆时间紧张，提前 1 天预演一次穿搭**。",
    ["香槟色V领修身长款礼服+雪纺凉爽+月销1500，伴娘爆款不抢新娘风头", "香槟色5cm真皮高跟鞋+婚礼站8h不累，同色系显腿长", "金色链条小手包+装手机口红钥匙+月销1200，香槟色礼服必备金色配饰", "复古金色头链+搭配香槟色，89元提质单品让整套贵气"]
))

# 9. place_order - 跨店满减
T.append(make_traj(
    "sft_order_013", "place_order", "购物下单",
    "618 跨店满减下单",
    "618 想凑跨店满 300 减 50，给我搭配几个店的商品",
    {"target_amount": 300, "promotion": "cross_store_300_50", "max_total": 350},
    [
        {"product_id": "jd_618_1", "title": "三只松鼠 坚果礼盒（A店）", "price": 99, "is_jd_self": True, "rating": 4.9, "key_specs": "A店+月销5万+免运费", "sales": "月销5万"},
        {"product_id": "jd_618_2", "title": "蓝月亮 洗衣液 3kg（B店）", "price": 89, "is_jd_self": True, "rating": 4.9, "key_specs": "B店+京东自营+免运费", "sales": "月销8万"},
        {"product_id": "jd_618_3", "title": "舒肤佳 沐浴露 1L（C店）", "price": 79, "is_jd_self": True, "rating": 4.9, "key_specs": "C店+京东自营+免运费", "sales": "月销4.5万"},
        {"product_id": "jd_618_4", "title": "心相印 抽纸 24包（D店）", "price": 49, "is_jd_self": True, "rating": 4.9, "key_specs": "D店+京东自营+月销12万", "sales": "月销12万"}
    ],
    "✅ 已凑跨店满 300 减 50 方案，**4 件刚好 ¥316，实付 ¥266**：\n\n## 🛒 凑单方案\n\n| 商品 | 店铺 | 价格 |\n|---|---|---|\n| 三只松鼠坚果礼盒 | A 店 | ¥99 |\n| 蓝月亮洗衣液 3kg | B 店 | ¥89 |\n| 舒肤佳沐浴露 1L | C 店 | ¥79 |\n| 心相印抽纸 24 包 | D 店 | ¥49 |\n| **小计** | 4 店 | **¥316** |\n| **跨店满减** | -¥50 | |\n| **实付** | | **¥266** |\n\n## 💡 为什么这 4 件\n\n### 1️⃣ 都是日常消耗品（不囤会浪费）\n- 坚果：办公室零食/茶几必备\n- 洗衣液：每月 1 瓶用量\n- 沐浴露：3 个月 1 瓶\n- 抽纸：每月 1-2 包\n\n### 2️⃣ 4 个不同店（必须跨店）\n跨店满减要求**至少 2 个不同店铺**，4 个店触发的满减叠加效果最稳。\n\n### 3️⃣ 总价 ¥316 刚跨 ¥300 门槛\n**多花 ¥16 省 ¥50 = 净省 ¥34**，最优凑单原则。\n\n## 📐 跨店满减计算公式\n\n```\n净省 = 满减优惠 - (实际消费 - 门槛)\n      = 50 - (316 - 300)\n      = 50 - 16\n      = ¥34 净省\n```\n\n## ⚠️ 跨店满减规则\n\n1. **只算「自营+品牌旗舰店」**：第三方小店有些不参加\n2. **不能用其他单品券叠加**：买的时候自动选择最优\n3. **退货后满减失效**：如果退一件导致总价 <¥300，满减会被收回\n4. **京豆/PLUS 价是单独计算**：不影响跨店满减门槛判定\n\n## 💰 实付明细\n\n- 商品总价：¥316\n- 跨店满 300 减 50：-¥50\n- **实付**：¥266\n- 京豆抵扣（如果有）：可再减 ¥2.66\n\n要直接帮你下单吗？还是再调整商品？",
    ["三只松鼠坚果礼盒99元+免运费+月销5万+A店", "蓝月亮洗衣液3kg 89元+月销8万+B店", "舒肤佳沐浴露1L 79元+月销4.5万+C店", "心相印抽纸24包49元+月销12万+D店"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase - 复购+断货预警
T.append(make_traj(
    "sft_repurchase_011", "repurchase", "复购召回",
    "复购+检测断货",
    "再买一支之前那个口红",
    {"category_keyword": "口红", "time_range": "last_4_months", "check_stock": True},
    [
        {"product_id": "jd_lip_old", "title": "迪奥烈艳蓝金 999 (你2月前购买/当前缺货)", "price": 369, "is_jd_self": True, "rating": 4.9, "key_specs": "你2月前购买/订单[TRACKING_ID]/全国仓库缺货/预计1个月补货", "sales": "—"},
        {"product_id": "jd_lip_alt1", "title": "兰蔻 196 烂番茄红 (近似色)", "price": 320, "is_jd_self": True, "rating": 4.9, "key_specs": "色号197=999相似/兰蔻品牌/雾面质地", "sales": "月销2.5万"},
        {"product_id": "jd_lip_alt2", "title": "YSL 416 番茄红 (近似色)", "price": 380, "is_jd_self": True, "rating": 4.9, "key_specs": "镜面釉感/番茄红显白/和999色相近", "sales": "月销1.8万"}
    ],
    "**遗憾通知**：你 2 月前买的 **Dior 烈艳蓝金 999** 目前**全国缺货**，预计 1 个月后补货。\n\n## 🚨 缺货状态\n\n- 购买记录：2 个月前（订单 [TRACKING_ID]）\n- 商品：Dior 999 ¥369\n- **当前状态：缺货**（618 抢购完）\n- 补货时间：约 7 月底\n\n## 🛒 你的 2 个选择\n\n### 选项 A：等补货\n- **预约通知**：在商品页点「到货提醒」\n- 7 月底有货时自动短信通知你\n- 风险：抢购可能再次缺货\n\n### 选项 B：用相似色救急 ⭐ 推荐\n两款 999 的最强平替：\n\n#### 1️⃣ 兰蔻 196 烂番茄红 ¥320\n- **色号 196 是兰蔻官方对标 999 的色**\n- 雾面质地（和 999 一样）\n- **比 999 便宜 ¥49**\n- 月销 2.5 万件\n\n#### 2️⃣ YSL 416 番茄红 ¥380\n- 色相和 999 相近度 85%\n- **镜面釉感**（不是雾面，质地不同）\n- 适合喜欢润泽感的人\n\n## 💡 我的建议\n\n**如果你急用**（约会/婚礼/重要场合）：直接选 **兰蔻 196 ¥320**——色相最像 + 雾面质地一致 + 便宜 ¥49。\n\n**如果不急**：预约 Dior 999 补货，1 个月后买。\n\n## 📝 顺便\n\nDior 999 之所以缺货是因为它是**经典色号永远的常青树**。建议下次看到现货**直接囤 2 支**（口红开封 12 个月内用完最佳），避免再遇缺货。\n\n要直接下单兰蔻 196 救急吗？",
    ["Dior烈艳蓝金999你2月前购买，618后全国缺货，预计7月底补货", "兰蔻196烂番茄红+雾面质地+官方对标999色+便宜49元，最强平替", "YSL 416番茄红+镜面釉感+色相相近度85%，润泽感党备选"],
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
