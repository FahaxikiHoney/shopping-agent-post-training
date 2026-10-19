# -*- coding: utf-8 -*-
import json

def make_traj(tid, sc, cat, focus, query, tool_input, products, final_content, card_reasons,
              tool_name="SkuRecallShopping", multi_turn=False, history=None):
    cards = [{"card_id": p["product_id"], "display_price": p["price"], "reason": r}
             for p, r in zip(products, card_reasons)]
    return {
        "trajectory_id": tid,
        "scenario_type": sc,
        "category": cat,
        "quality_label": "good",
        "training_focus": focus,
        "is_multi_turn": multi_turn,
        "conversation_history": history or [],
        "user_query": query,
        "thinking": "分析" + focus,
        "steps": [
            {
                "step_id": 1,
                "step_type": "tool_call",
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_output": {"status": "SUCCESS", "products": products},
                "error_type": None
            },
            {
                "step_id": 2,
                "step_type": "final_response",
                "content": final_content,
                "product_cards": cards
            }
        ],
        "final_response": final_content,
        "eval_score": 1.0,
        "sft_source": "claude_local_v1"
    }


trajectories = []

# ------------------------------------------------------------------ #
# 1. similar_rec: 电视推荐 -> 追问更大屏
# ------------------------------------------------------------------ #
t1 = make_traj(
    tid="sft_multi_001",
    sc="similar_rec",
    cat="家用电器",
    focus="多轮追问大屏尺寸偏好，结合上下文召回55寸以上电视",
    query="有没有更大屏的？65寸或者75寸那种",
    tool_input={
        "keywords": "大屏电视 65寸 75寸 4K",
        "category": "电视",
        "min_size_inch": 65,
        "sort_by": "sales_desc"
    },
    products=[
        {"product_id": "TV_65_001", "name": "海信 65E3H 65寸 4K QLED智慧屏", "price": 2799.00,
         "brand": "海信", "specs": "65寸 4K QLED 120Hz"},
        {"product_id": "TV_75_002", "name": "小米电视 S75 75寸 Mini LED", "price": 4499.00,
         "brand": "小米", "specs": "75寸 Mini LED 144Hz"},
        {"product_id": "TV_75_003", "name": "TCL 75C735 75寸 4K量子点", "price": 3999.00,
         "brand": "TCL", "specs": "75寸 QLED 120Hz 4K"}
    ],
    final_content=(
        "您上一轮看的是55寸电视，现在想换更大屏幕，我给您找了65寸和75寸的热销款：\n\n"
        "1. 海信 65E3H（65寸 QLED 4K）—— 2799元，120Hz高刷，画质细腻，适合客厅日常观影。\n"
        "2. TCL 75C735（75寸 量子点 4K）—— 3999元，色域宽广，大屏震撼感强，性价比突出。\n"
        "3. 小米 S75（75寸 Mini LED）—— 4499元，144Hz旗舰屏，局部控光出色，游戏与电影两用。\n\n"
        "如果客厅在15平米以上，推荐直接上75寸，沉浸感更好。需要帮您比较某两款吗？"
    ),
    card_reasons=[
        "65寸入门大屏，海信品质稳定，2799元高性价比",
        "75寸量子点旗舰，TCL主力款，3999元值得入手",
        "75寸Mini LED，小米高刷旗舰，游戏观影双优"
    ],
    multi_turn=True,
    history=[
        {"role": "user", "content": "给我推荐一款电视吧"},
        {"role": "assistant", "content": "好的！请问您大概预算多少，客厅大小怎样？一般推荐55寸左右的4K智能电视，比如海信55E3H，画质不错，售价1799元。"}
    ]
)
trajectories.append(t1)

# ------------------------------------------------------------------ #
# 2. sku_comp: 手机推荐 -> 预算限3000
# ------------------------------------------------------------------ #
t2 = make_traj(
    tid="sft_multi_002",
    sc="sku_comp",
    cat="手机数码",
    focus="多轮预算约束，过滤3000元以下手机并做性价比对比",
    query="我预算只有3000，帮我在这个价位里选一个最划算的",
    tool_input={
        "keywords": "智能手机 3000以下",
        "category": "手机",
        "max_price": 3000,
        "sort_by": "value_score_desc"
    },
    products=[
        {"product_id": "PHONE_001", "name": "Redmi Note 13 Pro+ 5G 12+256GB", "price": 2399.00,
         "brand": "红米", "specs": "骁龙7s Gen2 200MP主摄 67W快充"},
        {"product_id": "PHONE_002", "name": "荣耀90 5G 12+256GB", "price": 2299.00,
         "brand": "荣耀", "specs": "骁龙7 Gen1 200MP主摄 66W快充"},
        {"product_id": "PHONE_003", "name": "一加 Ace2V 16+256GB", "price": 2799.00,
         "brand": "一加", "specs": "天玑9000 150W超闪充 1.5K直屏"}
    ],
    final_content=(
        "明白，您预算3000以内，我从之前提到的旗舰方向给您筛出3款高性价比机型：\n\n"
        "1. 荣耀90（2299元）—— 200MP超清主摄，骁龙7 Gen1，日常拍照和流畅度都很扎实，最省钱。\n"
        "2. Redmi Note 13 Pro+（2399元）—— 同样200MP，67W快充，IP68防水，综合表现均衡。\n"
        "3. 一加 Ace2V（2799元）—— 天玑9000旗舰芯，150W超闪充，游戏性能最强，接近3000上限但值得加一点。\n\n"
        "如果注重性能游戏选一加，注重拍照省钱选荣耀90。您平时用手机主要做什么？"
    ),
    card_reasons=[
        "2299元200MP拍照旗舰，荣耀90性价比之选",
        "2399元IP68防水+200MP，红米综合均衡",
        "2799元天玑9000+150W超闪，一加性能旗舰"
    ],
    multi_turn=True,
    history=[
        {"role": "user", "content": "我想买一部新手机，拍照要好，性能也不能太差"},
        {"role": "assistant", "content": "了解！高拍照+高性能的话，华为Pura70、小米14这类旗舰机表现很出色，不过价格在4000-5000元区间。您有大概的预算范围吗？"}
    ]
)
trajectories.append(t2)

# ------------------------------------------------------------------ #
# 3. bundle: 礼物推荐 -> 送给男朋友
# ------------------------------------------------------------------ #
t3 = make_traj(
    tid="sft_multi_003",
    sc="bundle",
    cat="礼品",
    focus="多轮明确收礼人性别，针对男性偏好做礼品组合推荐",
    query="是送给男朋友的，他平时喜欢运动，预算500以内",
    tool_input={
        "keywords": "男士运动礼物套装 500以内",
        "category": "礼品",
        "gender": "male",
        "max_price": 500,
        "tags": ["运动", "礼盒"]
    },
    products=[
        {"product_id": "GIFT_M_001", "name": "耐克运动礼盒（护腕+跑步袜+水壶）", "price": 299.00,
         "brand": "耐克", "specs": "护腕x2 跑步袜x3双 500ml水壶"},
        {"product_id": "GIFT_M_002", "name": "迪卡侬健身礼包（瑜伽垫+跳绳+弹力带）", "price": 199.00,
         "brand": "迪卡侬", "specs": "6mm瑜伽垫 速跳绳 三级弹力带"},
        {"product_id": "GIFT_M_003", "name": "小米运动手环8 Pro 礼盒装", "price": 399.00,
         "brand": "小米", "specs": "血氧心率睡眠监测 14天续航 防水50米"}
    ],
    final_content=(
        "原来是送男朋友的，他又喜欢运动，那礼物方向就很清晰了！500以内有三个好选择：\n\n"
        "1. 耐克运动礼盒（299元）—— 护腕+跑步袜+水壶，实用组合，品牌有面子，适合跑步健身。\n"
        "2. 迪卡侬健身礼包（199元）—— 瑜伽垫+跳绳+弹力带，居家健身全套，价格最亲民。\n"
        "3. 小米运动手环8 Pro 礼盒（399元）—— 科技感强，心率血氧监测，运动男生很喜欢戴，拆礼物惊喜感最高。\n\n"
        "他是偏跑步户外还是健身房？如果户外跑步推荐耐克礼盒，居家健身推荐迪卡侬，喜欢数码的话小米手环最讨喜。"
    ),
    card_reasons=[
        "耐克品牌运动三件套，299元有品质有面子",
        "迪卡侬健身全套199元，居家运动性价比最高",
        "小米手环8 Pro礼盒399元，科技感强适合运动男士"
    ],
    multi_turn=True,
    history=[
        {"role": "user", "content": "我想买个礼物，不知道送什么好"},
        {"role": "assistant", "content": "送礼要看收礼人的喜好和关系哦，请问是送给谁的？朋友、家人还是另一半？大概预算是多少？"}
    ]
)
trajectories.append(t3)

# ------------------------------------------------------------------ #
# 4. similar_rec: 跑步鞋 -> 脚宽穿窄的夹脚
# ------------------------------------------------------------------ #
t4 = make_traj(
    tid="sft_multi_004",
    sc="similar_rec",
    cat="运动户外",
    focus="多轮脚型反馈，召回宽楦跑步鞋解决脚宽夹脚问题",
    query="我脚宽，穿上次推荐的那双有点夹脚，有没有宽楦版的",
    tool_input={
        "keywords": "宽楦跑步鞋 宽脚 EE宽度",
        "category": "跑步鞋",
        "foot_width": "wide",
        "tags": ["宽楦", "宽脚型"]
    },
    products=[
        {"product_id": "SHOE_W_001", "name": "New Balance 1080v13 宽楦 2E款", "price": 1099.00,
         "brand": "New Balance", "specs": "2E宽楦 氮气中底 缓震型"},
        {"product_id": "SHOE_W_002", "name": "亚瑟士 GEL-NIMBUS 25 宽楦", "price": 1299.00,
         "brand": "亚瑟士", "specs": "2E宽楦 GEL缓震 适合宽脚长距离"},
        {"product_id": "SHOE_W_003", "name": "Brooks Ghost 15 宽楦版", "price": 899.00,
         "brand": "Brooks", "specs": "2E宽楦 DNA LOFT缓震 舒适耐磨"}
    ],
    final_content=(
        "非常感谢您的反馈！上次推荐的是标准楦型，对宽脚确实不友好，这次我专门给您找宽楦（2E）版跑步鞋：\n\n"
        "1. Brooks Ghost 15 宽楦（899元）—— 2E宽楦，DNA LOFT软底，宽脚日常跑步最舒适，口碑极好。\n"
        "2. New Balance 1080v13 宽楦（1099元）—— 经典2E型号，NB一向对宽脚友好，氮气中底缓震出色。\n"
        "3. 亚瑟士 GEL-NIMBUS 25 宽楦（1299元）—— 2E宽楦旗舰缓震款，适合长距离，脚感最宽松。\n\n"
        "这三款都是真正的宽楦设计，不会出现夹脚情况。您平时跑几公里？距离不同推荐也略有差异。"
    ),
    card_reasons=[
        "Brooks Ghost 15宽楦2E，宽脚首选舒适跑鞋",
        "NB 1080v13宽楦，经典2E氮气中底缓震好",
        "亚瑟士GEL-NIMBUS25宽楦，长距离宽脚旗舰"
    ],
    multi_turn=True,
    history=[
        {"role": "user", "content": "帮我推荐一双跑步鞋，主要是日常慢跑用"},
        {"role": "assistant", "content": "好的！日常慢跑推荐缓震型跑鞋，比如Nike Pegasus 41（799元）或者Adidas Ultraboost 22（999元），两款都很受欢迎，舒适度高。"}
    ]
)
trajectories.append(t4)

# ------------------------------------------------------------------ #
# 5. repurchase: 查历史订单 -> 帮我再买一箱
# ------------------------------------------------------------------ #
t5 = make_traj(
    tid="sft_multi_005",
    sc="repurchase",
    cat="食品饮料",
    focus="多轮复购场景，识别历史订单商品并快速完成一键回购",
    query="帮我再买一箱，和上次一样的规格",
    tool_input={
        "user_action": "repurchase",
        "order_reference": "last_order",
        "product_id": "WATER_001",
        "quantity": 1,
        "spec": "550ml*24瓶"
    },
    products=[
        {"product_id": "WATER_001", "name": "农夫山泉天然矿泉水 550ml*24瓶", "price": 39.90,
         "brand": "农夫山泉", "specs": "550ml*24瓶 天然矿泉水"},
    ],
    final_content=(
        "找到您上次的订单记录了！您之前购买的是农夫山泉天然矿泉水 550ml*24瓶，单价39.90元。\n\n"
        "已为您准备好同款同规格的复购链接，点击下方商品卡片即可一键加购。\n\n"
        "目前库存充足，预计明天可以送达。需要我帮您直接下单吗？或者您想修改数量（比如买2箱）？"
    ),
    card_reasons=[
        "与上次订单完全相同的农夫山泉550ml*24瓶，一键复购"
    ],
    tool_name="SkuRepurchaseRecall",
    multi_turn=True,
    history=[
        {"role": "user", "content": "我上次买的矿泉水是哪个牌子的，多少钱？"},
        {"role": "assistant", "content": "已查到您上次于3天前购买了农夫山泉天然矿泉水 550ml*24瓶，实付39.90元，已签收。请问有什么需要帮忙的吗？"}
    ]
)
trajectories.append(t5)

# ------------------------------------------------------------------ #
# 6. sku_comp: 对比两款冰箱 -> 哪个更省电
# ------------------------------------------------------------------ #
t6 = make_traj(
    tid="sft_multi_006",
    sc="sku_comp",
    cat="家用电器",
    focus="多轮追问能耗指标，精准对比两款冰箱的年耗电量和能效等级",
    query="你上面说的那两款，哪个更省电？我最在意电费",
    tool_input={
        "keywords": "冰箱能效对比",
        "category": "冰箱",
        "product_ids": ["FRIDGE_001", "FRIDGE_002"],
        "compare_fields": ["energy_class", "annual_kwh", "compressor_type"]
    },
    products=[
        {"product_id": "FRIDGE_001", "name": "美的 BCD-516WSGPZM 516L 一级能效", "price": 3299.00,
         "brand": "美的", "specs": "516L 一级能效 变频 年耗电约270度"},
        {"product_id": "FRIDGE_002", "name": "海尔 BCD-470WDPD 470L 一级能效", "price": 2999.00,
         "brand": "海尔", "specs": "470L 一级能效 变频 年耗电约220度"}
    ],
    final_content=(
        "针对您最关心的省电问题，我来重点对比一下这两款：\n\n"
        "| 指标 | 美的 516L | 海尔 470L |\n"
        "|------|---------|----------|\n"
        "| 能效等级 | 一级 | 一级 |\n"
        "| 年耗电量 | 约270度 | 约220度 |\n"
        "| 压缩机 | 变频 | 变频 |\n"
        "| 容量 | 516L | 470L |\n\n"
        "结论：海尔470L更省电，年耗电约220度，比美的516L少约50度，按0.6元/度算，一年能省约30元。\n\n"
        "不过美的容量更大（516L vs 470L），如果家里人多储量需求大，多出的电费差也不大。您家里几口人用？"
    ),
    card_reasons=[
        "美的516L一级能效，年耗电约270度，大容量之选",
        "海尔470L一级能效，年耗电约220度，更省电推荐"
    ],
    multi_turn=True,
    history=[
        {"role": "user", "content": "帮我对比一下美的516L和海尔470L这两款冰箱"},
        {"role": "assistant", "content": "好的！美的BCD-516L售价3299元，容量更大；海尔BCD-470L售价2999元，价格更实惠。两款都是一级能效变频冰箱，外观和保鲜技术各有侧重。您最看重哪方面的性能？"}
    ]
)
trajectories.append(t6)

# ------------------------------------------------------------------ #
# 7. matching: 推荐了书桌 -> 需要配什么椅子
# ------------------------------------------------------------------ #
t7 = make_traj(
    tid="sft_multi_007",
    sc="matching",
    cat="家具家居",
    focus="多轮搭配场景，基于已选书桌风格推荐配套椅子",
    query="我已经选好那张书桌了，需要配什么椅子比较合适？",
    tool_input={
        "keywords": "北欧风书桌椅 人体工学椅 配套",
        "category": "椅子",
        "match_style": "北欧简约",
        "match_product_id": "DESK_001",
        "tags": ["书桌椅", "人体工学"]
    },
    products=[
        {"product_id": "CHAIR_001", "name": "林氏家居 北欧实木书桌椅 LS073", "price": 699.00,
         "brand": "林氏家居", "specs": "实木腿 布艺坐垫 可调节高度 北欧风"},
        {"product_id": "CHAIR_002", "name": "西昊 M57 人体工学电脑椅", "price": 999.00,
         "brand": "西昊", "specs": "腰托可调 3D扶手 网布透气 久坐不累"},
        {"product_id": "CHAIR_003", "name": "网易严选 原木风高背书椅", "price": 599.00,
         "brand": "网易严选", "specs": "白橡木腿 棉麻坐垫 北欧风 承重150kg"}
    ],
    final_content=(
        "恭喜选好了书桌！您上次选的是北欧简约风的实木书桌，给您搭配几款风格匹配的椅子：\n\n"
        "1. 网易严选原木风高背书椅（599元）—— 白橡木腿与北欧书桌风格最搭，棉麻坐垫舒适，颜值高。\n"
        "2. 林氏家居北欧书桌椅 LS073（699元）—— 同为北欧实木腿设计，与您的桌子是同系列风格，搭配最协调。\n"
        "3. 西昊 M57 人体工学椅（999元）—— 如果书桌主要用于工作学习，久坐需要腰托支撑，这款功能性最强。\n\n"
        "纯颜值搭配选网易严选或林氏，长时间伏案工作建议西昊M57保护腰椎。您桌子主要用来做什么？"
    ),
    card_reasons=[
        "网易严选白橡木书椅，北欧风格搭配书桌颜值满分",
        "林氏LS073同系列北欧实木椅，与书桌搭配最协调",
        "西昊M57人体工学椅，久坐工作护腰首选"
    ],
    multi_turn=True,
    history=[
        {"role": "user", "content": "帮我推荐一张书桌，北欧风格的，预算1500以内"},
        {"role": "assistant", "content": "北欧风实木书桌推荐林氏家居LS152W（1299元），白色实木腿+原木桌面，颜值很高；或者网易严选1.2米实木书桌（899元），简洁耐看。两款都在您预算内，请问书房大小怎样？"}
    ]
)
trajectories.append(t7)

# ------------------------------------------------------------------ #
# 8. similar_rec: 保温杯 -> 能装进包的小一点
# ------------------------------------------------------------------ #
t8 = make_traj(
    tid="sft_multi_008",
    sc="similar_rec",
    cat="生活用品",
    focus="多轮尺寸约束，从大容量保温杯切换为便携小容量款",
    query="能装进包里的小一点的，300ml左右的就够了",
    tool_input={
        "keywords": "迷你保温杯 便携 300ml",
        "category": "保温杯",
        "max_capacity_ml": 350,
        "min_capacity_ml": 250,
        "tags": ["便携", "小容量", "入包"]
    },
    products=[
        {"product_id": "CUP_S_001", "name": "象印 SM-WA30 300ml 便携保温杯", "price": 229.00,
         "brand": "象印", "specs": "300ml 真空断热 轻量132g 直径6.5cm"},
        {"product_id": "CUP_S_002", "name": "膳魔师 THMF-302 300ml 口袋杯", "price": 189.00,
         "brand": "膳魔师", "specs": "300ml 超细身设计 直径5.8cm 保温12h"},
        {"product_id": "CUP_S_003", "name": "虎牌 MMZ-A030 300ml 轻量保温杯", "price": 249.00,
         "brand": "虎牌", "specs": "300ml 119g超轻 直径6.2cm 保温18h"}
    ],
    final_content=(
        "明白了！您之前看的是500ml大杯，便携性差一些。专门为您找了300ml左右能塞进包里的款式：\n\n"
        "1. 膳魔师 THMF-302（189元）—— 杯身直径仅5.8cm，细长设计，任何背包都能装下，保温12小时。\n"
        "2. 象印 SM-WA30（229元）—— 300ml重量只有132g，6.5cm直径，象印真空技术保温效果扎实。\n"
        "3. 虎牌 MMZ-A030（249元）—— 119g超轻量，是这三款中最轻的，保温18小时最持久，通勤上学首选。\n\n"
        "这三款装A4书包、手提包都完全没问题。您平时带着跑步/通勤/上学用？可以进一步帮您缩小选择。"
    ),
    card_reasons=[
        "膳魔师300ml细身杯直径5.8cm，最容易塞进各类包袋",
        "象印300ml轻量真空保温杯，品质稳定口碑好",
        "虎牌300ml超轻119g，保温18小时，通勤最佳"
    ],
    multi_turn=True,
    history=[
        {"role": "user", "content": "推荐一个保温杯，每天上班带着用"},
        {"role": "assistant", "content": "上班通勤推荐500ml的保温杯，容量够用，比如虎牌MHT-A050（399元）或者象印SM-SA48（349元），保温24小时，品质很靠谱！"}
    ]
)
trajectories.append(t8)

# ------------------------------------------------------------------ #
# 9. bundle: 儿童节礼物 -> 孩子5岁男孩喜欢恐龙
# ------------------------------------------------------------------ #
t9 = make_traj(
    tid="sft_multi_009",
    sc="bundle",
    cat="玩具",
    focus="多轮用户细化孩子年龄性别兴趣，精准推荐恐龙主题儿童礼物",
    query="孩子5岁，男孩，超级喜欢恐龙，预算200以内",
    tool_input={
        "keywords": "恐龙玩具 5岁男孩 儿童节礼物",
        "category": "玩具",
        "age_min": 4,
        "age_max": 6,
        "gender": "male",
        "theme": "dinosaur",
        "max_price": 200
    },
    products=[
        {"product_id": "TOY_DINO_001", "name": "万代 侏罗纪世界 霸王龙模型 30cm", "price": 129.00,
         "brand": "万代", "specs": "30cm可动关节 仿真恐龙 适合3岁+"},
        {"product_id": "TOY_DINO_002", "name": "乐高 LEGO 恐龙化石积木套装（76940）", "price": 179.00,
         "brand": "乐高", "specs": "198片 适合4岁+ 恐龙骨架主题 益智拼搭"},
        {"product_id": "TOY_DINO_003", "name": "奥迪双钻 超龙战队变形恐龙玩具套装", "price": 168.00,
         "brand": "奥迪双钻", "specs": "6只恐龙可变形合体 适合4-8岁 男孩最爱"}
    ],
    final_content=(
        "太棒了，5岁男孩爱恐龙，这个礼物方向我太熟悉了！200以内有三款超级合适的：\n\n"
        "1. 万代霸王龙模型30cm（129元）—— 仿真恐龙可动关节，拿在手里超有质感，适合爱收藏恐龙模型的孩子。\n"
        "2. 奥迪双钻变形恐龙套装（168元）—— 6只恐龙能变形还能合体，玩法多，5岁男孩超爱，互动性最强。\n"
        "3. 乐高恐龙化石积木（179元）—— 198片拼搭恐龙骨架，益智又好玩，拼完还能展示，礼物惊喜感拉满。\n\n"
        "如果孩子喜欢动手拼搭，选乐高；喜欢角色扮演打怪，选奥迪双钻变形套装最嗨。需要我帮您加购礼品包装吗？"
    ),
    card_reasons=[
        "万代30cm霸王龙仿真模型，恐龙迷梦中珍藏款",
        "奥迪双钻变形合体恐龙6只套装，5岁男孩最爱玩法",
        "乐高恐龙化石积木，拼搭+展示两用益智好礼"
    ],
    multi_turn=True,
    history=[
        {"role": "user", "content": "儿童节快到了，想给孩子买个礼物，不知道买什么好"},
        {"role": "assistant", "content": "儿童节礼物选择很多！请问孩子多大，男孩还是女孩，有什么特别感兴趣的主题或者玩具类型吗？这样我可以给出更精准的推荐。"}
    ]
)
trajectories.append(t9)

# ------------------------------------------------------------------ #
# 10. place_order: 下单后 -> 填错地址
# ------------------------------------------------------------------ #
t10 = make_traj(
    tid="sft_multi_010",
    sc="place_order",
    cat="订单售后",
    focus="多轮下单后地址纠错，查询订单状态并引导用户修改收货地址",
    query="我刚才填错地址了，能帮我改一下吗？正确的地址是WORK_ADDRESS",
    tool_input={
        "action": "query_order",
        "order_id": "latest",
        "user_intent": "modify_address",
        "new_address": "WORK_ADDRESS"
    },
    products=[
        {"product_id": "ORDER_ITEM_001", "name": "已下单商品：Nike Air Max 270 运动鞋", "price": 799.00,
         "brand": "Nike", "specs": "41码 黑白配色 已付款待发货"}
    ],
    final_content=(
        "您好，我马上帮您查一下这笔订单的状态！\n\n"
        "订单查询结果：您的Nike Air Max 270订单（799元）目前状态为【已付款，待商家发货】，货物尚未揽收。\n\n"
        "好消息是：订单还未发货，地址仍然可以修改！\n\n"
        "修改方式有两种：\n"
        "1. 直接在「我的订单」-「订单详情」-「修改地址」中操作，可自助修改。\n"
        "2. 如果您告诉我正确地址（WORK_ADDRESS），我可以帮您发起地址修改申请。\n\n"
        "请确认新地址：WORK_ADDRESS，收件人姓名和手机号需要修改吗？"
    ),
    card_reasons=[
        "待发货订单Nike Air Max 270，地址可修改，点击查看订单详情"
    ],
    tool_name="OrderQuerySkill",
    multi_turn=True,
    history=[
        {"role": "user", "content": "帮我下单Nike Air Max 270，41码黑白配色"},
        {"role": "assistant", "content": "好的，已为您成功下单Nike Air Max 270运动鞋（41码，黑白配色），实付799元，订单号已生成，请注意查收短信。预计2-3个工作日发货，请保持手机畅通。"}
    ]
)
trajectories.append(t10)


# ------------------------------------------------------------------ #
# 写入 JSONL（追加模式）
# ------------------------------------------------------------------ #
output_path = "data/generated.jsonl"

with open(output_path, "a", encoding="utf-8") as f:
    for traj in trajectories:
        f.write(json.dumps(traj, ensure_ascii=False) + "\n")

print(f"已成功追加 {len(trajectories)} 条多轮对话轨迹到 {output_path}")
for t in trajectories:
    print(f"  {t['trajectory_id']}  scenario={t['scenario_type']}  multi_turn={t['is_multi_turn']}")
