# -*- coding: utf-8 -*-
"""Step 40: 第 28 批 10 条"""
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

# 1. similar_rec - 抱怨续航差（笔记本）
T.append(make_traj(
    "sft_simrec_067", "similar_rec", "相似品推荐",
    "抱怨续航不够 → 推荐续航长的同价位笔记本",
    "之前那台笔记本电脑满电只能用 4 小时，上课不够用，换续航长的同价位",
    {"query": "笔记本 长续航 学生 15小时+", "min_price": 5000, "max_price": 7000, "filters": {"battery_hours_min": 12}},
    [
        {"product_id": "mock_laptop_bat_1", "title": "华为 MateBook D16 12代酷睿 18h 续航", "price": 5499, "is_platform_self": True, "rating": 4.9, "key_specs": "18h续航/i5-12500H/16寸/1.7kg/月销1.5万", "sales": "月销1.5万"},
        {"product_id": "mock_laptop_bat_2", "title": "MacBook Air M3 15寸 18h苹果实测", "price": 9499, "is_platform_self": True, "rating": 4.9, "key_specs": "M3芯片/18h实测续航/超薄/超出预算", "sales": "月销6500"},
        {"product_id": "mock_laptop_bat_3", "title": "联想小新 Air 15 2025 15h续航 R7", "price": 5699, "is_platform_self": True, "rating": 4.8, "key_specs": "15h续航/R7-8845H/2.5K屏/月销1.2万", "sales": "月销1.2万"}
    ],
    "4 小时不够用是真实痛点，3 款续航 15h+ 的款：\n\n**1. 华为 MateBook D16（¥5499）** ⭐ 续航首选\n**实测 18 小时**，上一整天课充一次电。i5+16 寸大屏，月销 1.5 万件是续航党销冠。\n\n**2. 联想小新 Air 15（¥5699）**\n**15 小时**续航+2.5K 高清屏，R7 性能略强于华为的 i5。\n\n**3. MacBook Air M3（¥9499 超出预算）**\n续航最强（18h 苹果实测+不缩水），但超出你的预算。如果能接受加价，这是最好的选择。\n\n## 💡 续航差的根本原因\n\n上次那台 4h 续航，可能是：\n- 高性能显卡耗电（游戏本）\n- 旧电池老化（用了 2-3 年）\n- 高分辨率屏幕耗电\n\n选 MateBook D16——**18h 续航+华为生态+¥5499 是这个价位续航最强**。",
    ["华为MateBook D16 18h续航+i5+16寸+月销1.5万，学生上课续航首选", "联想小新Air 15 15h续航+2.5K屏+R7+月销1.2万，续航屏幕双优", "MacBook Air M3 18h实测续航+超薄+月销6500，超出预算但续航最强"]
))

# 2. similar_rec - 抱怨屏幕太小
T.append(make_traj(
    "sft_simrec_068", "similar_rec", "相似品推荐",
    "抱怨屏幕太小 → 推荐同价位大屏款",
    "之前买的 55 寸电视客厅放着太小了，换大屏同价位",
    {"query": "电视 65寸以上 4K 大屏", "min_price": 3000, "max_price": 5000, "filters": {"screen_size_min_inch": 65}},
    [
        {"product_id": "mock_tv_big_1", "title": "海信 75E5N 75寸 4K 智能 Mini LED", "price": 4199, "is_platform_self": True, "rating": 4.9, "key_specs": "75寸/Mini LED/120Hz/AI画质/月销1.5万", "sales": "月销1.5万"},
        {"product_id": "mock_tv_big_2", "title": "TCL 65C9K 65寸 Mini LED 144Hz", "price": 3499, "is_platform_self": True, "rating": 4.9, "key_specs": "65寸/Mini LED/144Hz/QLED/月销1.2万", "sales": "月销1.2万"},
        {"product_id": "mock_tv_big_3", "title": "小米电视 S85 85寸 4K 120Hz", "price": 4999, "is_platform_self": True, "rating": 4.8, "key_specs": "85寸/4K/120Hz/最大屏幕/月销4500", "sales": "月销4500"}
    ],
    "客厅 55 寸确实太小，3 款 65-85 寸替代：\n\n**1. TCL 65C9K Mini LED（¥3499）** ⭐ 性价比最高\n65 寸比 55 寸**画面面积增加 40%**，Mini LED+144Hz，¥3499 是这个价位最强。\n\n**2. 海信 75E5N Mini LED（¥4199）**\n75 寸是多数 20-30㎡ 客厅的**黄金尺寸**，Mini LED 分区背光画质更均匀。\n\n**3. 小米 S85 85 寸（¥4999）**\n**85 寸视觉冲击力最强**，适合 20㎡以上的大客厅。¥4999 是 85 寸最便宜的款之一。\n\n## 📐 客厅面积 vs 最佳电视尺寸\n\n| 客厅面积 | 推荐尺寸 |\n|---|---|\n| 10-15㎡ | 55-65 寸 |\n| 15-25㎡ | **65-75 寸** |\n| 25㎡以上 | 75-85 寸 |\n\n**先量客厅面积**，再决定买 65 还是 75 还是 85。",
    ["TCL 65C9K Mini LED+144Hz+QLED+月销1.2万，65寸性价比最高", "海信75E5N Mini LED+120Hz+月销1.5万，15-25㎡客厅黄金尺寸", "小米S85 85寸+120Hz+月销4500，大客厅最强视觉冲击"]
))

# 3. sku_comp
T.append(make_traj(
    "sft_skucomp_065", "sku_comp", "商品对比",
    "三种剃毛方式对比（脱毛仪/剃毛刀/激光脱毛）",
    "买脱毛产品，脱毛仪/剃毛刀/专业激光脱毛哪个更适合",
    {"skus": ["家用脱毛仪IPL", "剃毛刀电动款", "医院激光脱毛"], "mode": "method_comparison"},
    [
        {"product_id": "mock_hair_remove_1", "title": "Ulike Air10 脱毛仪 IPL 蓝宝石冰冷", "price": 2399, "is_platform_self": True, "rating": 4.9, "key_specs": "IPL强光/蓝宝石冰冷/家用/6次永久减少", "sales": "月销8500"},
        {"product_id": "mock_hair_remove_2", "title": "飞利浦 BRL140 电动剃毛刀 4方向", "price": 299, "is_platform_self": True, "rating": 4.8, "key_specs": "4方向刀头/干湿两用/快速除毛/不永久", "sales": "月销2.2万"},
        {"product_id": "mock_hair_remove_3", "title": "某某医美 激光脱毛套餐 全身 5次", "price": 1500, "is_platform_self": False, "rating": 4.7, "key_specs": "医院激光/全身5次套餐/专业医师/持久效果", "sales": "月销680"}
    ],
    "**三种方式本质不同，效果也完全不同**：\n\n## 📊 三种方法对比\n\n| 方式 | 代表 | 费用 | 效果 | 疼痛 |\n|---|---|---|---|---|\n| 剃毛刀 | 飞利浦 ¥299 | **最低**（一次）| ❌ 每周重复 | 无痛 |\n| 家用 IPL 脱毛仪 | Ulike ¥2399 | 中（一次性）| ✅ 6-8 次后 70-90% 减少 | 微温 |\n| 医院激光 | 套餐 ¥1500 | 中（5 次套餐）| **✅✅ 5 次后 95%+** | 有刺痛 |\n\n## 🎯 三种适合的人\n\n### 剃毛刀 ¥299（临时处理）\n- 腿毛/腋毛**快速清除**\n- 每周一次，长期要坚持\n- **不追求永久效果**的人\n\n### 家用 IPL 脱毛仪 ¥2399\n- **在家私密操作**\n- 6-8 次后毛发永久减少 70-90%\n- 价格贵但长期省（不用反复买剃毛刀）\n- Ulike 是国内 IPL 口碑第一\n\n### 医院激光 ¥1500（推荐）\n- **效果最好（95%+）**\n- 安全性最高（专业设备+医师操作）\n- 5 次套餐效果远超家用设备\n- 缺点：需要去医院\n\n## 💡 真心建议\n\n**医院激光 > 家用 IPL > 剃毛刀**\n\n如果你能去医院，**¥1500 做 5 次医院激光比 ¥2399 买家用仪器效果好**。\n\n家用 IPL 主要的价值是：**私密部位/懒得去医院/方便**。",
    ["飞利浦BRL140电动剃毛刀+干湿两用+月销2.2万，临时处理快速便宜", "Ulike Air10 IPL脱毛仪+蓝宝石冰冷+月销8500，在家私密6-8次70-90%减少", "医院激光脱毛5次套餐+专业医师+月销680，效果最好95%+推荐"]
))

# 4. sku_comp
T.append(make_traj(
    "sft_skucomp_066", "sku_comp", "商品对比",
    "三种制冷方案对比（空调/风扇/空调扇）",
    "家里没安空调，夏天降温，空调扇/落地扇/移动空调哪个最有效",
    {"skus": ["移动空调", "空调扇加冰", "大功率落地扇"], "mode": "cooling_effect_comparison"},
    [
        {"product_id": "mock_cool_ac_1", "title": "格力 移动空调 KY-26FNAf 1匹", "price": 2299, "is_platform_self": True, "rating": 4.8, "key_specs": "1匹移动空调/不用安装/真制冷/月销2800", "sales": "月销2800"},
        {"product_id": "mock_cool_fan_1", "title": "格力 KSVD-1203 空调扇 加冰", "price": 599, "is_platform_self": True, "rating": 4.8, "key_specs": "加冰块制冷/降温5-8℃/适合小房间", "sales": "月销1.2万"},
        {"product_id": "mock_cool_floor_1", "title": "美的 工业级落地扇 直径65cm 工业大扇", "price": 399, "is_platform_self": True, "rating": 4.8, "key_specs": "工业大扇/650mm扇叶/大风量/月销4500", "sales": "月销4500"}
    ],
    "没有固定空调的情况下，3 种制冷方案效果差距很大：\n\n## 📊 制冷效果对比\n\n| 方案 | 价格 | 降温效果 | 适合面积 |\n|---|---|---|---|\n| 移动空调 | ¥2299 | **真制冷 -10℃** | 15-20㎡ |\n| 空调扇+冰 | ¥599 | 降温 5-8℃（局部）| < 10㎡ |\n| 工业大风扇 | ¥399 | 散热体感降温 | 20-40㎡ |\n\n## 🎯 三种适合的场景\n\n### 移动空调 ¥2299（真制冷）\n- 有排气管（需要架窗排热风）\n- **真正让房间温度下降**\n- 适合没装固定空调的卧室\n- 缺点：噪音中等，需要排气管\n\n### 空调扇+冰 ¥599（局部降温）\n- 降温效果有限（冰块 2h 化完就无效）\n- **仅适合坐在扇子前 1 米内**\n- 小房间/无需全屋降温时用\n\n### 工业大风扇 ¥399（体感降温）\n- 风吹过皮肤加速汗液蒸发\n- **湿热天气有效，干热效果差**\n- 大空间通风最合适（客厅/仓库/办公室）\n\n## 💡 真心建议\n\n**如果需要睡觉用 → 必须移动空调**（空调扇睡觉降温不够，会热醒）\n\n**如果只是白天坐着用 → 工业大风扇 ¥399** 最便宜也够用",
    ["格力移动空调1匹+不用安装真制冷+月销2800，需要睡觉降温必选", "格力空调扇加冰+降温5-8℃+月销1.2万，坐在面前短时间降温", "美的工业大落地扇+月销4500，大空间通风预算最低"]
))

# 5. matching
T.append(make_traj(
    "sft_match_065", "matching_purchase", "搭配购物",
    "手办展示台整体搭配",
    "喜欢收藏手办，配展示柜+补光灯+防尘罩+价格标签",
    {"query": "手办展示柜 补光灯 防尘", "filters": {"category": "figure_display"}},
    [
        {"product_id": "mock_figure_1", "title": "宜家 DETOLF 展示柜 手办柜 玻璃", "price": 699, "is_platform_self": True, "rating": 4.9, "key_specs": "宜家DETOLF/玻璃展示柜/手办标准柜/月销3500", "sales": "月销3500"},
        {"product_id": "mock_figure_2", "title": "手办展示灯 LED 橱窗柜内灯 磁吸", "price": 159, "is_platform_self": True, "rating": 4.9, "key_specs": "LED磁吸/安装展示柜内/手办补光/月销2200", "sales": "月销2200"},
        {"product_id": "mock_figure_3", "title": "防尘罩 亚克力 手办专用 多尺寸", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "亚克力透明/防尘防氧化/贵手办必备", "sales": "月销4500"},
        {"product_id": "mock_figure_4", "title": "手办价格标签 白色小卡 不干胶", "price": 29, "is_platform_self": True, "rating": 4.8, "key_specs": "白色价格标签/不干胶/手写价格/收藏管理", "sales": "月销3500"}
    ],
    "手办展示 4 件套 ¥986，**从收藏到展示级别**：\n\n## 🎁 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 展示柜 | **宜家 DETOLF 玻璃柜** | ¥699 |\n| 补光灯 | LED 磁吸橱窗灯 | ¥159 |\n| 防尘罩 | 亚克力透明 | ¥99 |\n| 价格标签 | 白色不干胶 | ¥29 |\n\n## 💡 宜家 DETOLF 是手办圈标准\n\n这款柜子在手办收藏圈被称为「**手办圣柜**」：\n- 高 163cm，4 层玻璃\n- **可以展示 100+ 只手办**\n- 价格 ¥699 是同等展示效果里最便宜\n- 月销 3500 件，手办圈人手一个\n\n## 💡 补光灯的作用\n\n普通灯光下手办**颜色偏黄**，LED 橱窗灯磁吸安装在柜子内层：\n- 让手办在「舞台灯」效果下展示\n- 颜色还原更准确\n- 拍照出片非常好看\n\n## 💡 防尘罩不是所有手办都需要\n\n- **贵手办（¥500+）**：亚克力防尘罩独立展示\n- **普通手办**：展示柜本身防尘够了\n\n## 💡 价格标签管理收藏\n\n收藏越来越多后**记不清每个价格**，价格标签贴在底座上，**防止以后高价手办被人白拿走**。",
    ["宜家DETOLF玻璃展示柜+月销3500，手办圈标准圣柜100+手办展示", "LED磁吸橱窗灯+手办补光+月销2200，舞台灯效果颜色还原拍照好看", "亚克力透明防尘罩+月销4500，500元以上贵手办独立防尘保值", "白色价格标签不干胶+月销3500，收藏管理避免贵手办被忽视"]
))

# 6. matching
T.append(make_traj(
    "sft_match_066", "matching_purchase", "搭配购物",
    "毕业季整套穿搭",
    "下周毕业典礼，配汉服/毕业服+头饰+拍照道具",
    {"query": "毕业典礼穿搭 汉服+头饰+拍照道具", "filters": {"occasion": "graduation_ceremony"}},
    [
        {"product_id": "mock_grad_1", "title": "汉尚华莲 改良汉服 白色仙气飘飘款", "price": 399, "is_platform_self": True, "rating": 4.9, "key_specs": "改良汉服/白色飘逸/拍照出片/月销1500", "sales": "月销1500"},
        {"product_id": "mock_grad_2", "title": "毕业头饰 鲜花发圈 含干花", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "干花发圈/多色可选/毕业仪式感/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "mock_grad_3", "title": "毕业拍照道具 气球+毕业字母套装", "price": 59, "is_platform_self": True, "rating": 4.9, "key_specs": "气球+毕业字母/拍照道具/仪式感/月销4.5万", "sales": "月销4.5万"},
        {"product_id": "mock_grad_4", "title": "胶片相机 一次性 柯达 傻瓜相机 27张", "price": 89, "is_platform_self": True, "rating": 4.9, "key_specs": "柯达一次性/27张/胶片感/毕业记录", "sales": "月销3.5万"}
    ],
    "毕业季整套 4 件 ¥636，**留住最美的毕业**：\n\n## 🎓 完整方案\n\n| 单品 | 商品 | 价格 |\n|---|---|---|\n| 服装 | 汉尚华莲改良汉服白色 | ¥399 |\n| 头饰 | 干花发圈 | ¥89 |\n| 拍照道具 | 气球+毕业字母 | ¥59 |\n| 相机 | 柯达一次性胶片相机 | ¥89 |\n\n## 💡 毕业穿搭选白色汉服的原因\n\n白色飘逸汉服 = **校园拍照最出片**：\n- 与蓝天绿树形成鲜明对比\n- 同学帮拍时**不需要任何构图技巧**都好看\n- 和学士服(黑色)产生颜色切换的多样性\n\n## 💡 一次性胶片相机的价值\n\n**¥89 买的是胶片质感的毕业记忆**：\n- 和同学互相拍\n- 冲洗后得到实体照片\n- 数十年后拿出来的感觉完全不同于手机照片\n- 27 张刚好够典礼用\n\n## 📸 毕业拍照 3 个必拍\n\n1. **穿学士服**：和导师、班级合影\n2. **穿汉服**：校园花园/走廊/图书馆\n3. **和闺蜜**：拿气球道具的日常感\n\n## ⚠️ 毕业季注意\n\n- 汉服提前 **3-5 天到货**（确认合身）\n- 花发圈提前 1 天戴上试试（避免过敏）\n- 胶片相机**拍完尽快冲洗**（超过 3 个月颜色会变）",
    ["汉尚华莲白色改良汉服+月销1500，校园蓝天绿树拍照最出片", "干花发圈+月销2.5万，毕业仪式感头饰多色搭汉服", "气球+毕业字母道具+月销4.5万，拍照构图道具仪式感满分", "柯达一次性胶片相机27张+月销3.5万，胶片质感毕业记忆"]
))

# 7. bundle
T.append(make_traj(
    "sft_bundle_063", "bundle_purchase", "组合购物",
    "4500 元电竞装备升级（鼠标+键盘+耳机+椅子）",
    "电竞装备整体升级，4500 配鼠标+键盘+耳机+椅子",
    {"query": "电竞装备升级 鼠标+机械键盘+耳机+电竞椅", "max_price": 5000},
    [
        {"product_id": "mock_gaming_1", "title": "雷蛇 DeathAdder V3 HyperSpeed 无线鼠标", "price": 499, "is_platform_self": True, "rating": 4.9, "key_specs": "35000DPI/无线/轻量78g/电竞首选", "sales": "月销3500"},
        {"product_id": "mock_gaming_2", "title": "杜伽 Taurus 机械键盘 65% 热插拔", "price": 499, "is_platform_self": True, "rating": 4.9, "key_specs": "65%紧凑/热插拔/客制化/电竞美观兼备", "sales": "月销2500"},
        {"product_id": "mock_gaming_3", "title": "赛睿 Arctis Nova Pro 无线电竞耳机", "price": 1799, "is_platform_self": True, "rating": 4.9, "key_specs": "双无线/Hi-Res/游戏+听歌两用/月销1500", "sales": "月销1500"},
        {"product_id": "mock_gaming_4", "title": "傲风 电竞椅 4D扶手 腰托颈枕", "price": 1499, "is_platform_self": True, "rating": 4.9, "key_specs": "4D扶手/腰托/久坐不腰酸/月销1.5万", "sales": "月销1.5万"}
    ],
    "电竞装备全升级 4 件套 ¥4296，余 ¥204：\n\n## 🎮 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 🥇 椅子 | 傲风电竞椅 4D 扶手 | ¥1499 |\n| 耳机 | 赛睿 Arctis Nova Pro 无线 | ¥1799 |\n| 鼠标 | 雷蛇 DeathAdder V3 HyperSpeed | ¥499 |\n| 键盘 | 杜伽 Taurus 65% 热插拔 | ¥499 |\n\n## 💡 升级优先级\n\n**椅子 > 耳机 > 鼠标 > 键盘**\n\n### 椅子排第一（健康投资）\n打游戏**每天 3-6 小时**，垃圾椅子一年腰椎报废。¥1499 傲风是这个价位最值的电竞椅。\n\n### 耳机第二（听声辨位）\n**FPS 游戏（CS2/Valorant）中，耳机 > 显示器**。听到脚步声方向，胜率直接提升。赛睿 Nova Pro 是专业选手同款。\n\n### 鼠标第三（手感精准）\n DeathAdder V3 78g 超轻，35000 DPI 精准，**无线零延迟**。专业电竞选手大量使用。\n\n### 键盘第四（手感辅助）\n65% 热插拔键盘：\n- 无小键盘（鼠标空间更大）\n- 热插拔随时换轴\n- 客制化颜值\n\n## 💰 余 ¥204 加\n\n- 鼠标垫（大号 XXL）¥80\n- 键盘收纳袋 ¥50\n- 耳机挂架 ¥49",
    ["傲风电竞椅4D扶手+腰托+月销1.5万，每天3-6h打游戏腰椎健康第一位", "赛睿Arctis Nova Pro无线双Hi-Res+月销1500，FPS听声辨位胜率提升", "雷蛇DeathAdder V3 78g无线零延迟+月销3500，专业选手同款精准竞技", "杜伽Taurus 65%热插拔+客制化+月销2500，紧凑鼠标空间大美观兼备"]
))

# 8. bundle
T.append(make_traj(
    "sft_bundle_064", "bundle_purchase", "组合购物",
    "2000 元初中生开学全套",
    "孩子上初中了，2000 配齐全套文具+书包+台灯",
    {"query": "初中生开学装备 书包+文具+台灯", "max_price": 2200},
    [
        {"product_id": "mock_middle_1", "title": "耐克 Brasilia 9.5 初中生双肩包", "price": 299, "is_platform_self": True, "rating": 4.9, "key_specs": "耐克品牌/30L/防水拉链/初中生主流", "sales": "月销4500"},
        {"product_id": "mock_middle_2", "title": "晨光 全套文具礼盒 30件 初中版", "price": 99, "is_platform_self": True, "rating": 4.9, "key_specs": "30件文具/铅笔+圆规+量角器+橡皮/初中科目全覆盖", "sales": "月销3.5万"},
        {"product_id": "mock_middle_3", "title": "明基 台灯 e-Reading 国AA护眼 初中版", "price": 499, "is_platform_self": True, "rating": 4.9, "key_specs": "国AA护眼/无频闪/可调色温/初中生学习必备", "sales": "月销1.8万"},
        {"product_id": "mock_middle_4", "title": "考研系列错题本 12本 学科分类 初中版", "price": 59, "is_platform_self": True, "rating": 4.9, "key_specs": "12本学科分类/错题管理/月销2.5万", "sales": "月销2.5万"},
        {"product_id": "mock_middle_5", "title": "简约A4文件夹 20个 透明页套", "price": 39, "is_platform_self": True, "rating": 4.8, "key_specs": "A4/20个/透明页套/试卷收纳", "sales": "月销5.5万"}
    ],
    "初中生开学 5 件套 ¥995，余 ¥1005：\n\n## 📚 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 书包 | 耐克 Brasilia 30L | ¥299 |\n| 台灯 | 明基护眼 国 AA | ¥499 |\n| 文具 | 晨光 30 件礼盒 | ¥99 |\n| 错题本 | 12 本学科分类 | ¥59 |\n| 文件夹 | A4 透明 20 个 | ¥39 |\n\n## 💡 初中 vs 小学装备的区别\n\n初中开始有：\n- **理科**（圆规、量角器、直尺、铅笔→函数图画）\n- **理科笔记**（需要专用错题管理）\n- **试卷增多**（文件夹整理必须有）\n\n晨光 30 件礼盒专门针对**初中科目配置**，数学工具+语文工具+实验工具都有。\n\n## 💡 台灯是最重要的投资\n\n初中开始每天做作业 **4-5 小时**，护眼台灯每年防止 50-100 度近视加深。明基 AA 级是最高标准。\n\n## 💰 余 ¥1005 分配\n\n- **教材/辅导书**（语数英物化）¥500-800\n- **计算器（科学型）**：¥50-100\n- **订书机+文件袋**：¥30\n- **急救卡（书包里备）**：¥0（用卡片写好）",
    ["耐克Brasilia 30L初中生双肩包+防水+月销4500，初中生主流品牌书包", "明基台灯国AA护眼无频闪+月销1.8万，每天4-5h写作业护眼核心投资", "晨光30件文具礼盒初中版+月销3.5万，理科工具一次配齐", "12本学科分类错题本+月销2.5万，初中理科错题管理提分", "A4透明文件夹20个+月销5.5万，试卷收纳整理期末复习用"]
))

# 9. place_order
T.append(make_traj(
    "sft_order_034", "place_order", "购物下单",
    "抢购限定款配色",
    "明天上午 10 点限量发售那款 Air Jordan 1 黑红配色，怎么抢",
    {"product_id": "mock_aj1_ltd", "release_time": "2026-07-01 10:00", "action": "prepare_for_release"},
    [
        {"product_id": "mock_aj1_ltd", "title": "Air Jordan 1 Retro High OG 黑红 限量发售", "price": 1299, "is_platform_self": True, "rating": 4.9, "key_specs": "已预约/明天10点发售/限量抢购/提前准备完成", "sales": "—"}
    ],
    "明天 10 点限量发售，**提前做好 5 件准备**，成功率最高：\n\n## ⏰ 发售前的准备\n\n### 今晚必做\n\n**1. 加入购物车**\n- 打开商品页 → 点「**加入购物车**」（即使显示还没开售）\n- 部分商品支持加入购物车，发售时直接结算更快\n\n**2. 填好收货地址**\n- 确认默认地址正确\n- 不要发售时再填地址（浪费 10 秒）\n\n**3. 准备支付方式**\n- 推荐：**购物平台余额/白条**（比银行卡/微信快 0.5-1 秒）\n- 提前确认余额/额度够\n\n**4. 下载最新 App 版本**\n- 旧版可能不支持最快的抢购通道\n\n**5. 确认网络**\n- 明早 9:55 切换到 **5G 流量**（WiFi 有时延迟高）\n\n## 🕐 发售当天流程\n\n```\n09:55 进入商品页，等待\n09:59:30 手指悬停在「立即购买」按钮上方\n10:00:00 按钮变亮的瞬间立刻点击\n支付页面出现：10 秒内完成支付\n```\n\n## 💡 专业抢购技巧\n\n- **不要连击多次**（会产生多个订单请求，反而卡）\n- **一击必中**，点完等支付页面\n- 如果卡住：**退出 App 重进**比刷新快\n- **iPad 竖屏模式**：按钮更大更好点\n\n## ⚠️ 抢不到怎么办\n\n限量款经常**瞬间售罄**，备选方案：\n- 在商品页设「**到货提醒**」（补货机率约 30%）\n- 购物平台拍卖（溢价但正品）\n- 去 Nike SNKRS App 同步参与\n\n祝你手速够快！👟",
    ["Air Jordan 1黑红限量+明天10点发售+提前预约准备完成，5件准备最高成功率"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase
T.append(make_traj(
    "sft_repurchase_032", "repurchase", "复购召回",
    "复购零食+推荐新品尝鲜",
    "再买之前那包辣条，顺便问有没有新口味",
    {"category_keyword": "辣条", "time_range": "last_2_months", "show_new_flavors": True},
    [
        {"product_id": "mock_latiao_old", "title": "卫龙 辣条大礼包 亲嘴烧+辣棒 (1月前购买)", "price": 49, "is_platform_self": True, "rating": 4.9, "key_specs": "你1月前购买/订单[ORDER_ID]/亲嘴烧+辣棒组合", "sales": "月销8万"},
        {"product_id": "mock_latiao_new1", "title": "卫龙 魔芋爽 麻辣味 新品 2026", "price": 39, "is_platform_self": True, "rating": 4.9, "key_specs": "卫龙新品/魔芋爽/麻辣味/0脂/月销4.5万", "sales": "月销4.5万"},
        {"product_id": "mock_latiao_new2", "title": "卫龙 风吃海苔 咸蛋黄口味 2026新品", "price": 35, "is_platform_self": True, "rating": 4.8, "key_specs": "咸蛋黄海苔/卫龙新品/月销2.2万", "sales": "月销2.2万"}
    ],
    "你 1 个月前买的是**卫龙辣条大礼包 ¥49**（亲嘴烧+辣棒）。\n\n## 🌶️ 卫龙 2026 年新品\n\n**1. 魔芋爽 麻辣味 ¥39** ⭐ 新品热销第一\n- **0 脂肪**（魔芋做的不是面筋）\n- 麻辣口感比辣条更清爽\n- 月销 4.5 万件已经是卫龙新品销冠\n- 适合：减脂期想吃辣的/不想要太高热量\n\n**2. 咸蛋黄海苔 ¥35**\n- 咸蛋黄+海苔的奶香辣口味\n- 不同于传统辣条\n- 适合喜欢多元口味的人\n\n## 🛒 三种购买方案\n\n### 方案 A：直接复购同款 ¥49\n- 已知喜欢，不冒险\n\n### 方案 B：加买新品尝鲜 ¥88（推荐）⭐\n- 辣条 ¥49 + 魔芋爽 ¥39\n- 老口味续命 + 新品尝鲜\n- 两者口感完全不同，不腻\n\n### 方案 C：大礼包换成只买魔芋爽 ¥39\n- 0 脂肪更健康\n- 需要接受口感变化\n\n## 💡 辣条 vs 魔芋爽\n\n| 维度 | 辣条（面筋）| 魔芋爽 |\n|---|---|---|\n| 热量 | **高**（碳水+油）| **低**（0脂）|\n| 口感 | 软糯有嚼劲 | 爽脆 |\n| 适合 | 爽到无所谓 | 减脂期也能吃 |\n\n要同时下单两款试试吗？",
    ["卫龙辣条大礼包你1月前购买+月销8万，继续复购同款老口味", "卫龙魔芋爽麻辣新品+0脂+月销4.5万，2026新品热销第一减脂也能吃", "卫龙咸蛋黄海苔新品+月销2.2万，不同风格新口味尝鲜"],
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
