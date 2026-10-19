# -*- coding: utf-8 -*-
"""
SkuRecallShopping — 对应真实项目的 sku_recall_hub + scenario_recall_hub

真实项目：
    sku_recall(query, page_size, site, min_price, max_price, oxy_request)
    scenario_related_recall(queries, oxy_request)
    sku_detail_fetch(sku_ids, site_code, ...)

本工具：统一对外暴露为 SkuRecallShopping（SFT 数据中的 tool_name），
内部按 params 的 mode 或字段区分召回策略：
    - 普通搜索：query + min/max_price
    - matching 搭配：query + filters.style（无价格约束）
    - bundle 组合：query + max_price（多次调用，每次对应一个品类）
    - sku_comp 精确：skus=[sku_name1, sku_name2]（精确名称匹配）
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────
# Mock 商品池：10 品类 × 3 款 = 30 条
# 字段与 trajectories_final.jsonl 完全对齐
# ─────────────────────────────────────────────
MOCK_PRODUCT_POOL: List[Dict[str, Any]] = [
    # ── 手机 5000-6500元 ──
    {"product_id": "mock_10001001", "title": "小米14 Pro 16+512G 钛金属黑",
     "price": 5299.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "骁龙8 Gen3/徕卡光学三摄/6.73寸2K屏/4880mAh",
     "sales": "月销2.1万", "category": "手机",
     "aliases": ["小米14", "小米14Pro", "MI14", "小米14 Pro"]},
    {"product_id": "mock_10001002", "title": "华为Mate60 Pro 12+512G 雅丹黑",
     "price": 6499.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "麒麟9000S/卫星通话/XMAGE四摄/玄武架构",
     "sales": "月销1.8万", "category": "手机",
     "aliases": ["华为Mate60", "Mate60Pro", "华为Mate60 Pro", "华为旗舰"]},
    {"product_id": "mock_10001003", "title": "vivo X100 Ultra 16+512G 曜石黑",
     "price": 5999.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "天玑9300+/蔡司APO超级长焦/2K柔性AMOLED/5500mAh",
     "sales": "月销9800", "category": "手机",
     "aliases": ["vivo X100", "X100 Ultra", "vivoX100", "vivo旗舰"]},

    # ── 空气净化器 1000-2000元 ──
    {"product_id": "mock_10002001", "title": "小米米家空气净化器4 Pro 除甲醛款",
     "price": 1599.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "CADR 500m³/h(颗粒)/300m³/h(甲醛)/H13级HEPA/适用60-80㎡",
     "sales": "月销4.1万", "category": "空气净化器",
     "aliases": ["小米净化器", "米家净化器4", "小米空气净化器4Pro"]},
    {"product_id": "mock_10002002", "title": "352 X83C 大客厅空气净化器 白色",
     "price": 1999.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "CADR 750/400m³/h/双侧进风/CCM顶级F4/适用90㎡",
     "sales": "月销1.2万", "category": "空气净化器",
     "aliases": ["352净化器", "352 X83", "X83C"]},
    {"product_id": "mock_10002003", "title": "IAM KJ900F 全能除醛净化器 母婴款",
     "price": 1799.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "CADR 900/450m³/h/醛霾双独立滤芯/适用100㎡",
     "sales": "月销8500", "category": "空气净化器",
     "aliases": ["IAM净化器", "KJ900F", "IAM KJ900"]},

    # ── 跑步鞋 200-300元 ──
    {"product_id": "mock_10003001", "title": "安踏氢跑5代 男款减震跑步鞋 黑白",
     "price": 249.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "氢科技中底缓震/4D工程网鞋面/异形橡胶颗粒防滑",
     "sales": "月销5.1万双", "category": "跑步鞋",
     "aliases": ["安踏氢跑", "安踏跑步鞋", "氢跑5"]},
    {"product_id": "mock_10003002", "title": "李宁䨻烁2 男款跑步鞋 全网面透气",
     "price": 269.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "䨻轻弹中底/全网面鞋面/橡胶大底/轻量化设计",
     "sales": "月销2.8万双", "category": "跑步鞋",
     "aliases": ["李宁跑步鞋", "李宁䨻烁", "䨻烁2"]},
    {"product_id": "mock_10003003", "title": "特步竞速160X 5代 碳板竞速跑鞋",
     "price": 299.0, "is_platform_self": True, "rating": 4.6,
     "key_specs": "PEBA发泡中底/前掌碳板/单只218g超轻",
     "sales": "月销9800双", "category": "跑步鞋",
     "aliases": ["特步160X", "特步竞速", "160X5代"]},

    # ── 颈部按摩仪 200-500元 ──
    {"product_id": "mock_11223344", "title": "小米米家颈椎按摩仪 3档强度 热敷款",
     "price": 349.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "3档力度/15分钟自动断电/热敷功能/一键启动",
     "sales": "月销3.2万", "category": "颈部按摩仪",
     "aliases": ["小米按摩仪", "米家颈椎按摩仪", "小米颈部按摩"]},
    {"product_id": "mock_55667788", "title": "飞利浦肩颈按摩仪 PR3092 老人款",
     "price": 469.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "5档强度/40-50℃热敷/锂电池4小时续航",
     "sales": "月销1.8万", "category": "颈部按摩仪",
     "aliases": ["飞利浦按摩仪", "PR3092", "飞利浦颈椎"]},
    {"product_id": "mock_99001122", "title": "倍轻松颈椎按摩器 智能感应 老年款",
     "price": 299.0, "is_platform_self": True, "rating": 4.6,
     "key_specs": "贴合人体颈部/12分钟定时/极简一键设计",
     "sales": "月销1.5万", "category": "颈部按摩仪",
     "aliases": ["倍轻松按摩仪", "倍轻松颈椎", "倍轻松"]},

    # ── 扫地机器人 1500-4000元 ──
    {"product_id": "mock_10005001", "title": "石头扫地机器人G20S Pro 激光导航",
     "price": 2999.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "激光导航/7000Pa强吸力/自动集尘+烘干/全能站",
     "sales": "月销1.5万", "category": "扫地机",
     "aliases": ["石头G20S", "石头G20", "roborock G20S", "石头扫地机G20"]},
    {"product_id": "mock_10005002", "title": "科沃斯X2 Omni 扫拖一体全能机器人",
     "price": 3599.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "自动上下水/热风烘干/探索pro导航/避障Pro",
     "sales": "月销6800", "category": "扫地机",
     "aliases": ["科沃斯X2", "ecovacs X2", "X2 Omni", "科沃斯"]},
    {"product_id": "mock_10005003", "title": "追觅L20 Ultra 全能扫拖机器人",
     "price": 3299.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "7000Pa吸力/自动集尘清洗烘干/机械臂智能避障",
     "sales": "月销5200", "category": "扫地机",
     "aliases": ["追觅L20", "dreame L20", "L20 Ultra", "追觅扫地机"]},

    # ── 人体工学椅 1000-2000元 ──
    {"product_id": "mock_10006001", "title": "西昊 Doro C300 人体工学椅 4D扶手",
     "price": 1499.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "4D扶手/腰托/网布透气/可躺130°/承重150kg",
     "sales": "月销1.8万", "category": "椅子",
     "aliases": ["西昊C300", "西昊Doro", "Doro C300", "西昊工学椅"]},
    {"product_id": "mock_10006002", "title": "保友金豪E2 人体工学椅精英版",
     "price": 1999.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "联动扶手/腰托/头枕全可调/透气网背",
     "sales": "月销4500", "category": "椅子",
     "aliases": ["保友金豪E2", "保友E2", "保友工学椅"]},
    {"product_id": "mock_10006003", "title": "网易严选 云鲸C1 人体工学椅",
     "price": 1299.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "坐姿感应/腰靠可调/透气网椅/颜值高",
     "sales": "月销3200", "category": "椅子",
     "aliases": ["云鲸C1", "网易严选工学椅", "云鲸椅子"]},

    # ── 耳机 200-1300元 ──
    {"product_id": "mock_10007001", "title": "索尼WF-C700N 真无线降噪耳机",
     "price": 399.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "主动降噪/IPX4防水/7.5h续航/LDAC高清音频",
     "sales": "月销2.2万", "category": "耳机",
     "aliases": ["索尼WF-C700N", "索尼C700N", "sony WF-C700N"]},
    {"product_id": "mock_10007002", "title": "苹果AirPods 4 主动降噪版",
     "price": 1299.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "主动降噪/通透模式/30h总续航/H2芯片",
     "sales": "月销3.5万", "category": "耳机",
     "aliases": ["AirPods 4", "苹果AirPods4", "AirPods4降噪版"]},
    {"product_id": "mock_10007003", "title": "漫步者TWS1 Pro 开放式蓝牙耳机",
     "price": 199.0, "is_platform_self": True, "rating": 4.6,
     "key_specs": "开放式不入耳/8h续航/通话降噪/舒适佩戴",
     "sales": "月销8500", "category": "耳机",
     "aliases": ["漫步者TWS1", "EDIFIER TWS1", "漫步者开放式耳机"]},

    # ── 显示器 700-1400元 ──
    {"product_id": "mock_10008001", "title": "DELL S2722DC 27寸2K Type-C 90W",
     "price": 1099.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "27寸2K IPS/Type-C 90W反向供电/USB Hub/广色域",
     "sales": "月销4500", "category": "显示器",
     "aliases": ["DELL S2722DC", "戴尔S2722DC", "dell 27寸显示器"]},
    {"product_id": "mock_10008002", "title": "LG 27GP850-B 27寸2K 165Hz游戏显示器",
     "price": 1399.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "27寸2K Nano IPS/165Hz/1ms GTG/HDR400/G-Sync",
     "sales": "月销6200", "category": "显示器",
     "aliases": ["LG 27GP850", "LG 27GP850-B", "LG游戏显示器"]},
    {"product_id": "mock_10008003", "title": "小米 23.8寸 1080P 100Hz 办公显示器",
     "price": 699.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "23.8寸1080P/100Hz/IPS低蓝光/超薄边框",
     "sales": "月销1.2万", "category": "显示器",
     "aliases": ["小米显示器", "小米23.8寸", "米家显示器"]},

    # ── 炒锅 150-500元 ──
    {"product_id": "mock_10009001", "title": "苏泊尔钛系列不粘炒锅 32cm 明火电磁通用",
     "price": 459.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "钛合金不粘/32cm/明火电磁通用/送锅盖+硅胶铲",
     "sales": "月销3.5万", "category": "炒锅",
     "aliases": ["苏泊尔钛系列", "苏泊尔不粘锅", "苏泊尔炒锅"]},
    {"product_id": "mock_10009002", "title": "炊大皇麦饭石不粘炒锅 30cm 钛晶版",
     "price": 199.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "麦饭石涂层/30cm/无PFOA/性价比首选",
     "sales": "月销5万", "category": "炒锅",
     "aliases": ["炊大皇麦饭石", "炊大皇炒锅", "麦饭石炒锅"]},
    {"product_id": "mock_10009003", "title": "南山先生 铸铁无涂层炒锅 30cm 开锅版",
     "price": 289.0, "is_platform_self": True, "rating": 4.6,
     "key_specs": "铸铁无涂层/天然不粘/重4.2kg/越用越不粘",
     "sales": "月销2800", "category": "炒锅",
     "aliases": ["南山先生炒锅", "南山先生铸铁锅", "铸铁炒锅"]},

    # ── 保温杯 100-300元 ──
    {"product_id": "mock_10010001", "title": "膳魔师 经典系列保温杯 500ml 哑黑",
     "price": 199.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "316不锈钢/24h保温/500ml/防漏盖设计",
     "sales": "月销3.8万", "category": "保温杯",
     "aliases": ["膳魔师保温杯", "THERMOS保温杯", "膳魔师500ml"]},
    {"product_id": "mock_10010002", "title": "虎牌MHK-A050 500ml 保温杯 一键开盖",
     "price": 229.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "一键开盖/24h保温/真空双层304不锈钢",
     "sales": "月销2.1万", "category": "保温杯",
     "aliases": ["虎牌保温杯", "tiger MHK", "虎牌MHK-A050"]},
    {"product_id": "mock_10010003", "title": "小米MIGA 316不锈钢保温杯 480ml",
     "price": 129.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "316食品级钢/12h保温/480ml/米家生态链",
     "sales": "月销5.5万", "category": "保温杯",
     "aliases": ["小米保温杯", "米家保温杯", "MIGA保温杯"]},

    # ── 咖啡机 1000-3000元 ──
    {"product_id": "mock_11001001", "title": "德龙EN520 Nespresso胶囊咖啡机 钛金属",
     "price": 1299.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "Nespresso胶囊/19bar压力/33秒预热/0.7L水箱",
     "sales": "月销2.1万", "category": "咖啡机",
     "aliases": ["德龙胶囊咖啡机", "德龙EN520", "Delonghi EN520", "德龙咖啡"]},
    {"product_id": "mock_11001002", "title": "飞利浦EP2224 全自动意式咖啡机",
     "price": 2499.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "全自动研磨/双豆仓/3档浓度/奶泡系统",
     "sales": "月销8500", "category": "咖啡机",
     "aliases": ["飞利浦全自动咖啡机", "飞利浦EP2224", "Philips咖啡机"]},
    {"product_id": "mock_11001003", "title": "格米莱CRM3016 半自动意式咖啡机",
     "price": 1599.0, "is_platform_self": True, "rating": 4.6,
     "key_specs": "15bar泵压/双温控系统/PID控温/商用级磨豆",
     "sales": "月销5200", "category": "咖啡机",
     "aliases": ["格米莱咖啡机", "格米莱CRM3016", "GEMILAI咖啡机"]},

    # ── 跑步机 2000-5000元 ──
    {"product_id": "mock_11002001", "title": "舒华SH-T5100 折叠跑步机 家用款",
     "price": 3299.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "3.0HP电机/15档坡度/12km/h最高速/静音减震",
     "sales": "月销1.6万", "category": "跑步机",
     "aliases": ["舒华跑步机", "舒华SH-T5100", "舒华折叠跑步机"]},
    {"product_id": "mock_11002002", "title": "乔山A3跑步机 家用静音商用级",
     "price": 4599.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "3.5HP持续马力/16档坡度/20km/h/心率检测",
     "sales": "月销4500", "category": "跑步机",
     "aliases": ["乔山A3", "JOHNSON A3", "乔山跑步机A3"]},
    {"product_id": "mock_11002003", "title": "小米家用跑步机 折叠 智能联网款",
     "price": 2199.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "2.5HP电机/12km/h/米家APP控制/折叠收纳",
     "sales": "月销3.2万", "category": "跑步机",
     "aliases": ["小米跑步机", "米家跑步机", "小米家用跑步机"]},

    # ── 投影仪 1500-4000元 ──
    {"product_id": "mock_11003001", "title": "极米H6 4K激光投影仪 家用影院",
     "price": 3999.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "4K分辨率/2800流明/ALPD激光光源/内置安卓",
     "sales": "月销6800", "category": "投影仪",
     "aliases": ["极米H6", "XGIMI H6", "极米激光投影"]},
    {"product_id": "mock_11003002", "title": "当贝X4 Ultra 4K激光投影仪",
     "price": 3599.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "4K/3200流明CVIA/三色激光/自动对焦梯形校正",
     "sales": "月销4200", "category": "投影仪",
     "aliases": ["当贝X4", "Dangbei X4", "当贝激光投影"]},
    {"product_id": "mock_11003003", "title": "坚果N1 Ultra 三色激光投影仪 旗舰",
     "price": 3299.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "4K/2500流明/三色激光/AI智能画质引擎",
     "sales": "月销3500", "category": "投影仪",
     "aliases": ["坚果N1", "JmGO N1 Ultra", "坚果投影N1"]},

    # ── 键盘 100-600元 ──
    {"product_id": "mock_11004001", "title": "罗技MX Keys S 无线智能背光键盘",
     "price": 599.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "无线2.4G+蓝牙/背光/球形按键/10设备切换",
     "sales": "月销1.8万", "category": "键盘",
     "aliases": ["罗技MX Keys", "Logitech MX Keys S", "罗技无线键盘MX"]},
    {"product_id": "mock_11004002", "title": "杜伽K320W 无线三模机械键盘 红轴",
     "price": 319.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "三模连接/线性红轴/PBT键帽/Type-C充电",
     "sales": "月销2.5万", "category": "键盘",
     "aliases": ["杜伽K320", "DURGOD K320W", "杜伽三模键盘"]},
    {"product_id": "mock_11004003", "title": "飞利浦SPK8601 有线机械键盘 青轴",
     "price": 169.0, "is_platform_self": True, "rating": 4.6,
     "key_specs": "青轴/87键TKL/RGB背光/合金面板",
     "sales": "月销9800", "category": "键盘",
     "aliases": ["飞利浦SPK8601", "飞利浦机械键盘", "Philips SPK8601"]},

    # ── 鼠标 100-500元 ──
    {"product_id": "mock_11005001", "title": "罗技MX Master 3S 无线鼠标 深灰",
     "price": 499.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "8000DPI/无线2.4G+蓝牙/磁力滚轮/人体工学",
     "sales": "月销3.5万", "category": "鼠标",
     "aliases": ["罗技MX Master 3S", "Logitech MX Master 3S", "罗技MX鼠标"]},
    {"product_id": "mock_11005002", "title": "雷蛇蝰蛇V3 HyperSpeed 无线游戏鼠标",
     "price": 399.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "30000DPI/光学传感器/90h续航/2.4G极速无线",
     "sales": "月销1.9万", "category": "鼠标",
     "aliases": ["雷蛇蝰蛇V3", "Razer Viper V3", "雷蛇游戏鼠标V3"]},
    {"product_id": "mock_11005003", "title": "微软Arc人体工学无线鼠标 蓝影技术",
     "price": 299.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "蓝影技术/人体工学弧形/蓝牙+无线接收器/AA电池",
     "sales": "月销8500", "category": "鼠标",
     "aliases": ["微软人体工学鼠标", "Microsoft Arc鼠标", "微软Arc"]},

    # ── 护肤精华 200-800元 ──
    {"product_id": "mock_11006001", "title": "雅诗兰黛 第七代小棕瓶精华 50ml",
     "price": 780.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "夜间修护/ANF酵母精华/抗老淡纹/50ml",
     "sales": "月销4.2万", "category": "护肤精华",
     "aliases": ["雅诗兰黛小棕瓶", "小棕瓶精华", "Estee Lauder小棕瓶"]},
    {"product_id": "mock_11006002", "title": "兰蔻小黑瓶肌底液精华 50ml",
     "price": 680.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "双重益生元/安瓶精华/修护屏障/50ml",
     "sales": "月销3.1万", "category": "护肤精华",
     "aliases": ["兰蔻小黑瓶", "LANCOME小黑瓶", "兰蔻肌底液"]},
    {"product_id": "mock_11006003", "title": "修丽可CE精华 抗氧化精华液 30ml",
     "price": 680.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "15%维C+0.5%阿魏酸/抗氧化/淡斑提亮/30ml",
     "sales": "月销1.8万", "category": "护肤精华",
     "aliases": ["修丽可CE精华", "SkinCeuticals CE", "修丽可维C精华"]},

    # ── 洗碗机 2000-6000元 ──
    {"product_id": "mock_11007001", "title": "方太EW14Pro 嵌入式洗碗机 14套",
     "price": 5499.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "14套/热风烘干/第三层刀叉篮/75℃高温除菌",
     "sales": "月销6200", "category": "洗碗机",
     "aliases": ["方太嵌入式洗碗机", "方太EW14", "方太洗碗机Pro"]},
    {"product_id": "mock_11007002", "title": "西门子SJ556S00JC 全嵌入式洗碗机 13套",
     "price": 4999.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "全嵌入式/13套/zeolith沸石烘干/A+++能效",
     "sales": "月销4500", "category": "洗碗机",
     "aliases": ["西门子全嵌洗碗机", "西门子SJ556", "Siemens嵌入式洗碗机"]},
    {"product_id": "mock_11007003", "title": "美的WQP8-W3906H 台式洗碗机 8套",
     "price": 2199.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "8套/热风烘干/85℃高温/免安装台式款",
     "sales": "月销1.2万", "category": "洗碗机",
     "aliases": ["美的台式洗碗机", "美的WQP8", "美的洗碗机台式"]},

    # ── 空调 2000-5000元 ──
    {"product_id": "mock_11008001", "title": "美的风尊1.5P变频冷暖挂机 KFR-35GW",
     "price": 3299.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "1.5匹/一级能效/变频制冷/自清洁/超低噪22dB",
     "sales": "月销4.8万", "category": "空调",
     "aliases": ["美的1.5P空调", "美的变频空调", "美的KFR-35GW"]},
    {"product_id": "mock_11008002", "title": "格力大1匹 1级变频挂机 云锦系列",
     "price": 2699.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "1匹/一级能效/变频/强效净化/自清洁",
     "sales": "月销3.5万", "category": "空调",
     "aliases": ["格力大1P空调", "格力云锦", "格力变频挂机"]},
    {"product_id": "mock_11008003", "title": "海信小1匹 新一级变频挂机 卧室小空间",
     "price": 2099.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "0.8匹/新一级能效/适用10-14㎡/静音运行",
     "sales": "月销2.2万", "category": "空调",
     "aliases": ["海信小1P空调", "海信变频挂机", "海信卧室空调"]},

    # ── 婴儿推车 500-3000元 ──
    {"product_id": "mock_11009001", "title": "好孩子GB826 高景观婴儿推车 可坐躺",
     "price": 1299.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "高景观60cm/双向推行/一键折叠/适用0-3岁",
     "sales": "月销9500", "category": "婴儿推车",
     "aliases": ["好孩子GB826", "好孩子推车", "Goodbaby GB826"]},
    {"product_id": "mock_11009002", "title": "Bugaboo Cameleon3 Plus 双向婴儿推车",
     "price": 5999.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "双向坐躺/模块化设计/悬挂减震系统/0-4岁",
     "sales": "月销1200", "category": "婴儿推车",
     "aliases": ["Bugaboo Cameleon", "博格步Cameleon", "Bugaboo推车"]},
    {"product_id": "mock_11009003", "title": "UPPAbaby Cruz V2 婴儿推车 单手折叠",
     "price": 4599.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "单手折叠/可坐躺/四轮减震/0-3岁/欧美热销款",
     "sales": "月销1800", "category": "婴儿推车",
     "aliases": ["UPPAbaby Cruz", "UPPAbaby推车", "Cruz V2推车"]},

    # ── 台灯 100-500元 ──
    {"product_id": "mock_11010001", "title": "明基ScreenBar Plus 屏幕挂灯 带旋钮",
     "price": 499.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "屏幕挂灯/无频闪/自动调光/USB供电/旋钮控制",
     "sales": "月销2.8万", "category": "台灯",
     "aliases": ["明基ScreenBar", "BenQ ScreenBar Plus", "明基屏幕挂灯"]},
    {"product_id": "mock_11010002", "title": "小米米家台灯Pro 无极调光 护眼款",
     "price": 199.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "无极调光调色/Ra95高显色/无频闪/APP联动",
     "sales": "月销5.5万", "category": "台灯",
     "aliases": ["小米台灯Pro", "米家台灯Pro", "小米护眼台灯"]},
    {"product_id": "mock_11010003", "title": "飞利浦酷玥 护眼台灯 学生读写款",
     "price": 169.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "护眼认证/3档色温/无频闪/USB供电/折叠便携",
     "sales": "月销4.1万", "category": "台灯",
     "aliases": ["飞利浦护眼台灯", "飞利浦酷玥", "Philips护眼灯"]},

    # ── 电动牙刷 200-800元 ──
    {"product_id": "mock_12000001", "title": "飞利浦电动牙刷 HX9352 钻石系列 黑色",
     "price": 699.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "声波震动/62000次/分/4种清洁模式/2分钟计时/附4个刷头",
     "sales": "月销3.2万", "category": "电动牙刷",
     "aliases": ["飞利浦HX9352", "飞利浦钻石牙刷", "Philips HX9352", "飞利浦声波牙刷"]},
    {"product_id": "mock_12000002", "title": "欧乐B IO9 智能旋转微震动电动牙刷 黑色",
     "price": 799.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "磁力驱动IO技术/7种清洁模式/AI压力感应/OLED显示屏",
     "sales": "月销1.8万", "category": "电动牙刷",
     "aliases": ["欧乐B IO9", "OralB IO9", "欧乐B智能牙刷", "oral-b io9"]},
    {"product_id": "mock_12000003", "title": "小米米家电动牙刷 T700 声波牙刷",
     "price": 229.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "声波震动/31000次/分/5种清洁模式/NFC智能识别/60天续航",
     "sales": "月销5.6万", "category": "电动牙刷",
     "aliases": ["小米T700", "米家T700", "小米电动牙刷T700", "MIJIA T700"]},

    # ── 充电宝 100-300元 ──
    {"product_id": "mock_12100001", "title": "小米磁吸充电宝 10000mAh 20W 超薄款",
     "price": 149.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "MagSafe磁吸/10000mAh/20W快充/7.5mm超薄/USB-C双向",
     "sales": "月销8.5万", "category": "充电宝",
     "aliases": ["小米磁吸充电宝", "小米MagSafe充电宝", "米家磁吸充电宝", "小米10000磁吸"]},
    {"product_id": "mock_12100002", "title": "Anker 622 磁吸充电宝 5000mAh MagGo",
     "price": 199.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "MagSafe兼容/5000mAh/7.5W磁吸/USB-C 20W/轻薄便携",
     "sales": "月销4.1万", "category": "充电宝",
     "aliases": ["Anker622", "安克622", "Anker MagGo 622", "安克磁吸充电宝"]},
    {"product_id": "mock_12100003", "title": "品胜超薄充电宝 20000mAh 65W双向快充",
     "price": 259.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "20000mAh/65W快充/双USB-C+USB-A/支持笔记本充电/超薄设计",
     "sales": "月销6.2万", "category": "充电宝",
     "aliases": ["品胜65W充电宝", "品胜20000mAh", "品胜超薄移动电源", "PISEN充电宝"]},

    # ── 洗衣机 2000-4000元 ──
    {"product_id": "mock_12200001", "title": "小天鹅滚筒洗烘一体机 10kg TG100VT86WMAD5",
     "price": 3299.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "10kg洗/6kg烘/变频DD直驱/95℃高温洗/蒸汽除菌/A级能效",
     "sales": "月销2.3万", "category": "洗衣机",
     "aliases": ["小天鹅洗烘一体", "小天鹅TG100VT86", "TCL小天鹅洗衣机", "小天鹅滚筒10kg"]},
    {"product_id": "mock_12200002", "title": "海尔直驱滚筒洗衣机 10kg EG10014B939GU1",
     "price": 3599.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "10kg/直驱变频/精华洗2.0/双喷淋漂洗/自洁桶/超净洗",
     "sales": "月销1.6万", "category": "洗衣机",
     "aliases": ["海尔直驱洗衣机", "海尔EG10014B939", "海尔滚筒10kg", "Haier洗衣机"]},
    {"product_id": "mock_12200003", "title": "米家滚筒洗烘套装 10kg XQGS100MJ102S",
     "price": 2699.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "10kg洗烘一体/变频节能/APP智控/自动投放洗涤剂/蒸汽杀菌",
     "sales": "月销9800", "category": "洗衣机",
     "aliases": ["米家洗烘一体", "米家XQGS100MJ102S", "小米洗衣机", "MIJIA洗烘套装"]},

    # ── 电热水壶 100-300元 ──
    {"product_id": "mock_12300001", "title": "小米米家速热电热水壶 1.7L 2400W",
     "price": 129.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "2400W速热/1.7L大容量/304不锈钢内胆/3分钟烧开/自动断电",
     "sales": "月销12.5万", "category": "电热水壶",
     "aliases": ["小米电热水壶", "米家热水壶", "小米烧水壶", "MIJIA电热壶"]},
    {"product_id": "mock_12300002", "title": "美的MK-HJ1710B 速热电热水壶 1.7L 304钢",
     "price": 149.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "1800W速热/1.7L/304不锈钢内胆/360°旋转底座/防烫把手",
     "sales": "月销9.3万", "category": "电热水壶",
     "aliases": ["美的电热水壶", "美的MK-HJ1710B", "美的烧水壶HJ1710", "Midea热水壶"]},
    {"product_id": "mock_12300003", "title": "苏泊尔SWF17BK-400 超快速热电热水壶 1.7L",
     "price": 169.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "2200W速热/3分钟烧开/1.7L/304不锈钢/双层防烫壶身/自动保温",
     "sales": "月销7.8万", "category": "电热水壶",
     "aliases": ["苏泊尔电热水壶", "苏泊尔SWF17BK", "苏泊尔烧水壶", "SUPOR热水壶"]},

    # ── 电风扇 150-500元 ──
    {"product_id": "mock_12400001", "title": "追觅直流变频落地扇 DF07C 32档调速",
     "price": 399.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "直流变频/32档风速/AI智能感温/APP控制/超静音23dB/负离子",
     "sales": "月销3.1万", "category": "电风扇",
     "aliases": ["追觅落地扇", "追觅DF07C", "Dreame DF07C", "追觅变频风扇"]},
    {"product_id": "mock_12400002", "title": "美的落地扇 FS40-13JR 遥控定时静音",
     "price": 199.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "4档风速/遥控定时/7.5h定时/7叶片/底座稳固/适合卧室",
     "sales": "月销6.8万", "category": "电风扇",
     "aliases": ["美的落地扇", "美的FS40-13JR", "美的电风扇遥控", "Midea落地扇"]},
    {"product_id": "mock_12400003", "title": "戴森AM07 无叶风扇 静音节能 白银色",
     "price": 2990.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "无叶设计/Air Multiplier气流倍增/10档风速/遥控/定时/超静音",
     "sales": "月销4200", "category": "电风扇",
     "aliases": ["戴森无叶风扇", "dyson AM07", "Dyson AM07", "戴森AM07"]},

    # ── 背包/书包 200-600元 ──
    {"product_id": "mock_12500001", "title": "小米 90分 背包 20L 防水商务双肩包",
     "price": 259.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "20L容量/防水面料/15.6寸笔记本仓/USB充电口",
     "sales": "月销3.2万", "category": "背包",
     "aliases": ["小米90分背包", "90分双肩包", "米家背包20L", "90分背包"]},
    {"product_id": "mock_12500002", "title": "新秀丽 Samsonite 双肩包 15.6寸笔记本商务背包",
     "price": 559.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "15.6寸笔记本仓/防水耐磨/TSA密码锁/商务通勤",
     "sales": "月销8500", "category": "背包",
     "aliases": ["新秀丽双肩包", "Samsonite背包", "新秀丽笔记本包", "Samsonite双肩包"]},
    {"product_id": "mock_12500003", "title": "迪卡侬 20L 防水登山背包 户外徒步",
     "price": 199.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "20L/防水涂层/透气背负/登山扣/户外徒步适用",
     "sales": "月销1.5万", "category": "背包",
     "aliases": ["迪卡侬登山包", "迪卡侬背包20L", "DECATHLON背包", "迪卡侬户外背包"]},

    # ── 哑铃 100-600元 ──
    {"product_id": "mock_12600001", "title": "固定哑铃 5kg/对 铸铁镀铬 家用健身",
     "price": 129.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "5kg/对/铸铁镀铬/防滑橡胶手柄/家用入门首选",
     "sales": "月销2.8万", "category": "哑铃",
     "aliases": ["固定哑铃5kg", "铸铁哑铃5kg", "哑铃5公斤", "固定哑铃一对"]},
    {"product_id": "mock_12600002", "title": "可调节哑铃 5-25kg 拨盘式 单只",
     "price": 499.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "5-25kg可调/拨盘快调/9档重量/单只替代整套哑铃",
     "sales": "月销1.2万", "category": "哑铃",
     "aliases": ["可调哑铃", "拨盘哑铃", "可调节哑铃25kg", "智能哑铃"]},
    {"product_id": "mock_12600003", "title": "奥义 六角哑铃 10kg 橡胶包裹 防滚动",
     "price": 159.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "10kg单只/橡胶包裹六角形/防滚防磕地板/电镀钢芯",
     "sales": "月销9600", "category": "哑铃",
     "aliases": ["奥义哑铃", "奥义六角哑铃", "橡胶哑铃10kg", "奥义哑铃10kg"]},

    # ── 瑜伽垫 80-800元 ──
    {"product_id": "mock_12700001", "title": "Keep 瑜伽垫 6mm TPE 防滑 健身垫",
     "price": 129.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "6mm厚/TPE环保材质/双面防滑/183×61cm/附背带",
     "sales": "月销4.5万", "category": "瑜伽垫",
     "aliases": ["Keep瑜伽垫", "Keep健身垫", "Keep6mm瑜伽垫", "Keep运动垫"]},
    {"product_id": "mock_12700002", "title": "lululemon The Mat 5mm 天然橡胶瑜伽垫",
     "price": 798.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "5mm天然橡胶/双面防滑纹理/吸湿排汗/183×66cm",
     "sales": "月销6800", "category": "瑜伽垫",
     "aliases": ["lululemon瑜伽垫", "lululemon The Mat", "露露柠檬瑜伽垫", "lulu瑜伽垫"]},
    {"product_id": "mock_12700003", "title": "奥义 25mm 加厚超宽 TPE 瑜伽垫 舞蹈健身垫",
     "price": 199.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "25mm超厚/TPE材质/80cm加宽版/防滑防潮/附背袋",
     "sales": "月销2.1万", "category": "瑜伽垫",
     "aliases": ["奥义瑜伽垫", "奥义加厚瑜伽垫", "奥义25mm垫", "加厚瑜伽垫25mm"]},

    # ── 洁面产品 50-200元 ──
    {"product_id": "mock_12800001", "title": "芙丽芳丝 氨基酸泡沫洁面乳 150ml",
     "price": 139.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "氨基酸配方/绵密泡沫/温和不紧绷/适合敏感肌/150ml",
     "sales": "月销3.6万", "category": "洁面",
     "aliases": ["芙丽芳丝洁面", "freeplus洁面乳", "芙丽芳丝氨基酸洁面", "芙丽芳丝泡沫洁面"]},
    {"product_id": "mock_12800002", "title": "科颜氏 蜂蜜沐浴洁面膏 170ml",
     "price": 189.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "蜂蜜提取物/深层清洁/滋润保湿/泡沫丰富/170ml",
     "sales": "月销1.8万", "category": "洁面",
     "aliases": ["科颜氏洁面", "Kiehl's洁面膏", "科颜氏蜂蜜洁面", "科颜氏洗面奶"]},
    {"product_id": "mock_12800003", "title": "珂润 氨基酸洁面泡 150ml 敏感肌适用",
     "price": 89.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "氨基酸成分/预制泡沫/弱酸性pH/适合敏感肌/150ml",
     "sales": "月销5.2万", "category": "洁面",
     "aliases": ["珂润洁面", "珂润氨基酸洁面", "Curel洁面泡", "珂润洗面奶"]},

    # ── 运动裤 100-400元 ──
    {"product_id": "mock_12900001", "title": "Nike Pro 紧身训练裤 男款 速干健身裤",
     "price": 299.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "Dri-FIT速干/紧身压缩/弹力面料/跑步健身通用",
     "sales": "月销2.4万", "category": "运动裤",
     "aliases": ["Nike Pro训练裤", "耐克紧身裤", "Nike健身裤", "耐克Pro裤"]},
    {"product_id": "mock_12900002", "title": "lululemon ABC 宽松运动长裤 男款",
     "price": 398.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "防撕裂面料/宽松版型/四向弹力/多口袋设计",
     "sales": "月销9200", "category": "运动裤",
     "aliases": ["lululemon运动裤", "lululemon ABC裤", "露露柠檬运动裤", "lulu运动长裤"]},
    {"product_id": "mock_12900003", "title": "迪卡侬 健身训练裤 速干运动裤 男/女款",
     "price": 129.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "速干面料/弹力腰带/宽松剪裁/健身跑步通用/性价比优选",
     "sales": "月销6.8万", "category": "运动裤",
     "aliases": ["迪卡侬运动裤", "迪卡侬健身裤", "DECATHLON训练裤", "迪卡侬速干裤"]},

    # ── 旅行箱 300-1500元 ──
    {"product_id": "mock_13000001", "title": "新秀丽 Samsonite Omni PC 24寸 TSA锁 银色",
     "price": 1299.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "PC材质/TSA海关锁/24寸托运/双轮万向轮/防刮耐磨",
     "sales": "月销1.2万", "category": "旅行箱",
     "aliases": ["新秀丽Omni", "Samsonite Omni PC", "新秀丽24寸", "新秀丽行李箱"]},
    {"product_id": "mock_13100001", "title": "地平线8号 Washington PC 20寸 铝框拉杆箱",
     "price": 899.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "铝框PC材质/20寸登机箱/TSA锁/静音万向轮/超轻3.2kg",
     "sales": "月销8500", "category": "旅行箱",
     "aliases": ["地平线8号铝框", "地平线8号Washington", "地平线8号20寸", "铝框行李箱"]},
    {"product_id": "mock_13200001", "title": "小米 90分 拉杆箱 24寸 TSA密码锁 深空灰",
     "price": 399.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "PC+ABS材质/TSA密码锁/24寸/静音飞机轮/超大容量",
     "sales": "月销3.5万", "category": "旅行箱",
     "aliases": ["小米90分拉杆箱", "90分行李箱", "小米行李箱24寸", "90分旅行箱"]},

    # ── 摄影装备 100-500元 ──
    {"product_id": "mock_13000002", "title": "乐摄宝 Lowepro Fastpack BP250 II 双肩摄影包",
     "price": 449.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "双肩摄影包/可容单反+15寸笔记本/快取侧袋/防雨罩",
     "sales": "月销6200", "category": "摄影装备",
     "aliases": ["乐摄宝Fastpack", "Lowepro BP250", "乐摄宝双肩包", "摄影双肩包"]},
    {"product_id": "mock_13100002", "title": "思锐 A-3204X 碳纤维三脚架 球形云台套装",
     "price": 499.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "碳纤维管/4节/球形云台/最高160cm/承重10kg/重1.3kg",
     "sales": "月销3800", "category": "摄影装备",
     "aliases": ["思锐A3204X", "思锐碳纤维三脚架", "SIRUI A-3204X", "碳纤维三脚架"]},
    {"product_id": "mock_13200002", "title": "JJC 相机清洁套装 10件套 专业除尘",
     "price": 129.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "气吹+镜头笔+清洁液+擦拭布等10件/单反微单通用/便携收纳包",
     "sales": "月销2.1万", "category": "摄影装备",
     "aliases": ["JJC清洁套装", "相机清洁套装", "镜头清洁套装", "相机清洁10件套"]},

    # ── 猫咪用品 100-600元 ──
    {"product_id": "mock_13000003", "title": "贝适安 猫爬架 落地稳固多层 160cm 麻绳剑麻",
     "price": 399.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "160cm高/多层跳台/剑麻绳柱/顶部豪华窝/超稳底盘",
     "sales": "月销1.5万", "category": "猫咪用品",
     "aliases": ["贝适安猫爬架", "猫爬架160cm", "落地猫爬架", "多层猫爬架"]},
    {"product_id": "mock_13100003", "title": "PETKIT 小佩 全自动电动猫砂盆 Max智能版",
     "price": 599.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "全自动铲屎/APP远程控制/异味隔离/超大容量/适合多猫家庭",
     "sales": "月销8800", "category": "猫咪用品",
     "aliases": ["小佩猫砂盆", "PETKIT自动猫砂盆", "小佩电动猫砂盆", "自动猫砂盆"]},
    {"product_id": "mock_13200003", "title": "猫咪玩具套装 逗猫棒+隧道+响铃球 三件套",
     "price": 99.0, "is_platform_self": True, "rating": 4.6,
     "key_specs": "逗猫棒×2+折叠隧道×1+响铃球×3/安全无毒材质/互动解闷",
     "sales": "月销4.2万", "category": "猫咪用品",
     "aliases": ["猫咪玩具套装", "逗猫棒套装", "猫玩具三件套", "猫咪互动玩具"]},

    # ── 足浴盆 200-600元 ──
    {"product_id": "mock_13000004", "title": "奥克斯 足浴盆 加热按摩 AX-209 全自动",
     "price": 259.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "恒温加热/气泡按摩/滚轮指压/自动保温/可折叠桶身",
     "sales": "月销3.2万", "category": "足浴盆",
     "aliases": ["奥克斯足浴盆", "奥克斯AX-209", "奥克斯泡脚盆", "AX-209足浴器"]},
    {"product_id": "mock_13100004", "title": "欧姆龙 电子血压计 上臂式 HEM-7120 家用",
     "price": 339.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "上臂式/智能加压/心律失常提示/存储60组/大屏显示",
     "sales": "月销5.6万", "category": "足浴盆",
     "aliases": ["欧姆龙血压计", "欧姆龙HEM-7120", "OMRON血压计", "上臂式血压计"]},
    {"product_id": "mock_13200004", "title": "SKG 颈椎按摩器 G7 Pro 热敷款 无线",
     "price": 499.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "4D立体揉捏/热敷42℃/5档力度/无线充电/轻量280g",
     "sales": "月销2.1万", "category": "足浴盆",
     "aliases": ["SKG G7 Pro", "SKG颈椎按摩器", "SKG颈部按摩", "SKG G7Pro按摩仪"]},

    # ── 面霜 100-500元 ──
    {"product_id": "mock_13000005", "title": "雅诗兰黛 特润修护肌透精华霜 50ml 小棕瓶面霜",
     "price": 480.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "ANF酵母精华/夜间修护/保湿紧致/敏感肌可用/50ml",
     "sales": "月销3.8万", "category": "面霜",
     "aliases": ["雅诗兰黛面霜", "雅诗兰黛特润霜", "小棕瓶面霜", "Estee Lauder面霜"]},
    {"product_id": "mock_13100005", "title": "科颜氏 高保湿霜 125ml 超大容量款",
     "price": 399.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "冰川矿泉水/72h保湿/修护屏障/油皮水皮均适/125ml大容量",
     "sales": "月销2.9万", "category": "面霜",
     "aliases": ["科颜氏高保湿霜", "科颜氏面霜125ml", "Kiehl's高保湿霜", "科颜氏保湿霜"]},
    {"product_id": "mock_13200005", "title": "珂润 润浸保湿乳霜 100g 敏感肌专用",
     "price": 129.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "敏感肌可用/神经酰胺保湿/无香无色素/温和滋润/100g",
     "sales": "月销5.1万", "category": "面霜",
     "aliases": ["珂润乳霜", "珂润保湿乳霜", "Curel乳霜", "珂润面霜敏感肌"]},
]

# ─────────────────────────────────────────────
# Matching 专属 Mock 池（按 match_tags 分组）
# ─────────────────────────────────────────────
MATCHING_MOCK_POOL: List[Dict[str, Any]] = [
    # business_formal
    {"product_id": "mock_match_001a", "title": "Calvin Klein 真丝领带 经典酒红",
     "price": 459.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "100%桑蚕丝/7cm经典宽度/酒红配深蓝经典",
     "sales": "月销1800", "match_tags": ["business_formal", "tie"]},
    {"product_id": "mock_match_001b", "title": "海澜之家 商务领带 银灰提花",
     "price": 199.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "银灰色/低调商务/适合正式会议",
     "sales": "月销4500", "match_tags": ["business_formal", "tie"]},
    {"product_id": "mock_match_001c", "title": "BOSS Hugo Boss 皮质公文包 黑色",
     "price": 2980.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "头层牛皮/14寸笔记本仓/商务首选",
     "sales": "月销620", "match_tags": ["business_formal", "bag"]},

    # nordic 北欧风
    {"product_id": "mock_match_002a", "title": "源氏木语 白橡木圆形茶几 北欧实木",
     "price": 1599.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "白橡木实木/圆形直径80cm/原木色北欧风",
     "sales": "月销1200", "match_tags": ["nordic", "coffee_table"]},
    {"product_id": "mock_match_002b", "title": "棉麻混纺地毯 北欧风格 灰白条纹",
     "price": 399.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "棉麻/160×230cm/灰白条纹/北欧简约",
     "sales": "月销3500", "match_tags": ["nordic", "rug"]},
    {"product_id": "mock_match_002c", "title": "MUJI 无印良品 落地灯 白色简约",
     "price": 899.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "亚麻灯罩/三档调光/北欧极简/150cm高",
     "sales": "月销2200", "match_tags": ["nordic", "lamp"]},

    # mid_century 中古风
    {"product_id": "mock_match_003a", "title": "源氏木语 胡桃木Y椅 中古风餐椅 4把装",
     "price": 2680.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "实木胡桃木/Y字靠背/座高45cm/中古经典",
     "sales": "月销800", "match_tags": ["mid_century", "chair"]},
    {"product_id": "mock_match_003b", "title": "黄铜复古台灯 中古风床头灯",
     "price": 328.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "黄铜灯臂/复古E27灯口/中古工业风",
     "sales": "月销1500", "match_tags": ["mid_century", "lamp"]},

    # 3C 配件
    {"product_id": "mock_match_004a", "title": "Apple iPhone 15 Pro Max MagSafe硅胶壳 风暴蓝",
     "price": 449.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "原装MagSafe/液态硅胶/不发黄/官方配色",
     "sales": "月销1.2万", "match_tags": ["iphone15promax", "case", "magsafe"]},
    {"product_id": "mock_match_004b", "title": "PITAKA 凯夫拉纤维超薄壳 iPhone 15 Pro Max",
     "price": 599.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "0.85mm超薄/航空芳纶纤维/裸机手感",
     "sales": "月销3500", "match_tags": ["iphone15promax", "case"]},
    {"product_id": "mock_match_004c", "title": "Apple MagSafe充电器 15W 官方",
     "price": 299.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "MagSafe 15W/官方原装/精准磁吸定位",
     "sales": "月销8500", "match_tags": ["iphone15promax", "charger", "magsafe"]},

    # fitness 健身
    {"product_id": "mock_match_005a", "title": "哑铃 可调节 5-25kg 单只",
     "price": 499.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "可调节5-25kg/拨盘式调重/铸铁+塑料",
     "sales": "月销4500", "match_tags": ["fitness", "dumbbell"]},
    {"product_id": "mock_match_005b", "title": "lululemon 瑜伽垫 5mm 天然橡胶",
     "price": 899.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "天然橡胶/5mm/防滑纹理/183×61cm",
     "sales": "月销1800", "match_tags": ["fitness", "yoga_mat"]},
    {"product_id": "mock_match_005c", "title": "SPRI 弹力带训练套装 5条装",
     "price": 189.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "5种阻力等级/天然乳胶/附收纳袋+手柄",
     "sales": "月销6200", "match_tags": ["fitness", "resistance_band"]},

    # treadmill 跑步机搭配
    {"product_id": "mock_match_006a", "title": "澳洲狮 运动减震垫 跑步机专用 185×90cm",
     "price": 299.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "高密度EVA/185×90cm/减震隔音/防滑底面",
     "sales": "月销2.1万", "match_tags": ["treadmill", "mat"]},
    {"product_id": "mock_match_006b", "title": "艾美特 塔扇落地扇 静音循环 运动房用",
     "price": 399.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "塔式/9档风速/45dB静音/8小时定时/遥控",
     "sales": "月销1.5万", "match_tags": ["treadmill", "fan"]},
    {"product_id": "mock_match_006c", "title": "乐扣乐扣 运动水壶 600ml 大容量 Tritan材质",
     "price": 89.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "Tritan材质/600ml/一键弹盖/防漏/耐高温",
     "sales": "月销3.8万", "match_tags": ["treadmill", "bottle", "fitness"]},

    # coffee 咖啡机搭配
    {"product_id": "mock_match_007a", "title": "Fellow Ode Gen2 电动磨豆机 锥形刀盘",
     "price": 1899.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "83mm锥形钢刀/11档研磨度/单次剂量/低速静音",
     "sales": "月销3200", "match_tags": ["coffee", "grinder"]},
    {"product_id": "mock_match_007b", "title": "物生物 马克杯 350ml 陶瓷 带盖带勺",
     "price": 59.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "陶瓷/350ml/配硅胶盖+不锈钢勺/多色可选",
     "sales": "月销5.6万", "match_tags": ["coffee", "mug"]},
    {"product_id": "mock_match_007c", "title": "Cafiza 咖啡机清洁片 除垢片 10片装",
     "price": 39.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "10片装/适配全自动半自动/深度除垢/无味安全",
     "sales": "月销2.9万", "match_tags": ["coffee", "cleaning"]},

    # camera 相机搭配
    {"product_id": "mock_match_008a", "title": "思锐 A1205 铝合金三脚架 轻量",
     "price": 599.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "铝合金/最高165cm/承重8kg/单重1.4kg/球形云台",
     "sales": "月销8500", "match_tags": ["camera", "tripod"]},
    {"product_id": "mock_match_008b", "title": "乐摄宝 Fastpack 双肩摄影包 20L",
     "price": 799.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "20L/侧开快取/13寸笔记本仓/防雨罩/TSA锁",
     "sales": "月销4200", "match_tags": ["camera", "bag"]},
    {"product_id": "mock_match_008c", "title": "JJC 相机清洁套装 气吹+镜头笔+清洁布",
     "price": 69.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "气吹/镜头笔/超细纤维清洁布/清洁液/7件套",
     "sales": "月销1.2万", "match_tags": ["camera", "cleaning"]},

    # study_room 书房搭配
    {"product_id": "mock_match_009a", "title": "明基 WiT MindDuo 护眼台灯 可调色温",
     "price": 899.0, "is_platform_self": True, "rating": 4.9,
     "key_specs": "AI感光调光/2700-6500K色温/无频闪/Ra97高显色",
     "sales": "月销1.8万", "match_tags": ["study_room", "lamp"]},
    {"product_id": "mock_match_009b", "title": "乐歌 升降桌 电动 140×70cm 双电机",
     "price": 2499.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "双电机/140×70cm/60-125cm升降/防碰撞/USB插口",
     "sales": "月销9600", "match_tags": ["study_room", "desk"]},
    {"product_id": "mock_match_009c", "title": "源氏木语 书架 落地 简约 5层 钢木结构",
     "price": 799.0, "is_platform_self": True, "rating": 4.7,
     "key_specs": "钢木结合/5层/180cm高/承重60kg/组装简单",
     "sales": "月销6800", "match_tags": ["study_room", "shelf"]},

    # iphone_accessories iPhone配件扩充
    {"product_id": "mock_match_010a", "title": "倍思 20W PD快充头 TypeC 折叠",
     "price": 69.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "20W PD/TypeC/折叠插脚/兼容iPhone/GaN氮化镓",
     "sales": "月销8.2万", "match_tags": ["iphone_accessories", "charger"]},
    {"product_id": "mock_match_010b", "title": "小米 10000mAh 磁吸充电宝 MagSafe",
     "price": 199.0, "is_platform_self": True, "rating": 4.8,
     "key_specs": "MagSafe磁吸/10000mAh/15W无线/22.5W有线/轻薄",
     "sales": "月销3.5万", "match_tags": ["iphone_accessories", "power_bank", "magsafe"]},
    {"product_id": "mock_match_010c", "title": "苹果 AirPods 收纳包 EVA硬壳",
     "price": 49.0, "is_platform_self": True, "rating": 4.6,
     "key_specs": "EVA硬壳/防压防摔/附挂钩/适配AirPods全系列",
     "sales": "月销4.1万", "match_tags": ["iphone_accessories", "airpods_case"]},
]

# ── 品类关键词映射（用于 query 模糊匹配的辅助类目 ）
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "手机": ["手机", "phone", "iphone", "华为", "小米", "vivo", "oppo", "三星"],
    "空气净化器": ["净化器", "空气净化", "除甲醛", "除霾", "pm2.5", "hepa"],
    "跑步鞋": ["跑步鞋", "跑鞋", "running", "马拉松", "运动鞋"],
    "颈部按摩仪": ["按摩仪", "颈椎", "颈部", "肩颈", "massage"],
    "扫地机": ["扫地机", "扫地", "拖地", "扫拖", "robot", "扫地机器人"],
    "椅子": ["椅子", "座椅", "工学椅", "人体工学", "办公椅", "电脑椅"],
    "耳机": ["耳机", "耳塞", "降噪耳机", "蓝牙耳机", "tws", "airpods", "索尼", "漫步者"],
    "显示器": ["显示器", "屏幕", "monitor", "2k", "4k", "游戏显示"],
    "炒锅": ["炒锅", "锅", "不粘锅", "铸铁锅", "平底锅", "wok"],
    "保温杯": ["保温杯", "水杯", "不锈钢杯", "膳魔师", "虎牌", "咖啡杯"],
    "咖啡机": ["咖啡机", "胶囊咖啡", "全自动咖啡", "意式咖啡机", "coffee"],
    "跑步机": ["跑步机", "跑台", "健步机", "treadmill"],
    "投影仪": ["投影仪", "投影机", "家用投影", "激光投影", "projector"],
    "键盘": ["键盘", "机械键盘", "无线键盘", "keyboard"],
    "鼠标": ["鼠标", "无线鼠标", "游戏鼠标", "mouse", "滚轮", "卡顿"],
    "护肤精华": ["精华", "精华液", "小棕瓶", "小黑瓶", "护肤品", "serum"],
    "洗碗机": ["洗碗机", "嵌入式洗碗", "台式洗碗", "dishwasher"],
    "空调": ["空调", "挂机", "变频空调", "冷暖空调", "air conditioner"],
    "婴儿推车": ["婴儿推车", "推车", "溜娃车", "stroller", "童车"],
    "台灯": ["台灯", "护眼灯", "学习灯", "屏幕挂灯", "ScreenBar", "desk lamp"],
    "电动牙刷": ["电动牙刷", "飞利浦牙刷", "欧乐B", "声波牙刷", "智能牙刷"],
    "充电宝": ["充电宝", "移动电源", "磁吸充电宝", "快充充电宝", "超薄充电宝"],
    "洗衣机": ["洗衣机", "滚筒洗衣机", "洗烘一体", "波轮洗衣机"],
    "电热水壶": ["热水壶", "电热水壶", "烧水壶", "快速热水壶", "kettle"],
    "电风扇": ["风扇", "落地扇", "电风扇", "无叶风扇", "台式风扇", "循环扇"],
    "背包": ["背包", "书包", "双肩包", "笔记本包", "旅行背包", "登山包"],
    "哑铃": ["哑铃", "可调哑铃", "固定哑铃", "哑铃套装", "健身哑铃"],
    "瑜伽垫": ["瑜伽垫", "健身垫", "运动垫", "防滑垫", "lululemon垫"],
    "洁面": ["洁面", "洗面奶", "氨基酸洁面", "洁面乳", "洁颜"],
    "运动裤": ["运动裤", "健身裤", "训练裤", "瑜伽裤", "速干裤", "紧身裤"],
    "旅行箱": ["旅行箱", "拉杆箱", "行李箱", "登机箱", "TSA锁", "铝框行李箱"],
    "摄影装备": ["三脚架", "摄影包", "相机包", "清洁套装", "碳纤维三脚架"],
    "绘画用品": ["画板", "颜料", "画笔", "素描本", "水彩", "丙烯", "绘画", "美术"],
    "猫咪用品": ["猫爬架", "猫砂盆", "猫玩具", "自动猫砂盆", "猫咪用品"],
    "足浴盆": ["足浴盆", "泡脚桶", "足浴器", "泡脚"],
    "面霜": ["面霜", "保湿霜", "乳霜", "润肤霜", "雅诗兰黛面霜", "科颜氏面霜"],
}


class SkuRecallShopping:
    """
    SkuRecallShopping 工具。

    对应真实项目的 sku_recall_hub.sku_recall + scenario_recall_hub.scenario_related_recall。

    支持三种召回模式（通过 params 字段区分）：
    1. 普通搜索：{"query": "...", "min_price": 0, "max_price": 2000}
    2. 精确匹配（sku_comp）：{"skus": ["小米14 Pro", "华为Mate60"]}
    3. 搭配购物（matching）：{"query": "...", "filters": {"style": "nordic"}}
    """

    NAME = "SkuRecallShopping"

    def __call__(self, ctx: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._mock_call(params)

    def _mock_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # ── 精确 SKU 匹配模式（sku_comp 场景）──
        skus = params.get("skus", [])
        if skus:
            return self._exact_match(skus)

        # ── 搭配模式（matching 场景，filters.style）──
        filters = params.get("filters", {})
        style = filters.get("style", "")
        if style:
            return self._matching_call(params.get("query", ""), style, filters)

        # ── 普通搜索模式 ──
        return self._search_call(params)

    def _search_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """普通搜索：按 query + 价格范围过滤 MOCK_PRODUCT_POOL"""
        query = params.get("query", "").lower()
        min_p = float(params.get("min_price", 0) or 0)
        max_p = float(params.get("max_price", 0) or 0)
        page_size = int(params.get("page_size", 3))
        exclude = [e.lower() for e in params.get("exclude_skus", [])]

        pool = list(MOCK_PRODUCT_POOL)

        # 价格过滤
        if max_p > 0:
            pool = [p for p in pool if p["price"] <= max_p]
        if min_p > 0:
            pool = [p for p in pool if p["price"] >= min_p]

        # 排除指定商品
        if exclude:
            pool = [p for p in pool
                    if not any(e in p["title"].lower() for e in exclude)]

        # 关键词过滤：先尝试品类关键词精确匹配，再做 title/specs 模糊匹配
        if query:
            query_lower = query.lower()
            # 第一优先级：品类关键词匹配（更精确）
            cat_matched = []
            for cat, kws in _CATEGORY_KEYWORDS.items():
                if any(kw.lower() in query_lower for kw in kws):
                    cat_matched = [p for p in pool if p.get("category") == cat]
                    if cat_matched:
                        break
            if cat_matched:
                pool = cat_matched
            else:
                # 第二优先级：title + key_specs 模糊匹配
                matched = [
                    p for p in pool
                    if any(kw in p["title"].lower() or kw in p["key_specs"].lower()
                           for kw in query_lower.split())
                ]
                pool = matched if matched else pool

        products = pool[:page_size]
        if not products:
            return {"status": "NO_RESULT", "products": []}

        return {
            "status": "SUCCESS",
            "products": [self._slim(p) for p in products],
        }

    def _exact_match(self, sku_names: List[str]) -> Dict[str, Any]:
        """精确名称匹配（sku_comp 场景：skus=["商品A", "商品B"]）"""
        products = []
        used_ids: set = set()
        for name in sku_names:
            name_lower = name.lower()
            # 先尝试精确匹配 title
            found = None
            for p in MOCK_PRODUCT_POOL:
                if name_lower in p["title"].lower() and p["product_id"] not in used_ids:
                    found = p
                    break
            # 再尝试匹配 aliases
            if found is None:
                for p in MOCK_PRODUCT_POOL:
                    if p["product_id"] in used_ids:
                        continue
                    for alias in p.get("aliases", []):
                        if name_lower in alias.lower() or alias.lower() in name_lower:
                            found = p
                            break
                    if found:
                        break
            # 再尝试品类匹配
            if found is None:
                for cat, kws in _CATEGORY_KEYWORDS.items():
                    if any(kw in name_lower for kw in kws):
                        for p in MOCK_PRODUCT_POOL:
                            if p.get("category") == cat and p["product_id"] not in used_ids:
                                found = p
                                break
                        if found:
                            break
            # 最后取第一个未使用的
            if found is None:
                for p in MOCK_PRODUCT_POOL:
                    if p["product_id"] not in used_ids:
                        found = p
                        break
            if found:
                products.append(found)
                used_ids.add(found["product_id"])

        return {
            "status": "SUCCESS" if products else "NO_RESULT",
            "products": [self._slim(p) for p in products],
        }

    def _matching_call(self, query: str, style: str,
                       filters: Dict[str, Any]) -> Dict[str, Any]:
        """搭配购物（matching 场景）：从 MATCHING_MOCK_POOL 按 style/match_tags 过滤"""
        pool = list(MATCHING_MOCK_POOL)

        # 中文关键词 → match_tag 映射
        style_map: Dict[str, str] = {
            # 已有场景
            "商务": "business_formal",
            "正装": "business_formal",
            "北欧": "nordic",
            "北欧风": "nordic",
            "中古": "mid_century",
            "复古": "mid_century",
            "iphone": "iphone15promax",
            "苹果手机": "iphone15promax",
            "健身": "fitness",
            "运动": "fitness",
            # 新增场景
            "跑步机": "treadmill",
            "treadmill": "treadmill",
            "咖啡": "coffee",
            "咖啡机": "coffee",
            "coffee": "coffee",
            "相机": "camera",
            "摄影": "camera",
            "camera": "camera",
            "书房": "study_room",
            "书桌": "study_room",
            "study": "study_room",
            "iphone配件": "iphone_accessories",
            "苹果配件": "iphone_accessories",
            "手机配件": "iphone_accessories",
        }

        style_lower = style.lower()
        # 先尝试通过 style_map 将中文/别名转换为标准 tag
        resolved_tag = style_map.get(style_lower, style_lower)
        # 也尝试用 query 中的关键词做补充映射（仅当 style 本身在 style_map 中找不到时）
        if resolved_tag == style_lower:
            for kw, tag in style_map.items():
                if kw in query.lower():
                    resolved_tag = tag
                    break

        # 按 match_tags 过滤
        matched = [p for p in pool if resolved_tag in p.get("match_tags", [])]

        # 按 query 关键词进一步过滤
        if query and matched:
            kws = query.lower().split()
            refined = [p for p in matched
                       if any(kw in p["title"].lower() or kw in p["key_specs"].lower()
                              for kw in kws)]
            if refined:
                matched = refined

        # fallback 到普通池
        if not matched:
            matched = [MATCHING_MOCK_POOL[0], MATCHING_MOCK_POOL[1], MATCHING_MOCK_POOL[2]]

        products = matched[:int(filters.get("max_count", 4))]
        return {
            "status": "SUCCESS",
            "products": [self._slim(p) for p in products],
        }

    @staticmethod
    def _slim(p: Dict[str, Any]) -> Dict[str, Any]:
        """只保留 SFT 格式需要的字段"""
        return {k: p[k] for k in
                ["product_id", "title", "price", "is_platform_self", "rating", "key_specs", "sales"]
                if k in p}
