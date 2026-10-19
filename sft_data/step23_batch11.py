# -*- coding: utf-8 -*-
"""Step 23: 第 11 批 10 条"""
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

# 1. similar_rec - 抱怨过敏材质
T.append(make_traj(
    "sft_simrec_033", "similar_rec", "相似品推荐",
    "抱怨皮肤过敏 → 排除特定面料",
    "之前买的化纤被子让我皮肤痒，要纯棉或天丝的同价位款",
    {"query": "被子 纯棉天丝 不易过敏", "min_price": 400, "max_price": 800, "filters": {"materials": ["纯棉", "天丝", "亚麻"]}, "exclude_materials": ["化纤", "涤纶"]},
    [
        {"product_id": "jd_quilt_001", "title": "罗莱家纺 100%长绒棉夏被 双人", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "100%长绒棉/A类婴儿级/可机洗", "sales": "月销1200"},
        {"product_id": "jd_quilt_002", "title": "水星家纺 天丝夏被 凉感面料", "price": 699, "is_jd_self": True, "rating": 4.9, "key_specs": "100%天丝/凉感冰丝/夏季最舒适", "sales": "月销850"},
        {"product_id": "jd_quilt_003", "title": "MUJI 亚麻夏被 自然透气款", "price": 549, "is_jd_self": True, "rating": 4.8, "key_specs": "100%亚麻/A类认证/越用越柔软", "sales": "月销680"}
    ],
    "化纤被子过敏很常见。3 款天然纤维都规避了：\n\n**1. 罗莱长绒棉 ¥599** ⭐ 最稳\n100% 棉+A 类婴儿级，是过敏体质最安全的选择。可机洗维护方便。\n\n**2. 水星天丝夏被 ¥699**\n天丝是植物纤维（木材提取），**凉感是天丝独有**，夏天最舒服。\n\n**3. MUJI 亚麻夏被 ¥549**\n亚麻吸汗散热最快，**越洗越柔软**。预算紧选这个。\n\n## ⚠️ 旧化纤被处理\n\n你那条让你过敏的被子建议**直接扔**——化纤被洗了也还是化纤，过敏不会消失。",
    ["罗莱100%长绒棉+A类婴儿级+可机洗+月销1200，过敏体质最稳", "水星天丝夏被+凉感冰丝+月销850，夏季最舒适", "MUJI亚麻夏被+A类认证+越洗越软+月销680，性价比首选"]
))

# 2. similar_rec - 抱怨太占地
T.append(make_traj(
    "sft_simrec_034", "similar_rec", "相似品推荐",
    "抱怨家具太大 → 紧凑款",
    "上次买的微波炉占了半个台面，有迷你款的同价位选择吗",
    {"query": "迷你微波炉 紧凑款 单人量", "max_price": 600, "filters": {"size": "compact", "width_max_cm": 40}},
    [
        {"product_id": "jd_mw_mini_1", "title": "美的 PG23K1 紧凑型微波炉 23L 40cm宽", "price": 469, "is_jd_self": True, "rating": 4.9, "key_specs": "23L紧凑/宽40cm/单人量/平板加热", "sales": "月销1.8万"},
        {"product_id": "jd_mw_mini_2", "title": "格兰仕 G70F20CN1L-DG 20L 超小型 38cm", "price": 369, "is_jd_self": True, "rating": 4.8, "key_specs": "20L超小/38cm宽/200W省电", "sales": "月销1.2万"},
        {"product_id": "jd_mw_mini_3", "title": "松下 NN-DS591M 23L 紧凑+蒸汽功能", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "23L紧凑/蒸汽功能/松下品质", "sales": "月销680"}
    ],
    "懂，传统微波炉 50cm+ 宽小厨房塞不下。3 款紧凑版：\n\n**1. 美的 PG23K1 ¥469** ⭐ 综合最佳\n**40cm 宽是紧凑版主流**，但容量仍 23L（够放整盘菜）。平板加热免去转盘清洁。\n\n**2. 格兰仕 ¥369** 最便宜最小\n**38cm 宽 + 20L** 容量，**单人/出租屋最合适**。功率小省电。\n\n**3. 松下 ¥599** 多功能\n23L 紧凑但**带蒸汽功能**（蒸馒头/蒸鱼），一机多用。\n\n建议选美的 ¥469 ——尺寸和容量平衡最好。",
    ["美的PG23K1紧凑23L+40cm宽+平板加热+月销1.8万，小厨房综合最佳", "格兰仕20L+38cm宽超小+月销1.2万，单人出租屋最便宜", "松下23L紧凑+蒸汽功能+月销680，预算够多功能首选"]
))

# 3. sku_comp - 不同尺寸同型号
T.append(make_traj(
    "sft_skucomp_031", "sku_comp", "商品对比",
    "MacBook Pro 14寸 vs 16寸对比",
    "MacBook Pro M3 14寸 ¥14999 vs 16寸 ¥18999，差 4000 值不值",
    {"skus": ["MacBook Pro 14 M3 Pro", "MacBook Pro 16 M3 Pro"], "mode": "size_comparison"},
    [
        {"product_id": "jd_mbp14", "title": "MacBook Pro 14寸 M3 Pro 18+512G", "price": 14999, "is_jd_self": True, "rating": 4.9, "key_specs": "14寸/M3 Pro/18+512G/1.61kg", "sales": "月销2500"},
        {"product_id": "jd_mbp16", "title": "MacBook Pro 16寸 M3 Pro 36+512G", "price": 18999, "is_jd_self": True, "rating": 4.9, "key_specs": "16寸/M3 Pro/36+512G/2.14kg", "sales": "月销1200"}
    ],
    "**结论：90% 用户 14 寸够用，省 ¥4000 不亏**。\n\n## 📊 关键差异\n\n| 维度 | 14 寸 ¥14999 | 16 寸 ¥18999 |\n|---|---|---|\n| 屏幕 | 14.2 寸 | 16.2 寸 |\n| 内存 | 18GB | **36GB（双倍）**|\n| 重量 | 1.61kg | 2.14kg（重 530g）|\n| 续航 | 18h | 22h |\n| 散热 | 一般 | **更强**（不降频）|\n| 月销 | **2500** | 1200 |\n\n## 💰 ¥4000 拆解\n\n核心差异是**内存翻倍**（18G→36G）和**屏幕大 2 寸**：\n\n### 16 寸值得的人（10%）：\n- 视频剪辑师/3D 建模师（需要 36GB）\n- 家里固定使用不移动\n- 不出差/不通勤\n\n### 14 寸够用的人（90%）：\n- 程序员/设计师（18GB 够用）\n- 经常出差/咖啡馆办公\n- 18 小时续航刚需\n- 1.61kg vs 2.14kg 出差时差距巨大\n\n## 💡 真心建议\n\n**程序员开发**：14 寸 18GB 完全够（Docker + IDE + 浏览器 50+ 标签都不卡）\n**普通办公**：14 寸过剩了，可以考虑 MacBook Air M3 ¥9999\n**真正需要 16 寸**：你应该已经知道自己需要（4K 视频/科学计算）\n\n**别为「以防万一」多花 ¥4000**——这钱够买台 iPad Air + Apple Watch 了。",
    ["MacBook Pro 14寸M3 Pro+18+512G+1.61kg+月销2500，90%用户够用省4000", "MacBook Pro 16寸M3 Pro+36+512G+2.14kg+月销1200，视频剪辑/3D建模刚需"]
))

# 4. sku_comp - 不同代际同型号
T.append(make_traj(
    "sft_skucomp_032", "sku_comp", "商品对比",
    "Sony A7M3 vs A7M4 vs A7M5 三代对比",
    "Sony A7 系列纠结买 M3/M4/M5，差 7000 选哪个",
    {"skus": ["Sony A7M3", "Sony A7M4", "Sony A7M5"], "mode": "generation_comparison"},
    [
        {"product_id": "jd_a7m3", "title": "Sony A7M3 全画幅微单 单机 (2018)", "price": 9999, "is_jd_self": True, "rating": 4.9, "key_specs": "2018款/2420万像素/4K 30P/老旗舰最便宜", "sales": "月销1200"},
        {"product_id": "jd_a7m4", "title": "Sony A7M4 全画幅微单 单机 (2021)", "price": 13999, "is_jd_self": True, "rating": 4.9, "key_specs": "2021款/3300万像素/4K 60P/AI对焦/中端旗舰", "sales": "月销1800"},
        {"product_id": "jd_a7m5", "title": "Sony A7M5 全画幅微单 单机 (2024)", "price": 16999, "is_jd_self": True, "rating": 4.9, "key_specs": "2024款/3300万像素/8K视频/AI 2.0/最新旗舰", "sales": "月销680"}
    ],
    "Sony A7 系列 3 代对比，**性价比拐点在 A7M4**：\n\n## 📊 三代对比\n\n| 维度 | A7M3 ¥9999 | A7M4 ¥13999 | A7M5 ¥16999 |\n|---|---|---|---|\n| 发布年 | 2018 | 2021 | 2024 |\n| 像素 | 2420 万 | **3300 万** | 3300 万 |\n| 视频 | 4K 30P | **4K 60P** | **8K** |\n| 对焦 | 基础 | **AI 实时对焦** | AI 2.0 |\n| 月销 | 1200 | **1800（最热）**| 680 |\n\n## 💰 拼性价比\n\n### M3 → M4：¥4000 升级值（90% 用户）\n- 像素 +37%（剪裁余量大）\n- **4K 60P 可拍升格**\n- AI 对焦让人物/动物自动锁定\n- **性价比拐点**\n\n### M4 → M5：¥3000 不值（90% 用户）\n- 8K 视频用不到（输出还是 4K）\n- AI 2.0 提升微小\n- **专业商业摄影才值得**\n\n## 🎯 怎么选\n\n### A7M3 ¥9999（预算紧+入门）\n- 进入全画幅最便宜\n- 静态摄影画质不输 M4\n- **缺点**：对焦弱+视频规格落后\n\n### A7M4 ¥13999 ⭐ 推荐（80% 用户）\n- **甜点机型**\n- 视频摄影双修\n- 二手价稳定（保值率高）\n\n### A7M5 ¥16999（专业+商业摄影）\n- 8K 工作流（导演/婚礼跟拍）\n- 短期内不会被淘汰\n\n## 💡 真心建议\n\n**第一次买全画幅 → A7M4**\n- 性价比拐点\n- 二手价稳定（不喜欢 1 年内卖也亏不大）\n- 镜头投资也合理\n\n**已经有 A7M3 想升级**：直接 A7M5（M3→M4 跨度太小）",
    ["Sony A7M3 2018款+2420万+4K 30P+月销1200，全画幅入门最便宜", "Sony A7M4 2021款+3300万+4K 60P+AI实时对焦+月销1800，性价比拐点甜点机型", "Sony A7M5 2024款+8K视频+AI 2.0+月销680，专业商业摄影"]
))

# 5. matching - 精致咖啡桌面
T.append(make_traj(
    "sft_match_031", "matching_purchase", "搭配购物",
    "工位整体颜值升级",
    "工位想升级颜值，配什么键盘鼠标+鼠标垫+桌垫+周边",
    {"query": "工位升级 颜值党 键盘+鼠标+桌垫", "filters": {"style": "minimalist_aesthetic", "colors": ["白色", "米色", "原木"]}},
    [
        {"product_id": "jd_desk_1", "title": "Keychron K3 矮轴机械键盘 白色版", "price": 699, "is_jd_self": True, "rating": 4.9, "key_specs": "矮轴/无线/白色配色/Mac布局", "sales": "月销1500"},
        {"product_id": "jd_desk_2", "title": "罗技 MX Anywhere 3S 白色无线鼠标", "price": 549, "is_jd_self": True, "rating": 4.9, "key_specs": "白色/3设备切换/磁吸滚轮", "sales": "月销3500"},
        {"product_id": "jd_desk_3", "title": "ELECOM 鼠标垫 米色软垫 大号", "price": 89, "is_jd_self": True, "rating": 4.8, "key_specs": "米色软垫/大号45×30/防滑", "sales": "月销4500"},
        {"product_id": "jd_desk_4", "title": "全桌面皮革桌垫 80×40 燕麦色", "price": 159, "is_jd_self": True, "rating": 4.9, "key_specs": "皮革桌垫/80×40大尺寸/燕麦色", "sales": "月销1.2万"},
        {"product_id": "jd_desk_5", "title": "MUJI 收纳笔筒 白色陶瓷 极简款", "price": 79, "is_jd_self": True, "rating": 4.8, "key_specs": "白色陶瓷/极简款/MUJI风", "sales": "月销680"}
    ],
    "工位颜值升级 5 件套 ¥1575，**实用+ins 风兼顾**：\n\n## 💻 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 键盘 | **Keychron K3 矮轴白色** | ¥699 |\n| 鼠标 | **罗技 MX Anywhere 3S 白色** | ¥549 |\n| 鼠标垫 | ELECOM 米色软垫 | ¥89 |\n| 桌垫 | 皮革桌垫 80×40 燕麦色 | ¥159 |\n| 笔筒 | MUJI 白色陶瓷 | ¥79 |\n| **合计** | | **¥1575** |\n\n## 🎨 配色公式\n\n**白色键鼠 + 燕麦色桌垫 + 米色软垫 = 极简清新风**\n\n- ✅ 全浅色系统一\n- ✅ 不同材质（皮革+软垫+陶瓷）有层次\n- ❌ 避免黑色（看着 RGB 灯重）\n- ❌ 避免高饱和色（破坏极简感）\n\n## 💡 选品理由\n\n### Keychron K3 矮轴键盘 ¥699\n- 矮轴**比常规机械键盘薄一半**（不显笨重）\n- 白色配色少有 → 工位差异化\n- 无线避免线材凌乱\n- Mac 布局适合苹果用户\n\n### 罗技 MX Anywhere 3S\n- 罗技高端线，磁吸滚轮**滑长文档体验最好**\n- 3 设备切换（电脑+iPad+Mac）\n- 白色和键盘呼应\n\n### 燕麦色皮革桌垫\n- **80×40 大尺寸覆盖整个工作区**\n- 皮革质感比布料桌垫高级\n- 防水好打理\n\n## 💎 加 ¥500 升级到桌面顶配\n\n- 屏幕挂灯（明基 ScreenBar Halo）¥999\n- 桌面收纳架 ¥200\n- 真无线香薰扩香 ¥150\n\n## 📸 ins 工位拍照\n\n这套配色拍出来直接小红书爆款。**俯拍构图**：\n- 键盘居中下方\n- 鼠标在右\n- 笔筒左上\n- 留 30% 空白\n\n**每天上班看着开心+工作效率提升**。",
    ["Keychron K3矮轴白色机械键盘+无线+Mac布局+月销1500，工位颜值差异化", "罗技MX Anywhere 3S白色+3设备切换+磁吸滚轮+月销3500，配键盘呼应", "ELECOM米色软垫鼠标垫+大号防滑+月销4500，鼠标体验+颜值", "皮革桌垫80×40燕麦色+月销1.2万，覆盖整个工作区高级质感", "MUJI白色陶瓷笔筒+极简款+月销680，桌面收纳颜值担当"]
))

# 6. matching - 复古风家居
T.append(make_traj(
    "sft_match_032", "matching_purchase", "搭配购物",
    "复古风咖啡机周边搭配",
    "刚买了 SMEG 复古咖啡机，配什么咖啡杯+收纳+小家电统一复古风",
    {"query": "复古风厨房 SMEG搭配", "filters": {"style": "retro_vintage", "colors": ["米白", "薄荷绿", "复古蓝"]}, "match_with": "smeg_coffee_machine"},
    [
        {"product_id": "jd_retro_1", "title": "SMEG 复古电水壶 米白色 1.7L", "price": 1799, "is_jd_self": True, "rating": 4.9, "key_specs": "SMEG同品牌/米白色/1.7L/复古风同款", "sales": "月销680"},
        {"product_id": "jd_retro_2", "title": "SMEG 复古多士炉 2片 米白色", "price": 1599, "is_jd_self": True, "rating": 4.9, "key_specs": "SMEG多士炉/2片/米白色/同色系", "sales": "月销520"},
        {"product_id": "jd_retro_3", "title": "Lecreuset 复古咖啡杯套装 6 色", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "Lecreuset陶瓷/6色1套/复古风", "sales": "月销850"},
        {"product_id": "jd_retro_4", "title": "实木收纳架 复古做旧风 3 层", "price": 459, "is_jd_self": True, "rating": 4.8, "key_specs": "实木做旧风/3层/咖啡角专用", "sales": "月销380"}
    ],
    "SMEG 复古风 = 50 年代美式 diner 风格。4 件套 ¥4456 配齐完整咖啡角：\n\n## ☕ 完整方案\n\n| 装备 | 商品 | 价格 |\n|---|---|---|\n| 🥇 SMEG 电水壶 | **米白色 1.7L** | ¥1799 |\n| SMEG 多士炉 | 2 片 米白色 | ¥1599 |\n| 咖啡杯 | Lecreuset 6 色套装 | ¥599 |\n| 收纳架 | 实木做旧风 3 层 | ¥459 |\n| **合计** | | **¥4456** |\n\n## 🎨 复古风核心\n\n**米白色 + 实木 + 圆润造型**=SMEG 复古风的灵魂\n\n### 必须遵循的 3 个原则\n\n1. **同品牌系列**：SMEG 是套装思维，**水壶+多士炉+冰箱都买同色系**最和谐\n2. **避免现代极简电器**：黑色不锈钢的现代风会破坏整体复古感\n3. **加入实木+做旧元素**：让复古风更有层次\n\n## 💡 选品理由\n\n### SMEG 同品牌 ¥3398（水壶+多士炉）\n- **造型一致**（SMEG 标志性的圆润机身）\n- 米白色统一配色\n- 多 ¥1500 比杂牌买的是「**整体仪式感**」\n\n### Lecreuset 复古咖啡杯\n- 法国 Lecreuset 是复古陶瓷的代名词\n- **6 种颜色搭配心情**\n- 比 SMEG 自家杯子便宜还更经典\n\n### 实木做旧收纳架\n- 摆放咖啡豆罐+磨豆机+杯子\n- **做旧实木比新木更有年代感**\n- 3 层够装所有咖啡器具\n\n## 💎 进阶搭配（+¥2000）\n\n- SMEG 立式搅拌机 ¥3999（厨师机）\n- 复古吊灯 ¥500\n- 咖啡画装饰 ¥200\n- 老式称重盘 ¥150\n\n## 📸 拍照效果\n\n这套搭配出来：\n- **小红书咖啡角爆款**\n- 配色 = 50 年代美式餐厅\n- 早上煮一杯咖啡的仪式感是真治愈\n\n## ⚠️ 复古风避雷\n\n- ❌ **黑色现代电器**：风格冲突\n- ❌ **塑料杯子**：破坏整体陶瓷感\n- ❌ **金属反光面太多**：复古风讲究温暖感\n- ❌ **杂色搭配**：超过 3 种主色就乱了",
    ["SMEG米白电水壶+1.7L+同品牌同色系+月销680，SMEG复古风必备", "SMEG米白多士炉+2片+同色系+月销520，咖啡角早餐组合", "Lecreuset复古咖啡杯6色套装+法国陶瓷+月销850，杯子复古担当", "实木做旧风收纳架+3层+咖啡角专用+月销380，年代感层次担当"]
))

# 7. bundle - 8000元宝宝1岁
T.append(make_traj(
    "sft_bundle_029", "bundle_purchase", "组合购物",
    "8000 元 1 岁宝宝周岁礼包",
    "宝宝快 1 岁了，8000 预算配齐周岁礼包+辅食工具",
    {"query": "1岁宝宝礼包 益智+辅食+衣物", "max_price": 8500, "filters": {"target_age": "12months"}},
    [
        {"product_id": "jd_1y_1", "title": "费雪 早教益智桌 多功能 6-18个月", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "费雪经典款/多功能桌/亮灯+音乐+按钮", "sales": "月销2200"},
        {"product_id": "jd_1y_2", "title": "BABYBJÖRN 餐椅 高度可调 0-3岁", "price": 1899, "is_jd_self": True, "rating": 4.9, "key_specs": "瑞典BABYBJÖRN/可调高度/0-3岁通用", "sales": "月销680"},
        {"product_id": "jd_1y_3", "title": "辅食机+蒸煮搅打一体 婴儿专用", "price": 899, "is_jd_self": True, "rating": 4.9, "key_specs": "蒸煮搅打一体/食品级/12月+辅食必备", "sales": "月销1500"},
        {"product_id": "jd_1y_4", "title": "周岁衣物礼盒 含汉服+常服+鞋袜", "price": 1299, "is_jd_self": True, "rating": 4.9, "key_specs": "周岁汉服+日常款+鞋袜全套", "sales": "月销850"},
        {"product_id": "jd_1y_5", "title": "学步车 平衡+稳定 1-3岁", "price": 599, "is_jd_self": True, "rating": 4.8, "key_specs": "平衡车款/防侧翻/1-3岁可用", "sales": "月销1200"},
        {"product_id": "jd_1y_6", "title": "婴儿绘本套装 100本经典款", "price": 599, "is_jd_self": True, "rating": 4.9, "key_specs": "100本绘本/0-3岁经典/启蒙必备", "sales": "月销2500"},
        {"product_id": "jd_1y_7", "title": "婴儿体检+疫苗记录本套装", "price": 89, "is_jd_self": True, "rating": 4.8, "key_specs": "疫苗记录+体检+成长记录", "sales": "月销4500"}
    ],
    "1 岁宝宝周岁礼包 7 件 ¥5983，**余 ¥2017 留备用**：\n\n## 🎂 完整方案\n\n| 物品 | 商品 | 价格 |\n|---|---|---|\n| 🥇 餐椅 | **BABYBJÖRN 高度可调** | ¥1899 |\n| 早教桌 | 费雪多功能 | ¥599 |\n| 辅食机 | 蒸煮搅打一体 | ¥899 |\n| 周岁衣物 | 汉服+常服+鞋袜 | ¥1299 |\n| 学步车 | 平衡车款 | ¥599 |\n| 绘本套装 | 100 本经典 | ¥599 |\n| 记录本 | 体检+疫苗+成长 | ¥89 |\n| **合计** | | **¥5983** |\n\n## 💡 1 岁宝宝刚需 vs 可缓\n\n### 🥇 立即必买（前 3 件）\n\n1. **餐椅 ¥1899**：1 岁开始自主进食，**没餐椅吃饭就是灾难**\n2. **辅食机 ¥899**：1 岁辅食量加大，手工剁 10 分钟用辅食机 1 分钟\n3. **绘本 ¥599**：每天读 15 分钟，**语言能力提升 30%**\n\n### 🥈 1-2 个月内买（4-5 件）\n\n4. **学步车**：12-15 个月开始走\n5. **早教桌**：6-18 个月益智\n\n### 🥉 可选\n\n6. **周岁衣物**：拍周岁照用（汉服只穿 1 次）\n7. **记录本**：纪念意义\n\n## 💰 余 ¥2017 加这些\n\n按优先级：\n\n1. **奶粉+辅食食材**（¥800）：3 个月口粮\n2. **益生菌+维生素 D**（¥300）：医生建议补充\n3. **婴儿摄影**（¥600）：1 岁照专业拍\n4. **存款本**（¥0）：周岁存 ¥10000 给宝宝 18 岁\n\n## 🎂 周岁仪式感\n\n**抓周套装**：放课本/玩具/钱币/听诊器等 10 件物品，看宝宝抓哪个预示未来。**仪式感 ¥0 但回忆终身**。\n\n## ⚠️ 1 岁宝宝避雷\n\n- ❌ **学步车老款**（侧翻易摔伤，平衡车款更安全）\n- ❌ **过早穿鞋**（13 个月内光脚更利于足弓发育）\n- ❌ **甜食**（1 岁内绝对禁糖）\n- ❌ **果汁**（破坏宝宝味觉，吃水果就好）\n\n## 💎 不同预算方案\n\n### 紧凑版 ¥4000\n- 餐椅 ¥1899 + 辅食机 ¥899 + 绘本 ¥599 + 衣物 ¥600 = **¥3997**\n- 砍掉早教桌/学步车（家有空地宝宝爬就行）\n\n### 豪华版 ¥10000\n- 加投影仪（看动画）¥1500\n- 加儿童相机 ¥500\n- 加蒙台梭利教具 ¥1000\n\n本次 ¥5983 是平衡版本。",
    ["BABYBJÖRN餐椅+高度可调+0-3岁通用+月销680，1岁自主进食刚需", "费雪早教益智桌+亮灯音乐按钮+月销2200，6-18月益智发展", "辅食机蒸煮搅打一体+食品级+月销1500，1岁辅食加大刚需", "周岁汉服+常服+鞋袜礼盒+月销850，周岁照拍照仪式感", "平衡车款学步车+防侧翻+1-3岁+月销1200，12-15月开始走", "100本婴儿绘本套装+0-3岁经典+月销2500，每天读语言能力+30%", "疫苗体检成长记录本+月销4500，纪念终身的成长记录"]
))

# 8. bundle - 7000 自媒体加配
T.append(make_traj(
    "sft_bundle_030", "bundle_purchase", "组合购物",
    "5000 元线下小生意装备",
    "想开家小型奶茶店，5000 预算配齐封口机+冰箱+杯具+原料",
    {"query": "奶茶店装备 封口机+冰箱+杯", "max_price": 5500, "filters": {"category": "milktea_shop"}},
    [
        {"product_id": "jd_mt_1", "title": "商用半自动封口机 90R 全自动", "price": 1599, "is_jd_self": True, "rating": 4.9, "key_specs": "商用90R自动封口/适合90mm口径杯", "sales": "月销680"},
        {"product_id": "jd_mt_2", "title": "美的 商用展示冰箱 立式 460L", "price": 1899, "is_jd_self": True, "rating": 4.9, "key_specs": "商用展示+冷藏+460L", "sales": "月销520"},
        {"product_id": "jd_mt_3", "title": "奶茶杯+杯盖 90mm口径 1000个套装", "price": 299, "is_jd_self": True, "rating": 4.8, "key_specs": "PP杯/90mm/1000个/可定制LOGO", "sales": "月销2500"},
        {"product_id": "jd_mt_4", "title": "全自动雪克机+果糖机+果粉机三件套", "price": 999, "is_jd_self": True, "rating": 4.9, "key_specs": "雪克+果糖+果粉/商用三件套", "sales": "月销850"},
        {"product_id": "jd_mt_5", "title": "奶茶店原料起步套装(茶+奶+糖)", "price": 599, "is_jd_self": True, "rating": 4.8, "key_specs": "茶叶+植脂末+果糖+珍珠等", "sales": "月销1200"}
    ],
    "奶茶店开业 5 件套 ¥5395，**最基础配置**：\n\n## 🥤 完整方案\n\n| 装备 | 商品 | 价格 | 必要性 |\n|---|---|---|---|\n| 🥇 封口机 | 商用半自动 90R | ¥1599 | ⭐⭐⭐⭐⭐ |\n| 冰箱 | 美的 460L 展示款 | ¥1899 | ⭐⭐⭐⭐⭐ |\n| 雪克三件套 | 雪克+果糖+果粉 | ¥999 | ⭐⭐⭐⭐ |\n| 原料 | 起步套装 | ¥599 | ⭐⭐⭐⭐⭐ |\n| 杯具 | 1000 个 PP 杯 | ¥299 | ⭐⭐⭐⭐⭐ |\n| **合计** | | **¥5395** | |\n\n## ⚠️ 但要泼冷水：5000 真不够开奶茶店\n\n以上只是**最基础设备**，开店还需要：\n\n### 必备未列（约 ¥10000+）\n- **店面租金**（小县城 ¥2000/月+押 3 付 1）\n- **装修**（最简 ¥5000-10000）\n- **营业执照+食品经营许可证**（¥500-1000）\n- **POS 机/收款码**（¥500）\n- **员工培训**（¥1000）\n\n### 加盟 vs 自营\n\n**强烈建议加盟**：\n- 蜜雪冰城加盟费 ¥10000-30000（**含全套设备+培训+品牌**）\n- 自营容易做 3 个月倒闭（不会调配+不会运营+没流量）\n\n## 💰 真实奶茶店开店成本拆解\n\n| 项目 | 自营 | 加盟蜜雪冰城 |\n|---|---|---|\n| 设备 | ¥5395 | 含在加盟费 |\n| 装修 | ¥10000 | 含在加盟费 |\n| 加盟费 | ¥0 | ¥10000-30000 |\n| 房租押金 | ¥10000 | ¥10000 |\n| 原料 | ¥3000 | ¥3000 |\n| 杂费 | ¥5000 | ¥3000 |\n| **总投入** | **¥33395** | **¥35000-50000** |\n\n## 🎯 真心建议\n\n### 你是新手 → **加盟蜜雪冰城/茶百道/书亦**\n- 总投资 ¥3-5 万\n- 3 个月回本概率 70%\n- 品牌帮你引流\n\n### 你有奶茶经验 → 加盟+自营\n### 你只有 ¥5000 → **先别开店**\n- 5000 不够开店，会血本无归\n- 建议先在奶茶店打工 3-6 个月学经验\n- **存够 5 万再开**\n\n## 💎 如果坚持只用 5000 设备\n\n这套**仅适合「家庭奶茶」或「外卖纯线上小店」**：\n- 在家做+外卖平台接单\n- 月销 1000 杯起步\n- **不建议租店面**",
    ["商用半自动封口机90R+适合90mm杯+月销680，奶茶店基础设备", "美的商用展示冰箱460L+冷藏+月销520，原料/成品冷藏刚需", "奶茶杯+杯盖90mm 1000个+可定制LOGO+月销2500，1000杯起步用量", "雪克+果糖+果粉商用三件套+月销850，调奶茶必备工具", "奶茶店原料起步套装+茶+奶+珍珠+月销1200，开业第一周用量"]
))

# 9. place_order - 异地下单+代收
T.append(make_traj(
    "sft_order_017", "place_order", "购物下单",
    "异地下单礼物+代收",
    "想给在上海的爸妈下单一台 ¥3999 的电视，我在北京",
    {"product_id": "jd_tv_001", "address": "PARENT_SHANGHAI", "remote_purchase": True},
    [
        {"product_id": "jd_tv_001", "title": "海信 65 寸 4K 智能电视 (上海仓直发)", "price": 3999, "is_jd_self": True, "rating": 4.9, "key_specs": "订单[TRACKING_ID]-REMOTE-2284/CITY_ADDRESS", "sales": "—"}
    ],
    "✅ 远程下单成功！\n\n## 📦 订单详情\n\n- **商品**：海信 65 寸 4K 智能电视\n- **价格**：¥3999\n- **订单号**：[TRACKING_ID]-REMOTE-2284\n- **收货人**：你父母（上海地址）\n- **付款人**：你（北京账户）\n- **发货仓**：**上海仓直发**（不从北京调货）\n- **预计 3 天送达**\n\n## ⚠️ 异地下单 4 个关键注意事项\n\n### 1️⃣ 提前通知父母收货\n**父母经常不知道孩子下单**，导致：\n- 快递打电话被当作骚扰挂掉\n- 不在家被退回\n- 父母拒收以为是诈骗\n\n**立刻发微信**：「老爸/老妈，明天京东送货上门，是电视/给你们的礼物。」\n\n### 2️⃣ 安装服务必须提前预约\n65 寸大电视**需要 2 人抬+师傅上墙**：\n- 在订单页**勾选「免费上门安装」**\n- 师傅会提前 1 天电话联系父母\n- 父母可让物业帮忙抬到楼上\n\n### 3️⃣ 发票寄给谁\n- 默认**发票随商品寄到父母**\n- 如果你要报销/纪念，**改为「电子发票」**寄你邮箱\n\n### 4️⃣ 售后由谁处理\n京东自营**全国联保**：\n- 父母可直接打 950618 维修（用订单号）\n- 不需要通过你\n- **保修期 3 年（家电默认）**\n\n## 💡 远程购物贴心服务\n\n京东提供「**远程购物**」服务（适合给父母/孩子买东西）：\n\n1. **发货前打电话给收件人确认**（避免父母不知道）\n2. **安装时拍照发给你**（确认安装成功）\n3. **教学服务**：师傅可花 10 分钟教父母用电视\n\n## 🎁 顺便送出温暖\n\n下单后给爸妈打个电话：\n> 「老爸老妈，给你们买了台新电视，明天就到。\n> 安装师傅会上门，你们不用搬东西。\n> 用着有问题随时给我打电话。」\n\n**这个电话比电视本身还值钱**。\n\n## 💰 余 ¥0 但推荐加 ¥299\n\n京东自营**电视家会员**（¥299/年）：\n- 父母可看央视+地方台+电视剧\n- 不用学复杂操作（开机就有节目）\n- 比 IPTV 月费 ¥30 划算\n\n要不要加？",
    ["海信65寸4K智能电视已下单+CITY_ADDRESS付款，异地下单远程购物服务"],
    tool_name="ShoppingPlaceOrderTool"
))

# 10. repurchase - 复购+季节升级
T.append(member_t := make_traj(
    "sft_repurchase_015", "repurchase", "复购召回",
    "复购冬款+春夏季升级建议",
    "再买之前那条秋裤，但天热了想要薄款的",
    {"category_keyword": "保暖内衣裤", "time_range": "last_8_months", "include_seasonal_alt": True},
    [
        {"product_id": "jd_pants_winter", "title": "优衣库 HEATTECH 极暖秋裤 黑色 (你 5 月前购买)", "price": 199, "is_jd_self": True, "rating": 4.9, "key_specs": "你5月前购买/订单[ORDER_ID]/HEATTECH冬款", "sales": "月销1.2万"},
        {"product_id": "jd_pants_spring", "title": "优衣库 AIRism 凉感打底裤 黑色 (春夏款)", "price": 159, "is_jd_self": True, "rating": 4.9, "key_specs": "AIRism凉感/吸汗速干/夏季空调房专用", "sales": "月销4500"},
        {"product_id": "jd_pants_universal", "title": "优衣库 三季款打底裤 中等厚度 (春秋通用)", "price": 179, "is_jd_self": True, "rating": 4.8, "key_specs": "中等厚度/3-5月+9-10月通用/弹力舒适", "sales": "月销2200"}
    ],
    "你 5 个月前买的是 **优衣库 HEATTECH 极暖秋裤 ¥199**（冬款）。\n\n## 🌞 季节性建议\n\n现在 6 月底，**冬款秋裤穿不了**（会闷出汗）。优衣库同系列有 2 个季节款：\n\n### ☀️ 春夏选 → AIRism 凉感打底 ¥159\n\n- **吸汗速干**（夏天空调房刚需）\n- 比冬款薄 70%\n- **空调房+短裙搭配**最舒服\n- 月销 4500 件是夏季打底裤断档第一\n\n### 🍂 春秋选 → 三季款中厚 ¥179\n\n- 中等厚度，**3-5 月 + 9-10 月通用**\n- 1 件解决春秋\n- 弹力面料舒适\n\n## 📊 优衣库内衣系列季节适配\n\n| 季节 | 优衣库系列 | 价格 |\n|---|---|---|\n| 12-2 月（冬）| HEATTECH 极暖 | ¥199（你买的）|\n| 3-5 月（春）| 三季款 | ¥179 |\n| 6-8 月（夏）| **AIRism 凉感** | **¥159** |\n| 9-11 月（秋）| 三季款 | ¥179 |\n\n## 💡 一年 4 件最完整\n\n如果你想**全年穿优衣库系列**：\n\n- 1 件 HEATTECH（冬，你已有）\n- 1 件三季款（春秋）¥179\n- 1 件 AIRism（夏）¥159\n- 共 ¥338（再加你已有的）= **¥537 全年覆盖**\n\n## 🎯 我的建议\n\n**现在直接买 AIRism 凉感 ¥159**（夏季刚需）：\n- 即买即穿（北京已经 35℃）\n- 夏季穿 4 个月（6-9 月）\n- 平均每天 ¥1.3 的舒适\n\n要不要直接帮你下单 AIRism？或者三件全套（¥537）一年解决？",
    ["优衣库HEATTECH极暖秋裤你5月前购买，仅适合冬季12-2月", "优衣库AIRism凉感打底裤+吸汗速干+月销4500，夏季空调房刚需", "优衣库三季款打底裤中等厚度+月销2200，3-5月+9-10月通用"],
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
