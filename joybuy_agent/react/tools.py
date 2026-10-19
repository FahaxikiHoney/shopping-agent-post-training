# -*- coding: utf-8 -*-
"""
joybuy 工具定义 + Mock 执行层

工具 schema 对齐真实 joybuy-chatbot 工具，
Mock 数据返回真实格式的模拟数据。

真实 joybuy 工具：
  sku_recall              → 搜索召回商品列表
  sku_detail_fetch        → 获取单品/多品详情
  query_history_orders    → 查历史订单
  query_logistics_track   → 查物流
  calculate_budget        → 计算预算（bundle 场景）
  scenario_related_recall → 场景关联推荐（搭配场景）
"""
from __future__ import annotations

import json
import hashlib
import random
import re
import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence


# ─────────────────────────────────────────────────────────────────────────────
# 工具 Schema（对齐真实 joybuy 工具函数签名）
# ─────────────────────────────────────────────────────────────────────────────
JOYBUY_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "sku_recall",
            "description": "根据用户的自然语言搜索词召回商品列表。价格、品牌、尺寸和用途等约束应直接写入 query。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "完整搜索词，如「1500元以内适合新手的咖啡机」"},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },


    {
        "type": "function",
        "function": {
            "name": "similar_sku_recommend",
            "description": "根据用户当前商品的痛点，推荐同价位但更好的相似替换商品。用于用户抱怨现有商品不满意、想换一款的场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "original_desc": {"type": "string", "description": "用户当前使用的商品描述，如「膳魔师保温杯 169元」"},
                    "pain_point":    {"type": "string", "description": "用户反映的痛点/不满，如「保温只有5小时」「漏音严重」"},
                    "category":      {"type": "string", "description": "商品品类关键词，如「保温杯」「降噪耳机」"},
                    "max_price":     {"type": "number", "description": "当前站点币种的价格上限，0表示不限"},
                    "min_price":     {"type": "number", "description": "当前站点币种的价格下限，0表示不限"},
                    "page_size":     {"type": "integer", "description": "返回候选数量，建议3-5"},
                },
                "required": ["original_desc", "pain_point", "category"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_budget",
            "description": "计算多件商品的总价和预算余额。用于组合购物场景，验证是否在预算内。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "商品列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name":  {"type": "string", "description": "商品名"},
                                "price": {"type": "number", "description": "价格"},
                            },
                        },
                    },
                    "total_budget": {"type": "number", "description": "当前站点币种的总预算"},
                },
                "required": ["items", "total_budget"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scenario_related_recall",
            "description": "场景搭配推荐。用于家居风格搭配、户外露营搭配、健身装备搭配等场景，如买了北欧风沙发需要配茶几地毯。style参数指定搭配风格。",
            "parameters": {
                "type": "object",
                "properties": {
                    "main_item": {"type": "string", "description": "主商品描述，如「北欧风沙发」"},
                    "need_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "需要搭配的物品列表，如 [\"茶几\", \"落地灯\", \"地毯\"]",
                    },
                    "style": {"type": "string", "description": "风格标签：nordic/mid_century/modern/industrial"},
                },
                "required": ["main_item", "need_items"],
                "additionalProperties": False,
            },
        },
    },
]

# 工具名集合（用于校验）
VALID_TOOL_NAMES = {t["function"]["name"] for t in JOYBUY_TOOLS_SCHEMA}

# ─────────────────────────────────────────────────────────────────────────────
# 无货关键词（这些 query 会触发 sku_recall 返回空结果，模拟线上无货场景）
# ─────────────────────────────────────────────────────────────────────────────
NO_STOCK_KEYWORDS = {
    # 苹果高端产品
    "airpods max", "airpods max耳机", "苹果airpods max",
    "apple vision pro", "vision pro",
    # 戴森
    "戴森v15", "dyson v15", "戴森v12", "戴森吸尘器v15",
    "戴森airwrap", "dyson airwrap", "戴森卷发棒",
    # 任天堂
    "任天堂switch oled", "switch oled", "nintendo switch oled",
    # 索尼高端
    "sony wh-1000xm6", "wh-1000xm6", "索尼wh1000xm6",
    "索尼a95l", "sony a95l", "索尼oled电视",
    # 三星高端
    "三星fold6", "samsung galaxy fold6", "galaxy fold 6",
    "三星s25 ultra", "samsung s25 ultra",
    # 其他高需求低库存
    "lego积木限定款", "lego限定", "乐高限定版",
    "nike联名款", "jordan限定", "aj限定",
    "茅台飞天", "飞天茅台", "茅台酒",
    "特斯拉model y", "特斯拉model 3",
    "仓鼠", "仓鼠用品", "hamster", "hamster supplies", "hamster cage",
    "hamsterkäfig", "cage hamster", "hamsterkooi",
    "d’alba", "d'alba", "d alba",
    "kérastase nutritive masquintense", "kerastase nutritive masquintense",
    "risolles", "rissoles",
    "dyson hushjet mini", "hushjet mini",
    "ariana grande",
}

MULTILINGUAL_CATEGORY_ALIASES = {
    "降噪耳机": ["noise cancelling headphones", "noise canceling earbuds", "anc headphones", "casque antibruit", "kopfhörer noise cancelling", "ruisonderdrukkende koptelefoon"],
    "蓝牙耳机": ["bluetooth headphones", "wireless earbuds", "écouteurs bluetooth", "kabellose kopfhörer", "draadloze oordopjes"],
    "保温杯": ["thermal bottle", "insulated bottle", "vacuum flask", "thermos", "trinkflasche", "gourde isotherme", "thermosfles"],
    "人体工学椅": ["ergonomic chair", "office chair", "gaming chair", "chaise ergonomique", "chaise gaming", "bürostuhl", "gaming stuhl", "ergonomischen stuhl", "ergonomischem stuhl", "ergonomische stühle", "bureaustoel", "游戏椅", "电竞椅"],
    "扫地机": ["robot vacuum", "robot vacuum cleaner", "aspirateur robot", "saugroboter", "robotstofzuiger"],
    "咖啡机": ["coffee machine", "coffee maker", "espresso machine", "machine à café", "cafetière", "kaffeemaschine", "koffiemachine"],
    "跑步鞋": ["running shoes", "trainers", "chaussures de course", "laufschuhe", "hardloopschoenen"],
    "台灯": ["desk lamp", "table lamp", "lampe de bureau", "schreibtischlampe", "bureaulamp"],
    "投影仪": ["projector", "beamer", "vidéoprojecteur", "projecteur"],
    "洗衣液": ["laundry detergent", "washing pods", "detergent caps", "lessive", "wasmiddel", "waschmittel"],
    "跑步机": ["treadmill", "tapis de course", "laufband", "loopband"],
    "空气净化器": ["air purifier", "purificateur d'air", "luftreiniger", "luchtreiniger"],
    "吸尘器": ["vacuum cleaner", "cordless vacuum", "aspirateur", "staubsauger", "stofzuiger"],
    "电视": ["tv", "tv screen", "tv scherm", "television", "smart tv", "smart-tv", "qled tv", "oled tv", "fernseher", "téléviseur", "televisie"],
    "冰箱": ["refrigerator", "fridge freezer", "réfrigérateur", "kühlschrank", "koelkast"],
    "洗衣机": ["washing machine", "washer dryer", "lave-linge", "waschmaschine", "wasmachine"],
    "笔记本电脑": ["laptop", "notebook computer", "ordinateur portable", "ordinateur", "laptop computer"],
    "手机": ["smartphone", "mobile phone", "android phone", "iphone", "huawei mate", "mate 60", "mate 70", "téléphone", "handy", "telefoon"],
    "平板电脑": ["tablet", "ipad", "tablette", "tablet computer"],
    "智能手表": ["smart watch", "smartwatch", "montre connectée", "slimme watch"],
    "电动牙刷": ["electric toothbrush", "brosse à dents électrique", "elektrische zahnbürste", "elektrische tandenborstel"],
    "剃须刀": ["electric shaver", "razor", "rasoir électrique", "rasierer", "scheerapparaat", "qp420", "oneblade replacement blade"],
    "吹风机": ["hair dryer", "sèche-cheveux", "haartrockner", "föhn"],
    "空调": ["air conditioner", "portable air conditioner", "climatiseur", "klimaanlage", "airco"],
    "书桌": ["desk", "standing desk", "height adjustable desk", "bureau électrique", "schreibtisch", "bureau tafel"],
    "背包": ["backpack", "waterproof bag", "dry bag", "rucksack", "sac à dos", "rugzak", "swimming bag"],
    "护肤品": ["skin care", "skincare", "face cream", "serum", "soin visage", "hautpflege", "koriderm"],
    "洗发水": ["shampoo", "hair mask", "conditioner", "masque cheveux", "haarshampoo", "haar masker"],
    "儿童玩具": ["kids toys", "children toys", "birthday gift for girl", "birthday gift for boy", "jouets enfants", "kinderspielzeug", "cadeau enfant", "speelgoed", "cadeau jongen", "gift for boy", "voiture rc", "rc car", "rc drift", "ferngesteuertes auto", "radiografisch bestuurbare auto"],
    "宠物用品": ["pet supplies", "pet products", "haustierbedarf", "produits pour animaux", "huisdierbenodigdheden", "宠物用品"],
    "厨具": ["cookware", "frying pan", "kitchen utensils", "poêle", "casserole", "pfanne", "kookgerei"],
    "餐具": ["cutlery", "cutlery set", "fork knife spoon", "besteck", "couverts", "bestek", "刀叉勺", "餐具套装"],
    "收纳柜": ["tall black cabinet", "black storage cabinet", "black wardrobe", "wardrobe", "hoge zwarte kast", "zwarte kast", "kledingkast", "opbergkast", "schwarzer schrank", "hoher schrank", "armoire noire", "meuble de rangement", "黑色衣柜", "高柜", "衣柜", "收纳柜"],
    "装饰摆件": ["marble eggs", "marble egg", "decorative egg", "ornament", "deko ei", "oeuf décoratif", "decoratief ei", "装饰摆件", "大理石蛋"],
    "户外泳池": ["paddling pool", "metal frame pool", "above ground pool", "stahlrahmen pool", "piscine tubulaire", "frame zwembad", "金属框泳池"],
    "营养补充剂": ["mass protein", "mass gainer", "weight gainer", "eiwit mass", "增肌粉", "蛋白增肌粉"],
    "面条": ["noodles", "nouilles", "nudeln", "noedels", "les nuille", "面条", "方便面"],
    "零食": ["snacks", "chocolate", "cookies", "biscuits", "bonbons", "süßigkeiten", "snoep", "rice cake", "rijsttaart", "rijsttaartje", "米糕", "麻花"],
    "香水": ["perfume", "parfum", "eau de parfum", "eau de toilette", "duft"],
    "彩妆": ["makeup", "make-up", "nail polish", "nagellak", "vernis à ongles", "nagellack"],
    "床品": ["sheets", "bed sheets", "bedding", "mattress protector", "linge de lit", "bettwäsche", "beddengoed"],
    "数据线": ["charging cable", "usb cable", "keyboard cable", "câble usb", "ladekabel", "oplaadkabel", "usb-c jack adapter", "adaptateur jack usb-c", "adaptateur usb-c vers jack", "adaptateur audio usb-c jack", "usb-c audio adapter", "usb-c koptelefoonadapter"],
    "键盘鼠标": ["keyboard", "mechanical keyboard", "keyboard and mouse", "tastatur", "clavier", "toetsenbord", "键盘", "鼠标", "键鼠"],
    "折叠椅": ["camping chair", "folding chair", "chaise de camping", "campingstuhl", "campingstoel"],
    "户外灯": [
        "camping lantern", "camping light", "tent light", "tent lighting",
        "party tent lighting", "led lighting tent", "outdoor party tent light",
        "lampe de camping", "éclairage de tente", "campinglampe",
        "zeltbeleuchtung", "campinglamp", "tentverlichting",
        "led verlichting outdoor party tent", "帐篷灯", "帐篷照明", "户外灯",
    ],
    "帐篷": ["tent", "camping tent", "tente", "zelt"],
    "显示器": ["monitor", "pc screen", "écran pc", "bildschirm", "computerscherm"],
    "洗碗机": ["dishwasher", "lave-vaisselle", "geschirrspüler", "vaatwasser"],
    "行车记录仪": ["dash cam", "car camera", "dashcam", "caméra voiture", "autokamera"],
    "调味品": ["condiment", "soy sauce", "black soy sauce", "sweet soy sauce", "vinegar", "white vinegar", "sojasauce", "essig", "sauce soja", "vinaigre", "sojasaus", "azijn", "酱油", "甜酱油", "白醋", "食用醋"],
    "主食粮油": ["basmati rice", "basmoti", "rice 10kg", "barley", "gerste", "orge", "gerst", "long shelf life food", "lebensmittel lange haltbar", "lange haltbar", "lange haltbarkeit", "auf vorrat", "vorratshaltung", "konserven", "nudeln", "大米", "巴斯马蒂", "大麦"],
    "饮料": ["drink", "drinks", "getränk", "getränke", "boisson", "boissons", "drank", "dranken", "mineral water", "volvic water", "energy drink", "red bull", "instant milk tea", "mineralwasser", "boisson énergisante", "eau minérale", "energiedrank", "mineraalwater", "矿泉水", "能量饮料", "速溶奶茶"],
    "速冻食品": ["frozen breakfast", "frozen food", "quick frozen breakfast", "tiefkühlfrühstück", "petit déjeuner surgelé", "diepvriesontbijt", "冷冻早餐", "速冻早餐"],
    "水产食品": ["fresh fish", "dried fish", "trockenfisch", "frischer fisch", "poisson frais", "poisson séché", "verse vis", "gedroogde vis", "鲜鱼", "鱼干"],
    "马克杯": ["mug", "coffee mug", "ceramic mug", "becher", "tasse", "mok", "马克杯", "陶瓷杯"],
    "多功能工具": ["multi tool", "multi-tool", "multitool", "multipurpose tool", "multifunktionswerkzeug", "multifunktionale werkzeugsets", "werkzeugset", "outil multifonction", "multitool gereedschap", "多功能工具", "多功能钳"],
    "滤镜": ["camera filter", "nd filter", "nd-filter", "cpl filter", "kamerafilter", "filtre photo", "filtre nd", "camerafilter", "滤镜", "减光镜", "偏振镜"],
    "置物架": ["wall shelf", "wall slef", "floating shelf", "shelf", "wandregal", "étagère murale", "wandplank", "墙面置物架", "免打孔置物架"],
}

QUERY_LEVEL_MOCK_CATEGORY_ALIASES = {
    "收藏卡盒": ["football hobby box", "sports hobby box", "trading card box", "collectible card box"],
    "抹茶粉": ["matcha powder", "tsujisi matcha", "ceremonial matcha", "抹茶粉"],
    "和牛牛肉": ["wagyu", "wagyo", "wagyu beef", "和牛"],
    "烟灰缸": ["ash tray", "ashtray", "aschenbecher", "cendrier", "asbak", "烟灰缸"],
    "成人用品": ["penis ring", "cock ring", "阴茎环"],
    "电脑配件": [
        "pc component", "pc components", "computer component", "computer components",
        "motherboard and ram", "composant pc", "composants pc", "carte mère et ram",
        "pc-komponente", "pc-komponenten", "computeronderdeel", "computeronderdelen",
        "电脑配件",
    ],
    "3D扫描仪": ["3d scanner", "scanner 3d", "3d-scanner", "三维扫描仪"],
    "乒乓球器材": ["table tennis rubber", "ping pong rubber", "dhs cloud fog", "dhs 云雾", "乒乓球胶皮"],
    "泳池保温盖": ["swimming pool heat sheet", "pool heat sheet", "pool solar cover", "泳池保温盖"],
    "美工刀片": ["cutter klingen", "utility knife blades", "cutter blades", "美工刀片"],
    "闹钟": ["analog wecker", "analogue alarm clock", "analog alarm clock", "模拟闹钟"],
    "对讲门铃": ["interphone", "video intercom", "door intercom", "可视对讲"],
    "大幅面纸张": ["paper pack a1", "a1 paper", "a1 drawing paper", "a1纸"],
    "日式饺子": ["dumpling japanese", "japanese dumpling", "gyoza", "日式饺子"],
    "烘焙铁板": ["saj for baked goods", "saj griddle", "baking saj", "烘焙铁板"],
    "奶酪面包": ["käsebrötchen", "kasebrotchen", "cheese bread roll", "奶酪面包"],
    "底漆": ["mdf primer paint", "mdf primer", "wood primer", "木材底漆"],
    "精油": ["essential oil", "etherische olie", "lavender oil", "huile essentielle", "ätherisches öl", "精油", "薰衣草精油"],
    "管道清洁工具": ["sink drain grabber", "drain claw", "drain cleaning claw", "collect gunk from the sink", "管道抓取器", "下水道疏通抓手"],
    "熨衣用品": ["ironing board", "ironibg board", "strijkplank", "bügelbrett", "table à repasser", "熨衣板"],
    "洗车用品": ["car foam wash", "car fom wash", "car wash foam", "autowas schuim", "autowaschschaum", "mousse lavage voiture", "洗车泡沫"],
    "派对用品": ["birthday decorations", "party decorations", "party tableware", "anniversaire décoration", "partydeko", "feestdecoratie", "生日派对装饰"],
    "床垫": ["mattress", "matratze", "matras", "matelas", "床垫"],
    "文具套装": ["pen and paper", "pen & paper", "stationery set", "schreibwaren", "papeterie", "schrijfwarenset", "纸笔", "文具套装"],
    "曲面显示器": ["curved monitor", "curved pc monitor", "gebogener monitor", "monitor curved", "should be curved", "sollte curved", "mode portrait", "écran incurvé", "aoc q27g4zd", "曲面显示器"],
    "洗地吸尘器": ["vacuum mop", "robot vacuum mop", "aspirateur laveur", "saugwischer", "stofzuiger dweil", "扫拖一体", "洗地吸尘器", "p20 ultra plus"],
    "地毯清洁机": ["carpet cleaner", "steam carpet cleaner", "tapijtreiniger", "teppichreiniger", "nettoyeur tapis", "地毯清洁机"],
    "洗衣凝珠": ["washing pods", "laundry pods", "clothes washing pods", "waschmittel pods", "lessive capsules", "wascapsules", "洗衣凝珠"],
    "床笠": ["fitted sheet", "bed fitted sheet", "spannbettlaken", "drap-housse", "hoeslaken", "床笠", "床单 180 200"],
    "护肤面膜": ["hydrating face mask", "moisturizing face mask", "gesichtsmaske", "masque hydratant", "gezichtsmasker", "补水面膜"],
    "洁面产品": [
        "face cleanser", "facial cleanser", "cleanser set", "cleansing set",
        "gesichtsreiniger", "reinigungsset gesicht", "nettoyant visage",
        "coffret nettoyant visage", "gezichtsreiniger", "reinigingsset gezicht",
        "洁面", "洗面奶", "洁面组合", "洁面套装",
    ],
    "护发发膜": ["hair mask", "loreal elvive hair mask", "loreal elvital hair mask", "masque cheveux nourrissant", "masque cheveux", "haar masker", "haarmaske", "发膜"],
    "个人洗护": ["shower gel", "deodorant", "deoroller", "fabric softener", "duschgel", "déodorant", "gel douche", "wasverzachter", "柔顺剂", "沐浴露", "除臭剂"],
    "厨房餐具": ["dish set", "dish sets", "black plates", "kitchen plates", "metal serving bowl", "borden zwart", "geschirr set", "service de table", "serviesset", "餐盘", "餐具组合"],
    "厨房小家电": ["waffle maker", "gaufrier", "yogurt maker", "yaourtière", "kaffe maskin", "coffee maker", "koffiemachine", "kaffeemaschine", "咖啡机", "华夫饼机", "酸奶机"],
    "食品杂货": ["healthy protein sources", "protein foods", "noodle toppings", "hotpot foods", "basmati rice", "meat with good reviews", "meat with mostly good reviews", "snack recommendations", "下饭菜", "健康蛋白质", "健康的蛋白質", "香米", "零食推荐"],
    "酱料配料": ["fried rice sauce", "rice sauce", "gebakken rijst saus", "拌饭酱", "刨冰糖浆", "かき氷ミツ", "米粉", "调味酱"],
    "冷冻蔬菜": ["frozen vegetables", "tiefkühlgemüse", "légumes surgelés", "diepvriesgroenten", "冷冻蔬菜"],
    "礼物": ["birthday gift for best friend", "birthday gift for 5 year old", "gift for a 10 year old boy", "father's day gift", "fathers day gift", "idée de cadeau pour ma meilleure amie", "cadeau meilleure amie", "cadeau garçon 10 ans", "vaderdag cadeau", "父亲节礼物"],
    "婴童用品": ["stroller board", "planche de poussette", "baby weaning set", "kids ride-on luggage", "products for a 2 year old", "produits pour un petit de 2 ans", "婴儿辅食套装", "儿童骑行箱"],
    "家具收纳": ["shoe organizer", "shoe rack", "living room cabinet", "storage box", "foldable storage box", "waste recycle bin", "kullen komode", "tv furniture", "收纳盒", "鞋柜", "斗柜", "电视柜"],
    "衣物配饰": ["cargo trousers", "jeans men", "crossbody bag men", "men crossbody bag", "pantaloon", "男斜包", "男士牛仔裤", "工装裤"],
    "游戏主机": ["ps5 console", "ps5 pro", "playstation 5", "switch 2 console", "游戏主机"],
    "游戏软件": ["switch 2 games", "popular switch 2 games", "playstation games", "ps5 games", "任天堂游戏", "主机游戏"],
    "手机配件": ["phone holder", "phone hanger", "apple pencil pro", "samsung watch strap", "horlogebandje samsung", "smarttag2", "airtag battery", "手机支架", "手表表带", "触控笔"],
    "入门智能手机": ["smartphone under 200", "smartphone less than 200", "moto g75 5g", "samsung fold 8", "几百元的手机", "手机 200 euro"],
    "洗烘家电": ["washer dryer", "hisense washer dryer", "tumble dryer", "wärmepumpe trockner", "droger", "sèche-linge", "洗烘一体", "烘干机"],
    "特殊电视": ["12v tv", "95 inch tv", "95inch tv", "tv 95 inch", "tv 95inch", "tv between 20 inch and 30 inch", "20 inch tv", "30 inch tv", "电视 20 30 英寸"],
    "便携空调": ["portable air conditioner", "mobile air conditioner", "climatiseur mobile", "mobile airco", "portable air conditioning unit", "移动空调"],
    "空调配件": ["mobile airco window seal", "mobile airco raamafdichting", "air conditioner window kit", "raamafdichting mobile airco", "空调窗户配件", "移动空调密封套件"],
    "防水游泳包": ["waterproof swimming bag", "waterproof swim bag", "zwem tas waterdicht", "防水游泳包"],
    "智能塔扇": ["tower fan with alexa", "smart tower fan", "ventilateur colonne intelligent", "slimme torenventilator", "智能塔扇"],
    "电动出行": ["electric scooter", "e scooter", "foldable e bike", "folding ebike", "e bike die vouwbaar", "e-scooter", "电动滑板车", "折叠电动车"],
    "水杯水壶": ["thermal water bottle", "insulated bottle", "gourde isotherme", "thermosflasche", "thermosfles", "保温水杯"],
    "健康秤": ["body scale", "bathroom scale", "balance corporelle", "körperwaage", "personenweegschaal", "体脂秤"],
    "烟具": ["cigarette lighter", "lighter cigarette", "feuerzeug", "briquet", "aansteker", "打火机"],
    "车载用品": ["car window", "auto raam", "car accessories", "auto zubehör", "accessoires voiture", "汽车用品"],
    "清洁耗材": ["steel wool", "cleaning sponge", "glasdachreiniger", "mop", "esfregona", "vileda", "钢丝球", "玻璃清洁器"],
    "电竞鼠标": ["gaming mouse", "gaming mice", "gaming mouses", "gaming maus", "souris gaming", "gaming muis", "电竞鼠标"],
    "键盘连接线": ["keyboard cable", "keyboard usb cable", "tastaturkabel", "câble clavier", "toetsenbordkabel", "键盘连接线"],
    "纸巾用品": ["toilet paper", "paper towel", "kitchen paper", "essuie tout", "toilettenpapier", "keukenpapier", "卫生纸", "厨房纸"],
    "门窗防虫网": ["mosquito screen", "mosquito screen for door", "insect screen", "fliegengitter", "moustiquaire", "horgaas", "防蚊纱门", "防虫网"],
    "行李箱": ["suitcase", "valise 55", "ride on luggage", "luggage", "koffer", "行李箱"],
    "厨房清洁用品": ["kitchen hygiene", "kitchen cleaning products", "hygiène de la cuisine", "küchenhygiene", "keukenhygiëne", "厨房清洁用品"],
    "品牌护肤": ["laroche posay", "la roche posay", "premium makeup", "大牌美妆", "祛痘护肤", "acne skin care"],
    "耳机支架": ["headphone holder", "headset stand", "koptelefoon houder", "kopfhörerständer", "support casque", "耳机支架"],
    "鞋类收纳": ["shoe storage", "shoe organizer", "rangement pour chaussures", "schuhaufbewahrung", "schoenenopberger", "鞋子收纳"],
    "家具贴膜": ["furniture adhesive film", "film adhésif meuble", "möbelfolie", "meubelfolie", "家具贴膜"],
    "乳制饮品": ["buttermilk", "buttermilch", "karnemelk", "babeurre", "乳酸饮品", "酪乳"],
    "甜品烘焙": ["chocolate cake", "gateau chocolat", "egg roll snack", "red bean dessert", "korean ice cream", "蛋卷", "红豆甜品", "巧克力蛋糕", "韩式冰品"],
    "保鲜袋": ["food storage bag", "freezer bag", "large food bag", "sac conservation", "frischhaltebeutel", "vershoudzak", "保鲜袋"],
    "理发工具": ["barber set", "clipper trimmer shaver", "tondeuse clipper trimmer", "barbierset", "kit barbier", "理发器套装"],
    "浴室置物": ["soap holder", "wall soap holder", "fixation murale savon", "seifenhalter", "zeephouder", "肥皂架", "浴室置物架"],
    "平底锅": ["tefal pan", "frying pan 20", "poêle 20", "pfanne 20", "koekenpan 20", "平底锅"],
    "户外便携风扇": ["portable camping fan", "outdoor camping fan", "ventilateur camping", "camping ventilator", "campingventilator", "户外露营风扇"],
    "音响设备": ["soundbar", "barre de son", "bare de son", "construction site radio", "bouwplaatsradio", "baustellenradio", "音响条", "工地收音机"],
    "洗衣收纳": ["large laundry basket", "large wasmand", "clean laundry storage", "wasmand for clean laundry", "wasmand voor schone was", "wäschekorb", "panier à linge", "洗衣收纳篮"],
    "鞋靴": ["composite shoes", "hiking shoes", "walking shoes", "wanderschuhe", "chaussures randonnée", "wandelschoenen", "男鞋", "徒步鞋"],
    "脚部护理": ["foot odour", "foot odor", "athlete's foot", "fußgeruch", "fußpilz", "odeur des pieds", "voetschimmel", "脚气", "脚臭"],
    "折叠盆": ["foldable wash basin", "collapsible basin", "faltbares waschbecken", "bassine pliable", "opvouwbare waskom", "可折叠洗脸盆"],
    "日食眼镜": ["eclipse glasses", "solar eclipse glasses", "sonnenfinsternisbrille", "brille sonnenfinsterniss", "lunettes éclipse", "日食眼镜"],
}

QUERY_LEVEL_MOCK_CATEGORY_DISPLAY = {
    "收藏卡盒": {"en_GB": "trading card hobby box", "de_DE": "Sammelkarten-Hobbybox", "fr_FR": "boîte de cartes à collectionner", "nl_NL": "verzamelkaarten-hobbybox"},
    "抹茶粉": {"en_GB": "matcha powder", "de_DE": "Matcha-Pulver", "fr_FR": "poudre de matcha", "nl_NL": "matchapoeder"},
    "和牛牛肉": {"en_GB": "wagyu beef", "de_DE": "Wagyu-Rindfleisch", "fr_FR": "bœuf wagyu", "nl_NL": "wagyu-rundvlees"},
    "烟灰缸": {"en_GB": "ashtray", "de_DE": "Aschenbecher", "fr_FR": "cendrier", "nl_NL": "asbak"},
    "成人用品": {"en_GB": "penis ring", "de_DE": "Penisring", "fr_FR": "anneau pénien", "nl_NL": "penisring"},
    "电脑配件": {"en_GB": "PC components", "de_DE": "PC-Komponenten", "fr_FR": "composants PC", "nl_NL": "pc-onderdelen"},
    "3D扫描仪": {"en_GB": "3D scanner", "de_DE": "3D-Scanner", "fr_FR": "scanner 3D", "nl_NL": "3D-scanner"},
    "乒乓球器材": {"en_GB": "table-tennis equipment", "de_DE": "Tischtennis-Zubehör", "fr_FR": "équipement de tennis de table", "nl_NL": "tafeltennisuitrusting"},
    "泳池保温盖": {"en_GB": "pool solar cover", "de_DE": "Pool-Solarabdeckung", "fr_FR": "bâche solaire de piscine", "nl_NL": "zwembad-zonnezeil"},
    "美工刀片": {"en_GB": "utility knife blades", "de_DE": "Cuttermesser-Klingen", "fr_FR": "lames de cutter", "nl_NL": "afbreekmesjes"},
    "闹钟": {"en_GB": "analogue alarm clock", "de_DE": "analoger Wecker", "fr_FR": "réveil analogique", "nl_NL": "analoge wekker"},
    "对讲门铃": {"en_GB": "door intercom", "de_DE": "Türsprechanlage", "fr_FR": "interphone", "nl_NL": "deurintercom"},
    "大幅面纸张": {"en_GB": "A1 paper pack", "de_DE": "A1-Papierpackung", "fr_FR": "paquet de papier A1", "nl_NL": "A1-papierpak"},
    "日式饺子": {"en_GB": "Japanese gyoza", "de_DE": "japanische Gyoza", "fr_FR": "gyoza japonais", "nl_NL": "Japanse gyoza"},
    "烘焙铁板": {"en_GB": "saj baking griddle", "de_DE": "Saj-Backplatte", "fr_FR": "plaque de cuisson saj", "nl_NL": "saj-bakplaat"},
    "奶酪面包": {"en_GB": "cheese bread roll", "de_DE": "Käsebrötchen", "fr_FR": "petit pain au fromage", "nl_NL": "kaasbroodje"},
    "底漆": {"en_GB": "MDF primer", "de_DE": "MDF-Grundierung", "fr_FR": "apprêt MDF", "nl_NL": "MDF-grondverf"},
    "精油": {"en_GB": "essential oil", "de_DE": "ätherisches Öl", "fr_FR": "huile essentielle", "nl_NL": "etherische olie"},
    "管道清洁工具": {"en_GB": "sink drain cleaning claw", "de_DE": "Abfluss-Reinigungskralle", "fr_FR": "griffe de nettoyage de canalisation", "nl_NL": "afvoerreinigingsklauw"},
    "熨衣用品": {"en_GB": "ironing board", "de_DE": "Bügelbrett", "fr_FR": "table à repasser", "nl_NL": "strijkplank"},
    "洗车用品": {"en_GB": "car wash foam", "de_DE": "Autowaschschaum", "fr_FR": "mousse de lavage auto", "nl_NL": "autowasschuim"},
    "派对用品": {"en_GB": "birthday party supplies", "de_DE": "Geburtstags-Partyset", "fr_FR": "articles de fête d'anniversaire", "nl_NL": "verjaardagsfeestartikelen"},
    "床垫": {"en_GB": "mattress", "de_DE": "Matratze", "fr_FR": "matelas", "nl_NL": "matras"},
    "文具套装": {"en_GB": "stationery set", "de_DE": "Schreibwarenset", "fr_FR": "ensemble de papeterie", "nl_NL": "schrijfwarenset"},
    "曲面显示器": {"en_GB": "curved monitor", "de_DE": "gebogener Monitor", "fr_FR": "écran incurvé", "nl_NL": "gebogen monitor"},
    "洗地吸尘器": {"en_GB": "vacuum mop", "de_DE": "Saugwischer", "fr_FR": "aspirateur laveur", "nl_NL": "stofzuiger met dweilfunctie"},
    "地毯清洁机": {"en_GB": "carpet cleaner", "de_DE": "Teppichreiniger", "fr_FR": "nettoyeur de tapis", "nl_NL": "tapijtreiniger"},
    "洗衣凝珠": {"en_GB": "laundry pods", "de_DE": "Waschmittel-Pods", "fr_FR": "capsules de lessive", "nl_NL": "wascapsules"},
    "床笠": {"en_GB": "fitted sheet", "de_DE": "Spannbettlaken", "fr_FR": "drap-housse", "nl_NL": "hoeslaken"},
    "护肤面膜": {"en_GB": "hydrating face mask", "de_DE": "Feuchtigkeitsmaske", "fr_FR": "masque hydratant", "nl_NL": "hydraterend gezichtsmasker"},
    "洁面产品": {"en_GB": "facial cleanser set", "de_DE": "Gesichtsreinigungsset", "fr_FR": "coffret nettoyant visage", "nl_NL": "gezichtsreinigingsset"},
    "护发发膜": {"en_GB": "hair mask", "de_DE": "Haarmaske", "fr_FR": "masque capillaire", "nl_NL": "haarmasker"},
    "个人洗护": {"en_GB": "personal care", "de_DE": "Körperpflege", "fr_FR": "soins corporels", "nl_NL": "persoonlijke verzorging"},
    "厨房餐具": {"en_GB": "dinnerware set", "de_DE": "Geschirrset", "fr_FR": "service de table", "nl_NL": "serviesset"},
    "厨房小家电": {"en_GB": "small kitchen appliance", "de_DE": "Küchenkleingerät", "fr_FR": "petit électroménager de cuisine", "nl_NL": "klein keukenapparaat"},
    "食品杂货": {"en_GB": "food and groceries", "de_DE": "Lebensmittel", "fr_FR": "alimentation", "nl_NL": "boodschappen"},
    "酱料配料": {"en_GB": "sauce and toppings", "de_DE": "Sauce und Toppings", "fr_FR": "sauce et garnitures", "nl_NL": "saus en toppings"},
    "冷冻蔬菜": {"en_GB": "frozen vegetables", "de_DE": "Tiefkühlgemüse", "fr_FR": "légumes surgelés", "nl_NL": "diepvriesgroenten"},
    "礼物": {"en_GB": "gift", "de_DE": "Geschenk", "fr_FR": "cadeau", "nl_NL": "cadeau"},
    "婴童用品": {"en_GB": "baby and toddler product", "de_DE": "Baby- und Kleinkindprodukt", "fr_FR": "produit bébé et enfant", "nl_NL": "baby- en peuterproduct"},
    "家具收纳": {"en_GB": "home storage furniture", "de_DE": "Aufbewahrungsmöbel", "fr_FR": "meuble de rangement", "nl_NL": "opbergmeubel"},
    "衣物配饰": {"en_GB": "clothing accessory", "de_DE": "Bekleidung", "fr_FR": "vêtement", "nl_NL": "kleding"},
    "游戏主机": {"en_GB": "game console", "de_DE": "Spielkonsole", "fr_FR": "console de jeux", "nl_NL": "spelconsole"},
    "游戏软件": {"en_GB": "console game", "de_DE": "Konsolenspiel", "fr_FR": "jeu pour console", "nl_NL": "consolegame"},
    "手机配件": {"en_GB": "phone accessory", "de_DE": "Handyzubehör", "fr_FR": "accessoire téléphone", "nl_NL": "telefoonaccessoire"},
    "入门智能手机": {"en_GB": "affordable smartphone", "de_DE": "günstiges Smartphone", "fr_FR": "smartphone abordable", "nl_NL": "betaalbare smartphone"},
    "洗烘家电": {"en_GB": "washer dryer", "de_DE": "Waschtrockner", "fr_FR": "lave-linge séchant", "nl_NL": "was-droogcombinatie"},
    "特殊电视": {"en_GB": "special-size television", "de_DE": "Fernseher in Sondergröße", "fr_FR": "téléviseur format spécial", "nl_NL": "televisie met speciale maat"},
    "便携空调": {"en_GB": "portable air conditioner", "de_DE": "mobiles Klimagerät", "fr_FR": "climatiseur mobile", "nl_NL": "mobiele airco"},
    "空调配件": {"en_GB": "air-conditioner window kit", "de_DE": "Fensterabdichtung für Klimagerät", "fr_FR": "kit fenêtre pour climatiseur", "nl_NL": "raamafdichting voor airco"},
    "防水游泳包": {"en_GB": "waterproof swimming bag", "de_DE": "wasserdichte Schwimmtasche", "fr_FR": "sac de natation étanche", "nl_NL": "waterdichte zwemtas"},
    "智能塔扇": {"en_GB": "smart tower fan", "de_DE": "smarter Turmventilator", "fr_FR": "ventilateur colonne intelligent", "nl_NL": "slimme torenventilator"},
    "电动出行": {"en_GB": "electric mobility", "de_DE": "Elektromobilität", "fr_FR": "mobilité électrique", "nl_NL": "elektrische mobiliteit"},
    "水杯水壶": {"en_GB": "insulated water bottle", "de_DE": "Thermosflasche", "fr_FR": "gourde isotherme", "nl_NL": "thermosfles"},
    "健康秤": {"en_GB": "body scale", "de_DE": "Körperwaage", "fr_FR": "balance corporelle", "nl_NL": "personenweegschaal"},
    "烟具": {"en_GB": "cigarette lighter", "de_DE": "Feuerzeug", "fr_FR": "briquet", "nl_NL": "aansteker"},
    "车载用品": {"en_GB": "car accessory", "de_DE": "Autozubehör", "fr_FR": "accessoire auto", "nl_NL": "autoaccessoire"},
    "清洁耗材": {"en_GB": "cleaning supplies", "de_DE": "Reinigungszubehör", "fr_FR": "accessoires de nettoyage", "nl_NL": "schoonmaakartikelen"},
    "电竞鼠标": {"en_GB": "gaming mouse", "de_DE": "Gaming-Maus", "fr_FR": "souris gaming", "nl_NL": "gamingmuis"},
    "键盘连接线": {"en_GB": "keyboard cable", "de_DE": "Tastaturkabel", "fr_FR": "câble de clavier", "nl_NL": "toetsenbordkabel"},
    "纸巾用品": {"en_GB": "paper products", "de_DE": "Papierhygiene", "fr_FR": "produits en papier", "nl_NL": "papierwaren"},
    "门窗防虫网": {"en_GB": "door insect screen", "de_DE": "Fliegengitter", "fr_FR": "moustiquaire de porte", "nl_NL": "deurhor"},
    "行李箱": {"en_GB": "suitcase", "de_DE": "Koffer", "fr_FR": "valise", "nl_NL": "koffer"},
    "厨房清洁用品": {"en_GB": "kitchen cleaning supplies", "de_DE": "Küchenreinigung", "fr_FR": "produits d'hygiène de cuisine", "nl_NL": "keukenreiniging"},
    "品牌护肤": {"en_GB": "brand skincare", "de_DE": "Marken-Hautpflege", "fr_FR": "soin de marque", "nl_NL": "merk-huidverzorging"},
    "耳机支架": {"en_GB": "headphone stand", "de_DE": "Kopfhörerständer", "fr_FR": "support casque", "nl_NL": "koptelefoonhouder"},
    "鞋类收纳": {"en_GB": "shoe storage", "de_DE": "Schuhaufbewahrung", "fr_FR": "rangement à chaussures", "nl_NL": "schoenenopberger"},
    "家具贴膜": {"en_GB": "furniture adhesive film", "de_DE": "Möbelfolie", "fr_FR": "film adhésif pour meuble", "nl_NL": "meubelfolie"},
    "乳制饮品": {"en_GB": "buttermilk drink", "de_DE": "Buttermilch", "fr_FR": "babeurre", "nl_NL": "karnemelk"},
    "甜品烘焙": {"en_GB": "dessert and baked goods", "de_DE": "Dessert und Gebäck", "fr_FR": "dessert et pâtisserie", "nl_NL": "dessert en gebak"},
    "保鲜袋": {"en_GB": "food storage bags", "de_DE": "Frischhaltebeutel", "fr_FR": "sacs de conservation", "nl_NL": "vershoudzakken"},
    "理发工具": {"en_GB": "barber tool set", "de_DE": "Barber-Set", "fr_FR": "kit de barbier", "nl_NL": "barbierset"},
    "浴室置物": {"en_GB": "wall soap holder", "de_DE": "Seifenhalter", "fr_FR": "porte-savon mural", "nl_NL": "wandzeephouder"},
    "平底锅": {"en_GB": "frying pan", "de_DE": "Bratpfanne", "fr_FR": "poêle", "nl_NL": "koekenpan"},
    "户外便携风扇": {"en_GB": "portable camping fan", "de_DE": "Campingventilator", "fr_FR": "ventilateur de camping", "nl_NL": "campingventilator"},
    "音响设备": {"en_GB": "audio equipment", "de_DE": "Audiogerät", "fr_FR": "équipement audio", "nl_NL": "audioapparaat"},
    "洗衣收纳": {"en_GB": "large laundry basket", "de_DE": "großer Wäschekorb", "fr_FR": "grand panier à linge", "nl_NL": "grote wasmand"},
    "鞋靴": {"en_GB": "shoes", "de_DE": "Schuhe", "fr_FR": "chaussures", "nl_NL": "schoenen"},
    "脚部护理": {"en_GB": "foot care", "de_DE": "Fußpflege", "fr_FR": "soin des pieds", "nl_NL": "voetverzorging"},
    "折叠盆": {"en_GB": "foldable wash basin", "de_DE": "faltbare Waschschüssel", "fr_FR": "bassine pliable", "nl_NL": "opvouwbare waskom"},
    "日食眼镜": {"en_GB": "solar eclipse glasses", "de_DE": "Sonnenfinsternisbrille", "fr_FR": "lunettes pour éclipse", "nl_NL": "zonsverduisteringsbril"},
}

QUERY_LEVEL_MOCK_PRICE_RANGES = {
    "收藏卡盒": (25.0, 110.0), "抹茶粉": (8.0, 28.0), "和牛牛肉": (18.0, 65.0),
    "烟灰缸": (5.0, 22.0), "成人用品": (8.0, 30.0), "电脑配件": (45.0, 320.0),
    "3D扫描仪": (160.0, 480.0), "乒乓球器材": (15.0, 70.0), "泳池保温盖": (20.0, 90.0),
    "美工刀片": (4.0, 15.0), "闹钟": (8.0, 28.0), "对讲门铃": (35.0, 160.0),
    "大幅面纸张": (10.0, 35.0), "日式饺子": (3.0, 12.0), "烘焙铁板": (20.0, 85.0),
    "奶酪面包": (2.0, 8.0), "底漆": (8.0, 30.0),
    "精油": (6.0, 28.0), "管道清洁工具": (5.0, 22.0), "熨衣用品": (18.0, 65.0),
    "洗车用品": (6.0, 30.0), "派对用品": (8.0, 45.0), "床垫": (90.0, 420.0),
    "文具套装": (4.0, 20.0), "曲面显示器": (110.0, 420.0), "洗地吸尘器": (120.0, 520.0),
    "地毯清洁机": (70.0, 260.0), "洗衣凝珠": (8.0, 28.0), "床笠": (12.0, 45.0),
    "护肤面膜": (6.0, 35.0), "洁面产品": (7.0, 32.0), "护发发膜": (7.0, 32.0), "个人洗护": (4.0, 25.0),
    "厨房餐具": (18.0, 90.0), "厨房小家电": (22.0, 120.0), "食品杂货": (3.0, 35.0),
    "酱料配料": (2.0, 16.0), "冷冻蔬菜": (3.0, 22.0), "礼物": (8.0, 45.0),
    "婴童用品": (12.0, 85.0), "家具收纳": (25.0, 180.0), "衣物配饰": (15.0, 90.0),
    "游戏主机": (280.0, 780.0), "游戏软件": (25.0, 75.0), "手机配件": (8.0, 80.0),
    "入门智能手机": (90.0, 280.0), "洗烘家电": (260.0, 750.0), "特殊电视": (90.0, 850.0),
    "便携空调": (120.0, 480.0), "空调配件": (12.0, 55.0), "防水游泳包": (10.0, 45.0),
    "智能塔扇": (45.0, 180.0), "电动出行": (250.0, 950.0), "水杯水壶": (8.0, 45.0),
    "健康秤": (18.0, 70.0), "烟具": (3.0, 20.0), "车载用品": (8.0, 60.0),
    "清洁耗材": (3.0, 25.0),
    "电竞鼠标": (18.0, 95.0), "键盘连接线": (5.0, 22.0), "纸巾用品": (4.0, 24.0),
    "门窗防虫网": (12.0, 55.0), "行李箱": (28.0, 130.0), "厨房清洁用品": (5.0, 28.0),
    "品牌护肤": (10.0, 55.0), "耳机支架": (8.0, 35.0), "鞋类收纳": (18.0, 90.0),
    "家具贴膜": (6.0, 30.0), "乳制饮品": (2.0, 10.0), "甜品烘焙": (3.0, 28.0),
    "保鲜袋": (4.0, 18.0), "理发工具": (25.0, 140.0), "浴室置物": (8.0, 35.0),
    "平底锅": (18.0, 75.0), "户外便携风扇": (20.0, 85.0), "音响设备": (35.0, 220.0),
    "洗衣收纳": (12.0, 55.0), "鞋靴": (28.0, 140.0), "脚部护理": (6.0, 32.0),
    "折叠盆": (8.0, 30.0), "日食眼镜": (5.0, 22.0),
}

MULTILINGUAL_CONSTRAINT_ALIASES = {
    "quiet": ["quiet", "silent", "low noise", "leise", "geräuscharm", "silencieux", "faible bruit", "stil", "geluidsarm", "静音", "低噪"],
    "4k": ["4k", "uhd", "ultra hd"],
    "oled": ["oled"],
    "mini_led": ["mini led", "mini-led"],
    "high_refresh": ["120hz", "120fps", "144hz", "165hz", "high refresh", "hohe bildwiederholrate", "taux de rafraîchissement élevé", "hoge verversingssnelheid"],
    "energy_efficient": ["energy efficient", "low power", "energiesparend", "stromsparend", "économe en énergie", "energiezuinig", "省电", "节能"],
}

CONSTRAINT_PRODUCT_MARKERS = {
    "quiet": ["低噪", "静音", "30db", "31db", "32db"],
    "4k": ["4k", "uhd"],
    "oled": ["oled"],
    "mini_led": ["mini led", "mini-led"],
    "high_refresh": ["120hz", "144hz", "165hz", "240hz"],
    "energy_efficient": ["省电", "节能", "一级能效", "二级能效"],
}

HARD_RETRIEVAL_CONSTRAINTS = {"4k", "oled", "mini_led", "high_refresh"}

SPECIALIZED_PRODUCT_FILTERS = [
    ({"giotto chocolate bar", "giotto chocolate bars", "giotto schokoriegel"}, {"giotto"}),
    ({"sulfate-free shampoo", "shampoo without sulfates", "without sulfates", "sans sulfate", "sulfatfrei", "zonder sulfaten", "无硫酸盐洗发水"}, {"sulfate-free", "sans sulfate", "sulfatfrei", "zonder sulfaten", "无硫酸盐"}),
    ({"anti-tangle robot vacuum", "anti tangle brush", "anti-tangle brush", "anti haarborstel", "brosse anti-emmêlement", "防缠绕扫地机器人"}, {"anti-tangle", "anti tangle", "anti-emmêlement", "防缠绕", "防毛发缠绕"}),
    ({"dreame x60", "x60 pro ultra"}, {"dreame x60", "x60 pro ultra"}),
    ({"halal snack", "halal food", "halal snacks", "清真零食", "清真食品"}, {"halal", "清真"}),
    ({"underwear washing machine", "underwear washer", "mini underwear washer", "内衣洗衣机", "内裤洗衣机"}, {"underwear", "内衣", "内裤", "迷你洗"}),
    ({"low calorie snack", "low-calorie snack", "low cal snack", "低卡零食", "低热量零食"}, {"low calorie", "low-calorie", "kcal", "低卡", "低热量"}),
    ({"curved monitor", "curved screen", "curved display", "gebogener monitor", "écran incurvé", "gebogen monitor", "曲面显示器"}, {"curved", "incurvé", "gebogen", "曲面"}),
    ({"under 130 kcal", "130 kcal", "moins de 130 kcal", "unter 130 kcal", "低于130千卡"}, {"130 kcal", "kcal", "千卡", "卡路里"}),
    ({"tent lighting", "party tent lighting", "led lighting tent", "led verlichting outdoor party tent", "帐篷灯", "帐篷照明"}, {"tent lighting", "party light", "led lighting", "帐篷灯", "户外灯", "露营灯", "营地灯"}),
    ({"pepsi syrup", "zero pepsi syrup", "pepsi siroop", "pepsi sirup", "sirop pepsi", "百事糖浆"}, {"pepsi", "百事", "syrup", "sirup", "sirop", "糖浆"}),
    ({"standing air conditioner", "floor standing air conditioner", "floor air conditioner", "立式空调", "柜式空调", "立体空调"}, {"standing", "floor", "柜式", "立式"}),
    ({"tower fan with alexa", "fan with alexa", "ventilator mit alexa", "ventilateur alexa", "ventilator met alexa", "支持alexa的风扇"}, {"alexa", "voice assistant", "语音助手"}),
    ({"chinese makeup", "chinese cosmetics", "中国彩妆", "国货彩妆"}, {"花西子", "完美日记", "珀莱雅", "中国品牌"}),
    ({"drinking horn", "drink horn", "tankard", "groomsmen tankard", "corne à boire", "trinkhorn", "drinkhoorn", "饮酒角杯"}, {"drinking horn", "tankard", "corne à boire", "trinkhorn", "drinkhoorn", "角杯"}),
    ({"chocolate bar", "chocolate bars", "schokoriegel", "barre chocolatée", "chocoladereep", "巧克力棒"}, {"chocolate bar", "schokoriegel", "barre chocolatée", "chocoladereep", "巧克力棒"}),
    ({"washing pods", "detergent pods", "detergent caps", "laundry capsules", "waschmittel pods", "wasmiddel capsules", "洗衣凝珠"}, {"pods", "capsules", "凝珠"}),
    ({"curved", "incurve", "gebogen", "曲面"}, {"curved", "incurve", "gebogen", "曲面"}),
    ({"aspirateur laveur", "laveur et aspirateur robot", "robot aspirateur laveur", "wet dry vacuum", "vacuum mop", "staubsauger wischer", "stofzuiger dweil", "洗地吸尘器"}, {"laveur", "wet dry", "vacuum mop", "洗地", "吸拖", "扫拖", "拖地"}),
    ({"air cooler", "air cooling fan", "rafraichisseur d'air", "refroidisseur d'air", "luftkuhler", "luchtkoeler", "空调扇", "冷风扇"}, {"air cooler", "rafraichisseur", "luftkuhler", "luchtkoeler", "空调扇", "冷风"}),
    ({"ceiling fan", "ventilateur de plafond", "ventilateur de plafon", "deckenventilator", "plafondventilator", "吊扇"}, {"ceiling", "plafond", "decken", "吊扇"}),
    ({"kit fenetre climatiseur", "kit fenêtre climatiseur", "air conditioner window kit", "window seal kit", "window installation kit", "raamafdichting", "移动空调 窗户", "空调 窗户安装配件"}, {"window kit", "window seal", "raamafdichting", "fenster", "fenetre", "窗户", "挡板", "密封"}),
    ({"phone case", "iphone case", "smartphone case", "手机壳", "xr壳", "保护壳"}, {"phone case", "iphone case", "手机壳", "保护壳"}),
    ({"screen protector", "tempered glass", "钢化膜", "贴膜"}, {"screen protector", "tempered glass", "钢化膜", "贴膜"}),
    ({"mcvities", "mc vities"}, {"mcvities", "mc vities"}),
    ({"nothing ear"}, {"nothing ear"}),
    ({"p20 ultra plus"}, {"p20 ultra plus"}),
    ({"hp pavilion se 14"}, {"hp pavilion se 14"}),
    ({"marly parfum", "parfums de marly"}, {"marly"}),
    ({"iphone 17"}, {"iphone 17"}),
    ({"anchovy", "anchois", "sardelle", "ansjovis", "凤尾鱼"}, {"anchovy", "anchois", "sardelle", "ansjovis", "凤尾鱼"}),
    ({"12v tv", "12 v tv", "12v television", "12v fernseher"}, {"12v", "12 v"}),
    ({"hair catcher ball", "laundry hair catcher", "washing machine hair ball", "attached all the hair", "洗衣机毛发吸附球"}, {"hair catcher", "毛发吸附", "洗衣球"}),
    ({"laundry basket", "washing basket", "wasmand", "wäschekorb", "panier a linge", "洗衣篮"}, {"laundry basket", "wasmand", "wäschekorb", "洗衣篮"}),
    ({"3c认证", "3c certified", "ccc certified", "ccc认证"}, {"3c认证", "ccc", "中国强制认证"}),
    ({"mass protein", "mass gainer", "weight gainer"}, {"mass protein", "mass gainer", "weight gainer", "serious mass", "增肌粉"}),
    ({"rice cake", "rijsttaart", "rijsttaartje", "米糕"}, {"rice cake", "rijsttaart", "米糕"}),
    ({"qp420/50", "qp420"}, {"qp420/50", "qp420"}),
    ({"chocolate drink", "boisson chocolat", "chocolate beverage", "schokoladengetrank", "巧克力饮料"}, {"chocolate drink", "boisson chocolat", "schokolade", "巧克力饮料"}),
    ({"tv kbenet", "tv cabinet", "television cabinet", "meuble tv", "meubels tv", "fernsehschrank", "电视柜"}, {"tv cabinet", "meuble tv", "fernsehschrank", "电视柜"}),
    ({"tankyard", "tankyard cup"}, {"tankard", "drinking horn", "角杯"}),
    ({"sirup zero pepsi", "syrup zero pepsi", "siroop zero pepsi"}, {"pepsi", "syrup", "sirup", "siroop", "糖浆"}),
    ({"rug sproeie", "rug sproei", "rug spray", "rugspray"}, {"rug spray", "rugspray", "喷雾"}),
    ({"aa or aaa", "aa oder aaa", "aa/aaa", "aa ou aaa"}, {"aa battery", "aaa battery", "aa电池", "aaa电池"}),
    ({"mode portrait", "portrait mode monitor", "speakers integre", "integrated speakers monitor"}, {"portrait", "pivot", "integrated speakers", "内置音箱", "竖屏"}),
    ({"machine-wash laundry detergent", "machine wash detergent", "suitable for machine washing", "适合机洗", "机洗洗衣液"}, {"适合机洗", "机洗"}),
    ({"keyboard cable"}, {"keyboard cable", "键盘线"}),
    ({"english keyboard", "english layout keyboard", "englische tastatur"}, {"english layout", "uk layout", "us layout", "英文键盘"}),
    ({"getranke aus mekiko", "getranke aus mexiko", "drinks from mexico", "drinks from korea", "mexican drinks", "korean drinks"}, {"mexico", "korea", "墨西哥", "韩国"}),
    ({"ventilator platform lamp", "fan with lamp", "fan with light", "ventilateur avec lampe"}, {"lamp", "light", "lampe", "灯"}),
    ({"120 x 60 cm", "120x60 cm", "120 × 60 cm"}, {"120×60", "120 x 60", "120x60"}),
    ({"visiting from china", "cousins are visiting from china", "chinese visitors snacks"}, {"三只松鼠", "良品铺子", "旺仔", "好吃哒"}),
    ({"ventilateur 2 en 1", "2 in 1 fan", "2-in-1 fan", "二合一风扇"}, {"2-in-1", "2 en 1", "二合一", "2合1"}),
    ({"work with my iphone", "works with iphone", "compatible with iphone", "mit meinem iphone", "avec mon iphone", "met mijn iphone", "与iphone兼容"}, {"苹果手机", "iphone"}),
    ({"portable camping fan", "camping portable fan", "camping fan", "ventilateur camping portable", "tragbarer camping ventilator", "draagbare camping ventilator", "露营便携电风扇", "户外露营用的便携电风扇"}, {"portable", "camping", "battery", "rechargeable", "便携", "露营", "充电", "电池"}),
    ({"standing fan", "pedestal fan", "ventilateur sur pied", "sur pied", "standventilator", "staande ventilator", "落地扇"}, {"落地扇", "pedestal", "sur pied", "standventilator"}),
    ({"tower fan", "ventilateur colonne", "turmventilator", "torenventilator", "塔式风扇"}, {"塔式", "tower", "colonne", "turm", "toren"}),
    ({"climatiseur exterieur", "outdoor air conditioner", "aussen klimaanlage", "buiten airco", "户外空调"}, {"outdoor", "exterieur", "aussen", "buiten", "户外"}),
    ({"qled or miniled", "qled or mini led", "qled ou miniled", "qled oder miniled", "qled of miniled", "qled或miniled"}, {"qled", "mini led", "量子点"}),
    ({"android or google tv", "android ou google tv", "android oder google tv", "android of google tv", "android或google tv"}, {"android tv", "google tv"}),
    ({"drei bis funf jahre", "three to five years", "trois a cinq ans", "drie tot vijf jaar", "三到五年"}, {"长保质期", "long shelf life", "lange haltbarkeit"}),
    ({"periment dans tres longtemps", "ne perime jamais", "very long expiry food", "never expires food", "长期不易过期食品"}, {"长保质期", "long shelf life", "长期储存"}),
    ({"android 15"}, {"android 15"}),
    ({"jbl bar", "soundbar", "sound bar", "barre de son", "soundbar lautsprecher", "电视音响", "回音壁"}, {"soundbar", "sound bar", "barre de son", "回音壁", "条形音响"}),
    ({"galaxy buds 3 pro", "galaxy buds3 pro", "galaxy buds 4 pro", "galaxy buds4 pro"}, {"galaxy buds 3 pro", "galaxy buds3 pro", "galaxy buds 4 pro", "galaxy buds4 pro"}),
    ({"samsung smarttag", "galaxy smarttag", "smarttag2", "smart tag 2", "蓝牙防丢器"}, {"smarttag", "smart tag", "防丢"}),
    ({"tablet cover", "tablet case", "tab s10 lite cover", "ipad cover", "tablethülle", "housse tablette", "tablet hoes", "平板保护套", "平板壳"}, {"cover", "case", "hülle", "housse", "hoes", "保护套", "平板壳"}),
    ({"apple watch ultra 3", "apple watch ultra"}, {"apple watch ultra"}),
    ({"lego star wars 75412", "lego 75412"}, {"75412"}),
    ({"educational toy", "educational toys", "learning toy", "jouet éducatif", "lernspielzeug", "educatief speelgoed", "益智玩具"}, {"educational", "learning", "stem", "益智", "编程", "拼图"}),
    ({"fitted sheet", "single bed sheet", "spannbettlaken", "drap-housse", "hoeslaken", "床笠", "单件床单"}, {"fitted sheet", "spannbettlaken", "drap-housse", "hoeslaken", "床笠", "单件床单"}),
    ({"hair mask", "hair masque", "masque cheveux", "masque capillaire", "haar masker", "haar mask", "发膜", "头发护理膜"}, {"hair mask", "hair masque", "masque", "haar masker", "发膜"}),
    ({"hair conditioner", "conditioner for hair", "après-shampooing", "haarconditioner", "护发素"}, {"conditioner", "après-shampooing", "haarconditioner", "护发素"}),
    ({"camping air conditioner", "climatiseur camping", "12v air conditioner", "battery powered air conditioner", "camping airco"}, {"camping", "12v", "battery", "batterie", "露营", "车载"}),
    ({"portable air conditioner", "mobile air conditioner", "mobile airco", "climatiseur mobile", "mobiele airco", "mobile klimaanlage", "移动空调", "portasplit"}, {"portable", "mobile", "portasplit", "移动", "便携"}),
    ({"air conditioner window kit", "window seal kit", "window installation kit", "raamafdichting", "climatiseur fenêtre accessoire", "移动空调 窗户", "空调 窗户安装配件"}, {"window kit", "window seal", "raamafdichting", "fenster", "fenêtre", "窗户", "挡板", "密封套件"}),
    ({"gaming chair", "gaming stuhl", "chaise gaming", "gamestoel", "游戏椅", "电竞椅"}, {"gaming", "游戏", "电竞"}),
    ({"pool robot vacuum", "robot pool vacuum", "aspirateur robot piscine", "zwembadrobot", "poolroboter", "泳池机器人", "泳池吸尘"}, {"pool", "piscine", "zwembad", "泳池"}),
    ({"backpack strap pad", "pad for backpack strap", "shoulder strap pad", "sac à dos coussinet bretelle", "rucksack schulterpolster", "rugzak schouderpad", "背包肩带垫", "肩带护垫"}, {"strap pad", "shoulder pad", "bretelle", "schulterpolster", "schouderpad", "肩带垫", "护肩"}),
    ({"wireless casting device", "casting device", "casting bits", "hdmi casting", "draadloze casting apparaat", "wireless display adapter", "无线投屏器", "投屏器"}, {"casting", "wireless display", "miracast", "chromecast", "投屏", "同屏器"}),
    ({"tv stand", "presenting stand for the tv", "presentation stand for the tv", "tv cabinet", "tv console", "meuble tv", "meubles tv", "tv meubel", "tv meubels", "meubels tv", "fernsehschrank", "电视柜", "电视支架"}, {"tv stand", "tv cabinet", "tv console", "meuble tv", "tv meubel", "fernsehschrank", "电视柜", "电视支架"}),
    ({"bathroom cabinet", "bathroom vanity", "cabinet de salle de bain", "cabin de sale de bain", "meuble salle de bain", "armoire salle de bain", "badkamerkast", "badezimmerschrank", "浴室柜"}, {"bathroom", "vanity", "salle de bain", "badkamer", "badezimmer", "浴室柜", "卫浴柜"}),
    ({"waterproof swimming bag", "waterproof swim bag", "swimming dry bag", "sac étanche natation", "wasserdichte schwimmtasche", "waterdichte zwemtas", "游泳防水包"}, {"swimming", "swim bag", "dry bag", "natation", "schwimmtasche", "zwemtas", "游泳", "干湿分离"}),
    ({"no-drill wall shelf", "wall shelf without drilling", "wall slef without using drill", "floating shelf no drill", "wandregal ohne bohren", "étagère murale sans perçage", "wandplank zonder boren", "免打孔墙架", "免打孔置物架"}, {"no drill", "without drilling", "ohne bohren", "sans perçage", "zonder boren", "免打孔"}),
    ({"rug spray", "back spray", "back pain spray", "rugspray", "rug sproei", "背部喷雾", "腰背喷雾"}, {"back spray", "pain relief spray", "rugspray", "背部喷雾", "止痛喷雾"}),
    ({"giotto"}, {"giotto"}),
    ({"koriderm"}, {"koriderm"}),
    ({"iphone 16 pro"}, {"iphone 16 pro"}),
    ({"iphone 15"}, {"iphone 15"}),
    ({"麻花"}, {"麻花"}),
    ({"meat jerky", "beef jerky", "pork jerky", "肉干", "牛肉干", "猪肉脯"}, {"jerky", "肉干", "牛肉干", "猪肉脯"}),
    ({"hostile gift", "sarcastic resignation gift", "black humor office gift", "恶搞诅咒礼物", "离职暗示", "讽刺辞职", "讨厌的人 礼物", "讨厌的人", "不喜欢的人", "离开公司"}, {"hostile", "sarcastic", "black humor", "恶搞", "离职", "讽刺"}),
    ({"receipt printer", "pos printer", "kassendrucker", "imprimante ticket", "ticketprinter", "票据打印", "小票打印"}, {"receipt", "thermal", "pos", "票据", "小票", "热敏"}),
    ({"3d printer filament", "3d-print filament", "filament 3d", "filament", "3d打印耗材"}, {"filament", "耗材"}),
    ({"with straw", "avec paille", "mit trinkhalm", "met rietje", "带吸管", "吸管水壶"}, {"straw", "paille", "trinkhalm", "rietje", "吸管"}),
    ({"voiture rc", "rc car", "rc drift", "ferngesteuertes auto", "遥控车"}, {" rc", "遥控", "radiocommand"}),
    ({"nail polish", "nagellak", "vernis a ongles", "nagellack", "指甲油"}, {"nail polish", "指甲油"}),
    ({"sunscreen", "sun cream", "sunblock", "crème solaire", "sonnencreme", "zonnebrand", "防晒霜", "防晒乳"}, {"sunscreen", "sun cream", "sunblock", "solaire", "sonnencreme", "zonnebrand", "防晒"}),
    ({"usb-c jack adapter", "adaptateur jack usb-c", "usb-c audio adapter", "3.5mm"}, {"adapter", "adaptateur", "转接", "3.5mm"}),
    ({"black soy sauce", "zwart sojasaus", "黑酱油"}, {"black", "dark", "黑", "浓口"}),
    ({"甜酱油", "sweet soy sauce", "kecap manis"}, {"sweet", "甜", "kecap manis"}),
    ({"white vinegar", "白醋", "食用醋", "vinegar", "essig", "vinaigre", "azijn"}, {"vinegar", "essig", "vinaigre", "醋"}),
    ({"basmati", "basmoti"}, {"basmati", "巴斯马蒂"}),
    ({"barley", "gerste", "orge", "gerst"}, {"barley", "gerste", "orge", "大麦"}),
    ({"volvic", "mineral water", "mineralwasser", "mineraalwater"}, {"volvic", "mineral"}),
    ({"red bull", "energy drink", "energiedrank"}, {"red bull", "energy", "能量"}),
    ({"instant milk tea", "速溶奶茶"}, {"milk tea", "奶茶"}),
    ({"fresh fish", "frischer fisch", "poisson frais", "verse vis"}, {"fresh", "frisch", "frais", "鲜"}),
    ({"dried fish", "trockenfisch", "poisson seche", "gedroogde vis"}, {"dried", "trocken", "seche", "鱼干"}),
]

PRODUCT_ATTRIBUTE_ALIASES = [
    ({"striped", "gestreift", "raye", "gestreept", "条纹"}, {"条纹"}),
    ({"cotton-linen", "cotton linen", "baumwoll-leinen", "coton-lin", "katoen-linnen", "棉麻"}, {"棉麻"}),
    ({"jacquard", "提花"}, {"提花"}),
    ({"botanical", "feuillage", "blattmotiv", "bladmotief", "植物叶片"}, {"植物", "叶片"}),
    ({"black-and-white line", "black and white line", "schwarz-weisse linien", "ligne noir et blanc", "zwart-witte lijn", "黑白线条"}, {"黑白", "线条"}),
]

SPECIALIZED_PRODUCT_FILTERS.extend([
    ({"dark beige", "dark or beige", "dark and beige"}, {"dark", "beige", "深色", "米色"}),
    ({"dark mug", "dark colour mug", "dark color mug"}, {"dark", "深色", "深灰"}),
    ({"beige mug", "beige colour mug", "beige color mug"}, {"beige", "米色"}),
])

SITE_CONFIGS = {
    "UK-Site": {
        "site_lang_code": "en_GB",
        "currency_code": "GBP",
        "currency_symbol": "£",
        "price_rate": 0.11,
    },
    "DE-Site": {
        "site_lang_code": "de_DE",
        "currency_code": "EUR",
        "currency_symbol": "€",
        "price_rate": 0.13,
    },
    "FR-Site": {
        "site_lang_code": "fr_FR",
        "currency_code": "EUR",
        "currency_symbol": "€",
        "price_rate": 0.13,
    },
    "NL-Site": {
        "site_lang_code": "nl_NL",
        "currency_code": "EUR",
        "currency_symbol": "€",
        "price_rate": 0.13,
    },
}

CATEGORY_DISPLAY_NAMES = {
    "降噪耳机": {"en_GB": "noise-cancelling headphones", "de_DE": "Noise-Cancelling-Kopfhörer", "fr_FR": "casque antibruit", "nl_NL": "ruisonderdrukkende koptelefoon"},
    "蓝牙耳机": {"en_GB": "Bluetooth headphones", "de_DE": "Bluetooth-Kopfhörer", "fr_FR": "écouteurs Bluetooth", "nl_NL": "Bluetooth-koptelefoon"},
    "保温杯": {"en_GB": "insulated bottle", "de_DE": "Thermoflasche", "fr_FR": "gourde isotherme", "nl_NL": "thermosfles"},
    "电视": {"en_GB": "television", "de_DE": "Fernseher", "fr_FR": "téléviseur", "nl_NL": "televisie"},
    "显示器": {"en_GB": "monitor", "de_DE": "Monitor", "fr_FR": "écran PC", "nl_NL": "monitor"},
    "空调": {"en_GB": "air conditioner", "de_DE": "Klimaanlage", "fr_FR": "climatiseur", "nl_NL": "airconditioner"},
    "咖啡机": {"en_GB": "coffee machine", "de_DE": "Kaffeemaschine", "fr_FR": "machine à café", "nl_NL": "koffiemachine"},
    "扫地机": {"en_GB": "robot vacuum", "de_DE": "Saugroboter", "fr_FR": "aspirateur robot", "nl_NL": "robotstofzuiger"},
    "吸尘器": {"en_GB": "vacuum cleaner", "de_DE": "Staubsauger", "fr_FR": "aspirateur", "nl_NL": "stofzuiger"},
    "人体工学椅": {"en_GB": "ergonomic chair", "de_DE": "ergonomischer Stuhl", "fr_FR": "chaise ergonomique", "nl_NL": "ergonomische stoel"},
    "智能手表": {"en_GB": "smartwatch", "de_DE": "Smartwatch", "fr_FR": "montre connectée", "nl_NL": "smartwatch"},
    "笔记本电脑": {"en_GB": "laptop", "de_DE": "Laptop", "fr_FR": "ordinateur portable", "nl_NL": "laptop"},
    "手机": {"en_GB": "smartphone", "de_DE": "Smartphone", "fr_FR": "smartphone", "nl_NL": "smartphone"},
    "平板电脑": {"en_GB": "tablet", "de_DE": "Tablet", "fr_FR": "tablette", "nl_NL": "tablet"},
    "背包": {"en_GB": "backpack", "de_DE": "Rucksack", "fr_FR": "sac à dos", "nl_NL": "rugzak"},
    "折叠椅": {"en_GB": "folding chair", "de_DE": "Klappstuhl", "fr_FR": "chaise pliante", "nl_NL": "klapstoel"},
    "帐篷": {"en_GB": "tent", "de_DE": "Zelt", "fr_FR": "tente", "nl_NL": "tent"},
    "跑步鞋": {"en_GB": "running shoes", "de_DE": "Laufschuhe", "fr_FR": "chaussures de course", "nl_NL": "hardloopschoenen"},
    "台灯": {"en_GB": "desk lamp", "de_DE": "Schreibtischlampe", "fr_FR": "lampe de bureau", "nl_NL": "bureaulamp"},
    "投影仪": {"en_GB": "projector", "de_DE": "Beamer", "fr_FR": "vidéoprojecteur", "nl_NL": "projector"},
    "洗衣液": {"en_GB": "laundry detergent", "de_DE": "Waschmittel", "fr_FR": "lessive", "nl_NL": "wasmiddel"},
    "跑步机": {"en_GB": "treadmill", "de_DE": "Laufband", "fr_FR": "tapis de course", "nl_NL": "loopband"},
    "电动牙刷": {"en_GB": "electric toothbrush", "de_DE": "elektrische Zahnbürste", "fr_FR": "brosse à dents électrique", "nl_NL": "elektrische tandenborstel"},
    "剃须刀": {"en_GB": "electric shaver", "de_DE": "Elektrorasierer", "fr_FR": "rasoir électrique", "nl_NL": "scheerapparaat"},
    "吹风机": {"en_GB": "hair dryer", "de_DE": "Haartrockner", "fr_FR": "sèche-cheveux", "nl_NL": "föhn"},
    "书桌": {"en_GB": "desk", "de_DE": "Schreibtisch", "fr_FR": "bureau", "nl_NL": "bureau"},
    "护肤品": {"en_GB": "skincare product", "de_DE": "Hautpflege", "fr_FR": "soin visage", "nl_NL": "huidverzorging"},
    "洗发水": {"en_GB": "shampoo", "de_DE": "Shampoo", "fr_FR": "shampooing", "nl_NL": "shampoo"},
    "儿童玩具": {"en_GB": "children's toy", "de_DE": "Kinderspielzeug", "fr_FR": "jouet pour enfant", "nl_NL": "kinderspeelgoed"},
    "厨具": {"en_GB": "cookware", "de_DE": "Kochgeschirr", "fr_FR": "ustensile de cuisine", "nl_NL": "kookgerei"},
    "餐具": {"en_GB": "cutlery set", "de_DE": "Besteckset", "fr_FR": "service de couverts", "nl_NL": "bestekset"},
    "装饰摆件": {"en_GB": "decorative ornament", "de_DE": "Dekoobjekt", "fr_FR": "objet décoratif", "nl_NL": "decoratief ornament"},
    "户外泳池": {"en_GB": "outdoor pool", "de_DE": "Außenpool", "fr_FR": "piscine extérieure", "nl_NL": "buitenzwembad"},
    "营养补充剂": {"en_GB": "nutrition supplement", "de_DE": "Nahrungsergänzung", "fr_FR": "complément nutritionnel", "nl_NL": "voedingssupplement"},
    "面条": {"en_GB": "noodles", "de_DE": "Nudeln", "fr_FR": "nouilles", "nl_NL": "noedels"},
    "零食": {"en_GB": "snack", "de_DE": "Snack", "fr_FR": "en-cas", "nl_NL": "snack"},
    "香水": {"en_GB": "perfume", "de_DE": "Parfüm", "fr_FR": "parfum", "nl_NL": "parfum"},
    "床品": {"en_GB": "bedding", "de_DE": "Bettwäsche", "fr_FR": "linge de lit", "nl_NL": "beddengoed"},
    "数据线": {"en_GB": "charging cable", "de_DE": "Ladekabel", "fr_FR": "câble de charge", "nl_NL": "oplaadkabel"},
    "键盘鼠标": {"en_GB": "keyboard", "de_DE": "Tastatur", "fr_FR": "clavier", "nl_NL": "toetsenbord"},
    "洗碗机": {"en_GB": "dishwasher", "de_DE": "Geschirrspüler", "fr_FR": "lave-vaisselle", "nl_NL": "vaatwasser"},
    "行车记录仪": {"en_GB": "dash cam", "de_DE": "Dashcam", "fr_FR": "caméra embarquée", "nl_NL": "dashcam"},
    "颈椎按摩仪": {"en_GB": "neck massager", "de_DE": "Nackenmassagegerät", "fr_FR": "masseur cervical", "nl_NL": "nekmassageapparaat"},
    "家居搭配": {"en_GB": "home accessory", "de_DE": "Wohnaccessoire", "fr_FR": "accessoire maison", "nl_NL": "woonaccessoire"},
    "热水壶": {"en_GB": "electric kettle", "de_DE": "Wasserkocher", "fr_FR": "bouilloire électrique", "nl_NL": "waterkoker"},
    "跳绳": {"en_GB": "skipping rope", "de_DE": "Springseil", "fr_FR": "corde à sauter", "nl_NL": "springtouw"},
    "运动垫": {"en_GB": "exercise mat", "de_DE": "Trainingsmatte", "fr_FR": "tapis de sport", "nl_NL": "fitnessmat"},
    "弹力带": {"en_GB": "resistance band", "de_DE": "Widerstandsband", "fr_FR": "bande de résistance", "nl_NL": "weerstandsband"},
    "微波炉": {"en_GB": "microwave oven", "de_DE": "Mikrowelle", "fr_FR": "four à micro-ondes", "nl_NL": "magnetron"},
    "宠物用品": {"en_GB": "pet product", "de_DE": "Haustierprodukt", "fr_FR": "produit pour animaux", "nl_NL": "huisdierproduct"},
    "汽车用品": {"en_GB": "car accessory", "de_DE": "Autozubehör", "fr_FR": "accessoire automobile", "nl_NL": "auto-accessoire"},
    "运动服装": {"en_GB": "sportswear", "de_DE": "Sportbekleidung", "fr_FR": "vêtement de sport", "nl_NL": "sportkleding"},
    "文具": {"en_GB": "stationery", "de_DE": "Schreibwaren", "fr_FR": "papeterie", "nl_NL": "schrijfwaren"},
    "电烤箱": {"en_GB": "electric oven", "de_DE": "Elektrobackofen", "fr_FR": "four électrique", "nl_NL": "elektrische oven"},
    "彩妆": {"en_GB": "make-up product", "de_DE": "Make-up-Produkt", "fr_FR": "produit de maquillage", "nl_NL": "make-upproduct"},
    "睡袋": {"en_GB": "sleeping bag", "de_DE": "Schlafsack", "fr_FR": "sac de couchage", "nl_NL": "slaapzak"},
    "泡脚桶": {"en_GB": "foot spa", "de_DE": "Fußbad", "fr_FR": "bain de pieds", "nl_NL": "voetenbad"},
    "default": {"en_GB": "featured product", "de_DE": "Empfohlenes Produkt", "fr_FR": "produit sélectionné", "nl_NL": "uitgelicht product"},
    "空气净化器": {"en_GB": "air purifier", "de_DE": "Luftreiniger", "fr_FR": "purificateur d'air", "nl_NL": "luchtreiniger"},
    "洗衣机": {"en_GB": "washing machine", "de_DE": "Waschmaschine", "fr_FR": "lave-linge", "nl_NL": "wasmachine"},
    "冰箱": {"en_GB": "refrigerator", "de_DE": "Kühlschrank", "fr_FR": "réfrigérateur", "nl_NL": "koelkast"},
    "调味品": {"en_GB": "condiment", "de_DE": "Würzmittel", "fr_FR": "condiment", "nl_NL": "smaakmaker"},
    "主食粮油": {"en_GB": "pantry staple", "de_DE": "Grundnahrungsmittel", "fr_FR": "aliment de base", "nl_NL": "houdbaar basisvoedsel"},
    "饮料": {"en_GB": "drink", "de_DE": "Getränk", "fr_FR": "boisson", "nl_NL": "drank"},
    "速冻食品": {"en_GB": "frozen food", "de_DE": "Tiefkühlkost", "fr_FR": "produit surgelé", "nl_NL": "diepvriesproduct"},
    "水产食品": {"en_GB": "fish product", "de_DE": "Fischprodukt", "fr_FR": "produit de la mer", "nl_NL": "visproduct"},
    "马克杯": {"en_GB": "mug", "de_DE": "Becher", "fr_FR": "tasse", "nl_NL": "mok"},
    "多功能工具": {"en_GB": "multi-tool", "de_DE": "Multifunktionswerkzeug", "fr_FR": "outil multifonction", "nl_NL": "multitool"},
    "茶几": {"en_GB": "coffee table", "de_DE": "Couchtisch", "fr_FR": "table basse", "nl_NL": "salontafel"},
    "落地灯": {"en_GB": "floor lamp", "de_DE": "Stehlampe", "fr_FR": "lampadaire", "nl_NL": "vloerlamp"},
    "地毯": {"en_GB": "rug", "de_DE": "Teppich", "fr_FR": "tapis", "nl_NL": "vloerkleed"},
    "装饰画": {"en_GB": "wall art", "de_DE": "Wandbild", "fr_FR": "décoration murale", "nl_NL": "wanddecoratie"},
    "VR头显": {"en_GB": "VR headset", "de_DE": "VR-Headset", "fr_FR": "casque VR", "nl_NL": "VR-headset"},
    "三脚架": {"en_GB": "tripod", "de_DE": "Stativ", "fr_FR": "trépied", "nl_NL": "statief"},
    "云台": {"en_GB": "camera gimbal", "de_DE": "Kamera-Gimbal", "fr_FR": "stabilisateur caméra", "nl_NL": "cameragimbal"},
    "保温壶": {"en_GB": "vacuum flask", "de_DE": "Isolierkanne", "fr_FR": "bouteille isotherme", "nl_NL": "thermoskan"},
    "充电宝": {"en_GB": "power bank", "de_DE": "Powerbank", "fr_FR": "batterie externe", "nl_NL": "powerbank"},
    "冲锋衣": {"en_GB": "waterproof jacket", "de_DE": "Outdoorjacke", "fr_FR": "veste imperméable", "nl_NL": "waterdichte jas"},
    "净水器": {"en_GB": "water purifier", "de_DE": "Wasserfilter", "fr_FR": "purificateur d'eau", "nl_NL": "waterfilter"},
    "卷发棒": {"en_GB": "curling iron", "de_DE": "Lockenstab", "fr_FR": "fer à boucler", "nl_NL": "krultang"},
    "台式电脑": {"en_GB": "desktop computer", "de_DE": "Desktop-PC", "fr_FR": "ordinateur de bureau", "nl_NL": "desktopcomputer"},
    "哑铃": {"en_GB": "dumbbell set", "de_DE": "Hantelset", "fr_FR": "jeu d'haltères", "nl_NL": "halterset"},
    "存储卡": {"en_GB": "memory card", "de_DE": "Speicherkarte", "fr_FR": "carte mémoire", "nl_NL": "geheugenkaart"},
    "心率带": {"en_GB": "heart-rate monitor strap", "de_DE": "Herzfrequenz-Brustgurt", "fr_FR": "ceinture cardio", "nl_NL": "hartslagband"},
    "快门线": {"en_GB": "camera shutter release", "de_DE": "Fernauslöser", "fr_FR": "déclencheur à distance", "nl_NL": "afstandsontspanner"},
    "户外灯": {"en_GB": "camping lantern", "de_DE": "Campinglampe", "fr_FR": "lampe de camping", "nl_NL": "campinglamp"},
    "打印机": {"en_GB": "printer", "de_DE": "Drucker", "fr_FR": "imprimante", "nl_NL": "printer"},
    "抱枕": {"en_GB": "cushion", "de_DE": "Dekokissen", "fr_FR": "coussin", "nl_NL": "sierkussen"},
    "按摩椅": {"en_GB": "massage chair", "de_DE": "Massagesessel", "fr_FR": "fauteuil massant", "nl_NL": "massagestoel"},
    "掌机": {"en_GB": "handheld console", "de_DE": "Handheld-Konsole", "fr_FR": "console portable", "nl_NL": "handheldconsole"},
    "摄影包": {"en_GB": "camera bag", "de_DE": "Kameratasche", "fr_FR": "sac photo", "nl_NL": "cameratas"},
    "摄影装备": {"en_GB": "camera accessory", "de_DE": "Kamerazubehör", "fr_FR": "accessoire photo", "nl_NL": "camera-accessoire"},
    "摆件": {"en_GB": "decorative ornament", "de_DE": "Dekofigur", "fr_FR": "objet décoratif", "nl_NL": "decoratief ornament"},
    "收纳架": {"en_GB": "storage rack", "de_DE": "Aufbewahrungsregal", "fr_FR": "étagère de rangement", "nl_NL": "opbergrek"},
    "收纳柜": {"en_GB": "storage cabinet", "de_DE": "Aufbewahrungsschrank", "fr_FR": "meuble de rangement", "nl_NL": "opbergkast"},
    "桌面升降架": {"en_GB": "desk riser", "de_DE": "Schreibtischaufsatz", "fr_FR": "rehausseur de bureau", "nl_NL": "bureauverhoger"},
    "桌面收纳": {"en_GB": "desk organiser", "de_DE": "Schreibtisch-Organizer", "fr_FR": "organiseur de bureau", "nl_NL": "bureau-organizer"},
    "沙发垫": {"en_GB": "sofa cover", "de_DE": "Sofabezug", "fr_FR": "housse de canapé", "nl_NL": "bankhoes"},
    "泡沫轴": {"en_GB": "foam roller", "de_DE": "Faszienrolle", "fr_FR": "rouleau de massage", "nl_NL": "foamroller"},
    "清洁套装": {"en_GB": "camera cleaning kit", "de_DE": "Kamera-Reinigungsset", "fr_FR": "kit de nettoyage photo", "nl_NL": "camerareinigingsset"},
    "滤镜": {"en_GB": "camera filter", "de_DE": "Kamerafilter", "fr_FR": "filtre photo", "nl_NL": "camerafilter"},
    "炊具": {"en_GB": "camp cookware", "de_DE": "Camping-Kochgeschirr", "fr_FR": "batterie de cuisine camping", "nl_NL": "campingkookset"},
    "瑜伽垫": {"en_GB": "yoga mat", "de_DE": "Yogamatte", "fr_FR": "tapis de yoga", "nl_NL": "yogamat"},
    "电饭煲": {"en_GB": "rice cooker", "de_DE": "Reiskocher", "fr_FR": "cuiseur à riz", "nl_NL": "rijstkoker"},
    "登山鞋": {"en_GB": "hiking boots", "de_DE": "Wanderschuhe", "fr_FR": "chaussures de randonnée", "nl_NL": "wandelschoenen"},
    "破壁机": {"en_GB": "high-speed blender", "de_DE": "Hochleistungsmixer", "fr_FR": "blender haute vitesse", "nl_NL": "hogesnelheidsblender"},
    "窗帘": {"en_GB": "curtains", "de_DE": "Vorhänge", "fr_FR": "rideaux", "nl_NL": "gordijnen"},
    "绿植": {"en_GB": "houseplant", "de_DE": "Zimmerpflanze", "fr_FR": "plante d'intérieur", "nl_NL": "kamerplant"},
    "置物架": {"en_GB": "shelving unit", "de_DE": "Ablageregal", "fr_FR": "étagère", "nl_NL": "wandrek"},
    "蓝牙音箱": {"en_GB": "Bluetooth speaker", "de_DE": "Bluetooth-Lautsprecher", "fr_FR": "enceinte Bluetooth", "nl_NL": "Bluetooth-speaker"},
    "路由器": {"en_GB": "Wi-Fi router", "de_DE": "WLAN-Router", "fr_FR": "routeur Wi-Fi", "nl_NL": "wifi-router"},
    "运动手环": {"en_GB": "fitness tracker", "de_DE": "Fitness-Tracker", "fr_FR": "bracelet d'activité", "nl_NL": "fitnesstracker"},
    "运动毛巾": {"en_GB": "sports towel", "de_DE": "Sporthandtuch", "fr_FR": "serviette de sport", "nl_NL": "sporthanddoek"},
    "运动水壶": {"en_GB": "sports bottle", "de_DE": "Sportflasche", "fr_FR": "gourde de sport", "nl_NL": "sportfles"},
    "运动耳机": {"en_GB": "sports earphones", "de_DE": "Sportkopfhörer", "fr_FR": "écouteurs de sport", "nl_NL": "sportoordopjes"},
    "运动跳绳": {"en_GB": "speed skipping rope", "de_DE": "Speed-Springseil", "fr_FR": "corde à sauter rapide", "nl_NL": "speed springtouw"},
    "键盘": {"en_GB": "keyboard", "de_DE": "Tastatur", "fr_FR": "clavier", "nl_NL": "toetsenbord"},
    "镜子": {"en_GB": "mirror", "de_DE": "Spiegel", "fr_FR": "miroir", "nl_NL": "spiegel"},
    "闪光灯": {"en_GB": "camera flash", "de_DE": "Kamerablitz", "fr_FR": "flash photo", "nl_NL": "cameraflitser"},
    "防护膝盖": {"en_GB": "knee support", "de_DE": "Kniebandage", "fr_FR": "genouillère", "nl_NL": "kniebrace"},
    "防潮垫": {"en_GB": "camping mat", "de_DE": "Isomatte", "fr_FR": "matelas de camping", "nl_NL": "kampeermat"},
    "面包机": {"en_GB": "bread maker", "de_DE": "Brotbackautomat", "fr_FR": "machine à pain", "nl_NL": "broodbakmachine"},
    "风扇": {"en_GB": "fan", "de_DE": "Ventilator", "fr_FR": "ventilateur", "nl_NL": "ventilator"},
    "餐椅": {"en_GB": "dining chair", "de_DE": "Esszimmerstuhl", "fr_FR": "chaise de salle à manger", "nl_NL": "eetkamerstoel"},
    "香薰": {"en_GB": "home fragrance", "de_DE": "Raumduft", "fr_FR": "parfum d'intérieur", "nl_NL": "huisgeur"},
    "鼠标": {"en_GB": "computer mouse", "de_DE": "Computermaus", "fr_FR": "souris d'ordinateur", "nl_NL": "computermuis"},
    "鼠标垫": {"en_GB": "mouse mat", "de_DE": "Mauspad", "fr_FR": "tapis de souris", "nl_NL": "muismat"},
}

BRAND_ALIASES = {
    "小米": ["xiaomi"],
    "海信": ["hisense"],
    "索尼": ["sony"],
    "苹果": ["apple"],
    "华为": ["huawei"],
    "三星": ["samsung"],
    "格力": ["gree"],
    "美的": ["midea"],
    "海尔": ["haier"],
    "大金": ["daikin"],
    "飞利浦": ["philips"],
    "德龙": ["delonghi", "de'longhi"],
    "戴尔": ["dell"],
    "华硕": ["asus"],
    "联想": ["lenovo"],
    "宜家": ["IKEA"],
    "欧普": ["OPPLE"],
    "70迈": ["70mai"],
    "乐高": ["lego"],
    "Roberto Cavalli": ["roberto cavalli"],
    "Mauboussin": ["mauboussin"],
    "Ajmal": ["ajmal"],
}

BRAND_DISPLAY_NAMES = {
    "小米": "Xiaomi",
    "海信": "Hisense",
    "索尼": "Sony",
    "苹果": "Apple",
    "华为": "Huawei",
    "三星": "Samsung",
    "格力": "Gree",
    "美的": "Midea",
    "海尔": "Haier",
    "大金": "Daikin",
    "飞利浦": "Philips",
    "德龙": "De'Longhi",
    "戴尔": "Dell",
    "华硕": "ASUS",
    "联想": "Lenovo",
    "宜家": "IKEA",
    "欧普": "OPPLE",
    "70迈": "70mai",
    "乐高": "LEGO",
    "艾美特": "Airmate",
    "完美日记": "Perfect Diary",
    "三只松鼠": "Three Squirrels",
    "良品铺子": "Bestore",
    "旺仔": "Want Want",
    "好吃哒": "Haochidai",
    "桂发祥": "Guifaxiang",
}

PRODUCT_TYPE_DISPLAY_NAMES = {
    "nail_polish": {
        "en_GB": "nail polish",
        "de_DE": "Nagellack",
        "fr_FR": "vernis à ongles",
        "nl_NL": "nagellak",
    },
    "shaver_blade": {"en_GB": "replacement blade", "de_DE": "Ersatzklinge", "fr_FR": "lame de rechange", "nl_NL": "vervangmesje"},
    "cutlery_set": {"en_GB": "cutlery set", "de_DE": "Besteckset", "fr_FR": "ménagère", "nl_NL": "bestekset"},
    "marble_egg": {"en_GB": "marble egg ornament", "de_DE": "Marmor-Ei-Dekoration", "fr_FR": "œuf décoratif en marbre", "nl_NL": "marmeren ei-decoratie"},
    "pool_robot": {"en_GB": "pool-cleaning robot", "de_DE": "Poolroboter", "fr_FR": "robot nettoyeur de piscine", "nl_NL": "zwembadrobot"},
    "metal_frame_pool": {"en_GB": "metal-frame paddling pool", "de_DE": "Metallrahmen-Pool", "fr_FR": "piscine tubulaire", "nl_NL": "metalen framezwembad"},
    "mass_gainer": {"en_GB": "mass gainer", "de_DE": "Weight Gainer", "fr_FR": "gainer de masse", "nl_NL": "mass gainer"},
    "noodles": {"en_GB": "noodles", "de_DE": "Nudeln", "fr_FR": "nouilles", "nl_NL": "noedels"},
    "tall_black_cabinet": {"en_GB": "tall black storage cabinet", "de_DE": "hoher schwarzer Aufbewahrungsschrank", "fr_FR": "meuble de rangement haut noir", "nl_NL": "hoge zwarte opbergkast"},
    "black_wardrobe": {"en_GB": "black wardrobe", "de_DE": "schwarzer Kleiderschrank", "fr_FR": "armoire noire", "nl_NL": "zwarte kledingkast"},
}

LOCALIZED_TITLE_DESCRIPTOR_RULES = [
    ("米糕", {"en_GB": "rice cake", "de_DE": "Reiskuchen", "fr_FR": "gâteau de riz", "nl_NL": "rijsttaartje"}),
    ("麻花", {"en_GB": "fried dough twist", "de_DE": "frittiertes Teiggebäck", "fr_FR": "torsade de pâte frite", "nl_NL": "gefrituurde deegtwist"}),
    ("蒸馏白醋", {"en_GB": "white vinegar", "de_DE": "weißer Essig", "fr_FR": "vinaigre blanc", "nl_NL": "witte azijn"}),
    ("特级黑酱油", {"en_GB": "dark soy sauce", "de_DE": "dunkle Sojasauce", "fr_FR": "sauce soja foncée", "nl_NL": "donkere sojasaus"}),
    ("印尼甜酱油", {"en_GB": "sweet soy sauce", "de_DE": "süße Sojasauce", "fr_FR": "sauce soja sucrée", "nl_NL": "zoete sojasaus"}),
    ("健康低卡", {"en_GB": "low-calorie", "de_DE": "kalorienarm", "fr_FR": "peu calorique", "nl_NL": "caloriearm"}),
    ("风干牛肉干", {"en_GB": "beef jerky", "de_DE": "Trockenfleisch", "fr_FR": "bœuf séché", "nl_NL": "gedroogd rundvlees"}),
    ("速冻早餐包子", {"en_GB": "frozen breakfast buns", "de_DE": "tiefgekühlte Frühstücksbrötchen", "fr_FR": "brioches de petit-déjeuner surgelées", "nl_NL": "diepvries-ontbijtbroodjes"}),
    ("速冻水饺早餐", {"en_GB": "frozen breakfast dumplings", "de_DE": "tiefgekühlte Frühstücksteigtaschen", "fr_FR": "raviolis de petit-déjeuner surgelés", "nl_NL": "diepvries-ontbijtdumplings"}),
    ("免打孔", {"en_GB": "no-drill", "de_DE": "ohne Bohren", "fr_FR": "sans perçage", "nl_NL": "zonder boren"}),
    ("长保质期", {"en_GB": "long-shelf-life", "de_DE": "lange haltbar", "fr_FR": "longue conservation", "nl_NL": "lang houdbaar"}),
    ("扫拖", {"en_GB": "vacuum-and-mop", "de_DE": "Saug-Wisch", "fr_FR": "aspirateur-laveur", "nl_NL": "stofzuig-dweil"}),
    ("北欧编织", {"en_GB": "Nordic geometric woven", "de_DE": "nordisch geometrisch gewebt", "fr_FR": "tissé géométrique nordique", "nl_NL": "Scandinavisch geometrisch geweven"}),
    ("现代简约纯色短绒", {"en_GB": "modern plain low-pile", "de_DE": "modern einfarbig kurzflorig", "fr_FR": "moderne uni à poils courts", "nl_NL": "modern effen laagpolig"}),
    ("中古波斯风", {"en_GB": "mid-century Persian", "de_DE": "Mid-Century persisch", "fr_FR": "mid-century persan", "nl_NL": "mid-century Perzisch"}),
    ("现代简约条纹", {"en_GB": "modern striped", "de_DE": "modern gestreift", "fr_FR": "moderne rayé", "nl_NL": "modern gestreept"}),
    ("中古土耳其", {"en_GB": "mid-century Turkish", "de_DE": "Mid-Century türkisch", "fr_FR": "mid-century turc", "nl_NL": "mid-century Turks"}),
    ("植物叶片装饰画", {"en_GB": "botanical leaf", "de_DE": "botanisches Blattmotiv", "fr_FR": "feuillage botanique", "nl_NL": "botanisch bladmotief"}),
    ("黑白线条装饰画", {"en_GB": "black-and-white line", "de_DE": "schwarz-weiße Linien", "fr_FR": "ligne noir et blanc", "nl_NL": "zwart-witte lijn"}),
    ("棉麻窗帘", {"en_GB": "cotton-linen", "de_DE": "Baumwoll-Leinen", "fr_FR": "coton-lin", "nl_NL": "katoen-linnen"}),
    ("亚麻提花窗帘", {"en_GB": "linen jacquard", "de_DE": "Leinen-Jacquard", "fr_FR": "jacquard de lin", "nl_NL": "linnen jacquard"}),
    ("冰丝", {"en_GB": "cool-touch", "de_DE": "kühlend", "fr_FR": "toucher frais", "nl_NL": "koel aanvoelend"}),
    ("弹力绒", {"en_GB": "stretch velvet", "de_DE": "Stretch-Samt", "fr_FR": "velours extensible", "nl_NL": "stretchfluweel"}),
    ("运动吸管水壶", {"en_GB": "straw", "de_DE": "mit Trinkhalm", "fr_FR": "avec paille", "nl_NL": "met rietje"}),
    ("黑胡桃", {"en_GB": "black walnut", "de_DE": "Schwarznuss", "fr_FR": "noyer noir", "nl_NL": "zwart walnoot"}),
    ("白橡木", {"en_GB": "white oak", "de_DE": "Weißeiche", "fr_FR": "chêne blanc", "nl_NL": "wit eiken"}),
    ("藤编", {"en_GB": "rattan", "de_DE": "Rattan", "fr_FR": "rotin", "nl_NL": "rotan"}),
    ("大理石", {"en_GB": "marble", "de_DE": "Marmor", "fr_FR": "marbre", "nl_NL": "marmer"}),
    ("哑光烤漆", {"en_GB": "matte lacquer", "de_DE": "Mattlack", "fr_FR": "laque mate", "nl_NL": "matte lak"}),
    ("胡桃木", {"en_GB": "walnut", "de_DE": "Nussbaum", "fr_FR": "noyer", "nl_NL": "walnoot"}),
    ("三脚架", {"en_GB": "tripod", "de_DE": "Dreibein", "fr_FR": "trépied", "nl_NL": "driepoot"}),
    ("绿色陶瓷", {"en_GB": "green ceramic", "de_DE": "grüne Keramik", "fr_FR": "céramique verte", "nl_NL": "groen keramiek"}),
    ("植物标本", {"en_GB": "botanical", "de_DE": "botanisch", "fr_FR": "botanique", "nl_NL": "botanisch"}),
    ("复古海报", {"en_GB": "vintage poster", "de_DE": "Vintage-Poster", "fr_FR": "affiche vintage", "nl_NL": "vintageposter"}),
    ("城市建筑", {"en_GB": "city architecture", "de_DE": "Stadtarchitektur", "fr_FR": "architecture urbaine", "nl_NL": "stadsarchitectuur"}),
    ("钢化玻璃", {"en_GB": "tempered glass", "de_DE": "Hartglas", "fr_FR": "verre trempé", "nl_NL": "gehard glas"}),
    ("弧形", {"en_GB": "arched", "de_DE": "bogenförmig", "fr_FR": "arqué", "nl_NL": "gebogen"}),
    ("球形", {"en_GB": "globe", "de_DE": "Kugel", "fr_FR": "globe", "nl_NL": "bolvormig"}),
    ("蘑菇", {"en_GB": "mushroom", "de_DE": "Pilzform", "fr_FR": "champignon", "nl_NL": "paddenstoel"}),
    ("铜色", {"en_GB": "brass", "de_DE": "Messing", "fr_FR": "laiton", "nl_NL": "messing"}),
    ("抽象", {"en_GB": "abstract", "de_DE": "abstrakt", "fr_FR": "abstrait", "nl_NL": "abstract"}),
]


def _localized_brand_name(brand: str) -> str:
    localized = BRAND_DISPLAY_NAMES.get(brand, brand)
    if re.search(r"[\u4e00-\u9fff]", localized):
        return ""
    return localized


@lru_cache(maxsize=32768)
def _normalize_search_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", normalized).strip()


def _search_alias_matches(normalized_query: str, alias: str) -> bool:
    normalized_alias = _normalize_search_text(alias)
    if not normalized_alias:
        return False
    if re.search(r"[\u4e00-\u9fff]", normalized_alias):
        return normalized_alias in normalized_query
    return bool(_compiled_alias_pattern(normalized_alias).search(normalized_query))


@lru_cache(maxsize=8192)
def _compiled_alias_pattern(normalized_alias: str) -> re.Pattern:
    return re.compile(
        rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])",
        flags=re.IGNORECASE,
    )


def _longest_alias_match(
    normalized_query: str,
    aliases_by_key: Sequence[tuple[str, Sequence[str]]],
) -> Optional[str]:
    best_key = None
    best_length = -1
    for key, aliases in aliases_by_key:
        for alias in aliases:
            if not _search_alias_matches(normalized_query, alias):
                continue
            alias_length = len(_normalize_search_text(alias))
            if alias_length > best_length:
                best_key = key
                best_length = alias_length
    return best_key


def _specialized_product_marker_groups(query: str) -> List[Sequence[str]]:
    normalized_query = _normalize_search_text(query)
    matched_groups = []
    for index, (query_markers, product_markers) in enumerate(SPECIALIZED_PRODUCT_FILTERS):
        best_length = -1
        for marker in query_markers:
            if not _search_alias_matches(normalized_query, marker):
                continue
            marker_length = len(_normalize_search_text(marker))
            if marker_length > best_length:
                best_length = marker_length
        if best_length >= 0:
            matched_groups.append((best_length, index, product_markers))
    matched_groups.sort(key=lambda item: (-item[0], item[1]))
    return [product_markers for _, _, product_markers in matched_groups]


def has_fail_closed_specialized_intent(query: str) -> bool:
    return bool(_specialized_product_marker_groups(query))


def has_fail_closed_recall_intent(query: str) -> bool:
    normalized_query = _normalize_search_text(query)
    has_no_stock_marker = any(
        _normalize_search_text(keyword) in normalized_query
        or normalized_query in _normalize_search_text(keyword)
        for keyword in NO_STOCK_KEYWORDS
    )
    return has_no_stock_marker or has_fail_closed_specialized_intent(query)


def resolve_site_config(site_context: Any = None) -> Optional[Dict[str, Any]]:
    if not site_context:
        return None
    if isinstance(site_context, str):
        site_code = site_context
        overrides = {}
    else:
        site_code = site_context.get("site_code")
        overrides = dict(site_context)
    base = SITE_CONFIGS.get(site_code)
    if not base:
        return None
    return {"site_code": site_code, **overrides, **base}


def _extract_model_name(product: Dict[str, Any]) -> str:
    title = str(product.get("title", ""))
    brand = str(product.get("brand", ""))
    title_without_brand = title.replace(brand, " ")
    title_without_brand = re.sub(r"(\d+)\s*合\s*1", r"\1-in-1", title_without_brand)
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9+.:/°×-]*", title_without_brand)
    ignored = {
        "tv", "led", "oled", "uhd", "ips", "wifi", "usb", "max",
        "4k", "mini", "qled",
    }
    screen_sizes = {
        match.group(1)
        for match in re.finditer(r"(\d{2,3}(?:\.\d+)?)\s*(?:英寸|寸)", title)
    }
    localized_unit_numbers = {
        match.group(1)
        for match in re.finditer(r"(\d+(?:\.\d+)?)\s*匹", title)
    }
    useful = [
        token
        for token in tokens
        if token.lower() not in ignored
        and token not in screen_sizes
        and token not in localized_unit_numbers
    ]
    if useful:
        return " ".join(useful[:3])

    product_id = str(product.get("product_id", ""))
    if product_id.startswith("jd_match_"):
        return ""
    id_tokens = [
        token
        for token in re.split(r"[_-]+", product_id)
        if token and token.lower() not in {"jd", "mock", "product"}
    ]
    return " ".join(token.upper() for token in id_tokens[-2:])


def _localized_title_descriptor(product: Dict[str, Any], language: str) -> str:
    source = (
        f"{product.get('title', '')} {product.get('key_specs', '')} "
        f"{product.get('description', '')}"
    )
    for marker, translations in LOCALIZED_TITLE_DESCRIPTOR_RULES:
        if marker in source:
            return translations[language]
    return ""


def _extract_product_identifier(product: Dict[str, Any]) -> str:
    product_id = str(product.get("product_id", ""))
    tokens = [token for token in re.split(r"[_-]+", product_id) if token]
    if tokens and tokens[0].lower() in {"jd", "mock"}:
        tokens = tokens[1:]
    if not tokens or tokens[0].lower() in {
        "default", "product", "match", "table", "lamp", "rug", "art",
    }:
        return ""
    return tokens[0].upper()


def _localized_product_title(
    product: Dict[str, Any],
    category: str,
    site_config: Dict[str, Any],
) -> str:
    language = site_config["site_lang_code"]
    product_type = str(product.get("product_type", ""))
    category_name = PRODUCT_TYPE_DISPLAY_NAMES.get(product_type, {}).get(language)
    raw_title = str(product.get("title", ""))
    raw_source = (
        f"{raw_title} {product.get('key_specs', '')} {product.get('description', '')}"
    )
    if category == "键盘鼠标" and not category_name:
        if "键鼠" in raw_title:
            category_name = {
                "en_GB": "keyboard and mouse set",
                "de_DE": "Tastatur-Maus-Set",
                "fr_FR": "ensemble clavier-souris",
                "nl_NL": "toetsenbord-muisset",
            }[language]
        elif "鼠标" in raw_title:
            category_name = {
                "en_GB": "mouse",
                "de_DE": "Maus",
                "fr_FR": "souris",
                "nl_NL": "muis",
            }[language]
    if category == "数据线" and ("转3.5mm" in raw_source or "音频转接器" in raw_source):
        category_name = {
            "en_GB": "USB-C audio adapter",
            "de_DE": "USB-C-Audioadapter",
            "fr_FR": "adaptateur audio USB-C",
            "nl_NL": "USB-C-audioadapter",
        }[language]
    if category == "行车记录仪" and ("前后双录" in raw_source or "4K双录" in raw_source):
        category_name = {
            "en_GB": "front-and-rear dash cam",
            "de_DE": "Front- und Heck-Dashcam",
            "fr_FR": "caméra embarquée avant-arrière",
            "nl_NL": "dashcam voor en achter",
        }[language]
    if category == "洗衣液" and "机洗" in raw_source:
        category_name = {
            "en_GB": "machine-wash laundry detergent",
            "de_DE": "Maschinenwaschmittel",
            "fr_FR": "lessive pour machine",
            "nl_NL": "machinewasmiddel",
        }[language]
    if category == "儿童玩具" and "编程" in raw_source:
        category_name = {
            "en_GB": "STEM coding toy",
            "de_DE": "MINT-Programmierspielzeug",
            "fr_FR": "jouet éducatif de programmation",
            "nl_NL": "STEM-programmeerspeelgoed",
        }[language]
    elif category == "儿童玩具" and "拼图" in raw_source:
        category_name = {
            "en_GB": "educational puzzle",
            "de_DE": "Lernpuzzle",
            "fr_FR": "puzzle éducatif",
            "nl_NL": "educatieve puzzel",
        }[language]
    if category == "风扇" and "落地扇" in raw_source:
        category_name = {
            "en_GB": "pedestal fan",
            "de_DE": "Standventilator",
            "fr_FR": "ventilateur sur pied",
            "nl_NL": "staande ventilator",
        }[language]
    if category == "风扇" and (
        "塔式风扇" in raw_source
        or ("TP07" in raw_source and "无叶" in raw_source)
    ):
        category_name = {
            "en_GB": "tower fan",
            "de_DE": "Turmventilator",
            "fr_FR": "ventilateur colonne",
            "nl_NL": "torenventilator",
        }[language]
    if category == "空调" and ("低噪" in raw_source or "静音" in raw_source):
        category_name = {
            "en_GB": "low-noise air conditioner",
            "de_DE": "leise Klimaanlage",
            "fr_FR": "climatiseur silencieux",
            "nl_NL": "stille airconditioner",
        }[language]
    if category == "彩妆" and ("国货" in raw_source or "中国品牌" in raw_source):
        category_name = {
            "en_GB": "Chinese make-up",
            "de_DE": "chinesisches Make-up",
            "fr_FR": "maquillage chinois",
            "nl_NL": "Chinese make-up",
        }[language]
    if category == "儿童玩具" and ("漂移车" in raw_source or "漂移胎" in raw_source):
        category_name = {
            "en_GB": "RC drift car",
            "de_DE": "RC-Driftauto",
            "fr_FR": "voiture RC de drift",
            "nl_NL": "RC-driftauto",
        }[language]
    if category == "人体工学椅" and ("电竞椅" in raw_source or "gaming" in raw_source.lower()):
        category_name = {
            "en_GB": "gaming chair",
            "de_DE": "Gamingstuhl",
            "fr_FR": "chaise gaming",
            "nl_NL": "gamestoel",
        }[language]
    if not category_name:
        category_name = CATEGORY_DISPLAY_NAMES.get(category, {}).get(language)
    if not category_name:
        category_name = {
            "en_GB": "product",
            "de_DE": "Produkt",
            "fr_FR": "produit",
            "nl_NL": "product",
        }[language]
    raw_brand = str(product.get("brand", ""))
    brand = _localized_brand_name(raw_brand)
    model = _extract_model_name(product)
    descriptor = _localized_title_descriptor(product, language)
    if str(product.get("product_id", "")).startswith("jd_match_") and descriptor:
        if descriptor.lower() not in model.lower():
            model = f"{descriptor} {model}".strip()
    elif descriptor and category in {"调味品", "零食", "速冻食品", "主食粮油", "扫地机"}:
        category_name = f"{descriptor} {category_name}".strip()
    elif not model:
        model = descriptor
    if not brand:
        identifier = _extract_product_identifier(product)
        if identifier and identifier.lower() not in model.lower():
            model = f"{identifier} {model}".strip()
    specs = str(product.get("key_specs", ""))
    size_match = re.search(r"(\d{2,3}(?:\.\d+)?)\s*寸", specs)
    size = size_match.group(1) if size_match else ""
    features = []
    for feature in ("4K", "OLED", "Mini LED", "QLED"):
        if feature.lower() in specs.lower() or feature.lower() in str(product.get("title", "")).lower():
            features.append(feature)
    if category == "电视":
        if "Google TV" in raw_source:
            features.append("Google TV")
        elif "Android TV" in raw_source:
            features.append("Android TV")
        refresh_match = re.search(r"\b(120|144)\s*Hz\b", raw_source, flags=re.IGNORECASE)
        if refresh_match:
            features.append(f"{refresh_match.group(1)}Hz")
        if "智能电视" in raw_source and not any("TV" in feature for feature in features):
            features.append("Smart TV")
    if category == "显示器" and re.search(r"G-Sync", raw_source, flags=re.IGNORECASE):
        features.append("G-Sync")
    if category == "儿童玩具" and ("漂移车" in raw_source or "漂移胎" in raw_source):
        if "陀螺仪" in raw_source:
            features.append({
                "en_GB": "gyro",
                "de_DE": "Gyro",
                "fr_FR": "gyroscope",
                "nl_NL": "gyro",
            }[language])
        if "可升级底盘" in raw_source:
            features.append({
                "en_GB": "upgradeable chassis",
                "de_DE": "aufrüstbares Chassis",
                "fr_FR": "châssis évolutif",
                "nl_NL": "upgradebaar chassis",
            }[language])
    attributes = []
    if size:
        unit = {"en_GB": "inch", "de_DE": "Zoll", "fr_FR": "pouces", "nl_NL": "inch"}[language]
        attributes.append(f"{size} {unit}")
    capacity_match = re.search(
        r"(\d+(?:\.\d+)?)\s*匹",
        f"{product.get('title', '')} {specs}",
    )
    if capacity_match:
        capacity = capacity_match.group(1)
        if language in {"de_DE", "fr_FR", "nl_NL"}:
            capacity = capacity.replace(".", ",")
        unit = {
            "en_GB": "HP",
            "de_DE": "PS",
            "fr_FR": "CV",
            "nl_NL": "pk",
        }[language]
        attributes.append(f"{capacity} {unit}")
    attributes.extend(dict.fromkeys(features))
    details = " ".join(part for part in [brand, model, *attributes] if part).strip()
    if language == "fr_FR":
        return f"{category_name} {details}".strip()
    return f"{details} {category_name}".strip()


def _localized_price(price_cny: float, site_config: Dict[str, Any]) -> str:
    converted = price_cny * float(site_config["price_rate"])
    localized = max(0.99, int(converted) + 0.99)
    return f"{localized:.2f}"


def _parse_sales_count(sales: str) -> int:
    match = re.search(r"([\d.]+)\s*万", sales)
    if match:
        return int(float(match.group(1)) * 10000)
    digits = re.search(r"([\d,]+)", sales)
    return int(digits.group(1).replace(",", "")) if digits else 0


def _localized_sales(sales: str, site_config: Dict[str, Any]) -> str:
    count = _parse_sales_count(sales)
    language = site_config["site_lang_code"]
    formatted = f"{count:,}"
    if language in {"de_DE", "nl_NL"}:
        formatted = formatted.replace(",", ".")
    elif language == "fr_FR":
        formatted = formatted.replace(",", " ")
    suffix = {
        "en_GB": "sold",
        "de_DE": "verkauft",
        "fr_FR": "vendus",
        "nl_NL": "verkocht",
    }[language]
    return f"{formatted}+ {suffix}" if count else sales


def _contract_sku_id(raw_id: str) -> str:
    if raw_id.isdigit():
        return raw_id
    digest = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()
    return str(10_000_000 + int(digest[:10], 16) % 90_000_000)


def invalid_specialized_product_ids(
    query: str,
    products: Sequence[Dict[str, Any]],
) -> List[str]:
    product_marker_groups = _specialized_product_marker_groups(query)
    if not product_marker_groups or not products:
        return []

    raw_by_sku = _raw_products_by_sku()

    invalid = []
    for product in products:
        sku_id = str(product.get("sku_id", ""))
        raw_product = raw_by_sku.get(sku_id)
        source = raw_product or product
        normalized_source = _normalize_search_text(
            f"{source.get('title', '')} {source.get('sku_name', '')} "
            f"{source.get('brand', '')} {source.get('brand_name', '')} "
            f"{source.get('key_specs', '')} {source.get('description', '')}"
        )
        if any(
            not any(
                _normalize_search_text(marker) in normalized_source
                for marker in product_markers
            )
            for product_markers in product_marker_groups
        ):
            invalid.append(sku_id)
    return invalid


def _contract_product(
    product: Dict[str, Any],
    category: str,
    query: str,
    site_context: Any = None,
) -> Dict[str, Any]:
    raw_id = str(product.get("product_id", ""))
    sku_id = _contract_sku_id(raw_id)

    final_price = float(product.get("price", 0))
    original_price = float(product.get("original_price", final_price))
    sku_name = product.get("title", "")
    brand_name = product.get("brand", "")
    sales = product.get("sales", "")
    site_config = resolve_site_config(site_context)
    if site_config:
        sku_name = _localized_product_title(product, category, site_config)
        brand_name = _localized_brand_name(str(brand_name))
        final_price = _localized_price(final_price, site_config)
        original_price = _localized_price(original_price, site_config)
        sales = _localized_sales(str(sales), site_config)
    return {
        "sku_id": sku_id,
        "sku_name": sku_name,
        "brand_name": brand_name,
        "final_price": f"{float(final_price):.2f}",
        "price": f"{float(original_price):.2f}",
        "img_url": f"mock/products/{sku_id}.jpg",
        "good": None,
        "sales": sales,
        "keyword": query,
    }



MOCK_PRODUCTS: Dict[str, List[Dict]] = {
    "降噪耳机": [
        {"product_id": "jd_sony_wf_c700n", "title": "索尼WF-C700N 真无线降噪耳机 黑色",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销2.2万",
         "key_specs": "主动降噪42dB/IPX4防水/7.5h续航/LDAC高清音频/重量5.4g",
         "brand": "索尼", "category": "耳机",
         "description": "WF-C700N搭载高解析度降噪处理器，消噪效果出色，LDAC支持高清蓝牙音频传输，适合通勤和日常使用。"},
        {"product_id": "jd_bose_qcearbuds2", "title": "Bose QuietComfort Earbuds II 消噪耳塞",
         "price": 1799.0, "original_price": 1999.0, "rating": 4.9, "sales": "月销3500",
         "key_specs": "顶级主动降噪/6h续航/个性化降噪/IPX4/耳型适配",
         "brand": "Bose", "category": "耳机",
         "description": "Bose旗舰降噪耳塞，业界领先降噪性能，个性化耳型适配系统，6小时续航+24小时充电盒。"},
        {"product_id": "jd_edifier_tws1pro2", "title": "漫步者TWS1 Pro 2 主动降噪耳机",
         "price": 299.0, "original_price": 399.0, "rating": 4.7, "sales": "月销8500",
         "key_specs": "主动降噪35dB/通透模式/10h续航/Type-C充电/半入耳",
         "brand": "漫步者", "category": "耳机",
         "description": "漫步者TWS1 Pro2，35dB主动降噪，10小时长续航，适合预算有限用户。"},
        {"product_id": "jd_airpods_pro2", "title": "苹果AirPods Pro 2代 主动降噪",
         "price": 1299.0, "original_price": 1499.0, "rating": 4.9, "sales": "月销1.5万",
         "key_specs": "H2芯片/自适应透明模式/30h总续航/MagSafe/个性化空间音频",
         "brand": "苹果", "category": "耳机",
         "description": "AirPods Pro第2代，搭载H2芯片，降噪性能提升2倍，自适应透明模式，适合苹果生态用户。"},
        {"product_id": "jd_anker_q45", "title": "Anker Q45 头戴式主动降噪耳机",
         "price": 259.0, "original_price": 329.0, "rating": 4.7, "sales": "月销1.1万",
         "key_specs": "主动降噪/60h超长续航/折叠/多设备同连/蓝牙5.3",
         "brand": "Anker", "category": "耳机",
         "description": "Anker Q45头戴式降噪耳机，60小时超长续航，多设备无缝切换，轻量折叠便携，性价比极高的降噪入门之选。"},
        {"product_id": "jd_huawei_freebuds5i", "title": "华为FreeBuds 5i 主动降噪耳机",
         "price": 499.0, "original_price": 599.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "强力主动降噪/通透模式/9h续航/IP54防水/多设备连接",
         "brand": "华为", "category": "耳机",
         "description": "华为FreeBuds 5i，强力主动降噪多档可调，Hi-Res Audio认证高清音质，IP54防水，支持华为/安卓/iOS全平台。"},
        {"product_id": "jd_sony_wf1000xm5", "title": "索尼 WF-1000XM5 入耳式降噪耳机",
         "price": 1499.0, "original_price": 1799.0, "rating": 4.9, "sales": "月销6800",
         "key_specs": "入耳式密封/行业顶级主动降噪/零漏音设计/8h续航/LDAC/IPX4",
         "brand": "索尼", "category": "耳机",
         "description": "索尼WF-1000XM5旗舰入耳式降噪耳机，全封闭入耳设计实现零漏音，HD降噪处理器QN2e行业顶级降噪，LDAC高清传输，适合通勤和高要求听觉场景。"},
        {"product_id": "jd_jbl_tour_pro2", "title": "JBL Tour Pro 2 真无线入耳降噪耳机",
         "price": 699.0, "original_price": 999.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "入耳式密封零漏音/主动降噪ANC/智能触控屏充电仓/10h续航/三点式入耳稳固",
         "brand": "JBL", "category": "耳机",
         "description": "JBL Tour Pro 2，三点式入耳稳固贴合外耳道，密封性出众实现零漏音，ANC主动降噪，充电仓内置智能触控屏可直接调节设置。"},
        {"product_id": "jd_jabra_elite10", "title": "Jabra Elite 10 入耳降噪耳机 旗舰",
         "price": 1299.0, "original_price": 1599.0, "rating": 4.8, "sales": "月销3100",
         "key_specs": "入耳式密封/ComfortFit贴合耳道/主动降噪/全天候音频/8h续航/IP57",
         "brand": "Jabra", "category": "耳机",
         "description": "Jabra Elite 10，ComfortFit技术贴合耳道密封性极佳，彻底解决漏音问题，主动降噪模式专注工作，IP57防水，适合商务和日常使用。"},
    ],
    "保温杯": [
        {"product_id": "jd_zojirushi_sm_khe48", "title": "象印SM-KHE48 保温杯 480ml",
         "price": 199.0, "original_price": 249.0, "rating": 4.9, "sales": "月销1.8万",
         "key_specs": "304不锈钢/6小时保温70℃/24小时保温40℃/轻量化/一键开盖",
         "brand": "象印", "category": "保温杯",
         "description": "象印经典保温杯，6小时保温实测70℃以上，轻量设计携带方便，日本进口品质。"},
        {"product_id": "jd_tiger_mhk_a050", "title": "虎牌MHK-A050 保温杯 500ml",
         "price": 229.0, "original_price": 299.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "真空双层304不锈钢/一键开盖/24h保温/轻量/多色可选",
         "brand": "虎牌", "category": "保温杯",
         "description": "虎牌经典款，一键开盖设计，24小时长效保温，304不锈钢内胆安全无味。"},
        {"product_id": "jd_thermos_jnl502", "title": "膳魔师JNL-502 保温杯 500ml 哑光黑",
         "price": 169.0, "original_price": 229.0, "rating": 4.8, "sales": "月销3.5万",
         "key_specs": "316不锈钢/双层真空/24h保温/轻量190g/防漏",
         "brand": "膳魔师", "category": "保温杯",
         "description": "膳魔师热销款，316高级不锈钢内胆，24小时保温，仅重190g，是同价位性价比最高的选择。"},
        {"product_id": "jd_stanley_classic", "title": "Stanley 经典系列 保温杯 470ml 绿色",
         "price": 299.0, "original_price": 359.0, "rating": 4.9, "sales": "月销9800",
         "key_specs": "18/8不锈钢/24h保冷/终身保修/316食品级/BPA-Free",
         "brand": "Stanley", "category": "保温杯",
         "description": "Stanley百年经典保温杯，终身保修承诺，24小时保冷保冰，316不锈钢食品安全，颜色丰富深受年轻人喜爱。"},
        {"product_id": "jd_xiaomi_miga500", "title": "小米MIGA 保温杯 500ml 星空黑",
         "price": 99.0, "original_price": 139.0, "rating": 4.7, "sales": "月销4.2万",
         "key_specs": "316不锈钢/一键弹盖/12h保温/轻量230g/多色",
         "brand": "小米", "category": "保温杯",
         "description": "小米MIGA保温杯，316食品级不锈钢，一键弹盖单手操作，12小时保温，百元内最高性价比之选。"},
        {"product_id": "jd_fuguang_680ml", "title": "富光 运动保温杯 680ml 大容量",
         "price": 79.0, "original_price": 119.0, "rating": 4.6, "sales": "月销5.8万",
         "key_specs": "304不锈钢/大容量680ml/运动盖/防摔/提手设计",
         "brand": "富光", "category": "保温杯",
         "description": "富光大容量运动保温杯，680ml满足健身全程补水，运动盖单手可开，防摔设计适合户外使用，高性价比入门首选。"},
        {"product_id": "jd_zojirushi_sm_sf48", "title": "象印 SM-SF48 超级保温杯 480ml",
         "price": 299.0, "original_price": 369.0, "rating": 4.9, "sales": "月销9800",
         "key_specs": "48h超长保温/真空双层/超级不锈钢内胆/轻量200g/防漏一键开盖",
         "brand": "象印", "category": "保温杯",
         "description": "象印SM-SF48超级保温杯，采用最新真空绝热技术，实测48小时保温仍达55℃以上，超越普通保温杯3倍保温时长，解决保温时间短的痛点。"},
        {"product_id": "jd_tiger_mto_a050", "title": "虎牌 MTO-A050 超长保温杯 500ml",
         "price": 259.0, "original_price": 329.0, "rating": 4.9, "sales": "月销7600",
         "key_specs": "最高48h保温/Supa Bottle真空技术/304不锈钢/200g轻量/防漏",
         "brand": "虎牌", "category": "保温杯",
         "description": "虎牌MTO-A050，搭载Supa Bottle超级真空保温技术，48小时仍可保温，相比普通款保温时间翻倍，适合想彻底解决保温短暂问题的用户。"},
    ],
    "人体工学椅": [
        {"product_id": "jd_xihao_m57", "title": "西昊 M57 人体工学椅 入门款",
         "price": 799.0, "original_price": 999.0, "rating": 4.7, "sales": "月销2.1万",
         "key_specs": "2D扶手/腰托/透气网背/可躺120°/承重120kg",
         "brand": "西昊", "category": "椅子",
         "description": "西昊M57入门款人体工学椅，高性价比之选，2D扶手+腰托基础配置，透气网背久坐不闷，适合学生和初入职场人群。"},
        {"product_id": "jd_xihao_c300", "title": "西昊 Doro C300 人体工学椅 黑色",
         "price": 1499.0, "original_price": 1799.0, "rating": 4.9, "sales": "月销1.2万",
         "key_specs": "4D扶手/腰托/透气网布/可躺130°/承重150kg/5年保修",
         "brand": "西昊", "category": "椅子",
         "description": "西昊C300人体工学椅，4D全向扶手调节，独立腰托支撑，全透气网面，久坐不闷热，适合居家办公。"},
        {"product_id": "jd_baoyou_e2", "title": "保友金豪E2 人体工学椅 精英版",
         "price": 1999.0, "original_price": 2399.0, "rating": 4.8, "sales": "月销4500",
         "key_specs": "联动扶手/腰托头枕全可调/透气网背/10年保修",
         "brand": "保友", "category": "椅子",
         "description": "保友金豪E2精英版，联动扶手跟随坐姿调节，腰托和头枕独立可调，适合长时间工作。"},
        {"product_id": "jd_netease_c1", "title": "网易严选 云鲸C1 人体工学椅",
         "price": 1299.0, "original_price": 1599.0, "rating": 4.8, "sales": "月销6800",
         "key_specs": "3D扶手/独立腰托/透气网背/可躺125°/5档高度调节",
         "brand": "网易严选", "category": "椅子",
         "description": "网易严选云鲸C1，高性价比之选，3D扶手多向调节，独立腰托贴合脊椎曲线，透气网背散热，适合长时间办公。"},
        {"product_id": "jd_okamura_sylphy", "title": "冈村 Sylphy Light 人体工学椅 基础款",
         "price": 2499.0, "original_price": 2999.0, "rating": 4.9, "sales": "月销2200",
         "key_specs": "日本原装/自适应腰托/4D扶手/悬挂式网背/15年保修",
         "brand": "冈村", "category": "椅子",
         "description": "冈村Sylphy Light日本进口人体工学椅，自适应腰托随体型自动调节，悬挂式网背减压，15年品质保修，商务旗舰之选。"},
        {"product_id": "jd_hermanmiller_aeron", "title": "Herman Miller Aeron 人体工学椅 B码",
         "price": 8999.0, "original_price": 9999.0, "rating": 4.9, "sales": "月销800",
         "key_specs": "PostureFit SL腰骶支撑/8Z Pellicle网面/全铝底座/12年保修/可调前倾",
         "brand": "Herman Miller", "category": "椅子",
         "description": "Herman Miller Aeron经典人体工学椅，PostureFit SL专利腰骶支撑，8Z Pellicle网面均匀分散压力，12年保修，顶级办公椅代名词。"},
        {"product_id": "jd_xihao_m89_lumbar", "title": "西昊 M89 Plus 独立腰托人体工学椅",
         "price": 899.0, "original_price": 1199.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "独立腰托上下可调/3D扶手/透气网背/可躺125°/护腰专为久坐设计",
         "brand": "西昊", "category": "椅子",
         "description": "西昊M89 Plus，独立腰托可上下调节精准贴合每个人的腰椎曲线，专门针对久坐腰疼问题设计，3D扶手减轻肩颈压力，同价位腰托最强配置。"},
        {"product_id": "jd_gaoteng_c3_lumbar", "title": "高藤 C3 人体工学椅 腰托版 护腰款",
         "price": 1099.0, "original_price": 1399.0, "rating": 4.8, "sales": "月销8900",
         "key_specs": "S型独立腰枕/4D扶手/联动靠背/透气网背/可躺130°/5年保修",
         "brand": "高藤", "category": "椅子",
         "description": "高藤C3腰托版，S型独立腰枕精准贴合腰椎弧度，彻底解决久坐腰疼问题，4D扶手全方位调节，联动靠背跟随身体自然运动，高性价比腰部护理首选。"},
    ],
    "扫地机": [
        {"product_id": "jd_roborock_s8pro", "title": "石头扫地机器人S8 Pro Ultra 全能站",
         "price": 3999.0, "original_price": 4499.0, "rating": 4.9, "sales": "月销8500",
         "key_specs": "激光导航/6000Pa吸力/自动集尘+洗拖布+烘干/双边刷",
         "brand": "石头", "category": "扫地机",
         "description": "石头S8 Pro Ultra，全功能基站实现自动集尘、洗拖布、烘干，激光导航精准建图，适合全屋清洁。"},
        {"product_id": "jd_ecovacs_x2_omni", "title": "科沃斯X2 Omni 扫拖一体机器人",
         "price": 3599.0, "original_price": 3999.0, "rating": 4.8, "sales": "月销6200",
         "key_specs": "TrueMapping2.0激光导航/8000Pa/自动上下水/热风烘干",
         "brand": "科沃斯", "category": "扫地机",
         "description": "科沃斯X2 Omni，8000Pa强力吸尘，支持自动上下水，热风烘干防异味，旗舰级扫拖机器人。"},
        {"product_id": "jd_dreame_l20ultra", "title": "追觅 L20 Ultra 扫拖一体机器人",
         "price": 4999.0, "original_price": 5999.0, "rating": 4.9, "sales": "月销4100",
         "key_specs": "7000Pa/仿生双臂拖地/自动加水/热风烘干/AI识物避障",
         "brand": "追觅", "category": "扫地机",
         "description": "追觅L20 Ultra旗舰款，7000Pa超强吸力，仿生双臂深度清洁，AI识物避障精准绕行，自动加水热风烘干全自动。"},
        {"product_id": "jd_xiaomi_omni_s10", "title": "小米扫拖机器人 S10+ 全能版",
         "price": 1999.0, "original_price": 2499.0, "rating": 4.8, "sales": "月销1.3万",
         "key_specs": "4000Pa吸力/激光导航/自动集尘/米家APP/LDS激光",
         "brand": "小米", "category": "扫地机",
         "description": "小米S10+全能版，4000Pa强力吸尘，自动集尘基站告别频繁倒垃圾，米家APP智能控制，高性价比全能扫拖机器人。"},
        {"product_id": "jd_roborock_q7max", "title": "石头 Q7 Max+ 扫拖机器人",
         "price": 2499.0, "original_price": 2999.0, "rating": 4.8, "sales": "月销9200",
         "key_specs": "4200Pa/激光导航/自动集尘/拖布升降/多层地图",
         "brand": "石头", "category": "扫地机",
         "description": "石头Q7 Max+，4200Pa吸力搭配自动集尘基站，拖布遇地毯自动抬升，多层地图管理，中端性价比旗舰之选。"},
        {"product_id": "jd_irobot_roomba_j7", "title": "iRobot Roomba j7+ 扫地机器人",
         "price": 2999.0, "original_price": 3599.0, "rating": 4.7, "sales": "月销3100",
         "key_specs": "PrecisionVision/自动避障/自动集尘/Imprint智能地图/10倍吸力",
         "brand": "iRobot", "category": "扫地机",
         "description": "iRobot Roomba j7+，PrecisionVision AI视觉识别障碍物，自动避开电线宠物粪便，自动集尘，智能家居联动能力强。"},
        {"product_id": "jd_dreame_d10plus", "title": "追觅 D10 Plus 扫拖一体 5000Pa强吸力",
         "price": 1999.0, "original_price": 2499.0, "rating": 4.8, "sales": "月销1.1万",
         "key_specs": "5000Pa超强吸力/激光导航/自动集尘/拖布升降/多地图",
         "brand": "追觅", "category": "扫地机",
         "description": "追觅D10 Plus，5000Pa超强吸力有效清洁地毯毛发和顽固污垢，相比普通款吸力提升25%，激光导航精准建图，解决吸力不足痛点的中端首选。"},
        {"product_id": "jd_roborock_s8_6000pa", "title": "石头 S8 扫拖机器人 6000Pa 自动上下水",
         "price": 2799.0, "original_price": 3299.0, "rating": 4.8, "sales": "月销7500",
         "key_specs": "6000Pa强力吸尘/双振动拖地/激光导航/自动集尘/拖布自动清洗",
         "brand": "石头", "category": "扫地机",
         "description": "石头S8，6000Pa强劲吸力深入地毯纤维，双边刷+主刷彻底清扫边角，双振动拖地高频摩擦去除污渍，集尘基站自动清洗拖布，吸拖一体省心首选。"},
    ],
    "蓝牙耳机": [
        {"product_id": "jd_jbl_t670nc", "title": "JBL Tune 670NC 无线降噪耳机 黑色",
         "price": 249.0, "original_price": 349.0, "rating": 4.7, "sales": "月销1.8万",
         "key_specs": "主动降噪ANC/50h超长续航/折叠收纳/38mm大动圈/蓝牙5.3",
         "brand": "JBL", "category": "蓝牙耳机",
         "description": "JBL Tune 670NC头戴式蓝牙耳机，主动降噪让你专注其中，50小时超长续航满足全天使用需求，轻量折叠设计便于携带。"},
        {"product_id": "jd_jabra_elite4act", "title": "Jabra Elite 4 Active 防水运动耳机",
         "price": 299.0, "original_price": 399.0, "rating": 4.8, "sales": "月销9500",
         "key_specs": "IP57防水防汗/主动降噪/7h续航/4麦克风通话/运动专属设计",
         "brand": "Jabra", "category": "蓝牙耳机",
         "description": "Jabra Elite 4 Active专为运动设计，IP57级防水防汗，主动降噪帮助专注训练，4麦克风系统保障运动通话清晰。"},
        {"product_id": "jd_qcy_t13", "title": "QCY T13 真无线蓝牙耳机 白色",
         "price": 109.0, "original_price": 149.0, "rating": 4.6, "sales": "月销4.2万",
         "key_specs": "蓝牙5.1/13mm大动圈/40h总续航/IPX5防水/手机APP调节",
         "brand": "QCY", "category": "蓝牙耳机",
         "description": "QCY T13入门级真无线耳机，超高性价比，13mm大动圈音质出色，40小时超长续航，支持手机APP个性化调节。"},
        {"product_id": "jd_sony_wh1000xm5", "title": "索尼 WH-1000XM5 头戴式蓝牙耳机",
         "price": 2099.0, "original_price": 2499.0, "rating": 4.9, "sales": "月销1.2万",
         "key_specs": "业界顶级降噪/30h续航/自适应声音控制/多点连接/快充",
         "brand": "索尼", "category": "蓝牙耳机",
         "description": "索尼WH-1000XM5，采用两颗处理器和8个麦克风实现业界最高降噪，30小时超长续航，自适应声音控制智能切换，顶级头戴降噪体验。"},
        {"product_id": "jd_samsung_buds2pro", "title": "三星 Galaxy Buds2 Pro 旗舰降噪耳机",
         "price": 999.0, "original_price": 1299.0, "rating": 4.8, "sales": "月销6800",
         "key_specs": "主动降噪/360°空间音频/IPX7/5h续航/三星设备无缝切换",
         "brand": "三星", "category": "蓝牙耳机",
         "description": "三星Galaxy Buds2 Pro，360°空间音频沉浸体验，IPX7防水，与三星手机/平板/PC无缝切换，适合三星生态用户。"},
        {"product_id": "jd_beats_fitpro", "title": "Beats Fit Pro 主动降噪运动耳机",
         "price": 1299.0, "original_price": 1499.0, "rating": 4.8, "sales": "月销5200",
         "key_specs": "H1芯片/主动降噪/翼形稳定耳翼/IPX4/Apple全功能",
         "brand": "Beats", "category": "蓝牙耳机",
         "description": "Beats Fit Pro搭载苹果H1芯片，翼形稳定耳翼专为运动设计，主动降噪+通透模式，苹果设备一触即连，兼顾运动与音质。"},
        {"product_id": "jd_huawei_freebuds_pro3", "title": "华为 FreeBuds Pro 3 旗舰降噪耳机",
         "price": 1199.0, "original_price": 1499.0, "rating": 4.8, "sales": "月销8200",
         "key_specs": "三元音圈旗舰音质/主动降噪50dB/通透模式/IP54/6.5h续航/多设备连接",
         "brand": "华为", "category": "蓝牙耳机",
         "description": "华为FreeBuds Pro 3，三元音圈+平衡电枢双单元旗舰音质，50dB超强主动降噪业界领先，通透模式自然，6.5小时长续航，适合华为生态用户首选。"},
        {"product_id": "jd_soundcore_q45_nc", "title": "Soundcore Q45 头戴降噪耳机 超长续航",
         "price": 259.0, "original_price": 329.0, "rating": 4.7, "sales": "月销1.3万",
         "key_specs": "主动降噪ANC/60h超长续航/折叠收纳/多点连接/蓝牙5.3",
         "brand": "Soundcore", "category": "蓝牙耳机",
         "description": "Soundcore Q45头戴式降噪耳机，60小时超长续航满足多日使用，主动降噪多档可调，蓝牙5.3稳定连接，轻量折叠便携，300元内头戴降噪高性价比之选。"},
    ],
    "颈椎按摩仪": [
        {"product_id": "jd_breo_ineck4pro", "title": "倍轻松 iNeck 4 Pro 颈椎按摩仪",
         "price": 459.0, "original_price": 599.0, "rating": 4.8, "sales": "月销1.2万",
         "key_specs": "双电机揉捏/热敷42℃/EMS电脉冲/折叠便携/4档调节",
         "brand": "倍轻松", "category": "颈椎按摩仪",
         "description": "倍轻松iNeck 4 Pro颈椎按摩仪，双电机仿真揉捏，42℃智能热敷缓解颈部酸痛，EMS电脉冲深层放松，折叠设计随身携带。"},
        {"product_id": "jd_skg_g7pro", "title": "科摩 SKG G7 Pro 颈椎按摩器",
         "price": 369.0, "original_price": 499.0, "rating": 4.7, "sales": "月销8800",
         "key_specs": "石墨烯热敷/低频电脉冲/4档力度/APP智控/Type-C充电",
         "brand": "SKG", "category": "颈椎按摩仪",
         "description": "SKG G7 Pro采用石墨烯发热技术，均匀热敷颈部，低频电脉冲有效缓解肌肉紧张，APP远程控制，智能调节按摩强度。"},
        {"product_id": "jd_philips_ppm5101", "title": "飞利浦 PPM5101 肩颈按摩仪",
         "price": 259.0, "original_price": 329.0, "rating": 4.6, "sales": "月销6500",
         "key_specs": "3D揉捏按摩/红外热敷/3档速度/人体工学设计/自动关机",
         "brand": "飞利浦", "category": "颈椎按摩仪",
         "description": "飞利浦PPM5101肩颈按摩仪，3D仿真揉捏手法，红外热敷促进血液循环，人体工学外形贴合肩颈曲线，15分钟自动关机安全放心。"},
        {"product_id": "jd_xiaomi_neck_lrs", "title": "小米 米家颈椎按摩仪 LRS",
         "price": 199.0, "original_price": 249.0, "rating": 4.7, "sales": "月销2.8万",
         "key_specs": "EMS低频/热敷/3种模式/米家APP/轻量便携/Type-C",
         "brand": "小米", "category": "颈椎按摩仪",
         "description": "小米米家颈椎按摩仪LRS，EMS低频脉冲配合热敷，米家APP远程控制，轻量薄型佩戴舒适，百元内入门好选择。"},
        {"product_id": "jd_breo_ineck3pro", "title": "倍轻松 iNeck 3 Pro 颈椎按摩器",
         "price": 299.0, "original_price": 399.0, "rating": 4.7, "sales": "月销9600",
         "key_specs": "揉捏+热敷/5档强度/折叠/充电式/老人易用",
         "brand": "倍轻松", "category": "颈椎按摩仪",
         "description": "倍轻松iNeck 3 Pro，操作简单5档强度调节，老人小孩均可使用，揉捏+热敷双重舒缓，充电式随时随地使用。"},
        {"product_id": "jd_leravan_neck_elder", "title": "乐范 颈椎按摩仪 老年版 大字按钮",
         "price": 359.0, "original_price": 459.0, "rating": 4.8, "sales": "月销6200",
         "key_specs": "大字按钮一键操作/热敷45℃/EMS低频/3种预设模式/老人专属设计",
         "brand": "乐范", "category": "颈椎按摩仪",
         "description": "乐范老年版颈椎按摩仪，超大按钮简洁操作，三种预设模式一键选择无需复杂调节，45℃热敷快速缓解颈部酸痛，专为老年人操作习惯设计，送礼首选。"},
        {"product_id": "jd_renpho_neck_pro", "title": "RENPHO 颈椎按摩仪 专业版 360°包裹",
         "price": 499.0, "original_price": 659.0, "rating": 4.8, "sales": "月销4500",
         "key_specs": "360°包裹颈部/8个按摩节点/热敷/6档强度/USB充电/可定时",
         "brand": "RENPHO", "category": "颈椎按摩仪",
         "description": "RENPHO专业颈椎按摩仪，8个双向按摩节点360°全覆盖颈部和肩部，热敷+揉捏双重效果，6档强度可调，定时自动关机，专业级按摩体验居家可享。"},
    ],
    "咖啡机": [
        {"product_id": "jd_delonghi_en520", "title": "德龙 EN520 Nespresso 胶囊咖啡机 黑色",
         "price": 699.0, "original_price": 899.0, "rating": 4.8, "sales": "月销7500",
         "key_specs": "19bar意式萃取/胶囊兼容/0.8L水箱/25秒预热/紧凑设计",
         "brand": "德龙", "category": "咖啡机",
         "description": "德龙EN520与Nespresso胶囊完美兼容，19bar高压萃取保留咖啡精华，25秒快速预热，小巧机身适合厨房台面摆放。"},
        {"product_id": "jd_philips_ep2224", "title": "飞利浦 EP2224 全自动意式咖啡机",
         "price": 1899.0, "original_price": 2499.0, "rating": 4.9, "sales": "月销4200",
         "key_specs": "一键研磨萃取/15bar/内置陶瓷磨豆机/奶泡器/清洁提醒",
         "brand": "飞利浦", "category": "咖啡机",
         "description": "飞利浦EP2224全自动咖啡机，从研磨到萃取一键完成，内置陶瓷磨豆机保留咖啡风味，搭配奶泡器轻松制作拿铁卡布奇诺。"},
        {"product_id": "jd_bear_kfja02n1", "title": "小熊 KFJ-A02N1 美式滴漏咖啡机",
         "price": 129.0, "original_price": 169.0, "rating": 4.7, "sales": "月销2.1万",
         "key_specs": "650W/0.6L容量/保温底座/防滴漏设计/一键启动",
         "brand": "小熊", "category": "咖啡机",
         "description": "小熊KFJ-A02N1美式咖啡机，操作简单一键启动，保温底座持续保温，防滴漏设计随时取壶不漏液，适合咖啡入门用户。"},
        {"product_id": "jd_delonghi_ec685", "title": "德龙 EC685 半自动意式咖啡机 红色",
         "price": 999.0, "original_price": 1299.0, "rating": 4.8, "sales": "月销5600",
         "key_specs": "15bar泵压/快速预热/蒸汽棒打奶泡/不锈钢锅炉/紧凑机身",
         "brand": "德龙", "category": "咖啡机",
         "description": "德龙EC685半自动意式咖啡机，复古优雅外观，15bar泵压专业萃取，蒸汽棒手动打奶泡，适合有一定制作经验的咖啡爱好者。"},
        {"product_id": "jd_jura_e6", "title": "优瑞 JURA E6 全自动咖啡机",
         "price": 5999.0, "original_price": 6999.0, "rating": 4.9, "sales": "月销1200",
         "key_specs": "瑞士原装/一键拿铁/专业磨豆机/Aroma G3/智能预煮",
         "brand": "优瑞", "category": "咖啡机",
         "description": "瑞士优瑞JURA E6，顶级全自动咖啡机，Aroma G3磨豆机完美研磨，一键制作浓缩/美式/拿铁，智能预煮萃取更均匀，瑞士精密工艺代表。"},
        {"product_id": "jd_nespresso_vertuo", "title": "Nespresso Vertuo Pop 胶囊咖啡机",
         "price": 499.0, "original_price": 699.0, "rating": 4.7, "sales": "月销1.3万",
         "key_specs": "Centrifusion离心萃取/5种杯型/一键操作/15秒预热/紧凑",
         "brand": "Nespresso", "category": "咖啡机",
         "description": "Nespresso Vertuo Pop，独特离心萃取技术自动识别胶囊，15秒快速预热，支持5种杯型从浓缩到美式，颜色多样时尚百搭。"},
    ],
    "跑步鞋": [
        {"product_id": "jd_nike_revolution7", "title": "耐克 Revolution 7 男子跑步鞋",
         "price": 369.0, "original_price": 469.0, "rating": 4.7, "sales": "月销1.5万",
         "key_specs": "泡棉中底缓震/透气网面/橡胶外底/轻量化/多色可选",
         "brand": "耐克", "category": "跑步鞋",
         "description": "耐克Revolution 7日常跑步鞋，柔软泡棉中底提供良好缓震，透气网面鞋身保持脚部干爽，耐磨橡胶外底适合路面训练。"},
        {"product_id": "jd_asics_nimbus25", "title": "亚瑟士 GEL-NIMBUS 25 缓震跑鞋",
         "price": 899.0, "original_price": 1199.0, "rating": 4.9, "sales": "月销8800",
         "key_specs": "FF BLAST PLUS缓震/GEL技术/13mm落差/350g重量/LITETRUSS支撑",
         "brand": "亚瑟士", "category": "跑步鞋",
         "description": "亚瑟士GEL-NIMBUS 25旗舰缓震跑鞋，搭载FF BLAST PLUS中底和GEL减震胶，为长距离跑者提供卓越缓冲保护，适合马拉松训练。"},
        {"product_id": "jd_anta_h5pro", "title": "安踏 氢跑5 Pro 碳板竞速跑鞋",
         "price": 399.0, "original_price": 599.0, "rating": 4.8, "sales": "月销1.1万",
         "key_specs": "全掌碳板/氮科技中底/4.5mm落差/超轻215g/竞速设计",
         "brand": "安踏", "category": "跑步鞋",
         "description": "安踏氢跑5 Pro内置全掌碳纤维弹力板，配合氮科技发泡中底，215g超轻鞋身，为追求速度的跑者提供高效推进力。"},
        {"product_id": "jd_brooks_ghost15", "title": "Brooks Ghost 15 男子跑步鞋",
         "price": 799.0, "original_price": 999.0, "rating": 4.8, "sales": "月销7200",
         "key_specs": "DNA LOFT v2中底/柔软缓震/10mm落差/透气工程网面/适合日常跑",
         "brand": "Brooks", "category": "跑步鞋",
         "description": "Brooks Ghost 15，DNA LOFT v2超柔软中底，适应每一步的落地方式，出色的日常跑步鞋，适合初学者到进阶跑者。"},
        {"product_id": "jd_newbalance_1080v12", "title": "New Balance 1080v12 男子顶级缓震跑鞋",
         "price": 1099.0, "original_price": 1299.0, "rating": 4.9, "sales": "月销4500",
         "key_specs": "Fresh Foam X中底/超柔缓震/透气3D打印网面/8mm落差/适合长跑",
         "brand": "New Balance", "category": "跑步鞋",
         "description": "NB 1080v12旗舰缓震跑鞋，Fresh Foam X中底大量堆叠提供云感缓冲，透气3D打印鞋面包裹性强，长跑马拉松训练首选。"},
        {"product_id": "jd_lining_feidian3", "title": "李宁 飞电3 CHALLENGER 碳板跑鞋",
         "price": 599.0, "original_price": 799.0, "rating": 4.8, "sales": "月销6300",
         "key_specs": "全掌碳板/䨻Ultra中底/超轻198g/比赛级/国货之光",
         "brand": "李宁", "category": "跑步鞋",
         "description": "李宁飞电3 CHALLENGER国货竞速旗舰，全掌碳板配合䨻Ultra超临界发泡中底，198g极致轻量，比赛级竞速体验，国货性价比之王。"},
        {"product_id": "jd_asics_gel_kayano30", "title": "亚瑟士 GEL-KAYANO 30 稳定支撑跑鞋",
         "price": 899.0, "original_price": 1099.0, "rating": 4.9, "sales": "月销5600",
         "key_specs": "GEL前后双缓震胶/FF BLAST中底/厚底缓震/稳定支撑/适合长距离",
         "brand": "亚瑟士", "category": "跑步鞋",
         "description": "亚瑟士GEL-KAYANO 30，前后掌双GEL缓震胶吸收落地冲击，FF BLAST厚底中底层层缓冲，显著减少脚部疼痛，适合过度内旋和长距离跑者。"},
        {"product_id": "jd_hoka_clifton9", "title": "HOKA Clifton 9 厚底缓震跑鞋",
         "price": 849.0, "original_price": 1099.0, "rating": 4.9, "sales": "月销4800",
         "key_specs": "超厚EVA中底缓震/低落差4mm/早安鞋级缓冲/轻量255g/宽楦",
         "brand": "HOKA", "category": "跑步鞋",
         "description": "HOKA Clifton 9以超厚EVA中底著称，缓震性能极佳，脚部落地如踩云端，宽楦设计减少脚趾挤压，专为解决缓震差脚疼问题设计，跑步新手和长距离跑者神器。"},
        {"product_id": "jd_saucony_ride16", "title": "索康尼 Ride 16 日常训练跑鞋 缓震款",
         "price": 699.0, "original_price": 899.0, "rating": 4.8, "sales": "月销3900",
         "key_specs": "PWRRUN中底缓震/柔软回弹/8mm落差/透气网面/日常训练优选",
         "brand": "索康尼", "category": "跑步鞋",
         "description": "索康尼Ride 16，PWRRUN科技中底兼顾柔软缓震和回弹推进，8mm落差自然过渡，鞋型宽松不夹脚，是解决脚疼缓震差问题的中端日常训练首选。"},
    ],
    "台灯": [
        {"product_id": "jd_benq_mindduo", "title": "明基 WiT MindDuo 护眼台灯 白色",
         "price": 699.0, "original_price": 899.0, "rating": 4.9, "sales": "月销6800",
         "key_specs": "无蓝光/无频闪/3000K-6500K色温/400lux宽照面/感应调光",
         "brand": "明基", "category": "台灯",
         "description": "明基WiT MindDuo护眼台灯，专利宽大照明面积是普通台灯2倍，无蓝光无频闪认证，自动感应环境光调节亮度，守护用眼健康。"},
        {"product_id": "jd_xiaomi_mjtd02yl", "title": "小米米家台灯 Pro 智能调光",
         "price": 199.0, "original_price": 249.0, "rating": 4.8, "sales": "月销3.2万",
         "key_specs": "2700K-6500K/无级调光/米家APP控制/AA级护眼/USB充电口",
         "brand": "小米", "category": "台灯",
         "description": "小米米家台灯Pro，AA级护眼认证，无级调光调色，米家APP智能控制，内置USB充电口方便手机充电，颜值与功能兼备。"},
        {"product_id": "jd_philips_coolled", "title": "飞利浦 酷玥 LED护眼台灯",
         "price": 149.0, "original_price": 199.0, "rating": 4.7, "sales": "月销1.9万",
         "key_specs": "4档亮度调节/3档色温/无蓝光认证/触控开关/USB供电",
         "brand": "飞利浦", "category": "台灯",
         "description": "飞利浦酷玥护眼台灯，通过无蓝光和无频闪双重认证，4档亮度3档色温满足不同场景需求，触控操作简洁方便。"},
        {"product_id": "jd_nvc_e2led", "title": "雷士照明 E2 学习台灯 AA级护眼",
         "price": 89.0, "original_price": 129.0, "rating": 4.6, "sales": "月销4.5万",
         "key_specs": "AA级护眼/无频闪/3色调节/触控/USB供电/适合学生",
         "brand": "雷士照明", "category": "台灯",
         "description": "雷士E2学习台灯，AA级护眼认证，无频闪保护眼睛，3色调节适应学习/阅读/休息，USB供电方便，学生党入门首选。"},
        {"product_id": "jd_opple_led_study", "title": "欧普照明 LED书桌台灯 大学习版",
         "price": 129.0, "original_price": 179.0, "rating": 4.7, "sales": "月销2.8万",
         "key_specs": "大灯头/无蓝光/5档亮度/3档色温/可折叠/触控",
         "brand": "欧普照明", "category": "台灯",
         "description": "欧普大学习版台灯，超大灯头提供更宽照射面积，无蓝光无频闪双认证，5档亮度3档色温灵活调节，折叠收纳节省空间。"},
        {"product_id": "jd_yeelight_pro_r1", "title": "易来 Yeelight Pro R1 智能台灯",
         "price": 349.0, "original_price": 449.0, "rating": 4.8, "sales": "月销1.4万",
         "key_specs": "自然光谱/感应调光/HomeKit/Google/小爱同学/AA+护眼",
         "brand": "易来", "category": "台灯",
         "description": "易来Pro R1智能台灯，自然光谱技术模拟太阳光变化，支持HomeKit/Google/小爱多平台，感应周围光线自动调节，AA+护眼认证。"},
        {"product_id": "jd_benq_e21_dc", "title": "明基 E21 DC直流调光台灯 无频闪旗舰",
         "price": 399.0, "original_price": 499.0, "rating": 4.9, "sales": "月销8800",
         "key_specs": "DC直流调光零频闪/无蓝光认证/2700K-6500K/宽照面积/AA级护眼",
         "brand": "明基", "category": "台灯",
         "description": "明基E21采用DC直流调光技术，从根本上消除频闪，相比普通PWM调光台灯对眼睛刺激减少90%，无蓝光认证，宽照面积均匀照明，彻底解决频闪眼睛不适问题。"},
        {"product_id": "jd_philips_dc_study", "title": "飞利浦 66161 DC调光护眼台灯 无频闪",
         "price": 179.0, "original_price": 229.0, "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "DC直流调光无频闪/无蓝光/AA级护眼/触控调光/5档色温",
         "brand": "飞利浦", "category": "台灯",
         "description": "飞利浦66161，DC直流调光技术杜绝频闪危害，通过无蓝光无频闪双重国标认证，AA级护眼，5档色温适应学习工作休闲，解决频闪眼睛疲劳的平价之选。"},
    ],
    "投影仪": [
        {"product_id": "jd_xgimi_h6_4k", "title": "极米 H6 4K激光投影仪",
         "price": 3999.0, "original_price": 4999.0, "rating": 4.9, "sales": "月销5500",
         "key_specs": "4K分辨率/2200流明/ISA智能系统/双扬声器/自动对焦梯形校正",
         "brand": "极米", "category": "投影仪",
         "description": "极米H6 4K激光投影仪，原生4K超高清画质，ISA3.0智能投影系统自动对焦校正，2200ANSI流明支持白天使用，双10W扬声器音效出众。"},
        {"product_id": "jd_dangbei_x4ultra", "title": "当贝 X4 Ultra 4K激光投影仪",
         "price": 5999.0, "original_price": 7999.0, "rating": 4.8, "sales": "月销3200",
         "key_specs": "4K三色激光/3300流明/120Hz高刷/杜比全景声/AI超分",
         "brand": "当贝", "category": "投影仪",
         "description": "当贝X4 Ultra旗舰激光投影仪，三色激光技术色域覆盖110%BT.2020，3300流明超高亮度，杜比全景声沉浸音效，打造家庭影院级体验。"},
        {"product_id": "jd_nuts_n1ultra", "title": "坚果 N1 Ultra 4K投影仪",
         "price": 5499.0, "original_price": 6999.0, "rating": 4.8, "sales": "月销2800",
         "key_specs": "4K分辨率/2800流明/极短焦/10cm投100寸/哈曼卡顿音响",
         "brand": "坚果", "category": "投影仪",
         "description": "坚果N1 Ultra极短焦投影仪，10cm距离投出100寸大画面，避免人影遮挡，哈曼卡顿专业音响系统，是家庭客厅的理想选择。"},
        {"product_id": "jd_xgimi_halo2", "title": "极米 HALO 2 便携投影仪",
         "price": 2799.0, "original_price": 3499.0, "rating": 4.8, "sales": "月销7800",
         "key_specs": "1080P/800流明/ISA智能系统/内置电池/便携/哈曼卡顿",
         "brand": "极米", "category": "投影仪",
         "description": "极米HALO 2便携投影仪，内置电池随时随地投影，800流明明亮显示，ISA自动梯形校正对焦，哈曼卡顿音响，旅行投影首选。"},
        {"product_id": "jd_benq_th685p", "title": "明基 TH685P 家用游戏投影仪",
         "price": 4499.0, "original_price": 5499.0, "rating": 4.8, "sales": "月销2100",
         "key_specs": "1080P/3500流明/8.3ms超低延迟/HDR/HDMI2.0/游戏专属",
         "brand": "明基", "category": "投影仪",
         "description": "明基TH685P游戏投影仪，3500流明高亮明亮室内使用，8.3ms超低输入延迟，HDR增强画面层次，游戏/电影双模式切换，游戏迷必备。"},
        {"product_id": "jd_xiaomi_projector2pro", "title": "小米投影仪 2 Pro 家用智能投影",
         "price": 1999.0, "original_price": 2499.0, "rating": 4.7, "sales": "月销1.1万",
         "key_specs": "1080P全高清/1300流明/自动对焦梯形/MIUI TV/米家联动",
         "brand": "小米", "category": "投影仪",
         "description": "小米投影仪2 Pro，1080P全高清，自动对焦+梯形校正开箱即用，MIUI TV内容丰富，米家智能家居无缝联动，高性价比家用首选。"},
    ],
    "洗衣液": [
        {"product_id": "jd_bluemoon_3kg", "title": "蓝月亮 深层洁净洗衣液 3kg",
         "price": 49.9, "original_price": 69.0, "rating": 4.8, "sales": "月销15万",
         "key_specs": "3kg大容量/深层洁净/护色护纤维/适合机洗/无磷配方",
         "brand": "蓝月亮", "category": "洗衣液",
         "description": "蓝月亮深层洁净洗衣液，专利洁净因子深入纤维去除污渍，护色配方保持衣物鲜艳，3kg大容量家庭装经济实惠。"},
        {"product_id": "jd_tide_2kg_color", "title": "汰渍 全效护色洗衣液 2kg",
         "price": 39.9, "original_price": 55.0, "rating": 4.7, "sales": "月销8.5万",
         "key_specs": "2kg/全效护色/深层清洁/低泡易漂/适合所有衣物",
         "brand": "汰渍", "category": "洗衣液",
         "description": "汰渍全效护色洗衣液，专效护色技术防止衣物褪色，低泡配方轻松漂洗不残留，全面清洁各类面料衣物。"},
        {"product_id": "jd_ariel_3kg_anti", "title": "碧浪 除菌洗衣液 3kg",
         "price": 59.9, "original_price": 79.0, "rating": 4.8, "sales": "月销6.8万",
         "key_specs": "3kg/除菌99.9%/去渍/低温洗涤/留香持久",
         "brand": "碧浪", "category": "洗衣液",
         "description": "碧浪除菌洗衣液，有效除菌率达99.9%，强力去渍配方轻松应对顽固污渍，持久留香让衣物清新宜人，3kg家庭装超值划算。"},
        {"product_id": "jd_lam_pure_2kg", "title": "兰芸 天然植物洗衣液 2kg",
         "price": 45.9, "original_price": 65.0, "rating": 4.7, "sales": "月销3.2万",
         "key_specs": "植物提取/温和低刺激/适合婴幼儿/无荧光剂/留香",
         "brand": "兰芸", "category": "洗衣液",
         "description": "兰芸天然植物洗衣液，植物提取配方温和低刺激，无荧光剂、无磷酸盐，适合婴幼儿衣物，不伤肤不伤衣。"},
        {"product_id": "jd_liby_2kg_soft", "title": "立白 天然皂液 柔顺留香 2kg",
         "price": 29.9, "original_price": 42.0, "rating": 4.6, "sales": "月销12万",
         "key_specs": "2kg/天然皂液/柔顺/留香/适合手洗机洗",
         "brand": "立白", "category": "洗衣液",
         "description": "立白天然皂液，源自天然皂基，洗净力强，衣物柔顺不变形，持久留香，手洗机洗皆宜，超高性价比家庭常备款。"},
        {"product_id": "jd_dettol_wash_2kg_lav", "title": "滴露 除菌消毒洗衣液 2kg 薰衣草",
         "price": 54.9, "original_price": 75.0, "rating": 4.8, "sales": "月销4.1万",
         "key_specs": "2kg/99.9%除菌率/天然薰衣草/婴儿可用/适合机洗手洗",
         "brand": "滴露", "category": "洗衣液",
         "description": "滴露除菌洗衣液，有效除菌率99.9%，天然薰衣草精华清香持久，pH温和可用于婴幼儿衣物，低泡易漂清，家庭杀菌护衣首选。"},
    ],
    "跑步机": [
        {"product_id": "jd_shuhua_sht5100", "title": "舒华 SH-T5100 家用折叠跑步机",
         "price": 3999.0, "original_price": 4999.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "2.5HP电机/1-16km/h/10.1寸彩屏/减震缓冲/折叠收纳",
         "brand": "舒华", "category": "跑步机",
         "description": "舒华SH-T5100家用跑步机，2.5HP静音电机运行噪音低，10.1寸彩色触控屏内置多种训练课程，8层减震系统保护膝关节，折叠后省空间。"},
        {"product_id": "jd_merax_smart_trd", "title": "麦瑞克 智能跑步机 静音折叠款",
         "price": 2999.0, "original_price": 3999.0, "rating": 4.7, "sales": "月销5800",
         "key_specs": "2.0HP/0.8-14km/h/磁控静音/APP控制/多功能扶手",
         "brand": "麦瑞克", "category": "跑步机",
         "description": "麦瑞克智能跑步机，磁控静音技术将噪音控制在45分贝以下，支持手机APP远程控制，多功能扶手集成心率检测，适合家庭日常健身。"},
        {"product_id": "jd_xiaomi_treadmill", "title": "小米家庭健身跑步机 静音版",
         "price": 2499.0, "original_price": 2999.0, "rating": 4.8, "sales": "月销7600",
         "key_specs": "1.5HP/1-10km/h/静音电机/米家APP/折叠设计/儿童锁",
         "brand": "小米", "category": "跑步机",
         "description": "小米家庭跑步机静音版，接入米家智能家居系统，手机APP一键控制，儿童安全锁防止意外启动，折叠后仅占半平方米空间。"},
        {"product_id": "jd_reebok_one_gt40s", "title": "锐步 ONE GT40S 家用跑步机",
         "price": 4999.0, "original_price": 6499.0, "rating": 4.8, "sales": "月销2800",
         "key_specs": "3.0HP/1-20km/h/15档坡度/7寸彩屏/心率监测/减震",
         "brand": "锐步", "category": "跑步机",
         "description": "锐步ONE GT40S家用跑步机，3.0HP强劲电机最高20km/h，15档自动坡度训练，心率感应实时监控，专业级家用健身体验。"},
        {"product_id": "jd_johnson_t101", "title": "乔山 T101 家用跑步机 入门款",
         "price": 1999.0, "original_price": 2599.0, "rating": 4.7, "sales": "月销8900",
         "key_specs": "1.75HP/1-12km/h/5寸LCD/3档坡度/折叠收纳/心率扶手",
         "brand": "乔山", "category": "跑步机",
         "description": "乔山T101入门家用跑步机，1.75HP电机满足日常步行慢跑，3档手动坡度调节，心率扶手实时监测，折叠收纳方便，性价比之选。"},
        {"product_id": "jd_horizon_t101", "title": "爱康 NordicTrack T6.5S 跑步机",
         "price": 5499.0, "original_price": 6999.0, "rating": 4.9, "sales": "月销1600",
         "key_specs": "iFit教练课/2.6CHP/0-12%坡度/10寸触屏/减震FlexSelect",
         "brand": "爱康", "category": "跑步机",
         "description": "爱康NordicTrack T6.5S，内置iFit在线教练课程，10寸高清触屏互动，FlexSelect减震系统保护关节，智能坡度自动跟随教练调节。"},
    ],
    "家居搭配": [
        {"product_id": "jd_ikea_lack_white", "title": "宜家 LACK 茶几 白色极简款 90x55cm",
         "price": 199.0, "original_price": 249.0, "rating": 4.7, "sales": "月销2.2万",
         "key_specs": "90x55x45cm/蜂窝板轻量/承重25kg/极简设计/易清洁",
         "brand": "宜家", "category": "家居搭配",
         "description": "宜家LACK茶几，经典极简设计适配多种风格，蜂窝纸板芯轻量化设计，光滑表面易于清洁，是客厅和卧室的百搭之选。"},
        {"product_id": "jd_opple_floorlamp", "title": "欧普照明 落地灯 客厅北欧风",
         "price": 359.0, "original_price": 499.0, "rating": 4.8, "sales": "月销9500",
         "key_specs": "E27灯口/三档调光/1.6m高度/金属灯杆/布艺灯罩",
         "brand": "欧普照明", "category": "家居搭配",
         "description": "欧普照明北欧风落地灯，简约金属灯杆搭配温润布艺灯罩，三档亮度自由切换，160cm优雅高度，为客厅营造温馨氛围。"},
        {"product_id": "jd_nordic_rug_160", "title": "北欧风编织地毯 160×230cm 灰白色",
         "price": 399.0, "original_price": 599.0, "rating": 4.7, "sales": "月销1.4万",
         "key_specs": "160x230cm/棉麻编织/防滑底面/可机洗/北欧几何图案",
         "brand": "北欧风尚", "category": "家居搭配",
         "description": "北欧风格编织地毯，几何图案现代简约，棉麻混纺材质柔软舒适，防滑底面安全可靠，160x230cm大尺寸覆盖客厅主区域，可机洗方便护理。"},
        {"product_id": "jd_muji_shelf_oak", "title": "无印良品风格 橡木开放式书架 5层",
         "price": 599.0, "original_price": 799.0, "rating": 4.8, "sales": "月销6800",
         "key_specs": "橡木色/5层/承重50kg/简约/免打孔/180cm高",
         "brand": "优木良品", "category": "家居搭配",
         "description": "无印良品风格橡木开放式书架，天然木纹质感温润，5层大容量，坚固承重50kg，免打孔组装简单，适合客厅书房。"},
        {"product_id": "jd_decorpillow_set", "title": "北欧风抱枕套装 客厅沙发装饰 4件套",
         "price": 168.0, "original_price": 228.0, "rating": 4.6, "sales": "月销3.1万",
         "key_specs": "4件套/45×45cm/棉麻混纺/可拆洗/多色组合",
         "brand": "棉致", "category": "家居搭配",
         "description": "北欧风格抱枕套装，4种不同图案搭配出层次感，棉麻混纺柔软透气，可拆洗枕套清洁方便，点缀沙发客厅提升整体格调。"},
        {"product_id": "jd_greenplant_potten", "title": "绿植套装 多肉植物组合 桌面小盆栽 6盆",
         "price": 89.0, "original_price": 128.0, "rating": 4.7, "sales": "月销5.6万",
         "key_specs": "6盆组合/多肉品种/带陶瓷花盆/易养护/净化空气",
         "brand": "花蔚来", "category": "家居搭配",
         "description": "桌面多肉植物6盆组合，带精美陶瓷花盆，耐旱易养无需频繁浇水，净化空气改善居家环境，办公桌和窗台装饰首选。"},
    ],
    "三脚架": [
        {"product_id": "jd_sirui_a3204x", "title": "思锐 A-3204X 铝合金三脚架",
         "price": 399.0, "original_price": 549.0, "rating": 4.8, "sales": "月销8200",
         "key_specs": "铝合金/承重8kg/最高170cm/折叠40cm/球形云台",
         "brand": "思锐", "category": "三脚架",
         "description": "思锐A-3204X铝合金三脚架，稳固承重8kg，球形云台360°旋转，折叠仅40cm便携。"},
        {"product_id": "jd_benro_c2573f", "title": "百诺 C2573F 碳纤维三脚架套装",
         "price": 1299.0, "original_price": 1699.0, "rating": 4.9, "sales": "月销3200",
         "key_specs": "碳纤维/承重12kg/最高170cm/折叠42cm/球形云台B2",
         "brand": "百诺", "category": "三脚架",
         "description": "百诺C2573F碳纤维三脚架，轻量坚固，B2球形云台快装板设计，适合旅拍专业摄影师。"},
        {"product_id": "jd_utebit_tripod_60", "title": "UTEBIT 60寸铝合金三脚架 入门款",
         "price": 149.0, "original_price": 199.0, "rating": 4.6, "sales": "月销2.8万",
         "key_specs": "铝合金/60寸/承重3kg/球形云台/快装板/入门款",
         "brand": "UTEBIT", "category": "三脚架",
         "description": "UTEBIT入门三脚架，铝合金轻量，球形云台快装板，适合手机/微单日常拍摄，性价比之选。"},
        {"product_id": "jd_joby_gorillapod_5k", "title": "Joby GorillaPod 5K 章鱼三脚架套装",
         "price": 699.0, "original_price": 899.0, "rating": 4.8, "sales": "月销6500",
         "key_specs": "章鱼脚/承重5kg/球形云台/可弯曲缠绕固定/适合旅拍Vlog",
         "brand": "Joby", "category": "三脚架",
         "description": "Joby章鱼三脚架，可弯折脚管缠绕树枝栏杆任意固定，承重5kg兼容单反微单，随身小巧适合旅行Vlog博主，脑洞大开的拍摄必备。"},
        {"product_id": "jd_benro_s2_video", "title": "百诺 S2 Pro 视频三脚架 液压云台",
         "price": 899.0, "original_price": 1199.0, "rating": 4.8, "sales": "月销3800",
         "key_specs": "铝合金/液压云台/载重5kg/最高175cm/水平仪/视频专用",
         "brand": "百诺", "category": "三脚架",
         "description": "百诺S2 Pro视频三脚架，液压碗头阻尼均匀顺滑，适合视频运镜和延时摄影，内置水平仪保证水平，承重5kg满足单反+镜头。"},
        {"product_id": "jd_xiletu_mg284c", "title": "锡兰途 MG284C 碳纤维旅行三脚架",
         "price": 599.0, "original_price": 799.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "碳纤维/折叠40cm/承重10kg/轻量1.15kg/球形云台/旅行款",
         "brand": "锡兰途", "category": "三脚架",
         "description": "锡兰途MG284C碳纤维旅行三脚架，折叠仅40cm可放入行李箱，仅重1.15kg，承重10kg，球形云台360°旋转，旅行摄影神器。"},
        {"product_id": "jd_leofoto_ls284c", "title": "徕图 LS-284C 专业碳纤维三脚架",
         "price": 1599.0, "original_price": 1999.0, "rating": 4.9, "sales": "月销1800",
         "key_specs": "碳纤维/承重15kg/最高175cm/折叠44cm/LH40球台/专业级",
         "brand": "徕图", "category": "三脚架",
         "description": "徕图LS-284C专业碳纤维三脚架，15kg超强承重适合重型长焦镜头，LH40精准球台定位，折叠44cm便携，商业及风光摄影首选。"},
    ],
    "摄影包": [
        {"product_id": "jd_lowepro_fs400", "title": "乐摄宝 Flipside 400 AW III 双肩摄影包",
         "price": 799.0, "original_price": 999.0, "rating": 4.9, "sales": "月销5600",
         "key_specs": "25L容量/后开门防盗/AW防雨/可放13寸笔记本/TSA锁",
         "brand": "乐摄宝", "category": "摄影包",
         "description": "乐摄宝Flipside 400专业摄影背包，后开门防盗，全天候防雨罩，可同时携带机身镜头和笔记本。"},
        {"product_id": "jd_national_geo_ng_5168", "title": "国家地理 NG5168 单反摄影包 中型",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "中型/可放单反+3镜头/防水/侧取/14寸笔记本/帆布",
         "brand": "国家地理", "category": "摄影包",
         "description": "国家地理NG5168帆布摄影包，复古外观，可放单反+3支镜头，侧面快取设计，防水材质户外适用。"},
        {"product_id": "jd_tamrac_jazz_photo", "title": "天域 Jazz Photo 80 单肩摄影包",
         "price": 249.0, "original_price": 329.0, "rating": 4.7, "sales": "月销6800",
         "key_specs": "单肩/小型/适合微单/防水/隔层可调/日常街拍",
         "brand": "天域", "category": "摄影包",
         "description": "天域Jazz Photo 80小型单肩摄影包，专为微单设计，防水耐磨，可调隔层，日常街拍轻便首选。"},
        {"product_id": "jd_lowepro_trekker_450", "title": "乐摄宝 Trekker 450 AW II 户外双肩摄影包",
         "price": 1199.0, "original_price": 1499.0, "rating": 4.9, "sales": "月销2800",
         "key_specs": "大容量35L/舒适背负系统/全天候防雨/可外挂三脚架/登山带",
         "brand": "乐摄宝", "category": "摄影包",
         "description": "乐摄宝Trekker 450户外摄影双肩包，35L大容量可放无人机+双机身+多镜头，舒适背负系统适合长途徒步，全天候防雨罩，外挂系统挂载三脚架。"},
        {"product_id": "jd_vanguard_sydney_ii", "title": "精嘉 Sydney II 65 相机滚轮箱",
         "price": 999.0, "original_price": 1299.0, "rating": 4.8, "sales": "月销1800",
         "key_specs": "拉杆滚轮箱/65L/TSA密码锁/全铝合金外壳/防震内衬",
         "brand": "精嘉", "category": "摄影包",
         "description": "精嘉Sydney II摄影滚轮箱，全铝合金外壳保护设备不受挤压，TSA海关密码锁，65L大容量收纳全套摄影器材，国际旅行摄影师首选。"},
        {"product_id": "jd_f_stop_ajna_37", "title": "F-stop Ajna 37 防水摄影背包",
         "price": 2199.0, "original_price": 2699.0, "rating": 4.9, "sales": "月销1200",
         "key_specs": "37L/防水帆布/冰斧挂载/ICU内胆可拆/徒步专属/承重20kg",
         "brand": "F-stop", "category": "摄影包",
         "description": "F-stop Ajna 37L专业防水摄影背包，ICU内胆独立可拆，防水帆布抗极端天气，冰斧挂载系统专为山地摄影设计，承重20kg长距离徒步无压力。"},
    ],
    "摄影装备": [
        {"product_id": "jd_jjc_clean10set", "title": "JJC 相机清洁套装 10件套",
         "price": 89.0, "original_price": 119.0, "rating": 4.7, "sales": "月销3.8万",
         "key_specs": "10件套/气吹+镜头笔+清洁液+镜头布+棉签/适用各品牌",
         "brand": "JJC", "category": "摄影装备",
         "description": "JJC相机清洁套装10件套，包含气吹、镜头笔、清洁液、镜头布等，全面维护光学器材。"},
        {"product_id": "jd_godox_v1_canon", "title": "神牛 V1 圆头机顶闪光灯 佳能版",
         "price": 999.0, "original_price": 1299.0, "rating": 4.8, "sales": "月销4100",
         "key_specs": "76Ws/TTL/圆形灯头/磁吸配件/2.4G无线/锂电",
         "brand": "神牛", "category": "摄影装备",
         "description": "神牛V1圆头闪光灯，圆形灯头光线均匀，TTL全自动测光，内置2.4G无线主控。"},
        {"product_id": "jd_dji_osmo_mobile6", "title": "大疆 Osmo Mobile 6 手机云台稳定器",
         "price": 799.0, "original_price": 999.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "三轴稳定/折叠/跟踪拍摄/6h续航/延长杆",
         "brand": "大疆", "category": "摄影装备",
         "description": "大疆Osmo Mobile 6手机云台，三轴防抖，ActiveTrack智能跟踪，内置延长杆，折叠便携。"},
        {"product_id": "jd_godox_sl60w_led", "title": "神牛 SL60W LED补光灯 摄影持续灯",
         "price": 499.0, "original_price": 699.0, "rating": 4.8, "sales": "月销8900",
         "key_specs": "60W/5600K昼光色/无频闪/静音风扇/支持远程控制/附柔光罩",
         "brand": "神牛", "category": "摄影装备",
         "description": "神牛SL60W LED持续补光灯，60W高亮无频闪，5600K标准昼光色准确还原肤色，附柔光罩柔化光线，视频直播人像摄影必备。"},
        {"product_id": "jd_nisi_nd_variable", "title": "NiSi 可调ND减光镜 77mm 1.5-5档",
         "price": 398.0, "original_price": 499.0, "rating": 4.8, "sales": "月销5600",
         "key_specs": "可调ND/77mm/1.5-5档/真彩色不偏色/双层镀膜/防水镀膜",
         "brand": "NiSi", "category": "摄影装备",
         "description": "NiSi可调ND减光镜，1.5-5档连续调节，真彩色镀膜不偏色，防水镀膜易清洁，慢门拍水流云彩大光圈人像均适用，77mm大口径覆盖主流镜头。"},
        {"product_id": "jd_rode_wireless_go2", "title": "RØDE Wireless GO II 无线收音麦克风",
         "price": 2399.0, "original_price": 2799.0, "rating": 4.9, "sales": "月销4100",
         "key_specs": "双发射+单接收/200m传输/7h续航/内录/相机手机双适用/小巧",
         "brand": "RØDE", "category": "摄影装备",
         "description": "RØDE Wireless GO II专业无线领夹麦克风，双发射器同时收两人音频，200m远距传输，7小时续航，内置录音功能防信号中断，短视频Vlog采访旗舰之选。"},
        {"product_id": "jd_deity_d4_mini", "title": "Deity D4 Mini 超指向麦克风 相机话筒",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销7200",
         "key_specs": "超心形指向/低自噪音16dB/安装式/防风罩/冷靴适配/相机手机兼容",
         "brand": "Deity", "category": "摄影装备",
         "description": "Deity D4 Mini超指向枪型话筒，冷靴安装相机机顶，超心形指向只收正前方声音，低自噪16dB收音清晰，附防风罩，户外视频收音入门首选。"},
    ],
    "键盘鼠标": [
        {"product_id": "jd_logitech_mk470", "title": "罗技 MK470 无线键鼠套装 白色",
         "price": 249.0, "original_price": 299.0, "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "剪刀脚键盘/无线2.4G/1年续航/静音鼠标/纤薄设计",
         "brand": "罗技", "category": "键盘鼠标",
         "description": "罗技MK470纤薄无线键鼠套装，剪刀脚按键手感舒适，静音鼠标办公无干扰，单个USB接收器连接两件设备，1年超长续航省心省力。"},
        {"product_id": "jd_keychron_k2_v2", "title": "Keychron K2 V2 机械键盘 热插拔版",
         "price": 499.0, "original_price": 599.0, "rating": 4.9, "sales": "月销9800",
         "key_specs": "75%配列/热插拔/三模连接/铝合金框架/RGB背光/茶红青轴可选",
         "brand": "Keychron", "category": "键盘鼠标",
         "description": "Keychron K2 V2热插拔机械键盘，75%紧凑布局兼顾方向键，蓝牙/USB/2.4G三模，铝合金坚固机身，可随意更换轴体，Mac/Win双系统。"},
        {"product_id": "jd_logitech_mx_master3s", "title": "罗技 MX Master 3S 无线鼠标",
         "price": 499.0, "original_price": 599.0, "rating": 4.9, "sales": "月销8600",
         "key_specs": "8K DPI/电磁滚轮/静音点击/人体工学/充电/多设备切换",
         "brand": "罗技", "category": "键盘鼠标",
         "description": "罗技MX Master 3S旗舰鼠标，MagSpeed电磁滚轮极速滚动，8000 DPI精准追踪，静音点击，人体工学右手设计，一键切换3台设备。"},
        {"product_id": "jd_rapoo_mt760", "title": "雷柏 MT760 多模无线键鼠套装",
         "price": 199.0, "original_price": 269.0, "rating": 4.7, "sales": "月销1.4万",
         "key_specs": "三模连接/可连4设备/薄膜键盘/可充电/静音",
         "brand": "雷柏", "category": "键盘鼠标",
         "description": "雷柏MT760多模键鼠套装，蓝牙5.0+2.4G双模，同时管理4台设备，可充电无需换电池，轻薄静音适合办公室环境。"},
        {"product_id": "jd_hhkb_hybrid_type_s", "title": "HHKB Professional Hybrid Type-S 键盘",
         "price": 2299.0, "original_price": 2499.0, "rating": 4.9, "sales": "月销1200",
         "key_specs": "静电容轴/无线蓝牙4台/静音Type-S/60键紧凑/PD墨黑",
         "brand": "HHKB", "category": "键盘鼠标",
         "description": "HHKB Professional Hybrid Type-S，顶级静电容轴手感精准，Type-S超静音设计，60键极简布局，蓝牙连4台设备切换，程序员/设计师神器。"},
        {"product_id": "jd_razer_deathadder_v3", "title": "雷蛇 DeathAdder V3 人体工学鼠标",
         "price": 349.0, "original_price": 449.0, "rating": 4.8, "sales": "月销7400",
         "key_specs": "30K DPI光学/59g超轻/人体工学/Focus Pro传感器/有线",
         "brand": "雷蛇", "category": "键盘鼠标",
         "description": "雷蛇DeathAdder V3经典人体工学游戏鼠标，59g超轻机身减少手部疲劳，Focus Pro 30K光学传感器精准响应，适合MOBA/FPS游戏及长时间办公。"},
    ],
    "热水壶": [
        {"product_id": "jd_bear_fast_hot", "title": "小熊 快速加热电热水壶 1.5L 大功率",
         "price": 89.0, "original_price": 119.0, "rating": 4.7, "sales": "月销2.1万",
         "key_specs": "2400W大功率/45秒快速加热/316不锈钢/1.5L/自动断电/防烫",
         "brand": "小熊", "category": "热水壶",
         "description": "小熊大功率快速电热水壶，2400W超强功率45秒快速烧开，相比普通1500W水壶速度提升60%，316不锈钢内胆安全无味。"},
        {"product_id": "jd_philips_hd9316", "title": "飞利浦 HD9316 电热水壶 1.7L",
         "price": 129.0, "original_price": 179.0, "rating": 4.8, "sales": "月销3.6万",
         "key_specs": "1.7L/2200W快热/316不锈钢/防烫手柄/自动断电",
         "brand": "飞利浦", "category": "热水壶",
         "description": "飞利浦HD9316电热水壶，2200W大功率3分钟快速烧开，316不锈钢内胆安全无味，防烫手柄设计，水烧开自动断电安全放心。"},
        {"product_id": "jd_xiaomi_mjdsh01ym", "title": "小米 米家恒温电热水壶 Pro",
         "price": 199.0, "original_price": 249.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "1.5L/55-100℃恒温/米家APP/1800W/304不锈钢",
         "brand": "小米", "category": "热水壶",
         "description": "小米米家恒温电热水壶Pro，支持55-100℃精确温控，米家APP远程预约，304不锈钢内胆，适合泡茶泡咖啡的精致生活人群。"},
        {"product_id": "jd_bears_zzb_p15s1", "title": "小熊 电热水壶 1.5L 玻璃款",
         "price": 79.0, "original_price": 109.0, "rating": 4.7, "sales": "月销5.2万",
         "key_specs": "1.5L/玻璃内胆/2000W/LED蓝光/可视水位/自动断电",
         "brand": "小熊", "category": "热水壶",
         "description": "小熊玻璃电热水壶，透明玻璃内胆直观可视，LED蓝光氛围感十足，2000W快速沸腾，自动断电干烧保护双重安全，颜值实用兼备。"},
        {"product_id": "jd_morphy_m8120", "title": "摩飞 MR8120 多功能折叠水壶 旅行款",
         "price": 199.0, "original_price": 259.0, "rating": 4.7, "sales": "月销8800",
         "key_specs": "0.5L/折叠收纳/双电压/304不锈钢/旅行专用/轻量",
         "brand": "摩飞", "category": "热水壶",
         "description": "摩飞MR8120折叠旅行水壶，硅胶折叠设计仅占普通水壶1/3体积，支持100-240V全球双电压，304不锈钢内胆，商旅出行神器。"},
        {"product_id": "jd_joyoung_k15ed_wb150", "title": "九阳 K15ED-WB150 多段控温电热水壶 1.5L",
         "price": 169.0, "original_price": 219.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "1.5L/五段控温/保温1h/304不锈钢/触控面板/2000W",
         "brand": "九阳", "category": "热水壶",
         "description": "九阳K15ED-WB150五段控温电热水壶，45/60/75/85/100℃精确控温，1小时保温功能，304不锈钢内胆，触控面板简洁易用，泡茶爱好者必备。"},
        {"product_id": "jd_supor_sw15e50a", "title": "苏泊尔 SW15E50A 电热水壶 1.5L 白色",
         "price": 99.0, "original_price": 139.0, "rating": 4.7, "sales": "月销2.9万",
         "key_specs": "1.5L/304不锈钢/1800W/自动断电/大开口易清洗",
         "brand": "苏泊尔", "category": "热水壶",
         "description": "苏泊尔SW15E50A简约电热水壶，304不锈钢内胆安全卫生，大开口设计方便清洗，1800W快速沸腾，自动断电防干烧，居家厨房必备。"},
    ],
    "哑铃": [
        {"product_id": "jd_aoyi_dumbbell_10kg", "title": "奥义 可调节哑铃 2-10kg 一对装",
         "price": 299.0, "original_price": 399.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "2-10kg可调/包胶防滑/一对/防摔/收纳方便",
         "brand": "奥义", "category": "哑铃",
         "description": "奥义可调节哑铃，2-10kg多档调节，包胶防滑保护地板，一对装入门家庭健身首选。"},
        {"product_id": "jd_keep_dumbbell_5kg", "title": "Keep 铸铁哑铃 5kg×2 烤漆固定",
         "price": 129.0, "original_price": 169.0, "rating": 4.7, "sales": "月销2.8万",
         "key_specs": "5kg×2/烤漆铸铁/防滑包胶/固定重量/女性友好",
         "brand": "Keep", "category": "哑铃",
         "description": "Keep入门哑铃，5kg适合女性和健身新手，烤漆铸铁耐用，防滑包胶手感舒适。"},
        {"product_id": "jd_bofit_dumbbell_20kg", "title": "博飞 可调哑铃 5-20kg 快调式",
         "price": 599.0, "original_price": 799.0, "rating": 4.8, "sales": "月销6800",
         "key_specs": "5-20kg快调/旋转调节/铸铁/防滑手柄/收纳托盘",
         "brand": "博飞", "category": "哑铃",
         "description": "博飞快调哑铃，旋转拨盘秒速调重，5-20kg满足进阶训练，铸铁耐用，附收纳托盘整洁桌面。"},
        {"product_id": "jd_bowflex_552", "title": "Bowflex 552 可调哑铃 2.3-24kg 单只",
         "price": 1299.0, "original_price": 1699.0, "rating": 4.9, "sales": "月销2100",
         "key_specs": "2.3-24kg/15档可调/快速拨盘/单只/专业健身",
         "brand": "Bowflex", "category": "哑铃",
         "description": "Bowflex 552专业可调哑铃，15档重量秒速切换，2.3-24kg覆盖全训练需求，替代15对传统哑铃，家庭健身房旗舰选择。"},
        {"product_id": "jd_reebok_dumbbell_8kg_pair", "title": "锐步 包胶固定哑铃 8kg×2 防滑",
         "price": 199.0, "original_price": 259.0, "rating": 4.7, "sales": "月销1.1万",
         "key_specs": "8kg×2/包胶铸铁/防滑纹/防震防噪/固定重量/家用",
         "brand": "锐步", "category": "哑铃",
         "description": "锐步8kg固定哑铃一对装，包胶铸铁防滑耐磨，落地不损伤地板，适合有一定基础的女性或健身新手做肩部胸部训练，性价比优选。"},
        {"product_id": "jd_xiaomi_adj_dumbbell_24kg", "title": "小米有品 可调节哑铃 5-24kg 旋转锁",
         "price": 499.0, "original_price": 649.0, "rating": 4.7, "sales": "月销8200",
         "key_specs": "5-24kg/旋转锁调节/防摔包胶/单只/家用进阶",
         "brand": "小米有品", "category": "哑铃",
         "description": "小米有品可调节哑铃，旋转锁快速切换重量，5-24kg覆盖初级到进阶训练需求，防摔包胶设计，居家健身房空间节省利器。"},
    ],
    "瑜伽垫": [
        {"product_id": "jd_aoyi_yogamat_6mm", "title": "奥义 天然橡胶瑜伽垫 6mm 加厚",
         "price": 198.0, "original_price": 259.0, "rating": 4.8, "sales": "月销3.2万",
         "key_specs": "天然橡胶/6mm/183×68cm/防滑/吸汗/可机洗",
         "brand": "奥义", "category": "瑜伽垫",
         "description": "奥义天然橡胶加厚瑜伽垫，6mm保护膝盖，宽版68cm活动空间大，天然橡胶防滑耐磨，性价比之选。"},
        {"product_id": "jd_lululemon_themat", "title": "lululemon The Mat 5mm 天然橡胶瑜伽垫",
         "price": 898.0, "original_price": 998.0, "rating": 4.9, "sales": "月销1800",
         "key_specs": "天然橡胶/5mm/183×61cm/防滑纹/正反双面",
         "brand": "lululemon", "category": "瑜伽垫",
         "description": "lululemon顶级瑜伽垫，天然橡胶双面纹路，正面防滑背面防移，5mm厚度关节友好，适合高强度瑜伽训练。"},
        {"product_id": "jd_keep_yogamat_4mm", "title": "Keep 瑜伽垫 4mm TPE环保材质",
         "price": 79.0, "original_price": 109.0, "rating": 4.7, "sales": "月销5.6万",
         "key_specs": "TPE环保/4mm/183×61cm/双面防滑/附背带",
         "brand": "Keep", "category": "瑜伽垫",
         "description": "Keep入门瑜伽垫，TPE环保无味材质，双面防滑纹路，附赠收纳背带，轻量便携适合初学者。"},
        {"product_id": "jd_decathlon_yogamat", "title": "迪卡侬 瑜伽垫 8mm 加厚防滑",
         "price": 149.0, "original_price": 199.0, "rating": 4.7, "sales": "月销4.1万",
         "key_specs": "NBR材质/8mm加厚/183×61cm/防滑/耐磨",
         "brand": "迪卡侬", "category": "瑜伽垫",
         "description": "迪卡侬8mm加厚瑜伽垫，NBR材质软弹兼备，超厚保护关节，适合健身初学者和地面训练。"},
        {"product_id": "jd_manduka_pro_yoga_mat", "title": "Manduka PRO 瑜伽垫 6mm 超密度天然橡胶",
         "price": 1298.0, "original_price": 1498.0, "rating": 4.9, "sales": "月销3200",
         "key_specs": "天然橡胶/6mm/183×66cm/封闭式气泡防滑/终身保修/专业级",
         "brand": "Manduka", "category": "瑜伽垫",
         "description": "Manduka PRO专业瑜伽垫，超密度天然橡胶封闭式气泡提供顶级缓震，干湿均防滑，终身保修承诺，专业瑜伽练习者最终选择。"},
        {"product_id": "jd_kepai_tpe_yoga_80cm", "title": "科派 TPE环保瑜伽垫 双色 6mm 加宽80cm",
         "price": 168.0, "original_price": 228.0, "rating": 4.7, "sales": "月销2.1万",
         "key_specs": "TPE环保/6mm/183×80cm加宽/双面防滑/无异味/附背带",
         "brand": "科派", "category": "瑜伽垫",
         "description": "科派TPE双色环保瑜伽垫，加宽80cm活动空间充足，6mm厚度关节友好，环保无毒无异味，双面防滑纹路，附赠背带方便携带，健身房家庭双用首选。"},
    ],
    "跳绳": [
        {"product_id": "jd_keep_skipping_smart", "title": "Keep 智能跳绳 计数款 无绳磁力",
         "price": 99.0, "original_price": 129.0, "rating": 4.8, "sales": "月销8.9万",
         "key_specs": "智能计数/无绳磁力版/App联动/可调长度/室内专属",
         "brand": "Keep", "category": "跳绳",
         "description": "Keep智能跳绳，App实时同步运动数据，无绳磁力版适合室内小空间，自动计数无需手动记录。"},
        {"product_id": "jd_ropejump_bearing", "title": "专业跳绳 培林钢丝绳 竞速款",
         "price": 39.0, "original_price": 59.0, "rating": 4.8, "sales": "月销6.2万",
         "key_specs": "培林轴承/钢丝绳/可调长度/竞速/防缠绕",
         "brand": "火速", "category": "跳绳",
         "description": "培林轴承竞速跳绳，钢丝绳极速旋转顺滑，可调节长度适配不同身高，专业运动员级别体验百元内到手。"},
        {"product_id": "jd_tangram_f3c", "title": "切割者 F3C 智能跳绳 可计数",
         "price": 149.0, "original_price": 199.0, "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "LCD计数/培林/PVC绳/可调/卡路里计算",
         "brand": "切割者", "category": "跳绳",
         "description": "切割者F3C智能跳绳，LCD屏实时显示次数和热量，培林顺滑防缠，PVC软绳不打脚，家用健身首选。"},
        {"product_id": "jd_ropejump_speed_pro", "title": "火速 竞速钢丝跳绳 专业比赛款",
         "price": 59.0, "original_price": 89.0, "rating": 4.8, "sales": "月销9800",
         "key_specs": "双培林/304不锈钢丝/可调节/轻量46g/双色花样适用",
         "brand": "火速", "category": "跳绳",
         "description": "火速竞速专业钢丝跳绳，双培林轴承超顺滑，304不锈钢丝极速旋转，46g轻量减少手腕负担，竞技跳绳选手和健身爱好者首选。"},
        {"product_id": "jd_crossrope_get_lean", "title": "Crossrope Get Lean 花样跳绳套装",
         "price": 699.0, "original_price": 899.0, "rating": 4.9, "sales": "月销2800",
         "key_specs": "轻重两根绳/快换系统/计次App/1/4磅轻绳+1/2磅重绳/进阶训练",
         "brand": "Crossrope", "category": "跳绳",
         "description": "Crossrope Get Lean套装，含轻绳和重绳两款，快换卡扣2秒切换，配套App记录训练数据，轻绳适合速度训练，重绳锻炼上肢肌耐力，花样健身跳绳旗舰。"},
        {"product_id": "jd_xiaomi_weighted_rope", "title": "小米有品 负重跳绳 加重款 300g",
         "price": 89.0, "original_price": 119.0, "rating": 4.7, "sales": "月销1.8万",
         "key_specs": "300g加重/培林/PVC绳/可调长度/肌力增强/含计数显示",
         "brand": "小米有品", "category": "跳绳",
         "description": "小米有品负重跳绳，300g加重设计强化上肢力量，培林轴承旋转顺畅，LCD计数显示，长期训练后可换轻绳感受速度飞升，进阶训练利器。"},
    ],
    "运动垫": [
        {"product_id": "jd_aozhoushi_treadmill_mat", "title": "澳洲狮 跑步机专用减震垫 185×90cm",
         "price": 199.0, "original_price": 259.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "NBR材质/185×90cm/8mm厚/防滑防震/减噪",
         "brand": "澳洲狮", "category": "运动垫",
         "description": "跑步机专用减震垫，8mm厚NBR有效降噪，防滑底面保护地板，185×90cm适配大多数跑步机。"},
        {"product_id": "jd_aoyi_fitnessmat_10mm", "title": "奥义 健身垫 10mm 加厚防滑",
         "price": 89.0, "original_price": 129.0, "rating": 4.7, "sales": "月销3.8万",
         "key_specs": "NBR/10mm/180×80cm/防滑/多功能/卷收",
         "brand": "奥义", "category": "运动垫",
         "description": "奥义多功能健身垫，10mm加厚缓震，防滑纹路稳固支撑，仰卧起坐俯卧撑跑步机均适用，卷收节省空间。"},
        {"product_id": "jd_keep_fitmat_8mm", "title": "Keep 运动垫 8mm 双面防滑",
         "price": 69.0, "original_price": 99.0, "rating": 4.7, "sales": "月销5.1万",
         "key_specs": "TPE/8mm/183×80cm/双面防滑/附绑带",
         "brand": "Keep", "category": "运动垫",
         "description": "Keep运动垫，TPE环保材质双面防滑，8mm厚度保护关节，宽版80cm训练不受限，附赠捆绑带方便收纳。"},
        {"product_id": "jd_aoyi_stretch_mat", "title": "奥义 拉伸垫 185×100cm 宽幅版",
         "price": 129.0, "original_price": 169.0, "rating": 4.8, "sales": "月销2.8万",
         "key_specs": "NBR/10mm/185×100cm大尺寸/防滑双面/附收纳袋/拉伸瑜伽均适",
         "brand": "奥义", "category": "运动垫",
         "description": "奥义宽幅拉伸垫，185×100cm超大面积提供充足活动空间，10mm厚度缓震保护，双面防滑纹路，拉伸热身、核心训练均适用，附收纳袋整洁存放。"},
        {"product_id": "jd_decathlon_fold_mat", "title": "迪卡侬 折叠健身垫 便携运动垫",
         "price": 99.0, "original_price": 139.0, "rating": 4.7, "sales": "月销3.6万",
         "key_specs": "EVA折叠/10mm/180×60cm/折叠便携/防水/户外健身适用",
         "brand": "迪卡侬", "category": "运动垫",
         "description": "迪卡侬折叠运动垫，EVA材质可对折便携出行，10mm厚度缓震，防水面料户外地面皆可铺，轻量外出健身不受限，学生宿舍折叠收纳首选。"},
        {"product_id": "jd_lonsdale_pro_mat", "title": "龙斯戴尔 专业地板武术垫 厚款 10mm",
         "price": 159.0, "original_price": 199.0, "rating": 4.7, "sales": "月销1.4万",
         "key_specs": "PVC/10mm/200×90cm/防滑/适合武术搏击/防摔抗冲击",
         "brand": "龙斯戴尔", "category": "运动垫",
         "description": "龙斯戴尔专业运动垫，200×90cm超宽面积，防滑PVC表面稳固，10mm厚度抗冲击性强，适合武术、搏击、拉伸等需要大活动面积的运动。"},
    ],
    "运动耳机": [
        {"product_id": "jd_jabra_elite4_active", "title": "Jabra Elite 4 Active 防水运动耳机",
         "price": 299.0, "original_price": 399.0, "rating": 4.8, "sales": "月销9500",
         "key_specs": "IP57防水/主动降噪/7h续航/4麦克风/运动稳固",
         "brand": "Jabra", "category": "运动耳机",
         "description": "Jabra Elite 4 Active专为运动设计，IP57防水，主动降噪专注训练，4麦克风运动通话清晰。"},
        {"product_id": "jd_beats_fitpro_sport", "title": "Beats Fit Pro 主动降噪运动耳机",
         "price": 1299.0, "original_price": 1499.0, "rating": 4.8, "sales": "月销5200",
         "key_specs": "H1芯片/翼形稳定耳翼/主动降噪/IPX4/Apple全功能",
         "brand": "Beats", "category": "运动耳机",
         "description": "Beats Fit Pro翼形稳定耳翼专为运动设计，H1芯片苹果设备一触即连，降噪让你专注训练。"},
        {"product_id": "jd_shokz_openrun", "title": "韶音 OpenRun 骨传导运动耳机",
         "price": 799.0, "original_price": 999.0, "rating": 4.8, "sales": "月销3.6万",
         "key_specs": "骨传导/IP67防水/8h续航/不入耳/户外安全",
         "brand": "韶音", "category": "运动耳机",
         "description": "韶音OpenRun骨传导耳机，不入耳设计保留环境音，跑步骑行安全感知周围，IP67防水汗水雨水无惧。"},
        {"product_id": "jd_samsung_buds_fe", "title": "三星 Galaxy Buds FE 运动耳机",
         "price": 399.0, "original_price": 499.0, "rating": 4.7, "sales": "月销7800",
         "key_specs": "主动降噪/IPX2/6h续航/翼形耳翼/三星设备优化",
         "brand": "三星", "category": "运动耳机",
         "description": "三星Galaxy Buds FE，翼形耳翼运动稳固，主动降噪专注模式，三星设备无缝连接，性价比运动款。"},
        {"product_id": "jd_sony_wf_sp800n_sport", "title": "索尼 WF-SP800N 防水运动降噪耳机",
         "price": 549.0, "original_price": 699.0, "rating": 4.8, "sales": "月销1.3万",
         "key_specs": "IP55防水防汗/主动降噪/9h续航/环境声模式/运动稳固翼片",
         "brand": "索尼", "category": "运动耳机",
         "description": "索尼WF-SP800N运动版降噪耳机，IP55防水可在雨中训练，主动降噪专注，环境声模式户外安全感知，稳固翼片防脱落，运动与降噪双全。"},
        {"product_id": "jd_jbl_endurance_peak3_sport", "title": "JBL Endurance Peak 3 运动防水耳机 IP68",
         "price": 399.0, "original_price": 499.0, "rating": 4.7, "sales": "月销8900",
         "key_specs": "IP68防水/挂耳式稳固/10h续航/主动降噪/快充/运动专属",
         "brand": "JBL", "category": "运动耳机",
         "description": "JBL Endurance Peak 3挂耳式运动耳机，IP68顶级防水可游泳，FlexSoft C型挂钩牢固佩戴，主动降噪专注训练，10小时续航马拉松全程无忧，运动爱好者必备。"},
    ],
    "弹力带": [
        {"product_id": "jd_aoyi_band_5pack", "title": "奥义 弹力带套装 5条装 深蹲翘臀",
         "price": 59.0, "original_price": 89.0, "rating": 4.8, "sales": "月销4.6万",
         "key_specs": "5条/乳胶/5种阻力/防滚动宽版/收纳袋",
         "brand": "奥义", "category": "弹力带",
         "description": "奥义弹力带5条套装，5种阻力循序渐进，宽版防滚动贴合腿部，乳胶材质耐拉伸，深蹲塑形必备。"},
        {"product_id": "jd_keep_band_3pack", "title": "Keep 弹力带 3条装 健身阻力带",
         "price": 39.0, "original_price": 59.0, "rating": 4.7, "sales": "月销3.2万",
         "key_specs": "3条/轻中重/乳胶/防滑/适合初学者",
         "brand": "Keep", "category": "弹力带",
         "description": "Keep弹力带3条装，轻中重三档阻力适合不同训练阶段，乳胶材质弹性持久，初学者入门首选。"},
        {"product_id": "jd_resistance_tube_set", "title": "弹力绳套装 11件套 拉力绳健身",
         "price": 89.0, "original_price": 129.0, "rating": 4.7, "sales": "月销1.8万",
         "key_specs": "11件套/5条拉力绳+把手+踝套+门挂/可叠加",
         "brand": "飞力士", "category": "弹力带",
         "description": "11件套弹力绳组合，5条不同阻力可叠加使用，配套把手踝套门挂，全身训练一套搞定，家庭健身房必备。"},
        {"product_id": "jd_wodfitters_tube_set", "title": "弹力管拉力器套装 5管可叠加 全身训练",
         "price": 119.0, "original_price": 159.0, "rating": 4.7, "sales": "月销2.2万",
         "key_specs": "5根管/乳胶/D型把手/踝套/门锚/轻中重超重4档/总阻力68kg",
         "brand": "飞力士", "category": "弹力带",
         "description": "弹力管拉力器5根套装，乳胶管阻力均匀，D型把手舒适握感，可同时使用多根叠加阻力最高68kg，门锚固定随时开练，全身力量训练必备。"},
        {"product_id": "jd_meglio_x_band", "title": "X形弹力拉力绳 交叉拉力带 背肌肩部",
         "price": 69.0, "original_price": 99.0, "rating": 4.7, "sales": "月销1.5万",
         "key_specs": "X形交叉/双手柄/背肌肩部/腰背训练/TPE材质/轻中重3档",
         "brand": "健牌", "category": "弹力带",
         "description": "X形交叉拉力绳，双向拉力符合背肌肩部发力路径，有效强化菱形肌和后三角，TPE弹力均匀不易断裂，久坐族纠正体态神器。"},
        {"product_id": "jd_thera_band_set", "title": "TheraBand 康复理疗弹力带 6米卷装",
         "price": 159.0, "original_price": 199.0, "rating": 4.8, "sales": "月销3800",
         "key_specs": "乳胶/6米卷/轻中重超重/康复物理治疗/平整宽带/可裁剪",
         "brand": "TheraBand", "category": "弹力带",
         "description": "TheraBand专业康复弹力带，物理治疗行业标准，6米卷可按需裁剪，平整宽带贴合身体不切割皮肤，适合关节康复训练和老人康复锻炼。"},
    ],
    "空气净化器": [
        {"product_id": "jd_xiaomi_air4pro", "title": "小米 空气净化器 4 Pro",
         "price": 1299.0, "original_price": 1599.0, "rating": 4.9, "sales": "月销2.1万",
         "key_specs": "CADR 500m³/h/PM2.5/甲醛检测/OLED屏/米家APP/静音",
         "brand": "小米", "category": "空气净化器",
         "description": "小米空气净化器4 Pro，CADR 500m³/h适合大面积房间，内置甲醛传感器实时监测，OLED屏显示空气质量，米家APP远程控制，静音模式仅32dB。"},
        {"product_id": "jd_blueair_211plus", "title": "布鲁雅尔 Blue 211+ 空气净化器",
         "price": 1999.0, "original_price": 2499.0, "rating": 4.8, "sales": "月销9500",
         "key_specs": "CADR 350m³/h/HEPASilent双效过滤/超静音/简约设计/瑞典品牌",
         "brand": "布鲁雅尔", "category": "空气净化器",
         "description": "布鲁雅尔Blue 211+，HEPASilent专利技术同时去除PM2.5和病毒，超静音运行仅17dB，瑞典百年品牌品质保证，简约设计家居百搭。"},
        {"product_id": "jd_352_x83c", "title": "352 X83C 空气净化器 大面积",
         "price": 2999.0, "original_price": 3999.0, "rating": 4.9, "sales": "月销6200",
         "key_specs": "CADR 800m³/h/6重过滤/去甲醛/适合150㎡/APP控制",
         "brand": "352", "category": "空气净化器",
         "description": "352 X83C大面积旗舰净化器，CADR高达800m³/h，6重过滤系统全面净化，高效去除甲醛、PM2.5、细菌，适合大客厅开放式空间。"},
        {"product_id": "jd_dyson_tp07", "title": "戴森 Purifier Cool TP07 净化风扇",
         "price": 3999.0, "original_price": 4999.0, "rating": 4.8, "sales": "月销4800",
         "key_specs": "净化+制冷二合一/HEPA13/无叶安全/LCD屏/APP控制/全屋循环",
         "brand": "戴森", "category": "空气净化器",
         "description": "戴森TP07净化风扇二合一，HEPA H13过滤99.97%颗粒物，无叶设计安全省电，360°全屋均匀送风，夏天净化降温一台解决，颜值与功能并存。"},
        {"product_id": "jd_philips_ac2887", "title": "飞利浦 AC2887 空气净化器",
         "price": 1799.0, "original_price": 2299.0, "rating": 4.7, "sales": "月销7100",
         "key_specs": "CADR 333m³/h/4重过滤/实时PM2.5/自动感应/静音睡眠模式",
         "brand": "飞利浦", "category": "空气净化器",
         "description": "飞利浦AC2887，4重过滤高效去除过敏原、烟雾、细菌，实时空气质量数字显示，自动感应污染自动调速，静音睡眠模式22dB超安静。"},
        {"product_id": "jd_smartmi_p1", "title": "智米 空气净化器 P1",
         "price": 999.0, "original_price": 1299.0, "rating": 4.7, "sales": "月销1.2万",
         "key_specs": "CADR 400m³/h/三效滤芯/PM2.5传感器/米家联动/轻量设计",
         "brand": "智米", "category": "空气净化器",
         "description": "智米P1空气净化器，CADR 400m³/h适合中等面积房间，三效复合滤芯过滤PM2.5+异味+细菌，米家生态联动，轻量外观适合卧室摆放。"},
    ],
    "吸尘器": [
        {"product_id": "jd_dyson_v12detect", "title": "戴森 V12 Detect Slim 无线吸尘器",
         "price": 3499.0, "original_price": 3999.0, "rating": 4.9, "sales": "月销4200",
         "key_specs": "280AW吸力/激光探尘/HEPA过滤/60min续航/0.35L尘桶/轻量2.2kg",
         "brand": "戴森", "category": "吸尘器",
         "description": "戴森V12 Detect Slim，激光照明技术精准探测微尘，280AW超强吸力，HEPA过滤99.99%，60分钟超长续航，2.2kg轻量设计。"},
        {"product_id": "jd_xiaomi_vacuum_g10plus", "title": "小米 无线吸尘器 G10 Plus",
         "price": 999.0, "original_price": 1299.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "185AW吸力/HEPA过滤/60min续航/0.5L尘桶/轻量1.65kg/低噪音",
         "brand": "小米", "category": "吸尘器",
         "description": "小米G10 Plus无线吸尘器，185AW强力吸力，HEPA四重过滤，60分钟超长续航，1.65kg超轻机身，适合全屋清洁。"},
        {"product_id": "jd_roborock_h13pro", "title": "石头 H13 Pro 无线吸尘器",
         "price": 1999.0, "original_price": 2499.0, "rating": 4.8, "sales": "月销9600",
         "key_specs": "280AW/五重过滤/90min续航/LED探尘灯/自动除尘基站",
         "brand": "石头", "category": "吸尘器",
         "description": "石头H13 Pro，280AW超强吸力，LED探尘灯可见微尘，配备自动除尘基站，90分钟长续航，五重过滤系统。"},
        {"product_id": "jd_philips_xc8349", "title": "飞利浦 XC8349 无线吸尘器 旗舰款",
         "price": 1599.0, "original_price": 1999.0, "rating": 4.7, "sales": "月销6800",
         "key_specs": "280AW/HEPA13/60min/LCD显示/软绒滚刷/宠物版",
         "brand": "飞利浦", "category": "吸尘器",
         "description": "飞利浦XC8349旗舰无线吸尘器，280AW强劲吸力，HEPA13高效过滤，LCD实时显示吸力模式，软绒滚刷适合宠物毛发。"},
        {"product_id": "jd_ecovacs_v_omni", "title": "科沃斯 V Omni 手持无线吸尘器",
         "price": 1299.0, "original_price": 1599.0, "rating": 4.8, "sales": "月销7200",
         "key_specs": "230AW/HEPA/75min续航/自动清洗基站/多附件/低噪音",
         "brand": "科沃斯", "category": "吸尘器",
         "description": "科沃斯V Omni无线吸尘器，230AW吸力，配备自动清洗基站，75分钟超长续航，多附件适配全屋场景。"},
        {"product_id": "jd_roidmi_eve_plus_vac", "title": "睿米 EVE Plus 无线吸尘器 自清洁基站",
         "price": 1699.0, "original_price": 1999.0, "rating": 4.8, "sales": "月销5400",
         "key_specs": "200AW吸力/自动集尘基站/HEPA/75min续航/LED探尘灯/宠物版",
         "brand": "睿米", "category": "吸尘器",
         "description": "睿米EVE Plus无线吸尘器配自动集尘基站，200AW强力吸尘，LED探尘灯照亮微尘，HEPA过滤净化空气，75分钟长续航，宠物毛发克星，自动清空告别频繁倒尘。"},
    ],
    "卷发棒": [
        {"product_id": "jd_philips_bhb879", "title": "飞利浦 BHB879 多功能卷发棒 负离子",
         "price": 299.0, "original_price": 399.0, "rating": 4.8, "sales": "月销1.6万",
         "key_specs": "32mm/负离子护发/200℃/防烫手柄/多档温控/快速加热",
         "brand": "飞利浦", "category": "卷发棒",
         "description": "飞利浦BHB879卷发棒，32mm大卷筒制造蓬松大波浪，负离子技术减少毛躁，多档温控，60秒快速加热，防烫手柄安全易用。"},
        {"product_id": "jd_remington_ci96", "title": "雷明顿 CI96W1 陶瓷卷发棒 26mm",
         "price": 199.0, "original_price": 269.0, "rating": 4.7, "sales": "月销2.3万",
         "key_specs": "26mm/陶瓷镀层/5档温控/负离子/快速加热/防静电",
         "brand": "雷明顿", "category": "卷发棒",
         "description": "雷明顿CI96W1陶瓷卷发棒，26mm适合中小卷，陶瓷镀层均匀加热不损伤，负离子防静电，5档温控，入门性价比之选。"},
        {"product_id": "jd_ghd_curve_classic", "title": "ghd Curve Classic Curl 专业卷发棒",
         "price": 1299.0, "original_price": 1599.0, "rating": 4.9, "sales": "月销4800",
         "key_specs": "26mm/恒温185℃/陶瓷/快速加热25s/睡眠模式/英国专业品牌",
         "brand": "ghd", "category": "卷发棒",
         "description": "ghd专业卷发棒，智能恒温185℃保护发质，25秒快速加热，360°旋转电线，自动睡眠模式，英国顶级美发品牌专业之选。"},
        {"product_id": "jd_panasonic_eh_ht65", "title": "松下 EH-HT65 卷发棒 离子护理",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销8900",
         "key_specs": "26mm/纳米水离子/190℃/三温控/快速加热/防烫",
         "brand": "松下", "category": "卷发棒",
         "description": "松下EH-HT65卷发棒，纳米水离子技术深层护发补水，190℃高温快速定型，三档温控，适合不同发质，日本品质保障。"},
        {"product_id": "jd_conair_infiniti_curl32", "title": "康奈尔 InfinitiPRO 卷发棒 32mm 陶瓷",
         "price": 229.0, "original_price": 299.0, "rating": 4.7, "sales": "月销1.5万",
         "key_specs": "32mm/陶瓷电气石涂层/5档温控/负离子/旋转电线/快热",
         "brand": "康奈尔", "category": "卷发棒",
         "description": "康奈尔InfinitiPRO陶瓷电气石卷发棒，32mm适合大卷波浪，陶瓷涂层加热均匀不灼烧，负离子减少毛躁，5档温控适合各类发质，性价比入门专业款。"},
        {"product_id": "jd_babyliss_c326e_auto", "title": "宝莱氏 C326E 自动卷发器 全自动旋转",
         "price": 699.0, "original_price": 899.0, "rating": 4.8, "sales": "月销6800",
         "key_specs": "自动旋转/32mm/陶瓷涂层/智能恒温/计时提示/左右双向卷",
         "brand": "宝莱氏", "category": "卷发棒",
         "description": "宝莱氏C326E自动卷发器，全自动旋转吸入发丝，左右双向卷发自由切换，智能恒温保护发质，计时提示避免过热，初学者也能轻松卷出专业效果。"},
    ],
    "掌机": [
        {"product_id": "jd_steam_deck_oled", "title": "Steam Deck OLED 掌机 1TB 旗舰版",
         "price": 4499.0, "original_price": 4999.0, "rating": 4.9, "sales": "月销2100",
         "key_specs": "7.4寸OLED/1TB/AMD APU/90Hz/WiFi6/全PC游戏库",
         "brand": "Valve", "category": "掌机",
         "description": "Steam Deck OLED旗舰版，7.4寸90Hz OLED显示屏，1TB高速固态，可玩完整PC Steam游戏库，是迄今最强掌机。"},
        {"product_id": "jd_rog_ally_x", "title": "ROG Ally X 掌上游戏机 AMD Z1 Extreme",
         "price": 5999.0, "original_price": 6999.0, "rating": 4.8, "sales": "月销1800",
         "key_specs": "7寸1080P 120Hz/AMD Z1 Extreme/24GB内存/1TB/Windows11",
         "brand": "华硕ROG", "category": "掌机",
         "description": "华硕ROG Ally X，AMD Z1 Extreme旗舰处理器，7寸1080P 120Hz高刷屏，24GB大内存，完整Windows 11系统，顶级掌上游戏电脑。"},
        {"product_id": "jd_gamesir_x4_phone", "title": "盖世小鸡 X4 Aileron 手机游戏手柄",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销3.6万",
         "key_specs": "伸缩式/霍尔磁性摇杆/蓝牙5.3/20h续航/兼容Android/iOS",
         "brand": "盖世小鸡", "category": "掌机",
         "description": "盖世小鸡X4手机游戏手柄，伸缩设计兼容各尺寸手机，霍尔磁性摇杆精准无漂移，20小时续航，将手机变成掌机。"},
        {"product_id": "jd_retroid_pocket4_pro", "title": "Retroid Pocket 4 Pro 安卓掌机 6寸",
         "price": 1499.0, "original_price": 1799.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "6寸1080P AMOLED/骁龙G3x Gen1/8GB+128GB/Android 13/模拟器神器",
         "brand": "Retroid", "category": "掌机",
         "description": "Retroid Pocket 4 Pro安卓掌机，骁龙G3x Gen1强劲性能，6寸1080P AMOLED显示屏，Android 13原生系统，完美运行各平台模拟器和云游戏，性价比安卓掌机旗舰。"},
        {"product_id": "jd_logitech_g_cloud", "title": "罗技 G Cloud 云游戏掌机 WiFi版",
         "price": 1999.0, "original_price": 2499.0, "rating": 4.7, "sales": "月销3100",
         "key_specs": "7寸1080P 60Hz/骁龙720G/447g超轻/12h续航/Xbox Cloud/Steam Link",
         "brand": "罗技", "category": "掌机",
         "description": "罗技G Cloud云游戏掌机，7寸1080P高清屏，447g超轻于同类产品，专为云游戏优化，支持Xbox Cloud Gaming和Steam Link，12小时超长续航无忧畅玩。"},
        {"product_id": "jd_odin2_mini", "title": "Ayn Odin 2 Mini 安卓掌机 骁龙8 Gen2",
         "price": 2299.0, "original_price": 2799.0, "rating": 4.8, "sales": "月销2200",
         "key_specs": "5.98寸AMOLED/骁龙8 Gen2/12GB+256GB/Android 13/PC质量游戏体验",
         "brand": "Ayn", "category": "掌机",
         "description": "Ayn Odin 2 Mini旗舰安卓掌机，骁龙8 Gen2顶级移动芯片，5.98寸AMOLED高色域屏幕，运行原神赛马娘等高性能游戏流畅无卡顿，安卓掌机性能天花板。"},
    ],
    "电视": [
        {"product_id": "jd_xiaomi_tv_ea65", "title": "小米 EA65 65寸 4K智能电视",
         "price": 2299.0, "original_price": 2799.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "65寸/4K超高清/120Hz/MIUI TV/杜比全景声/低蓝光护眼",
         "brand": "小米", "category": "电视",
         "description": "小米EA65 65寸4K智能电视，MIUI TV内容丰富，120Hz高刷流畅画质，杜比全景声临场感强，内置小爱同学语音控制，高性价比家用首选。"},
        {"product_id": "jd_hisense_u7h_65", "title": "海信 U7H 65寸 ULED量子点电视",
         "price": 3299.0, "original_price": 3999.0, "rating": 4.9, "sales": "月销9500",
         "key_specs": "65寸/ULED量子点/1000nit高亮度/144Hz/IMAX增强/4K",
         "brand": "海信", "category": "电视",
         "description": "海信U7H ULED量子点电视，1000nit高亮度HDR表现出众，144Hz超高刷新率，IMAX增强认证，游戏电影双模旗舰体验。"},
        {"product_id": "jd_tcl_c735_55", "title": "TCL C735 55寸 Mini LED量子点电视",
         "price": 2999.0, "original_price": 3599.0, "rating": 4.8, "sales": "月销7200",
         "key_specs": "55寸/Mini LED/1200nit峰值亮度/144Hz/HDMI2.1/Google TV",
         "brand": "TCL", "category": "电视",
         "description": "TCL C735 Mini LED电视，1200nit峰值亮度HDR画面层次分明，144Hz高刷，HDMI2.1支持4K120Hz游戏，Google TV内容生态完整。"},
        {"product_id": "jd_sony_x90l_55", "title": "索尼 XR-55X90L 55寸 4K智能电视",
         "price": 4999.0, "original_price": 5999.0, "rating": 4.9, "sales": "月销3800",
         "key_specs": "55寸/XR认知芯片/120Hz/4K/Google TV/杜比视界杜比全景声",
         "brand": "索尼", "category": "电视",
         "description": "索尼X90L搭载XR认知芯片智能优化画质，120Hz自然动态，杜比视界+全景声影院级体验，Google TV内容丰富，品质旗舰之选。"},
        {"product_id": "jd_xiaomi_tv_max86", "title": "小米电视 Max 86寸 大屏旗舰",
         "price": 5999.0, "original_price": 7299.0, "rating": 4.8, "sales": "月销2100",
         "key_specs": "86寸/4K/120Hz/MIUI TV/144分区背光/低蓝光",
         "brand": "小米", "category": "电视",
         "description": "小米Max 86超大屏旗舰，86寸沉浸式观影体验，144分区背光对比度出众，120Hz高刷，MIUI TV生态丰富，超大尺寸最高性价比之选。"},
        {"product_id": "jd_hisense_laser_80", "title": "海信 80L5 激光电视 80寸",
         "price": 7999.0, "original_price": 9999.0, "rating": 4.8, "sales": "月销1500",
         "key_specs": "80寸/激光光源/4K/100%色域覆盖/护眼/极短焦",
         "brand": "海信", "category": "电视",
         "description": "海信L5激光电视，极短焦近距离投出80寸大画面，激光光源护眼无蓝光伤害，100%色域还原自然色彩，家庭影院终极体验。"},
        {"product_id": "jd_tcl_p745_75", "title": "TCL P745 75寸 4K全面屏电视",
         "price": 3999.0, "original_price": 4699.0, "rating": 4.7, "sales": "月销5600",
         "key_specs": "75寸/4K/60Hz/Google TV/HDR10/Dolby Audio/超薄边框",
         "brand": "TCL", "category": "电视",
         "description": "TCL P745 75寸大屏4K电视，超薄全面屏外观时尚，Google TV内容丰富，HDR10画质提升，Dolby Audio音效，大屏追剧首选实惠款。"},
    ],
    "冰箱": [
        {"product_id": "jd_samsung_rb38c776cs9", "title": "三星 RB38C776CS9 下置冷冻室冰箱 390L",
         "price": 5999.0, "original_price": 6999.0, "rating": 4.8, "sales": "月销3200",
         "key_specs": "390L/下置冷冻室/无霜/节能/多门储鲜", "brand": "三星", "category": "冰箱",
         "description": "Samsung RB38C776CS9 下置冷冻室冰箱，390L容量，无霜制冷和分区储鲜。"},
        {"product_id": "jd_midea_bcd_536", "title": "美的 BCD-536WSPZM 对开门冰箱 536L",
         "price": 3999.0, "original_price": 4999.0, "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "536L/双变频/风冷无霜/超薄嵌入/WiFi远控/一级能效",
         "brand": "美的", "category": "冰箱",
         "description": "美的BCD-536对开门冰箱，536L大容量适合三口之家，双变频压缩机静音省电，风冷无霜技术食材不结冰，WiFi智控一级能效。"},
        {"product_id": "jd_haier_bcd_470", "title": "海尔 BCD-470WBHSS6WY 多门冰箱 470L",
         "price": 4599.0, "original_price": 5499.0, "rating": 4.9, "sales": "月销1.5万",
         "key_specs": "470L/四门/干湿分储/变温室/净味除菌/一级能效/零嵌设计",
         "brand": "海尔", "category": "冰箱",
         "description": "海尔470L四门冰箱，干湿分储保鲜分区精准，变温室-18℃到8℃灵活切换，纳米净味除菌，零嵌设计完美嵌入橱柜，旗舰保鲜体验。"},
        {"product_id": "jd_siemens_ka92nv", "title": "西门子 KA92NV02TI 对开门冰箱 610L",
         "price": 6999.0, "original_price": 8499.0, "rating": 4.9, "sales": "月销6800",
         "key_specs": "610L/对开门/VitaFresh保鲜/超低噪音38dB/精控温/德国品质",
         "brand": "西门子", "category": "冰箱",
         "description": "西门子KA92NV对开门冰箱，610L超大容量，VitaFresh保鲜技术延长蔬果新鲜度，超低噪音38dB，精控温±0.5℃，德国精密工艺品质。"},
        {"product_id": "jd_midea_bcd_215", "title": "美的 BCD-215WTPZM 三门冰箱 215L",
         "price": 1599.0, "original_price": 1999.0, "rating": 4.7, "sales": "月销3.8万",
         "key_specs": "215L/三门/风冷无霜/变频/双重净味/一级能效/适合小户型",
         "brand": "美的", "category": "冰箱",
         "description": "美的215L三门冰箱，小户型首选，风冷无霜不结冰，变频压缩机省电静音，双重净味抑菌，一级能效省电，入门价格高性价比。"},
        {"product_id": "jd_haier_bcd_252", "title": "海尔 BCD-252WDVLU1 法式四门冰箱 252L",
         "price": 2999.0, "original_price": 3599.0, "rating": 4.8, "sales": "月销9200",
         "key_specs": "252L/法式多门/抽屉式冷冻/风冷无霜/净味/智能APP/一级能效",
         "brand": "海尔", "category": "冰箱",
         "description": "海尔BCD-252法式四门冰箱，抽屉式冷冻取物方便，分区储鲜精准保鲜，净味除菌，智能APP远控，设计感十足，中高端家用首选。"},
        {"product_id": "jd_panasonic_nr_d560", "title": "松下 NR-D560 三门冰箱 560L 日本技术",
         "price": 5499.0, "original_price": 6499.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "560L/三门/AG+银离子除菌/精控温/全风冷无霜/变频/日本技术",
         "brand": "松下", "category": "冰箱",
         "description": "松下NR-D560三门冰箱，AG+银离子除菌99.9%，精控温±1℃精准保鲜，全风冷无霜，变频节能，日本技术品质保障，注重食品安全的首选。"},
    ],
    "洗衣机": [
        {"product_id": "jd_haier_ew10014bd", "title": "海尔 EG100MATE89S 10kg 滚筒洗衣机",
         "price": 2999.0, "original_price": 3599.0, "rating": 4.9, "sales": "月销1.6万",
         "key_specs": "10kg/滚筒/1400转/免污内筒/直驱电机/一级能效/WIFI",
         "brand": "海尔", "category": "洗衣机",
         "description": "海尔EG100MATE89S 10kg滚筒洗衣机，免污内筒防止二次污染，直驱电机低噪高效，1400高转速脱水，WIFI智控，一级能效省电省水。"},
        {"product_id": "jd_littleswan_tg100", "title": "小天鹅 TG100VT096WDG 10kg 滚筒洗衣机",
         "price": 2599.0, "original_price": 3199.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "10kg/滚筒/DD直驱/蒸汽除菌/水魔方技术/一级能效/APP控制",
         "brand": "小天鹅", "category": "洗衣机",
         "description": "小天鹅TG100VT096W滚筒洗衣机，DD直驱电机减少噪音磨损，蒸汽除菌高温杀菌，水魔方技术精准控水，美的集团品质，一级能效节能。"},
        {"product_id": "jd_siemens_wg54a2x00", "title": "西门子 WG54A2X00W 10kg 变频滚筒洗衣机",
         "price": 3999.0, "original_price": 4999.0, "rating": 4.9, "sales": "月销8900",
         "key_specs": "10kg/滚筒/EcoSilence Drive变频/1400转/iQdrive/德国工艺/除菌",
         "brand": "西门子", "category": "洗衣机",
         "description": "西门子WG54A2X00W变频滚筒洗衣机，EcoSilence Drive超静音变频电机，iQdrive传感器智能调节，1400转高速脱水，德国精密工艺，中高端家用旗舰。"},
        {"product_id": "jd_haier_b10b66eu", "title": "海尔 EGW100HBDC189U1 10kg 洗烘一体机",
         "price": 4599.0, "original_price": 5499.0, "rating": 4.8, "sales": "月销6200",
         "key_specs": "10kg洗/6kg烘/滚筒洗烘一体/空气洗/免污内筒/WIFI/一级能效",
         "brand": "海尔", "category": "洗衣机",
         "description": "海尔EGW100HBDC洗烘一体机，10kg洗涤+6kg烘干，空气洗除菌除螨，免污内筒，洗完直接烘干无需晾晒，解放双手全自动洗烘。"},
        {"product_id": "jd_midea_mb100v11dy", "title": "美的 MB100V11DY 10kg 全自动波轮洗衣机",
         "price": 1699.0, "original_price": 1999.0, "rating": 4.7, "sales": "月销3.5万",
         "key_specs": "10kg/波轮/变频/桶自洁/快洗15min/一级能效/低噪音",
         "brand": "美的", "category": "洗衣机",
         "description": "美的MB100V11DY 10kg波轮洗衣机，变频电机节能静音，15分钟快洗应急需求，桶自洁功能除菌防霉，价格亲民高性价比家用首选。"},
        {"product_id": "jd_littleswan_tb80", "title": "小天鹅 TB80V20 8kg 波轮洗衣机",
         "price": 999.0, "original_price": 1299.0, "rating": 4.7, "sales": "月销5.8万",
         "key_specs": "8kg/波轮/立体瀑布洗/智能模糊控制/低泡洗涤/入门款",
         "brand": "小天鹅", "category": "洗衣机",
         "description": "小天鹅TB80V20 8kg波轮洗衣机，立体瀑布洗衣技术洗净率高，智能模糊控制自动调节程序，低泡洗涤容易漂清，千元内入门好选择。"},
    ],
    "行车记录仪": [
        {"product_id": "jd_70mai_a800s", "title": "70迈 A800S 行车记录仪 4K双录",
         "price": 499.0, "original_price": 599.0, "rating": 4.9, "sales": "月销2.8万",
         "key_specs": "4K前录+1080P后录/140°广角/GPS测速/ADAS预警/夜视增强/WiFi",
         "brand": "70迈", "category": "行车记录仪",
         "description": "70迈A800S 4K超高清行车记录仪，前后双录同步记录，GPS测速轨迹，ADAS行驶辅助预警，夜视增强清晰记录夜间细节，行车安全必备。"},
        {"product_id": "jd_ddpai_z40", "title": "盯盯拍 Z40 行车记录仪 4K旗舰",
         "price": 599.0, "original_price": 799.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "4K/超级夜视4.0/140°广角/AI感知/停车监控/内置GPS",
         "brand": "盯盯拍", "category": "行车记录仪",
         "description": "盯盯拍Z40 4K旗舰记录仪，超级夜视4.0技术夜间画质业界领先，AI智能感知，停车监控全天候看护爱车，内置GPS精准定位。"},
        {"product_id": "jd_lingdu_c50", "title": "凌度 C50 4K行车记录仪 前后双录",
         "price": 299.0, "original_price": 399.0, "rating": 4.7, "sales": "月销4.2万",
         "key_specs": "4K前录/1080P后录/150°超广角/WDR宽动态/停车监控/WiFi传输",
         "brand": "凌度", "category": "行车记录仪",
         "description": "凌度C50前后双录行车记录仪，4K超清前录，150°超广角全景无死角，WDR宽动态平衡明暗细节，WiFi快速传输视频，性价比之选。"},
        {"product_id": "jd_70mai_a500s", "title": "70迈 A500S 行车记录仪 1944P高清",
         "price": 199.0, "original_price": 249.0, "rating": 4.8, "sales": "月销6.8万",
         "key_specs": "1944P超清/130°广角/ADAS/停车监控/内存卡32G/WiFi",
         "brand": "70迈", "category": "行车记录仪",
         "description": "70迈A500S经典款记录仪，1944P超清分辨率拍清车牌，130°广角视野宽，ADAS辅助驾驶预警，200元档最高性价比，随附32G内存卡。"},
        {"product_id": "jd_ddpai_n3pro", "title": "盯盯拍 N3Pro 行车记录仪 极夜版",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销2.2万",
         "key_specs": "2K+超清/极夜视觉/超大光圈F1.4/AI感知/停车监控/重力感应",
         "brand": "盯盯拍", "category": "行车记录仪",
         "description": "盯盯拍N3Pro极夜版，超大光圈F1.4进光量更多，极夜视觉算法夜间录像亮如白昼，2K+超清分辨率，AI智能感知重要事件自动标记。"},
        {"product_id": "jd_mio_mivue_955wd", "title": "Mio MiVue 955WD 星光夜视记录仪",
         "price": 549.0, "original_price": 649.0, "rating": 4.8, "sales": "月销8900",
         "key_specs": "2K高清/星光夜视/140°广角/WIFI/停车监控/GPS/前后双录",
         "brand": "Mio", "category": "行车记录仪",
         "description": "Mio MiVue 955WD星光夜视前后双录，2K高清录制，专业星光感光元件夜视清晰，140°广角覆盖全路况，GPS轨迹记录，台湾专业行车安全品牌。"},
    ],
    "笔记本电脑": [
        {"product_id": "jd_lenovo_xiaoxin_pro16", "title": "联想 小新Pro16 2024 16寸轻薄本",
         "price": 5499.0, "original_price": 6299.0, "rating": 4.8, "sales": "月销1.2万",
         "key_specs": "英特尔Core Ultra5/16GB/512GB/16寸2.5K/120Hz/1.99kg轻薄",
         "brand": "联想", "category": "笔记本电脑",
         "description": "联想小新Pro16 2024，Core Ultra5旗舰处理器，16寸2.5K 120Hz高刷屏，16GB大内存流畅多任务，1.99kg轻薄机身，办公创作全能本。"},
        {"product_id": "jd_huawei_matebook_x_pro", "title": "华为 MateBook X Pro 2024 14.2寸旗舰",
         "price": 8999.0, "original_price": 10499.0, "rating": 4.9, "sales": "月销5600",
         "key_specs": "Core Ultra7/32GB/1TB/14.2寸3.1K OLED/华为生态/指纹解锁/1.26kg",
         "brand": "华为", "category": "笔记本电脑",
         "description": "华为MateBook X Pro 2024旗舰笔记本，14.2寸3.1K OLED触控屏色彩惊艳，Core Ultra7高性能处理器，32GB大内存，1.26kg超轻，华为生态多屏协同。"},
        {"product_id": "jd_apple_macbook_air_m3", "title": "苹果 MacBook Air 13寸 M3芯片 16GB",
         "price": 9499.0, "original_price": 10499.0, "rating": 4.9, "sales": "月销8800",
         "key_specs": "M3芯片/16GB/256GB/13.6寸2560×1664/18h续航/无风扇静音/1.24kg",
         "brand": "苹果", "category": "笔记本电脑",
         "description": "苹果MacBook Air M3，M3芯片性能大幅提升，16GB统一内存流畅运行，18小时超长续航，无风扇被动散热完全静音，1.24kg超轻，苹果生态首选。"},
        {"product_id": "jd_xiaomi_book_pro16", "title": "小米 Book Pro 16 2024 16寸创作本",
         "price": 6999.0, "original_price": 7999.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "Core Ultra7/32GB/1TB/16寸4K OLED/120Hz/2.05kg/雷电4",
         "brand": "小米", "category": "笔记本电脑",
         "description": "小米Book Pro16 2024，16寸4K OLED触控屏色彩专业级，Core Ultra7高性能，32GB+1TB大配置，雷电4高速扩展，适合摄影师设计师创作人群。"},
        {"product_id": "jd_lenovo_thinkpad_x1c", "title": "联想 ThinkPad X1 Carbon 14寸商务本",
         "price": 10999.0, "original_price": 12999.0, "rating": 4.9, "sales": "月销2800",
         "key_specs": "Core Ultra7/32GB/1TB/14寸2.8K/OLED/1.12kg超轻/军规认证",
         "brand": "联想", "category": "笔记本电脑",
         "description": "ThinkPad X1 Carbon旗舰商务本，1.12kg行业最轻，14寸2.8K OLED屏，军规耐用认证，商务安全功能齐全，全天续航，商务出行首选标杆。"},
        {"product_id": "jd_apple_macbook_pro_m3", "title": "苹果 MacBook Pro 14寸 M3 Pro芯片",
         "price": 14999.0, "original_price": 16999.0, "rating": 4.9, "sales": "月销3600",
         "key_specs": "M3 Pro芯片/18GB/512GB/14.2寸Liquid Retina XDR/18h续航/全能旗舰",
         "brand": "苹果", "category": "笔记本电脑",
         "description": "苹果MacBook Pro M3 Pro，专业级M3 Pro芯片，18GB内存流畅处理4K视频剪辑，14.2寸Liquid Retina XDR专业屏，18小时续航，专业创作旗舰。"},
        {"product_id": "jd_asus_rog_zephyrus", "title": "华硕 ROG幻14 2024 14寸游戏本",
         "price": 9999.0, "original_price": 11999.0, "rating": 4.8, "sales": "月销3200",
         "key_specs": "AMD Ryzen 9/RTX 4070/32GB/1TB/14寸2K 165Hz/1.5kg/ROG游戏本",
         "brand": "华硕", "category": "笔记本电脑",
         "description": "华硕ROG幻14 2024游戏本，Ryzen 9+RTX 4070顶级游戏配置，14寸2K 165Hz高刷屏，1.5kg轻量化机身，游戏本中最便携，游戏创作两用旗舰。"},
    ],
    "手机": [
        {"product_id": "jd_apple_iphone16pro", "title": "苹果 iPhone 16 Pro 256GB 黑色钛金属",
         "price": 7999.0, "original_price": 8499.0, "rating": 4.9, "sales": "月销2.1万",
         "key_specs": "A18 Pro芯片/6.3寸超视网膜XDR/4800万像素/钛金属边框/USB-C/256GB",
         "brand": "苹果", "category": "手机",
         "description": "iPhone 16 Pro搭载A18 Pro芯片，性能领先安卓旗舰，6.3寸超视网膜XDR全面屏，4800万像素三摄系统，钛金属轻量机身，支持Apple Intelligence，苹果生态用户首选。"},
        {"product_id": "jd_huawei_mate70pro", "title": "华为 Mate 70 Pro 512GB 雅丹黑",
         "price": 6999.0, "original_price": 7499.0, "rating": 4.9, "sales": "月销1.8万",
         "key_specs": "麒麟9010/6.8寸LTPO曲屏/5000万像素/卫星通信/HarmonyOS 5/512GB",
         "brand": "华为", "category": "手机",
         "description": "华为Mate 70 Pro搭载自研麒麟9010芯片，支持卫星通话全球通信无死角，6.8寸LTPO曲面屏，5000万像素徕卡影像，HarmonyOS 5流畅生态，国产旗舰高端之选。"},
        {"product_id": "jd_xiaomi_15ultra", "title": "小米 15 Ultra 512GB 白色",
         "price": 5999.0, "original_price": 6499.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "骁龙8 Elite/6.73寸2K+120Hz/5000万徕卡四摄/6000mAh/90W快充/512GB",
         "brand": "小米", "category": "手机",
         "description": "小米15 Ultra搭载骁龙8 Elite旗舰芯片，徕卡四摄系统主摄5000万，6000mAh超大电池，90W有线+50W无线快充，6.73寸2K+120Hz屏幕，拍照续航双旗舰。"},
        {"product_id": "jd_samsung_s25ultra", "title": "三星 Galaxy S25 Ultra 256GB 钛黑",
         "price": 9299.0, "original_price": 9999.0, "rating": 4.8, "sales": "月销8600",
         "key_specs": "骁龙8 Elite/6.9寸AMOLED/2亿像素/S Pen/Galaxy AI/256GB",
         "brand": "三星", "category": "手机",
         "description": "三星Galaxy S25 Ultra内置S Pen手写笔，骁龙8 Elite处理器，2亿像素主摄超高清拍摄，Galaxy AI智能功能，6.9寸大屏沉浸体验，Android顶级旗舰商务首选。"},
        {"product_id": "jd_oppo_find_x8pro", "title": "OPPO Find X8 Pro 256GB 星际黑",
         "price": 5999.0, "original_price": 6499.0, "rating": 4.8, "sales": "月销1.1万",
         "key_specs": "天玑9400/6.78寸2K+AMOLED/哈苏四摄/5910mAh/100W超闪/256GB",
         "brand": "OPPO", "category": "手机",
         "description": "OPPO Find X8 Pro搭载天玑9400旗舰芯片，哈苏专业相机系统，6.78寸2K+超感屏，5910mAh大电池，100W超闪充电速度极快，色彩出众影像旗舰之选。"},
        {"product_id": "jd_vivo_x200pro", "title": "vivo X200 Pro 256GB 玫瑰金",
         "price": 4999.0, "original_price": 5499.0, "rating": 4.8, "sales": "月销1.3万",
         "key_specs": "天玑9400/6.78寸AMOLED/5000万蔡司三摄/6000mAh/90W快充/256GB",
         "brand": "vivo", "category": "手机",
         "description": "vivo X200 Pro蔡司三摄系统，6.78寸AMOLED大屏，天玑9400旗舰性能，6000mAh电池搭配90W快充，拍照和续航兼顾的综合旗舰，女性用户颜值担当。"},
        {"product_id": "jd_redmi_note14pro", "title": "Redmi Note 14 Pro+ 256GB 深海蓝",
         "price": 1999.0, "original_price": 2299.0, "rating": 4.8, "sales": "月销3.2万",
         "key_specs": "天玑9200+/6.67寸2K+AMOLED/2亿像素/5000mAh/120W秒充/256GB",
         "brand": "Redmi", "category": "手机",
         "description": "Redmi Note 14 Pro+配备2亿像素超清主摄，天玑9200+高性能芯片，6.67寸2K+旗舰屏，5000mAh大电池120W秒充，2000元内最强影像旗舰，性价比天花板。"},
    ],
    "平板电脑": [
        {"product_id": "jd_apple_ipadpro13_m4", "title": "苹果 iPad Pro 13寸 M4 256GB WIFI",
         "price": 8999.0, "original_price": 9999.0, "rating": 4.9, "sales": "月销6800",
         "key_specs": "M4芯片/13寸Ultra Retina XDR/OLED全面屏/Apple Pencil Pro/256GB",
         "brand": "苹果", "category": "平板电脑",
         "description": "iPad Pro 13 M4搭载苹果最强M4芯片，13寸OLED Ultra Retina XDR屏幕色彩绚丽，支持Apple Pencil Pro，专业创作生产力工具，画图视频剪辑顶级体验。"},
        {"product_id": "jd_apple_ipadair_m2", "title": "苹果 iPad Air 11寸 M2 128GB WIFI",
         "price": 4799.0, "original_price": 5299.0, "rating": 4.9, "sales": "月销1.5万",
         "key_specs": "M2芯片/11寸Liquid Retina/Apple Pencil兼容/128GB/轻薄462g",
         "brand": "苹果", "category": "平板电脑",
         "description": "iPad Air 11 M2轻薄设计仅462g，M2芯片流畅运行所有App，11寸Liquid Retina屏色准，兼容Apple Pencil和妙控键盘，日常学习办公创作全场景。"},
        {"product_id": "jd_huawei_matepadpro13", "title": "华为 MatePad Pro 13.2寸 256GB WIFI",
         "price": 4999.0, "original_price": 5499.0, "rating": 4.8, "sales": "月销9200",
         "key_specs": "麒麟9000S/13.2寸2.8K OLED/HarmonyOS/华为手写笔/256GB/580g",
         "brand": "华为", "category": "平板电脑",
         "description": "华为MatePad Pro 13.2寸2.8K OLED屏显示效果细腻，麒麟9000S强劲性能，HarmonyOS多设备协同，华为手写笔精准书写，与华为手机无缝互联，国产生态最优解。"},
        {"product_id": "jd_xiaomi_pad7pro", "title": "小米 Pad 7 Pro 256GB WIFI",
         "price": 2799.0, "original_price": 3199.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "骁龙8s Gen3/11.2寸3K LCD/144Hz/10000mAh/33W/256GB/580g",
         "brand": "小米", "category": "平板电脑",
         "description": "小米Pad 7 Pro骁龙8s Gen3旗舰处理器，11.2寸3K 144Hz高刷屏，10000mAh大电池长续航，33W快充，2800元档性价比最强平板，学生党游戏党首选。"},
        {"product_id": "jd_samsung_tabs10", "title": "三星 Galaxy Tab S10+ 256GB WIFI",
         "price": 5999.0, "original_price": 6499.0, "rating": 4.8, "sales": "月销5600",
         "key_specs": "骁龙8 Gen3/12.4寸AMOLED/S Pen/DeX桌面模式/256GB/575g",
         "brand": "三星", "category": "平板电脑",
         "description": "三星Galaxy Tab S10+内置S Pen，12.4寸AMOLED大屏，DeX模式变身电脑，骁龙8 Gen3旗舰性能，Android平板中生产力体验最接近电脑的机型。"},
        {"product_id": "jd_oppo_pad3pro", "title": "OPPO Pad 3 Pro 12.1寸 256GB WIFI",
         "price": 3299.0, "original_price": 3799.0, "rating": 4.7, "sales": "月销8800",
         "key_specs": "天玑9300/12.1寸3K OLED/144Hz/9510mAh/67W/256GB/567g",
         "brand": "OPPO", "category": "平板电脑",
         "description": "OPPO Pad 3 Pro搭载天玑9300，12.1寸3K OLED屏色彩出众，144Hz刷新率流畅，9510mAh大电池，67W快充半小时充满一半，追剧游戏生产力全能平板。"},
    ],
    "智能手表": [
        {"product_id": "jd_apple_watch_s10", "title": "苹果 Apple Watch Series 10 GPS 46mm 星光色",
         "price": 2999.0, "original_price": 3199.0, "rating": 4.9, "sales": "月销1.8万",
         "key_specs": "S10芯片/46mm AMOLED/血氧心率睡眠/18h续航/WatchOS/防水50m",
         "brand": "苹果", "category": "智能手表",
         "description": "Apple Watch Series 10最轻薄Apple Watch，S10芯片性能强，全天血氧心率睡眠监测，18小时续航，watchOS生态完善，苹果手机用户健康管理首选。"},
        {"product_id": "jd_huawei_watch_gt5pro", "title": "华为 WATCH GT 5 Pro 46mm 黑色",
         "price": 2188.0, "original_price": 2488.0, "rating": 4.9, "sales": "月销2.3万",
         "key_specs": "自研芯片/46mm AMOLED/14天续航/血氧心率血糖/GPS/防水/HarmonyOS",
         "brand": "华为", "category": "智能手表",
         "description": "华为WATCH GT 5 Pro超长14天续航，自研芯片低功耗，血氧心率血糖全面健康监测，精准GPS户外导航，专业运动100+模式，颜值与功能兼备的旗舰智能手表。"},
        {"product_id": "jd_xiaomi_watch_s4", "title": "小米 Watch S4 47mm 黑色",
         "price": 1299.0, "original_price": 1499.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "骁龙W5/1.43寸AMOLED/7天续航/血氧心率/NFC/支付宝微信/GPS",
         "brand": "小米", "category": "智能手表",
         "description": "小米Watch S4骁龙W5处理器，1.43寸AMOLED大屏，7天超长续航，支持NFC刷地铁、支付宝微信Pay，全天血氧心率监测，1300元内功能最全的智能手表。"},
        {"product_id": "jd_samsung_galaxy_watch7", "title": "三星 Galaxy Watch 7 44mm 绿色",
         "price": 1799.0, "original_price": 1999.0, "rating": 4.8, "sales": "月销9800",
         "key_specs": "Exynos W1000/44mm AMOLED/3天续航/血糖监测/Galaxy AI/NFC",
         "brand": "三星", "category": "智能手表",
         "description": "三星Galaxy Watch 7搭载Galaxy AI智能功能，Exynos W1000快速处理器，血糖监测健康预警，与三星手机无缝配合，NFC支付，Android用户旗舰手表之选。"},
        {"product_id": "jd_garmin_fenix8", "title": "Garmin Fenix 8 47mm 黑色",
         "price": 5299.0, "original_price": 5999.0, "rating": 4.9, "sales": "月销4200",
         "key_specs": "47mm钛合金/AMOLED/16天续航/GPS+北斗/多运动/心率血氧/防水100m",
         "brand": "Garmin", "category": "智能手表",
         "description": "Garmin Fenix 8顶级户外运动手表，钛合金坚固外壳，16天超长续航，多星定位精准轨迹，100米防水游泳不怕，专业运动分析功能齐全，马拉松户外爱好者顶配。"},
        {"product_id": "jd_oppo_watch4pro_47mm", "title": "OPPO Watch 4 Pro 47mm 运动健康手表",
         "price": 1599.0, "original_price": 1999.0, "rating": 4.8, "sales": "月销1.2万",
         "key_specs": "47mm AMOLED/骁龙W5/4天续航/血氧心率血糖/NFC/双系统",
         "brand": "OPPO", "category": "智能手表",
         "description": "OPPO Watch 4 Pro搭载骁龙W5双系统，AMOLED高清屏，NFC刷地铁公交，全天血氧心率血糖监测，4天续航，与OPPO手机深度联动，安卓生态智能手表高性价比之选。"},
    ],
    "电动牙刷": [
        {"product_id": "jd_oralb_io9", "title": "欧乐B iO9 旗舰电动牙刷 白色",
         "price": 799.0, "original_price": 999.0, "rating": 4.8, "sales": "月销1.2万",
         "key_specs": "磁力驱动/7种模式/AI识别/2min定时/压力传感/2周续航",
         "brand": "欧乐B", "category": "电动牙刷",
         "description": "欧乐B iO9磁力驱动技术，去除99.9%牙菌斑，AI刷牙识别追踪，7种清洁模式，压力传感防刷伤牙龈，2分钟智能定时，两周续航省心，口腔护理旗舰之选。"},
        {"product_id": "jd_philips_sonicare9900", "title": "飞利浦 Sonicare 9900 钻石系列",
         "price": 1199.0, "original_price": 1499.0, "rating": 4.8, "sales": "月销8800",
         "key_specs": "声波震动/62000次/分/SenseIQ自适应/14天续航/3种强度/4模式",
         "brand": "飞利浦", "category": "电动牙刷",
         "description": "飞利浦Sonicare 9900钻石级声波震动，62000次/分超高频振动，SenseIQ智能自适应压力，每天调整刷牙计划，14天长续航，专业牙科级清洁体验。"},
        {"product_id": "jd_xiaomi_t501", "title": "小米 米家电动牙刷 T501 黑色",
         "price": 149.0, "original_price": 199.0, "rating": 4.8, "sales": "月销4.5万",
         "key_specs": "声波震动/31000次/分/4模式/25天续航/IPX7防水/米家APP",
         "brand": "小米", "category": "电动牙刷",
         "description": "小米米家T501声波电动牙刷，31000次/分高频震动，4种清洁模式，25天超长续航减少充电烦恼，IPX7防水放心使用，米家APP记录刷牙数据，百元内高性价比首选。"},
        {"product_id": "jd_usmile_p10pro", "title": "usmile P10 Pro 旗舰声波电动牙刷",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "声波震动/自适应清洁/30天续航/IPX8防水/蓝牙APP/3D传感",
         "brand": "usmile", "category": "电动牙刷",
         "description": "usmile P10 Pro颜值出众国产牙刷，3D传感自适应调节，30天超长续航，IPX8深度防水，蓝牙App记录口腔健康数据，多种刷头可选，年轻人颜值口腔护理首选。"},
        {"product_id": "jd_oralb_pro2", "title": "欧乐B Pro 2 电动牙刷 白色",
         "price": 199.0, "original_price": 269.0, "rating": 4.7, "sales": "月销3.8万",
         "key_specs": "3D清洁/3种模式/压力传感/2min定时/2周续航/入门款",
         "brand": "欧乐B", "category": "电动牙刷",
         "description": "欧乐B Pro 2入门级电动牙刷，3D清洁技术去除牙菌斑，压力传感器防止用力过猛，2分钟定时培养刷牙习惯，2周续航，欧乐B品质保障的性价比之选。"},
        {"product_id": "jd_sonicare_protectclean4", "title": "飞利浦 Sonicare ProtectClean 4300 声波牙刷",
         "price": 299.0, "original_price": 399.0, "rating": 4.7, "sales": "月销2.9万",
         "key_specs": "声波震动/31000次/分/3种模式/压力传感/14天续航/IPX7防水",
         "brand": "飞利浦", "category": "电动牙刷",
         "description": "飞利浦Sonicare ProtectClean 4300，声波震动技术31000次/分，3种清洁模式，内置压力传感防止刷伤牙龈，14天续航，IPX7防水，飞利浦入门声波牙刷高性价比选择。"},
    ],
    "剃须刀": [
        {"product_id": "jd_philips_9000prestige", "title": "飞利浦 9000 Prestige S9986 电动剃须刀",
         "price": 1299.0, "original_price": 1599.0, "rating": 4.9, "sales": "月销6800",
         "key_specs": "V轨追踪/三刀头自适应/60min续航/5分钟快充/湿干两用/LED屏",
         "brand": "飞利浦", "category": "剃须刀",
         "description": "飞利浦9000 Prestige旗舰剃须刀，V轨追踪技术贴合每个面部轮廓，三刀头自适应调节，60分钟续航，5分钟快充，湿剃干剃均适用，旗舰级舒适剃须体验。"},
        {"product_id": "jd_braun_series9pro", "title": "博朗 Series 9 Pro+ 9565cc 电动剃须刀",
         "price": 2199.0, "original_price": 2699.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "五刀头/ProLift提胡须/自动清洁站/60min续航/湿干两用/蓝牙",
         "brand": "博朗", "category": "剃须刀",
         "description": "博朗Series 9 Pro+五刀头设计，专利ProLift提胡须技术剃净顽固胡须，附带自动清洁充电站，湿剃干剃均适用，蓝牙连接App分析剃须习惯，德国品质顶级体验。"},
        {"product_id": "jd_panasonic_es_lv67", "title": "松下 ES-LV67 旋转式电动剃须刀",
         "price": 799.0, "original_price": 999.0, "rating": 4.8, "sales": "月销9800",
         "key_specs": "五刀头/多维弹性/全身水洗/45min续航/湿剃/送礼首选",
         "brand": "松下", "category": "剃须刀",
         "description": "松下ES-LV67五刀头多维弹性浮动，紧贴脸部轮廓，可全身水洗方便清洁，45分钟续航，湿剃干剃均可，外观精致适合送礼，日本品质可靠之选。"},
        {"product_id": "jd_xiaomi_mijia_s801", "title": "小米 米家电动剃须刀 S801 黑色",
         "price": 199.0, "original_price": 249.0, "rating": 4.7, "sales": "月销2.8万",
         "key_specs": "三刀头浮动/IPX7防水/60min续航/Type-C充电/干湿两用/入门款",
         "brand": "小米", "category": "剃须刀",
         "description": "小米米家S801三刀头浮动设计，IPX7防水可冲洗，60分钟续航，Type-C充电方便，干湿两用，操作简单，200元入门款剃须刀中最高性价比选择，新手必选。"},
        {"product_id": "jd_flyco_fs986", "title": "飞科 FS986 剃须刀 男士电动",
         "price": 129.0, "original_price": 169.0, "rating": 4.6, "sales": "月销5.6万",
         "key_specs": "三刀头/浮动贴面/IPX7/60min续航/旅行充电/国货高性价比",
         "brand": "飞科", "category": "剃须刀",
         "description": "飞科FS986三浮动刀头紧贴脸部，IPX7全身水洗，60分钟续航，旅行充电座方便携带，100元价位段国产剃须刀口碑之选，实惠耐用，上班族通勤首选。"},
        {"product_id": "jd_roamer_shaver_s5_pro", "title": "荣泰 S5 Pro 男士电动剃须刀 五刀头",
         "price": 349.0, "original_price": 449.0, "rating": 4.7, "sales": "月销1.6万",
         "key_specs": "五刀头/5D浮动/全身水洗/60min续航/USB充电/多档调节",
         "brand": "荣泰", "category": "剃须刀",
         "description": "荣泰S5 Pro五刀头5D浮动设计，紧贴面部轮廓360度刮净，全身水洗清洁方便，60分钟续航，USB充电，国产性价比男士剃须刀，200-400元档高口碑选择。"},
    ],
    "吹风机": [
        {"product_id": "jd_dyson_supersonic_hd15", "title": "戴森 Supersonic HD15 吹风机 黑铜色",
         "price": 2999.0, "original_price": 3299.0, "rating": 4.9, "sales": "月销1.1万",
         "key_specs": "数字马达/智能测温/4种风速/4种温度/负离子/折叠设计/磁吸配件",
         "brand": "戴森", "category": "吹风机",
         "description": "戴森Supersonic HD15专业吹风机，数字马达每分钟11万转强劲风速，智能测温防热损伤，4速4温精准控制，负离子减少毛躁，磁吸配件切换快，护发速干双全。"},
        {"product_id": "jd_laifen_swift_premium", "title": "徕芬 LAIFEN Swift Premium 吹风机",
         "price": 699.0, "original_price": 799.0, "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "10万转/110000RPM/快干/3档温控/负离子护发/600g轻量/低噪音",
         "brand": "徕芬", "category": "吹风机",
         "description": "徕芬Swift Premium高速吹风机，10万转电机强劲送风，发量大也能快速吹干，3档温控精准护发，负离子抗毛躁，600g轻量减少手臂疲劳，戴森平替高性价比之选。"},
        {"product_id": "jd_philips_bha530", "title": "飞利浦 BHA530 ProCare 吹风机",
         "price": 499.0, "original_price": 649.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "1800W/热敏技术/2200W冷风/离子护理/2档速/3档温/折叠手柄",
         "brand": "飞利浦", "category": "吹风机",
         "description": "飞利浦BHA530 ProCare专利热敏技术实时监测温度，每秒调节防过热，1800W大功率快速吹干，离子护理减少毛糙，折叠手柄便于收纳旅行，护发吹干两不误。"},
        {"product_id": "jd_panasonic_eh_na0j", "title": "松下 EH-NA0J 纳米水离子吹风机",
         "price": 599.0, "original_price": 749.0, "rating": 4.8, "sales": "月销1.4万",
         "key_specs": "纳米水离子/负离子/1800W/4档温度/3档风速/护发修护/日本品质",
         "brand": "松下", "category": "吹风机",
         "description": "松下EH-NA0J纳米水离子技术深层护发，微细水分子渗入发芯修护损伤，负离子同步去静电，1800W快速出风，4档温度精细控制，高频染烫发质受损者救星。"},
        {"product_id": "jd_xiaomi_mijia_h800", "title": "小米 米家高速吹风机 H800",
         "price": 399.0, "original_price": 499.0, "rating": 4.7, "sales": "月销3.6万",
         "key_specs": "8万转高速/1600W/3档温控/负离子/低噪音/米家APP/轻量580g",
         "brand": "小米", "category": "吹风机",
         "description": "小米米家H800高速吹风机，8万转大风量快速吹干头发，负离子护发减少毛糙，3档温控灵活切换，米家App联动记录，580g轻盈好握，400元内高速吹风机首选。"},
        {"product_id": "jd_remington_d3190_pro", "title": "雷明顿 D3190 专业负离子吹风机 2300W",
         "price": 259.0, "original_price": 329.0, "rating": 4.7, "sales": "月销2.2万",
         "key_specs": "2300W大功率/负离子护发/陶瓷技术/3档风速/2档温度/折叠",
         "brand": "雷明顿", "category": "吹风机",
         "description": "雷明顿D3190专业级吹风机，2300W大功率快速干燥，陶瓷技术均匀加热减少热损伤，负离子科技抑制毛躁保持光滑，折叠设计旅行收纳方便，高性价比专业吹风机。"},
    ],
    "微波炉": [
        {"product_id": "jd_galanz_g80f23cn3lq_r2", "title": "格兰仕 G80F23CN3LQ-R2 微波炉 23L",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "23L/900W/机械旋钮/11档功率/内腔平板/不锈钢内腔/简洁操作",
         "brand": "格兰仕", "category": "微波炉",
         "description": "格兰仕G80F23CN3LQ-R2平板微波炉，内腔平底清洁方便，不锈钢内腔耐用卫生，机械旋钮简洁操作，23L大容量适合家用，格兰仕主流热销款，性价比高稳定可靠。"},
        {"product_id": "jd_midea_mg23cn4_aa5", "title": "美的 MG23CN4-AA5 微蒸烤一体机",
         "price": 699.0, "original_price": 899.0, "rating": 4.8, "sales": "月销1.4万",
         "key_specs": "23L/微波+蒸+烤三合一/APP智控/100+菜单/内腔平板/触控面板",
         "brand": "美的", "category": "微波炉",
         "description": "美的MG23CN4微蒸烤三合一，一台搞定微波加热、蒸制、烤制，100+智能菜单一键操作，APP远程控制，触控面板易清洁，厨房三合一节省台面空间神器。"},
        {"product_id": "jd_panasonic_nn_gf574m", "title": "松下 NN-GF574M 变频微波炉 27L",
         "price": 899.0, "original_price": 1099.0, "rating": 4.8, "sales": "月销8900",
         "key_specs": "27L/变频静音/烧烤功能/自动除臭/1000W/5档功率/日本品质",
         "brand": "松下", "category": "微波炉",
         "description": "松下NN-GF574M变频微波炉，变频技术加热均匀不夹生，运行噪音低，27L大容量适合多人家庭，自动除臭保持内腔清新，烧烤功能多用途，日本松下品质保障。"},
        {"product_id": "jd_galanz_c1tt23n2pvb", "title": "格兰仕 变频微波炉 23L 触控",
         "price": 299.0, "original_price": 399.0, "rating": 4.7, "sales": "月销3.5万",
         "key_specs": "23L/变频/触控面板/智能解冻/8档功率/平板腔体/易清洁",
         "brand": "格兰仕", "category": "微波炉",
         "description": "格兰仕变频微波炉，变频加热更均匀，触控面板好操作好清洁，智能解冻不夹生，23L容量家用够用，平板腔体转盘清洗方便，300元高性价比微波炉首选。"},
        {"product_id": "jd_midea_mw_25l_smart", "title": "美的 YP25Easy 25L 智能平板微波炉",
         "price": 499.0, "original_price": 649.0, "rating": 4.8, "sales": "月销1.1万",
         "key_specs": "25L/平板腔体/APP智控/语音控制/智能菜谱80+/触控屏",
         "brand": "美的", "category": "微波炉",
         "description": "美的YP25Easy智能微波炉，APP远程控制语音操控，80+智能菜谱一键操作，25L大容量家庭使用，平板腔体易清洁，触控屏简洁美观，智能厨房必备升级款。"},
        {"product_id": "jd_samsung_ms23k3515aw", "title": "三星 MS23K3515AW 23L 纯平按键微波炉",
         "price": 599.0, "original_price": 749.0, "rating": 4.7, "sales": "月销7800",
         "key_specs": "23L/800W/纯平玻璃面板/6段功率/自动除菌/韩国品牌",
         "brand": "三星", "category": "微波炉",
         "description": "三星MS23K3515AW纯平玻璃面板微波炉，外观简约时尚，6段功率精确控制，自动除菌功能保持内腔洁净，23L容量家用足够，三星家电品质，厨房颜值担当。"},
    ],
    "电饭煲": [
        {"product_id": "jd_zojirushi_np_znq18", "title": "象印 NP-ZNQ18 IH电磁加热电饭煲 1.8L",
         "price": 1299.0, "original_price": 1599.0, "rating": 4.9, "sales": "月销8800",
         "key_specs": "IH电磁加热/1.8L/多段压力/银离子内胆/SPFC整流功能/日本品质",
         "brand": "象印", "category": "电饭煲",
         "description": "象印NP-ZNQ18旗舰IH电饭煲，全面高温均匀加热，多段压力控制米饭甜度，银离子内胆抑菌保鲜，SPFC整流提升火力，煮出松软香糯大米饭，日本进口品质保证。"},
        {"product_id": "jd_tiger_jpf_g550", "title": "虎牌 JPF-G550 IH压力电饭煲 0.54L",
         "price": 799.0, "original_price": 999.0, "rating": 4.8, "sales": "月销1.2万",
         "key_specs": "IH+压力/0.54L迷你/多功能定时/蒸煮炖煮/小巧适合1-2人/日本品质",
         "brand": "虎牌", "category": "电饭煲",
         "description": "虎牌JPF-G550迷你IH压力电饭煲，0.54L超小容量适合单人或两人家庭，IH加压力双重加热煮饭香糯，多功能蒸煮炖煮一机搞定，小巧节省台面，日本品质生活入门。"},
        {"product_id": "jd_midea_mb_fc4060", "title": "美的 MB-FC4060 IH变频电饭煲 4L",
         "price": 599.0, "original_price": 799.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "IH变频/4L/精铸厚釜内胆/十六段火力/APP智控/3-5人家庭适用",
         "brand": "美的", "category": "电饭煲",
         "description": "美的MB-FC4060 IH变频电饭煲，精铸厚釜内胆均匀导热，十六段火力精控，APP远程预约定时，4L容量适合3-5人家庭，国产IH电饭煲性价比旗舰，煮出香软好饭。"},
        {"product_id": "jd_supor_sfb40hc828", "title": "苏泊尔 SFB40HC828 电饭煲 4L 智能",
         "price": 299.0, "original_price": 399.0, "rating": 4.7, "sales": "月销3.2万",
         "key_specs": "4L/智能控温/球形内胆/8段火力/蒸煮多功能/触控/3-5人家庭",
         "brand": "苏泊尔", "category": "电饭煲",
         "description": "苏泊尔SFB40HC828球形内胆设计均匀受热，智能温控保持最佳口感，8段火力可调，蒸煮汤粥多功能，触控面板简洁易用，300元实惠电饭煲满足日常煮饭需求。"},
        {"product_id": "jd_jiuyang_f40fd60", "title": "九阳 F40FD60 4L 破壁电饭煲",
         "price": 399.0, "original_price": 499.0, "rating": 4.7, "sales": "月销2.4万",
         "key_specs": "4L/米汤分离/三维加热/超声波煮饭/APP智控/蒸煮炖/3-4人",
         "brand": "九阳", "category": "电饭煲",
         "description": "九阳F40FD60米汤分离电饭煲，超声波技术使米粒充分膨胀，三维立体加热均匀，APP智能控制，蒸煮炖多种功能，低糖饭模式适合血糖管理人群，健康饮食好帮手。"},
        {"product_id": "jd_panasonic_sr_hb184_ih", "title": "松下 SR-HB184 5L IH电磁加热电饭煲",
         "price": 899.0, "original_price": 1099.0, "rating": 4.8, "sales": "月销6800",
         "key_specs": "IH电磁加热/5L/微压力/双层厚釜/13段火力/全网版/3-6人家庭",
         "brand": "松下", "category": "电饭煲",
         "description": "松下SR-HB184 IH电磁加热电饭煲，双层厚釜内胆导热均匀，微压力模式让米饭更软糯鲜甜，13段火力精控，5L大容量适合3-6人家庭，松下日本品质，煮饭体验升级。"},
    ],
    "按摩椅": [
        {"product_id": "jd_aojiahua_a900pro", "title": "奥佳华 A900 Pro 全身按摩椅 太空舱",
         "price": 9999.0, "original_price": 12999.0, "rating": 4.9, "sales": "月销2800",
         "key_specs": "L形导轨/零重力/AI按摩/4D机械手/全身气囊/热敷/足底滚轮",
         "brand": "奥佳华", "category": "按摩椅",
         "description": "奥佳华A900 Pro太空舱按摩椅，L形导轨从颈部延伸至腿部，零重力姿态解压，4D机械手仿真穴位按摩，全身气囊包裹，热敷舒筋活络，足底滚轮深度放松，全家共享。"},
        {"product_id": "jd_rongtai_rt7870s", "title": "荣泰 RT-7870S 太空舱按摩椅",
         "price": 6999.0, "original_price": 8999.0, "rating": 4.8, "sales": "月销3600",
         "key_specs": "SL形导轨/零重力/3D机械手/AI扫描体型/热敷/负离子/语音控制",
         "brand": "荣泰", "category": "按摩椅",
         "description": "荣泰RT-7870S SL形超长导轨，AI智能体型扫描定制按摩方案，3D机械手立体按摩，零重力太空舱体位减脊柱压力，热敷促进血液循环，语音控制无需起身操作。"},
        {"product_id": "jd_westinghouse_wm600", "title": "西屋 WM-600 家用按摩椅 入门款",
         "price": 3999.0, "original_price": 4999.0, "rating": 4.7, "sales": "月销4800",
         "key_specs": "L形导轨/零重力/2D机械手/全身气囊/热敷/足底按摩/经典款",
         "brand": "西屋", "category": "按摩椅",
         "description": "西屋WM-600家用入门按摩椅，L形导轨覆盖背部腰部腿部，零重力减压体位，全身气囊按摩，热敷背部缓解腰酸，足底滚轮刺激穴位，4000元入门款高性价比。"},
        {"product_id": "jd_panasonic_ep_ma105", "title": "松下 EP-MA105 按摩椅 棕色",
         "price": 12999.0, "original_price": 15999.0, "rating": 4.9, "sales": "月销1600",
         "key_specs": "S形导轨/3D机械手/指压按摩/气囊/加热/自动识别肩位/日本设计",
         "brand": "松下", "category": "按摩椅",
         "description": "松下EP-MA105指压按摩专家，S形导轨贴合脊椎曲线，3D机械手深度指压，自动识别肩部位置，气囊全身包裹，加热功能舒缓肌肉，日本松下设计品质卓越。"},
        {"product_id": "jd_trumedic_mc1500_chair", "title": "好医生 MC-1500 全身按摩椅 零重力",
         "price": 5999.0, "original_price": 7499.0, "rating": 4.8, "sales": "月销2100",
         "key_specs": "L形导轨/零重力/3D机械手/气囊按摩/热敷/足底按摩/家用实惠款",
         "brand": "好医生", "category": "按摩椅",
         "description": "好医生MC-1500全身按摩椅，L形导轨延伸至臀腿部，零重力减重感舒适，3D机械手多穴位揉捏，全身气囊包裹，热敷背部腰部，足底滚轮刺激穴位，6000元段高性价比按摩椅。"},
        {"product_id": "jd_irest_sl830_zero_g", "title": "奥克斯 SL-830 太空舱按摩椅 中端款",
         "price": 4999.0, "original_price": 6499.0, "rating": 4.7, "sales": "月销3200",
         "key_specs": "SL形导轨/零重力/2D机械手/全身气囊/热敷/足底/多种模式",
         "brand": "奥克斯", "category": "按摩椅",
         "description": "奥克斯SL-830按摩椅，SL形超长导轨覆盖颈部到腿部，零重力倾斜减轻脊椎压力，全身气囊配合2D机械手多维按摩，热敷配合按摩舒缓，5000元段家用入门太空舱之选。"},
    ],
    "空调": [
        {"product_id": "jd_gree_kfr_35gw_nhwb3", "title": "格力 KFR-35GW/NhWb3 大1.5匹变频空调",
         "price": 2499.0, "original_price": 2999.0, "rating": 4.8, "sales": "月销2.8万",
         "key_specs": "1.5匹/变频/WIFI智控/一级能效/快速制冷/低噪音32dB/自清洁",
         "brand": "格力", "category": "空调",
         "description": "格力大1.5匹变频空调，一级能效节能省电，15分钟快速制冷，WIFI智能控制，低噪音32dB不扰睡，自清洁功能防细菌，15-23㎡卧室客厅均适用，国内空调销量冠军品牌。"},
        {"product_id": "jd_midea_kfr_35gw_bvdn8", "title": "美的 KFR-35GW/BVDN8 1.5匹 酷省电",
         "price": 2199.0, "original_price": 2699.0, "rating": 4.8, "sales": "月销3.2万",
         "key_specs": "1.5匹/一级变频/35℃舒适制冷/无风感送风/WIFI/自清洁/低噪音",
         "brand": "美的", "category": "空调",
         "description": "美的酷省电1.5匹变频空调，专利无风感技术避免直吹不舒适，一级能效节省电费，35℃高温也能快速制冷，WIFI远程控制回家前就凉，自清洁健康用机。"},
        {"product_id": "jd_aux_kfr_35gw_bpc1", "title": "奥克斯 KFR-35GW/BPC1 1.5匹 变频",
         "price": 1599.0, "original_price": 1999.0, "rating": 4.7, "sales": "月销4.1万",
         "key_specs": "1.5匹/变频/二级能效/WIFI智控/快速制冷/低噪音/入门实惠",
         "brand": "奥克斯", "category": "空调",
         "description": "奥克斯1.5匹变频空调，二级能效性价比高，快速制冷制热，WIFI手机控制，低噪音不影响睡眠，1600元以内价位最热销空调，租房党购房党装修预算有限的首选。"},
        {"product_id": "jd_haier_kfr_35gw_08eca82", "title": "海尔 KFR-35GW/08ECA82 1.5匹 自清洁",
         "price": 2299.0, "original_price": 2699.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "1.5匹/一级变频/自清洁/WIFI智控/净化除菌/低噪31dB/12年免清洗",
         "brand": "海尔", "category": "空调",
         "description": "海尔1.5匹变频空调，首创自清洁技术免拆洗，12年免维护，净化除菌空气更洁净，一级能效节电，WIFI智控，31dB超低噪音好睡眠，家有孩子老人的健康首选。"},
        {"product_id": "jd_daikin_ftxs335nc", "title": "大金 FTXS335NC 1.5匹 变频空调",
         "price": 4599.0, "original_price": 5199.0, "rating": 4.9, "sales": "月销6800",
         "key_specs": "1.5匹/双重净化/变频/低噪音/闪蒸技术/湿度智控/日本品质",
         "brand": "大金", "category": "空调",
         "description": "大金FTXS335NC日本精工品质，双重净化过滤PM2.5，闪蒸技术极速制冷，智能湿度控制保持舒适，变频压缩机超低噪音，日本品牌空调代名词，高品质家庭装修首选。"},
        {"product_id": "jd_midea_kfr_35_1p5_wifiplus", "title": "美的 KFR-35GW 1.5匹 风尊 变频空调",
         "price": 2599.0, "original_price": 3099.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "1.5匹/一级变频/智能除菌/自清洁/无风感/WIFI/超省电/30dB低噪",
         "brand": "美的", "category": "空调",
         "description": "美的风尊系列1.5匹变频空调，独特无风感技术温度均衡不直吹，超静音30dB好睡眠，智能除菌净化空气，一键自清洁保持机器洁净，一级能效超省电，居家健康首选。"},
    ],
    "书桌": [
        {"product_id": "jd_yimuhe_zdl1820", "title": "宜木禾 电动升降桌 1.8m 白色",
         "price": 1599.0, "original_price": 1999.0, "rating": 4.8, "sales": "月销8800",
         "key_specs": "1800×700mm/电动升降60-125cm/双电机/记忆高度/防碰撞/承重100kg",
         "brand": "宜木禾", "category": "书桌",
         "description": "宜木禾电动升降桌，站立坐姿自由切换保护腰椎，1.8m宽大桌面放双显示器，双电机稳定升降，4个高度记忆一键切换，防碰撞安全，居家办公健康利器。"},
        {"product_id": "jd_ikea_lack_desk", "title": "宜家 MICKE 书桌 白色 105×50cm",
         "price": 399.0, "original_price": 499.0, "rating": 4.7, "sales": "月销1.2万",
         "key_specs": "105×50×75cm/白色/带线管孔/小巧适合小空间/层板承重/抽屉",
         "brand": "宜家", "category": "书桌",
         "description": "宜家MICKE书桌简约设计，105cm紧凑尺寸适合小户型，带线管孔整理桌面线路，内置抽屉收纳小物件，白色清新百搭，学生宿舍小卧室桌面空间优化首选。"},
        {"product_id": "jd_songbao_l_desk", "title": "松宝 L形转角书桌 140+100cm 白色",
         "price": 799.0, "original_price": 999.0, "rating": 4.7, "sales": "月销9600",
         "key_specs": "L形转角/140+100cm/充足桌面/带置物架/线孔设计/多色可选",
         "brand": "松宝", "category": "书桌",
         "description": "松宝L形转角书桌充分利用墙角空间，超大桌面同时摆主机显示器还有余量，内置置物架收纳书籍，线孔设计整洁美观，游戏主播程序员居家办公必备大桌。"},
        {"product_id": "jd_flexispot_e7", "title": "乐歌 E7 Pro 电动升降桌 160×80cm",
         "price": 2499.0, "original_price": 2999.0, "rating": 4.9, "sales": "月销5600",
         "key_specs": "160×80cm/双电机/58-123cm升降/承重125kg/4记忆高度/碰撞保护",
         "brand": "乐歌", "category": "书桌",
         "description": "乐歌E7 Pro专业电动升降桌，双电机承重125kg稳固无晃动，58-123cm升降范围适合各身高，4个高度记忆精准复位，碰撞保护安全使用，久坐党护腰神器。"},
        {"product_id": "jd_student_study_desk", "title": "林氏木业 儿童学习桌 升降书桌 120cm",
         "price": 899.0, "original_price": 1199.0, "rating": 4.8, "sales": "月销1.1万",
         "key_specs": "120cm/手动升降/倾斜桌面/护眼/书架一体/大储物/3-15岁",
         "brand": "林氏木业", "category": "书桌",
         "description": "林氏木业儿童升降学习桌，高度随孩子成长调节，倾斜桌面减轻颈部压力，护眼书写，书架一体收纳书本文具，120cm大桌面够放课本作业，3-15岁陪伴成长。"},
        {"product_id": "jd_tangmu_oak_desk_140", "title": "棠木 北欧实木书桌 白橡木 140×60cm",
         "price": 1299.0, "original_price": 1699.0, "rating": 4.8, "sales": "月销4500",
         "key_specs": "白橡木实木/140×60cm/带储物抽屉/线孔设计/极简风格/承重80kg",
         "brand": "棠木", "category": "书桌",
         "description": "棠木白橡木实木书桌，天然木纹质感温润，140cm宽大桌面放显示器键盘还有余地，带储物抽屉收纳杂物，线孔设计整洁走线，北欧极简风格适合现代家居，实木家具首选。"},
    ],
    "净水器": [
        {"product_id": "jd_aosmith_ar600l", "title": "A.O.史密斯 AR600-L 反渗透净水器 600G",
         "price": 2999.0, "original_price": 3599.0, "rating": 4.9, "sales": "月销1.1万",
         "key_specs": "RO反渗透/600G流量/净水率75%/TDS检测/5年长效滤芯/不用桶",
         "brand": "A.O.史密斯", "category": "净水器",
         "description": "A.O.史密斯AR600-L反渗透净水器，600G大流量即饮不等待，无桶直饮设计节省空间，TDS实时检测水质，滤芯5年超长寿命，过滤重金属细菌病毒，全家饮水健康保障。"},
        {"product_id": "jd_xiaomi_mr632_a1", "title": "小米 净水器 1600G Pro 厨下式",
         "price": 1499.0, "original_price": 1799.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "RO反渗透/1600G超大流量/75%节水/5年滤芯/TDS实时检测/米家APP",
         "brand": "小米", "category": "净水器",
         "description": "小米净水器1600G超大流量，出水速度快不用等，75%高节水率环保，5年滤芯更换频率低节省费用，TDS检测水质可视，米家App监控滤芯寿命，高性价比净水器首选。"},
        {"product_id": "jd_philips_aut2015", "title": "飞利浦 AUT2015 台上净水器",
         "price": 799.0, "original_price": 999.0, "rating": 4.7, "sales": "月销1.4万",
         "key_specs": "超滤/台上式/3级过滤/99.99%滤菌/无需电源/保留矿物质/即装即用",
         "brand": "飞利浦", "category": "净水器",
         "description": "飞利浦AUT2015台上超滤净水器，无需打孔安装即装即用，无需电源省心，3级过滤去除99.99%细菌，保留水中有益矿物质，租房一族无需改造的净水首选。"},
        {"product_id": "jd_qinyuan_uf_kc2011", "title": "沁园 QU-UF-KC2011 厨下净水器",
         "price": 599.0, "original_price": 799.0, "rating": 4.7, "sales": "月销1.8万",
         "key_specs": "超滤/厨下式/5级过滤/不需电/直饮/滤芯12个月更换/实惠耐用",
         "brand": "沁园", "category": "净水器",
         "description": "沁园QU-UF-KC2011超滤净水器，5级深度过滤，去除泥沙氯气细菌，不需电直饮，滤芯12个月更换成本低，厨下安装整洁，600元以内高性价比厨下净水器之选。"},
        {"product_id": "jd_midea_mc1688_ro", "title": "美的 MC1688-4 家用反渗透净水器 400G",
         "price": 1699.0, "original_price": 2099.0, "rating": 4.8, "sales": "月销1.3万",
         "key_specs": "RO反渗透/400G流量/4重过滤/TDS检测/无桶直饮/美的品牌",
         "brand": "美的", "category": "净水器",
         "description": "美的MC1688-4反渗透净水器，400G流量出水快速，4重过滤去除重金属农药细菌，无桶直饮节省空间，TDS水质显示实时监控，美的国民品牌品质可靠，家用净水性价比首选。"},
        {"product_id": "jd_haier_hpu8841b_ro", "title": "海尔 HPU8841B 反渗透净水器 800G",
         "price": 2199.0, "original_price": 2699.0, "rating": 4.8, "sales": "月销9200",
         "key_specs": "RO反渗透/800G大流量/净水率70%/5年超长滤芯/APP监测/厨下安装",
         "brand": "海尔", "category": "净水器",
         "description": "海尔HPU8841B反渗透净水器，800G超大流量即开即饮，净水率70%高效节水，5年超长滤芯更换频率低，APP远程监测滤芯寿命，厨下安装不占台面，海尔品质家用直饮水首选。"},
    ],
    "背包": [
        {"product_id": "jd_samsonite_pro_dlx6", "title": "新秀丽 PRO-DLX 6 双肩背包 15.6寸 黑色",
         "price": 1299.0, "original_price": 1699.0, "rating": 4.8, "sales": "月销6800",
         "key_specs": "15.6寸笔记本/TSA锁/减压肩带/防水拉链/USB充电口/26L",
         "brand": "新秀丽", "category": "背包",
         "description": "新秀丽PRO-DLX 6商务双肩包，可放15.6寸笔记本，TSA认证密码锁安全过安检，减压肩带背久不累，防水拉链防突然降雨，USB充电口随时给手机充电，商旅必备。"},
        {"product_id": "jd_northface_vault", "title": "北面 VAULT 经典双肩包 黑色 27L",
         "price": 499.0, "original_price": 599.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "27L/15寸笔记本仓/多隔层/耐磨面料/人体工学背系统/学生通勤",
         "brand": "北面", "category": "背包",
         "description": "北面Vault经典双肩包，27L大容量一包走天下，独立笔记本隔层，多口袋分区整理，人体工学背系统减轻重量压力，耐磨面料经久耐用，学生上课通勤户外均适用。"},
        {"product_id": "jd_xiaomi_backpack_40l", "title": "小米 多功能双肩包 大容量 40L",
         "price": 199.0, "original_price": 269.0, "rating": 4.7, "sales": "月销3.2万",
         "key_specs": "40L大容量/USB充电/防水/15.6寸笔电仓/旅行通勤两用/轻量720g",
         "brand": "小米", "category": "背包",
         "description": "小米40L大容量双肩包，旅行装换洗衣物绰绰有余，USB外置充电口方便，15.6寸笔记本独立仓，防水面料应对突发天气，720g轻量不增加负担，200元高性价比旅行通勤包。"},
        {"product_id": "jd_decathlon_forclaz50", "title": "迪卡侬 FORCLAZ 50L 登山背包",
         "price": 499.0, "original_price": 599.0, "rating": 4.7, "sales": "月销9800",
         "key_specs": "50L/背负系统/防雨罩/侧取水袋/胸腰带/登山徒步专用/防泼水",
         "brand": "迪卡侬", "category": "背包",
         "description": "迪卡侬FORCLAZ 50L专业登山背包，人体工学背负系统分散负重，附带防雨罩防突发大雨，侧取水袋喝水无需停下，胸腰带固定重心，50L容量满足3-5天徒步需求。"},
        {"product_id": "jd_lv_journey_pm", "title": "路易威登 JOURNEY PM 男士背包 黑色",
         "price": 15800.0, "original_price": 17500.0, "rating": 4.9, "sales": "月销800",
         "key_specs": "Monogram Eclipse/全皮内衬/笔记本仓/金属扣件/正品保障",
         "brand": "路易威登", "category": "背包",
         "description": "路易威登JOURNEY PM经典Monogram Eclipse帆布，金属扣件精致耐用，全皮内衬高端质感，独立笔记本隔层商务实用，奢侈品级双肩包，商务精英身份象征，送礼品鉴之选。"},
        {"product_id": "jd_osprey_daylite_plus", "title": "Osprey Daylite Plus 日常背包 20L 黑色",
         "price": 559.0, "original_price": 699.0, "rating": 4.8, "sales": "月销7600",
         "key_specs": "20L/AirSpeed背负/15寸笔记本仓/防泼水/轻量520g/可挂接大包",
         "brand": "Osprey", "category": "背包",
         "description": "Osprey Daylite Plus轻量日用背包，AirSpeed背负系统背部透气，20L容量日常通勤足够，15寸笔记本独立仓，防泼水面料，仅520g超轻量，可扣接Osprey大背包使用，户外旅行两用。"},
    ],
    "护肤品": [
    ],
    "护肤品": [
        {"product_id": "jd_sk2_fte", "title": "SK-II 神仙水 护肤精华液 230ml",
         "price": 1380.0, "original_price": 1600.0, "rating": 4.9, "sales": "月销1.2万",
         "key_specs": "230ml/PITERA酵母精华/提亮肤色/收缩毛孔/保湿/28天见效",
         "brand": "SK-II", "category": "护肤品",
         "description": "SK-II神仙水核心成分PITERA酵母精华，持续使用28天肌肤更透亮，毛孔明显细致，保湿持久，经典爽肤水中的旗舰，送礼自用均是高端护肤首选。"},
        {"product_id": "jd_lamer_creme", "title": "海蓝之谜 经典面霜 30ml",
         "price": 2150.0, "original_price": 2350.0, "rating": 4.9, "sales": "月销4800",
         "key_specs": "30ml/奇迹精华/深层修复/抗衰老/敏感肌可用/大牌面霜",
         "brand": "海蓝之谜", "category": "护肤品",
         "description": "海蓝之谜经典面霜含独家奇迹精华成分，深层修复受损肌肤屏障，抗老保湿双效，敏感肌友好，奢侈护肤品代名词，给肌肤最高级的呵护。"},
        {"product_id": "jd_estee_dw_serum", "title": "雅诗兰黛 第七代小棕瓶精华 50ml",
         "price": 780.0, "original_price": 980.0, "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "50ml/HDRA水解酵母/抗老/提亮/修复/晚间使用/经典精华",
         "brand": "雅诗兰黛", "category": "护肤品",
         "description": "雅诗兰黛小棕瓶第七代精华，HDRA水解酵母核心成分，晚间修复加速肌肤新陈代谢，抗老提亮双效，50ml大容量高性价比，30岁以上抗老护肤必入经典。"},
        {"product_id": "jd_lancome_genifique", "title": "兰蔻 小黑瓶精华肌底液 50ml",
         "price": 850.0, "original_price": 1050.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "50ml/益生菌发酵精粹/提亮/修复/水润/全肤质/经典精华",
         "brand": "兰蔻", "category": "护肤品",
         "description": "兰蔻小黑瓶精华含益生菌发酵精粹，强化肌肤屏障，7天肌肤更透亮有光泽，全肤质适用，质地轻薄吸收快，与面霜叠加效果翻倍，全球销量精华经典。"},
        {"product_id": "jd_winona_repair_cream", "title": "薇诺娜 特护霜 清爽型 50g",
         "price": 168.0, "original_price": 218.0, "rating": 4.8, "sales": "月销3.6万",
         "key_specs": "50g/马齿苋提取物/舒缓修护/敏感肌专用/无香精无酒精/国货之选",
         "brand": "薇诺娜", "category": "护肤品",
         "description": "薇诺娜特护霜专为敏感肌设计，马齿苋提取物舒缓泛红和刺激，修护受损皮肤屏障，无香精无酒精无防腐剂，哺乳期可用，皮肤科推荐敏感肌护肤国货首选。"},
        {"product_id": "jd_proya_black_crystal", "title": "珀莱雅 黑晶瓶精华液 30ml 淡纹抗老",
         "price": 299.0, "original_price": 399.0, "rating": 4.8, "sales": "月销4.2万",
         "key_specs": "30ml/A醇+六胜肽/抗老淡纹/烟酰胺提亮/夜间使用/国货精华",
         "brand": "珀莱雅", "category": "护肤品",
         "description": "珀莱雅黑晶瓶含A醇和六胜肽双重抗老成分，淡化细纹法令纹，烟酰胺提亮肤色，夜间密集修护，300元内国货抗老精华天花板，成分党和平价抗老必入。"},
    ],
    "洗发水": [
        {"product_id": "jd_lux_shampoo_damage", "title": "力士 乳钻护发洗发水 750ml 修护损伤",
         "price": 49.9, "original_price": 69.0, "rating": 4.7, "sales": "月销5.8万",
         "key_specs": "750ml/氨基酸/修护受损/丰盈柔顺/适合烫染发/家庭装",
         "brand": "力士", "category": "洗发水",
         "description": "力士乳钻护发洗发水氨基酸配方，修护烫染受损毛鳞片，洗后头发柔顺不打结，750ml大容量实惠，平价日常洗发好选择，适合经常烫染的发质。"},
        {"product_id": "jd_pantene_shampoo_smooth", "title": "潘婷 氨基酸洗发水 750ml 顺滑",
         "price": 59.9, "original_price": 79.0, "rating": 4.7, "sales": "月销4.2万",
         "key_specs": "750ml/氨基酸/顺滑/防断发/活性修护/洗护合一",
         "brand": "潘婷", "category": "洗发水",
         "description": "潘婷氨基酸洗发水，活性修护复方修复受损发丝，洗后顺滑不缠绕，减少断发，750ml家庭实惠装，经典品牌日常洗发信赖之选。"},
        {"product_id": "jd_alpecin_c1", "title": "阿派欣 C1 咖啡因洗发水 250ml 防脱发",
         "price": 109.0, "original_price": 139.0, "rating": 4.7, "sales": "月销1.8万",
         "key_specs": "250ml/咖啡因/防脱生发/刺激毛囊/男士专用/德国进口",
         "brand": "阿派欣", "category": "洗发水",
         "description": "阿派欣C1咖啡因洗发水，专利咖啡因复方直达毛囊，刺激毛发生长抑制脱发，德国进口品质，脱发男士专用，坚持使用显著改善发际线，防脱洗发水热销款。"},
        {"product_id": "jd_freeplus_shampoo", "title": "芙丽芳丝 净润洗发露 300ml 氨基酸",
         "price": 98.0, "original_price": 129.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "300ml/氨基酸表活/温和无硅油/敏感头皮/日本品质/无香",
         "brand": "芙丽芳丝", "category": "洗发水",
         "description": "芙丽芳丝氨基酸洗发水，pH弱酸性接近头皮，温和不刺激，无硅油不堵毛囊，适合敏感头皮和掉发困扰人群，日本品质，洗完头皮清爽不紧绷。"},
        {"product_id": "jd_rejoice_shampoo_800", "title": "飘柔 2合1洗护洗发水 800ml 顺滑",
         "price": 29.9, "original_price": 42.0, "rating": 4.6, "sales": "月销8.9万",
         "key_specs": "800ml/洗护合一/顺滑/防打结/日常用/经济实惠",
         "brand": "飘柔", "category": "洗发水",
         "description": "飘柔2合1洗护一体洗发水，洗发护发同步完成节省时间，800ml超大容量极实惠，日常洗发顺滑不打结，国民品牌家庭装性价比之选。"},
        {"product_id": "jd_kiehl_scalp_shampoo", "title": "科颜氏 氨基酸头皮净化洗发水 250ml",
         "price": 198.0, "original_price": 258.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "250ml/氨基酸/头皮净化/控油去屑/无硅油/适合油性头皮",
         "brand": "科颜氏", "category": "洗发水",
         "description": "科颜氏氨基酸头皮净化洗发水，深度清洁头皮多余油脂和堵塞毛孔，有效控油去屑，无硅油配方不堵毛囊，氨基酸温和不刺激，适合油性头皮和头皮敏感人群。"},
    ],
    "儿童玩具": [
        {"product_id": "jd_wltoys_k969_rc_drift", "title": "WLtoys K969 1:28 RC漂移车 陀螺仪版",
         "price": 299.0, "original_price": 369.0, "rating": 4.7, "sales": "月销4600",
         "key_specs": "1:28/四驱/漂移胎/陀螺仪/室内遥控车", "brand": "WLtoys", "category": "儿童玩具",
         "description": "WLtoys K969 室内RC漂移车，1:28比例，四驱底盘，配漂移胎和陀螺仪。"},
        {"product_id": "jd_mst_rmx_2_5_rc_drift", "title": "MST RMX 2.5 RC漂移车 入门套装",
         "price": 699.0, "original_price": 799.0, "rating": 4.8, "sales": "月销1800",
         "key_specs": "后驱/可调悬挂/漂移胎/可升级底盘/遥控套装", "brand": "MST", "category": "儿童玩具",
         "description": "MST RMX 2.5 RC漂移车入门套装，后驱布局，可调悬挂与可升级底盘。"},
        {"product_id": "jd_lego_city_60371", "title": "乐高 City 消防局 60371 积木 766块",
         "price": 499.0, "original_price": 599.0, "rating": 4.9, "sales": "月销8800",
         "key_specs": "766块/6-12岁/消防主题/可组合场景/含消防员人偶/儿童礼物",
         "brand": "乐高", "category": "儿童玩具",
         "description": "乐高City消防局60371，766块积木培养专注力和空间想象，消防主题场景真实有趣，含消防员人偶和消防车，6-12岁男孩女孩都爱，生日节日礼物首选。"},
        {"product_id": "jd_barbie_dream_house", "title": "芭比 梦想豪宅 豪华玩具套装",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销6200",
         "key_specs": "3层豪宅/75+配件/含芭比娃娃/滑梯电梯/3-10岁女孩/过家家",
         "brand": "芭比", "category": "儿童玩具",
         "description": "芭比梦想豪宅3层结构含滑梯和电梯，75+配件场景丰富，含经典芭比娃娃，3-10岁女孩过家家玩耍，培养创意和社交想象力，经典芭比礼物套装。"},
        {"product_id": "jd_hot_wheels_track", "title": "风火轮 赛车轨道套装 超级加速弯道",
         "price": 199.0, "original_price": 259.0, "rating": 4.8, "sales": "月销1.1万",
         "key_specs": "3m长轨道/含2辆小车/发射器/弯道特技/3岁以上/男孩玩具",
         "brand": "风火轮", "category": "儿童玩具",
         "description": "风火轮超级加速弯道赛车套装，3米长轨道拼接场景刺激，含2辆合金小车和发射器，特技弯道翻滚挑战，3岁以上男孩最爱，节日生日礼物超受欢迎。"},
        {"product_id": "jd_xiaomi_robot_coding", "title": "小米 米兔编程机器人 儿童益智玩具",
         "price": 299.0, "original_price": 399.0, "rating": 4.8, "sales": "月销9200",
         "key_specs": "图形化编程/积木拼接/多形态变换/APP连接/4-10岁/STEM教育",
         "brand": "小米", "category": "儿童玩具",
         "description": "小米米兔编程机器人图形化编程启蒙，孩子无需基础即可上手，积木拼接多形态变换，App联动互动，4-10岁STEM教育首选，培养逻辑思维和创造力。"},
        {"product_id": "jd_playdoh_kitchen", "title": "培乐多 厨房玩具套装 彩泥创意",
         "price": 89.0, "original_price": 119.0, "rating": 4.7, "sales": "月销2.8万",
         "key_specs": "彩泥16色/厨房模具/安全无毒/可重复使用/3岁以上/创意玩具",
         "brand": "培乐多", "category": "儿童玩具",
         "description": "培乐多厨房彩泥套装16色丰富，专业厨房模具做出逼真食物，无毒安全材质放心孩子使用，可重复使用经济，3岁以上开始启发创意和动手能力。"},
        {"product_id": "jd_disney_puzzle_100", "title": "迪士尼 100片儿童拼图 冰雪奇缘",
         "price": 39.0, "original_price": 59.0, "rating": 4.7, "sales": "月销3.4万",
         "key_specs": "100片/冰雪奇缘/高清画面/厚纸板/5岁以上/益智拼图",
         "brand": "迪士尼", "category": "儿童玩具",
         "description": "迪士尼冰雪奇缘100片儿童拼图，高清画面色彩鲜艳，厚纸板不易折损，5岁以上锻炼专注力和空间认知，迪士尼IP女孩必爱，价格实惠亲子互动好选择。"},
    ],
    "宠物用品": [
        {"product_id": "jd_royal_canin_adult", "title": "皇家 成猫猫粮 室内成猫 2kg",
         "price": 139.0, "original_price": 169.0, "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "2kg/高消化蛋白/控制体重/牙齿清洁/1-7岁成猫/法国进口",
         "brand": "皇家", "category": "宠物用品",
         "description": "皇家成猫室内猫粮，高消化蛋白质满足日常营养，特殊颗粒设计清洁牙齿，膳食纤维控制体重，1-7岁室内成猫专属配方，法国进口品质，宠物主人信赖之选。"},
        {"product_id": "jd_hills_dog_adult", "title": "希尔斯 成犬粮 均衡营养 3kg",
         "price": 219.0, "original_price": 269.0, "rating": 4.8, "sales": "月销1.6万",
         "key_specs": "3kg/高蛋白/均衡营养/维护心脏/美毛/1-6岁成犬/美国进口",
         "brand": "希尔斯", "category": "宠物用品",
         "description": "希尔斯成犬均衡营养粮，高质量蛋白质维持肌肉量，Omega-6美化毛发，维护心脏和肾脏健康，1-6岁成犬全面营养，兽医推荐品牌，美国进口放心选。"},
        {"product_id": "jd_petkit_fountain", "title": "PETKIT 宠物自动循环饮水机 2.5L",
         "price": 179.0, "original_price": 229.0, "rating": 4.8, "sales": "月销3.2万",
         "key_specs": "2.5L/循环过滤/静音泵/无线充电版/3层过滤/猫狗通用",
         "brand": "PETKIT", "category": "宠物用品",
         "description": "PETKIT宠物自动饮水机，循环过滤保持水质新鲜，2.5L大容量减少加水频率，静音泵不影响宠物和主人，无线充电方便，3层过滤去除异味杂质，猫狗均适用。"},
        {"product_id": "jd_catlink_litter", "title": "CATLINK 自动猫砂盆 封闭式智能",
         "price": 899.0, "original_price": 1199.0, "rating": 4.8, "sales": "月销9800",
         "key_specs": "全封闭/自动清理/除臭/APP监测/大容量/适合体重<8kg猫咪",
         "brand": "CATLINK", "category": "宠物用品",
         "description": "CATLINK智能自动猫砂盆，全封闭设计隔绝异味，自动定时清理无需铲屎，APP实时监测猫咪如厕记录健康状况，大容量减少清理频率，铲屎官偷懒神器。"},
        {"product_id": "jd_tofu_cat_litter", "title": "豆腐猫砂 6L 无尘除臭 可冲马桶",
         "price": 39.9, "original_price": 55.0, "rating": 4.7, "sales": "月销6.8万",
         "key_specs": "6L/豆腐材质/可冲马桶/无粉尘/吸水快/除臭/环保",
         "brand": "猫王", "category": "宠物用品",
         "description": "豆腐猫砂天然大豆材质，粉尘极少不影响猫咪呼吸，可直接冲入马桶处理方便，快速吸水结团，除臭效果好，环保可降解，养猫人日常必备高性价比猫砂。"},
        {"product_id": "jd_pidan_cat_scratcher", "title": "PIDAN 猫抓板 瓦楞纸 双层加厚 猫玩具",
         "price": 59.9, "original_price": 79.0, "rating": 4.8, "sales": "月销4.5万",
         "key_specs": "双层加厚/瓦楞纸/保护家具/含猫薄荷/可翻面使用/猫狗通用",
         "brand": "PIDAN", "category": "宠物用品",
         "description": "PIDAN双层加厚瓦楞纸猫抓板，耐磨耐抓使用寿命是普通款2倍，引导猫咪正确磨爪保护沙发家具，附赠猫薄荷吸引猫咪使用，可翻面继续使用超值，宠物主人必备。"},
    ],
    "厨具": [
        {"product_id": "jd_supor_wok_32", "title": "苏泊尔 火红点 不粘炒锅 32cm",
         "price": 199.0, "original_price": 269.0, "rating": 4.8, "sales": "月销3.6万",
         "key_specs": "32cm/不粘涂层/麦饭石/燃气电磁炉通用/加厚锅底/附锅铲",
         "brand": "苏泊尔", "category": "厨具",
         "description": "苏泊尔火红点不粘炒锅，麦饭石纹理不粘层持久耐用，32cm大容量适合4-6人家庭，加厚锅底均匀导热，燃气电磁炉均适用，附送锅铲，厨房日常炒菜必备。"},
        {"product_id": "jd_wusthof_knife", "title": "双立人 经典系列 主厨刀 20cm",
         "price": 699.0, "original_price": 899.0, "rating": 4.9, "sales": "月销4800",
         "key_specs": "20cm/德国不锈钢/58HRC硬度/整体锻造/平衡手感/终身保修",
         "brand": "双立人", "category": "厨具",
         "description": "双立人经典系列主厨刀，德国工厂整体锻造，58HRC硬度锋利持久，20cm刀刃切割流畅，握柄平衡舒适，终身保修，德国品质厨房专业刀具，厨师家庭必备精品。"},
        {"product_id": "jd_tefal_pressure_cooker", "title": "特福 高压锅 压力锅 6L 不锈钢",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "6L/304不锈钢/双重安全阀/三重安全保护/燃气电磁炉通用/5-6人",
         "brand": "特福", "category": "厨具",
         "description": "特福不锈钢高压锅6L大容量，304食品级不锈钢安全卫生，双重安全阀三重安全保护放心使用，高压炖肉排骨速度是普通锅3倍，5-6人家庭聚餐必备。"},
        {"product_id": "jd_jiuyang_blender", "title": "九阳 多功能料理棒 搅拌棒",
         "price": 149.0, "original_price": 199.0, "rating": 4.7, "sales": "月销2.1万",
         "key_specs": "600W/不锈钢刀头/10档调速/打蛋器配件/婴儿辅食/手持搅拌",
         "brand": "九阳", "category": "厨具",
         "description": "九阳手持料理棒600W强力，不锈钢刀头耐用，10档调速从慢到快自由控制，附赠打蛋器配件，制作婴儿辅食细腻顺滑，奶昔果汁汤汁一棒搞定，厨房百搭小家电。"},
        {"product_id": "jd_midea_induction_cooker", "title": "美的 C21 电磁炉 2100W 大功率",
         "price": 199.0, "original_price": 269.0, "rating": 4.8, "sales": "月销4.5万",
         "key_specs": "2100W/IH加热/8档火力/定时/防干烧/爆炒快/适配铁锅",
         "brand": "美的", "category": "厨具",
         "description": "美的C21电磁炉2100W大功率，IH精准加热均匀，8档火力从小火炖汤到大火爆炒全覆盖，定时防干烧安全放心，适配铁锅不锈钢锅，厨房必备小家电。"},
        {"product_id": "jd_deslon_baking_sheet", "title": "德世朗 不粘烤盘 28cm 烤箱烤盘",
         "price": 59.0, "original_price": 89.0, "rating": 4.7, "sales": "月销3.8万",
         "key_specs": "28cm/不粘涂层/碳钢/耐高温/烤饼干披萨/易清洁",
         "brand": "德世朗", "category": "厨具",
         "description": "德世朗不粘烤盘，28cm大尺寸烤饼干披萨蛋糕均适用，不粘涂层食物不粘连，碳钢导热均匀，耐高温250℃，烘焙完轻松清洁，家庭烘焙必备基础装备。"},
    ],
    "汽车用品": [
        {"product_id": "jd_70mai_a800s_car", "title": "70迈 A800S 4K双录行车记录仪 前后",
         "price": 599.0, "original_price": 799.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "4K前录+1080P后录/ADAS驾驶辅助/超强夜视/140°广角/GPS/停车监控",
         "brand": "70迈", "category": "汽车用品",
         "description": "70迈A800S 4K超清双录，前置4K清晰记录车牌，后置1080P全面覆盖，ADAS驾驶辅助智能预警，超强夜视昏暗环境也清晰，GPS轨迹记录，24小时停车监控守护爱车。"},
        {"product_id": "jd_baseus_car_charger", "title": "倍思 车载充电器 120W 双口快充",
         "price": 79.0, "original_price": 99.0, "rating": 4.8, "sales": "月销5.6万",
         "key_specs": "120W总功率/USB-A+USB-C双口/PD快充/苹果安卓兼容/即插即用",
         "brand": "倍思", "category": "汽车用品",
         "description": "倍思120W双口车载充电器，USB-A+USB-C双口同时快充两台设备，PD快充苹果安卓均支持，小巧不遮挡视线，即插即用，长途驾驶手机充电必备，高性价比之选。"},
        {"product_id": "jd_xiaomi_car_mount", "title": "小米 车载手机支架 出风口 磁吸",
         "price": 69.0, "original_price": 99.0, "rating": 4.7, "sales": "月销4.2万",
         "key_specs": "磁吸固定/出风口夹/360°旋转/单手取放/兼容磁吸手机壳/稳固",
         "brand": "小米", "category": "汽车用品",
         "description": "小米磁吸车载支架，强力磁吸固定手机瞬间吸附，出风口安装不遮挡视野，360°旋转随意调角度，单手即可取放，兼容大多数磁吸手机壳，开车导航必备神器。"},
        {"product_id": "jd_3m_car_vacuum", "title": "3M 车载吸尘器 无线手持 6000Pa",
         "price": 199.0, "original_price": 259.0, "rating": 4.7, "sales": "月销2.3万",
         "key_specs": "6000Pa/无线充电/多吸嘴/缝隙清洁/车载家用两用/HEPA过滤",
         "brand": "3M", "category": "汽车用品",
         "description": "3M车载无线吸尘器，6000Pa强力吸尘深入座椅缝隙，附多种吸嘴适配不同场景，无线设计使用灵活，HEPA过滤不二次污染，车载家用两用，保持车内清洁必备。"},
        {"product_id": "jd_stp_engine_cleaner", "title": "STP 发动机保护剂 燃油宝 473ml",
         "price": 49.0, "original_price": 69.0, "rating": 4.7, "sales": "月销8.9万",
         "key_specs": "473ml/清洁积碳/保护发动机/提升动力/燃油添加剂/每5000km一瓶",
         "brand": "STP", "category": "汽车用品",
         "description": "STP燃油宝清洁发动机积碳，有效保护燃油系统，恢复动力提升燃油经济性，每5000公里或一次保养添加一瓶，汽车日常养护性价比之选，美国进口品质。"},
        {"product_id": "jd_baseus_air_freshener_car", "title": "倍思 车载空气净化器 除甲醛负离子",
         "price": 129.0, "original_price": 169.0, "rating": 4.7, "sales": "月销3.8万",
         "key_specs": "负离子/活性炭/HEPA过滤/USB供电/低噪音/车内空气净化",
         "brand": "倍思", "category": "汽车用品",
         "description": "倍思车载空气净化器，负离子杀菌消毒，活性炭吸附甲醛异味烟味，HEPA过滤PM2.5，USB供电无需换电，低噪音不影响开车，新车去味老车改善空气，车内空气守护必备。"},
    ],
    "运动服装": [
        {"product_id": "jd_lululemon_leggings", "title": "lululemon Align 瑜伽裤 25寸 黑色",
         "price": 850.0, "original_price": 980.0, "rating": 4.9, "sales": "月销6800",
         "key_specs": "25寸/Nulu面料/裸感/高腰/瑜伽普拉提专用/0-12码",
         "brand": "lululemon", "category": "运动服装",
         "description": "lululemon Align裸感瑜伽裤，Nulu超柔面料如第二层皮肤，高腰设计修身显瘦，25寸长度覆盖膝盖，瑜伽普拉提健身全场景，经典黑色百搭，运动服装顶配之选。"},
        {"product_id": "jd_nike_dri_fit_tshirt", "title": "耐克 Dri-FIT 速干T恤 男款 黑色 L",
         "price": 199.0, "original_price": 269.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "Dri-FIT速干/轻量面料/吸汗透气/修身剪裁/跑步健身/男款",
         "brand": "耐克", "category": "运动服装",
         "description": "耐克Dri-FIT速干T恤，专利速干技术将汗液快速导出，轻量面料跑步健身不束缚，修身剪裁线条好看，耐克经典款运动短袖，健身房跑步户外均适用。"},
        {"product_id": "jd_anta_compression_pants", "title": "安踏 专业压缩裤 紧身裤 男 黑色 L",
         "price": 149.0, "original_price": 199.0, "rating": 4.7, "sales": "月销1.5万",
         "key_specs": "压缩设计/速干/护膝/提升循环/跑步骑行/弹力面料/男款",
         "brand": "安踏", "category": "运动服装",
         "description": "安踏专业压缩裤，分级压缩技术提升下肢血液循环，减轻肌肉疲劳，速干弹力面料运动无阻，护膝设计保护关节，跑步骑行户外全能，国产专业运动裤高性价比。"},
        {"product_id": "jd_uniqlo_airism", "title": "优衣库 AIRism 运动短裤 男 深灰 M",
         "price": 99.0, "original_price": 129.0, "rating": 4.8, "sales": "月销3.6万",
         "key_specs": "AIRism面料/速干透气/内裤一体/健身跑步/四向弹力/M-3XL",
         "brand": "优衣库", "category": "运动服装",
         "description": "优衣库AIRism运动短裤，内衬一体设计省去内裤，AIRism面料速干透气，四向弹力无拘束，健身跑步日常百搭，设计简洁耐看，高性价比日常运动休闲短裤。"},
        {"product_id": "jd_decathlon_running_jacket", "title": "迪卡侬 跑步防风夹克 男 轻量 黑色 L",
         "price": 179.0, "original_price": 229.0, "rating": 4.7, "sales": "月销9800",
         "key_specs": "防风防泼水/轻量150g/反光条/可折叠收纳/跑步骑行/男款",
         "brand": "迪卡侬", "category": "运动服装",
         "description": "迪卡侬跑步防风夹克，防风防泼水应对户外恶劣天气，仅150g超轻量不增加负担，反光条夜跑安全可见，可折叠收入口袋便携，跑步骑行骑行徒步全场景。"},
        {"product_id": "jd_adidas_essentials_tee", "title": "阿迪达斯 Essentials 速干T恤 男款 黑色 L",
         "price": 179.0, "original_price": 239.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "AEROREADY速干/轻量面料/修身剪裁/吸汗透气/跑步健身/男款",
         "brand": "阿迪达斯", "category": "运动服装",
         "description": "阿迪达斯Essentials速干训练T恤，AEROREADY技术快速吸汗排湿，轻量面料跑步健身舒适自如，修身剪裁运动线条好看，经典阿迪运动服性价比选择，日常训练必备。"},
    ],
    "零食": [
        {"product_id": "jd_threepoints_chips", "title": "三只松鼠 坚果大礼包 8袋装 混合坚果",
         "price": 69.9, "original_price": 99.0, "rating": 4.8, "sales": "月销8.6万",
         "key_specs": "8袋/腰果+夏威夷果+碧根果+巴旦木/小包装/每日坚果/零食礼盒",
         "brand": "三只松鼠", "category": "零食",
         "description": "三只松鼠混合坚果8袋装，腰果夏威夷果碧根果巴旦木多种营养，独立小袋分量适合每日一包，方便携带，健康低卡零食，送礼自吃两用，坚果零食热销爆款。"},
        {"product_id": "jd_bestore_beef_jerky", "title": "良品铺子 风干牛肉干 500g 原味",
         "price": 69.0, "original_price": 89.0, "rating": 4.8, "sales": "月销4.2万",
         "key_specs": "500g/内蒙古牛肉/低脂高蛋白/原味/独立小包装/健身零食",
         "brand": "良品铺子", "category": "零食",
         "description": "良品铺子内蒙古风干牛肉干，精选优质牛肉低温风干，低脂高蛋白符合健身需求，嚼劲十足越嚼越香，500g大包量足实惠，独立小袋卫生方便，健身党追剧必备零食。"},
        {"product_id": "jd_oreo_original", "title": "奥利奥 经典夹心饼干 558g 大礼包",
         "price": 29.9, "original_price": 42.0, "rating": 4.8, "sales": "月销15万",
         "key_specs": "558g/经典巧克力夹心/独立小包/可泡牛奶/全家分享/经典款",
         "brand": "奥利奥", "category": "零食",
         "description": "奥利奥经典夹心饼干，酥脆巧克力饼干+香浓奶油夹心完美搭配，泡牛奶吃口感更好，558g大礼包独立小袋方便分享，经典国民零食，囤货必选。"},
        {"product_id": "jd_lays_chips_potato", "title": "乐事 薯片 原味 经典桶 154g",
         "price": 12.9, "original_price": 18.0, "rating": 4.7, "sales": "月销18万",
         "key_specs": "154g/原味/薄切/酥脆/桶装/分享装/追剧零食",
         "brand": "乐事", "category": "零食",
         "description": "乐事原味薯片经典桶装，薄切工艺口感酥脆，原味经典百吃不厌，154g满满一大桶，追剧看电影必备零食，国民薯片第一品牌，全家共享好零食。"},
        {"product_id": "jd_wangzai_milk", "title": "旺仔 牛奶 糖果味 250ml×24罐",
         "price": 65.0, "original_price": 85.0, "rating": 4.8, "sales": "月销6.2万",
         "key_specs": "250ml×24罐/复原乳/糖果味/儿童饮料/常温保存/囤货装",
         "brand": "旺仔", "category": "零食",
         "description": "旺仔牛奶经典糖果味，香浓奶味儿时记忆，250ml单罐适合儿童，24罐家庭囤货装实惠，常温保存方便，孩子爱喝老人也爱，国民经典乳饮料全家囤货首选。"},
        {"product_id": "jd_haochidai_spicy_duck", "title": "好吃哒 麻辣鸭脖 200g 重庆风味",
         "price": 29.9, "original_price": 42.0, "rating": 4.7, "sales": "月销5.2万",
         "key_specs": "200g/麻辣重庆风味/真空包装/低温烘烤/无防腐剂/追剧必备",
         "brand": "好吃哒", "category": "零食",
         "description": "好吃哒重庆风味麻辣鸭脖，精选鸭脖低温烘烤入味，麻辣鲜香回味悠长，真空包装锁鲜，200g肉量足够满足，无防腐剂更健康，追剧打游戏下酒必备零食爆款。"},
    ],
    "文具": [
        {"product_id": "jd_xiaomi_sign_pen", "title": "小米 巨能写 中性笔 0.5mm 黑色 10支",
         "price": 29.9, "original_price": 42.0, "rating": 4.8, "sales": "月销12万",
         "key_specs": "0.5mm/大容量墨水/顺滑书写/子弹头/学生考试/10支装",
         "brand": "小米", "category": "文具",
         "description": "小米巨能写中性笔，大容量墨水是普通笔3倍，0.5mm线条流畅清晰，书写顺滑不断墨，学生考试办公两用，10支装性价比超高，小米文具中的热销爆款。"},
        {"product_id": "jd_zebra_mildliner", "title": "斑马 MILDLINER 双头荧光笔 5色套装",
         "price": 39.0, "original_price": 55.0, "rating": 4.9, "sales": "月销8.6万",
         "key_specs": "5色/双头设计/细头0.7+粗头4mm/温柔色系/不透纸/笔记划重点",
         "brand": "斑马", "category": "文具",
         "description": "斑马MILDLINER双头荧光笔，温柔莫兰迪色系划重点不刺眼，双头细粗两用，不透纸不破坏背面，5色套装笔记本手账均适用，考研备考笔记必备神器。"},
        {"product_id": "jd_muji_notebook_a5", "title": "无印良品 A5 空白笔记本 80页",
         "price": 15.0, "original_price": 20.0, "rating": 4.8, "sales": "月销5.4万",
         "key_specs": "A5/80页/空白/米色纸/书写顺滑/可平铺/简约设计",
         "brand": "无印良品", "category": "文具",
         "description": "无印良品A5空白笔记本，米色护眼纸张不伤视力，80页厚度适中，可完全平铺书写方便，简约无印设计百搭，日记手账创作规划均适用，简约生活必备文具。"},
        {"product_id": "jd_stapler_deli", "title": "得力 订书机 12号 办公学生用",
         "price": 29.0, "original_price": 42.0, "rating": 4.7, "sales": "月销2.8万",
         "key_specs": "订书机/配500枚钉/最大20页/金属机身/安全设计/办公常备",
         "brand": "得力", "category": "文具",
         "description": "得力订书机金属机身坚固耐用，一次最多订20页，配500枚订书钉够用很久，安全设计防夹手，办公室学校家庭必备，得力品质可靠，高性价比文具首选。"},
        {"product_id": "jd_faber_castell_pencil", "title": "辉柏嘉 学生绘图彩色铅笔 48色",
         "price": 79.0, "original_price": 99.0, "rating": 4.8, "sales": "月销4.1万",
         "key_specs": "48色/油性/高显色/不易断芯/学生美术/绘画写生/德国品质",
         "brand": "辉柏嘉", "category": "文具",
         "description": "辉柏嘉48色彩铅，油性配方颜色饱和鲜艳，笔芯强韧不易断，涂色流畅均匀，适合学生美术课绘画写生，德国百年品牌品质保障，美术生专业彩铅之选。"},
        {"product_id": "jd_deli_correction_tape", "title": "得力 修正带 5m 学生涂改白 10支装",
         "price": 19.9, "original_price": 29.0, "rating": 4.7, "sales": "月销8.9万",
         "key_specs": "5m长/顺滑涂改/即写即盖/无毒/环保/适合学生考试/10支装",
         "brand": "得力", "category": "文具",
         "description": "得力修正带顺滑好用，一拉即出覆盖力强即写即盖不等干，5m长用量足，无毒环保放心学生使用，10支装实惠囤货，考试日常修改必备文具。"},
    ],
    "电烤箱": [
        {"product_id": "jd_boss_bs_electric_oven", "title": "老板 嵌入式电烤箱 70L 家用",
         "price": 2999.0, "original_price": 3599.0, "rating": 4.8, "sales": "月销4800",
         "key_specs": "70L/嵌入式/热风循环/10种烤制模式/独立温控/不锈钢内腔",
         "brand": "老板", "category": "电烤箱",
         "description": "老板嵌入式电烤箱70L超大容量，热风循环加热均匀，10种专业烤制模式烤肉烘焙两用，独立精准温控，不锈钢内腔易清洁，家庭烘焙爱好者和美食达人首选。"},
        {"product_id": "jd_galanz_oven_32l", "title": "格兰仕 电烤箱 32L 家用烘焙 多功能",
         "price": 299.0, "original_price": 399.0, "rating": 4.7, "sales": "月销2.1万",
         "key_specs": "32L/上下管独立控温/旋转烤叉/热风/定时/自动关机",
         "brand": "格兰仕", "category": "电烤箱",
         "description": "格兰仕32L家用电烤箱，上下管独立控温烤制更精准，附旋转烤叉烤鸡烤肉均适用，热风循环功能，60分钟定时自动断电安全，初学烘焙入门首选。"},
        {"product_id": "jd_bear_oven_25l", "title": "小熊 电烤箱 25L 烘焙 迷你",
         "price": 199.0, "original_price": 259.0, "rating": 4.7, "sales": "月销3.6万",
         "key_specs": "25L/双管加热/定时/3档控温/烤盘+烤架/小巧省台面/入门款",
         "brand": "小熊", "category": "电烤箱",
         "description": "小熊25L迷你电烤箱，小巧机身省台面，25L容量日常烤蛋挞烤饼干够用，双管均匀加热，3档温度调节，定时提醒，送烤盘烤架配件，学生宿舍小家庭烘焙入门神器。"},
        {"product_id": "jd_panasonic_oven_nb_hm3800", "title": "松下 NB-HM3800 电烤箱 38L 智能",
         "price": 899.0, "original_price": 1099.0, "rating": 4.8, "sales": "月销9800",
         "key_specs": "38L/智能双热风/8种自动菜单/上下管独立控温/不粘内腔/日本品质",
         "brand": "松下", "category": "电烤箱",
         "description": "松下NB-HM3800智能电烤箱，双热风循环均匀加热，8种自动菜单一键烤制，38L容量家庭日常烘焙足够，不粘内腔易清洁，日本精工品质，烘焙爱好者心水之选。"},
        {"product_id": "jd_midea_oven_t7_38l", "title": "美的 T7-L386E 电烤箱 38L 多功能",
         "price": 499.0, "original_price": 699.0, "rating": 4.8, "sales": "月销1.4万",
         "key_specs": "38L/旋转烤叉/热风/上下独立控温/12段发热/精准控温±2℃",
         "brand": "美的", "category": "电烤箱",
         "description": "美的T7-L386E电烤箱±2℃精准控温，12段发热管独立调节，38L大容量烤整鸡整鱼均可，旋转烤叉热风循环，均匀受热不夹生，500元档性价比烤箱首选。"},
        {"product_id": "jd_joyoung_kx_35j601", "title": "九阳 KX-35J601 电烤箱 35L 热风循环",
         "price": 399.0, "original_price": 499.0, "rating": 4.7, "sales": "月销1.5万",
         "key_specs": "35L/热风循环/上下管独立控温/旋转烤叉/12种程序/不粘内腔",
         "brand": "九阳", "category": "电烤箱",
         "description": "九阳KX-35J601电烤箱，35L容量日常烘焙足够，热风循环均匀加热不留生点，12种智能程序覆盖烤肉烘焙解冻，不粘内腔清洁方便，国产电烤箱高性价比之选。"},
    ],
    "面包机": [
        {"product_id": "jd_petrus_bread_maker", "title": "柏翠 PE9600WT 面包机 全自动 500g",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "500g/全自动/13种程序/酵母盒自动投放/无糖无油程序/预约12h",
         "brand": "柏翠", "category": "面包机",
         "description": "柏翠PE9600WT全自动面包机，酵母自动投放无需守候，13种程序涵盖吐司蛋糕果酱，无糖无油健康程序，12小时预约定时早起直接吃，一键操作厨房新手友好。"},
        {"product_id": "jd_donlim_bread_maker", "title": "东菱 DL-4706 面包机 750g 全自动",
         "price": 299.0, "original_price": 399.0, "rating": 4.7, "sales": "月销2.4万",
         "key_specs": "750g/全自动揉面发酵烘烤/15个菜单/预约/可做酸奶果冻/适合2-4人",
         "brand": "东菱", "category": "面包机",
         "description": "东菱DL-4706全自动面包机，750g容量适合2-4人家庭，15个智能菜单一键操作，揉面发酵烘烤全自动，还能做酸奶冰淇淋果冻多功能，入门价格物超所值。"},
        {"product_id": "jd_midea_bread_maker", "title": "美的 MM-TGN25A 面包机 500g 全自动",
         "price": 259.0, "original_price": 329.0, "rating": 4.7, "sales": "月销1.6万",
         "key_specs": "500g/全自动/12种功能/不粘内桶/预约13h/和面发酵烘烤一体",
         "brand": "美的", "category": "面包机",
         "description": "美的MM-TGN25A全自动面包机，12种功能涵盖白吐司全麦甜面包，不粘内桶面包不粘连，13小时预约定时，一键启动全程自动，价格亲民适合烘焙入门新手。"},
        {"product_id": "jd_bear_bread_maker", "title": "小熊 MBJ-A10U5 面包机 1000g 大容量",
         "price": 349.0, "original_price": 449.0, "rating": 4.7, "sales": "月销1.2万",
         "key_specs": "1000g大容量/全自动/19种程序/米糕饺子皮/无糖无油/适合4-6人",
         "brand": "小熊", "category": "面包机",
         "description": "小熊MBJ-A10U5大容量面包机，1000g大吐司满足4-6人家庭，19种程序超丰富，还能做米糕饺子皮，无糖无油健康模式，每日新鲜出炉，家庭烘焙最佳选择。"},
        {"product_id": "jd_joyoung_t900_bread", "title": "九阳 T900 面包机 900g 可做软欧包",
         "price": 329.0, "original_price": 429.0, "rating": 4.7, "sales": "月销1.8万",
         "key_specs": "900g/全自动/16种程序/软欧包模式/预约定时/不粘桶/2-4人",
         "brand": "九阳", "category": "面包机",
         "description": "九阳T900面包机，16种程序涵盖软欧包硬面包吐司，软欧包模式专为网红软欧包设计，900g大容量满足2-4人，预约定时早起直接享用，不粘内桶清洁简单，烘焙爱好者推荐。"},
        {"product_id": "jd_panasonic_sd_pt1000", "title": "松下 SD-PT1000 全自动面包机 500g",
         "price": 999.0, "original_price": 1299.0, "rating": 4.8, "sales": "月销8900",
         "key_specs": "500g/全自动/28种程序/酵母自投/可做果酱米糕/日本品质",
         "brand": "松下", "category": "面包机",
         "description": "松下SD-PT1000全自动面包机，28种丰富程序面包果酱米糕均能做，酵母自动投放技术，日本松下精密工艺，面包口感媲美专业面包房，烘焙爱好者高端首选。"},
    ],
    "充电宝": [
        {"product_id": "jd_xiaomi_pb30", "title": "小米 充电宝 30000mAh 33W 快充",
         "price": 179.0, "original_price": 219.0, "rating": 4.8, "sales": "月销3.2万",
         "key_specs": "30000mAh/33W快充/双USB-A+USB-C/LED电量显示/旅行用/黑色",
         "brand": "小米", "category": "充电宝",
         "description": "小米30000mAh大容量充电宝，33W快充给手机快速补电，双USB-A+USB-C三口同时充，LED显示精准电量，厚度适中携带方便，出差旅行大容量续航神器。"},
        {"product_id": "jd_anker_a1651", "title": "Anker A1651 充电宝 20000mAh 22.5W",
         "price": 149.0, "original_price": 189.0, "rating": 4.9, "sales": "月销2.8万",
         "key_specs": "20000mAh/22.5W快充/USB-C+USB-A双口/轻量390g/兼容苹果安卓",
         "brand": "Anker", "category": "充电宝",
         "description": "Anker A1651充电宝，22.5W快充手机充满不等待，20000mAh充手机5-6次，390g轻盈不重手，USB-C+USB-A双口充两台，苹果安卓全兼容，出行必备高品质充电宝。"},
        {"product_id": "jd_baseus_20000_pd", "title": "倍思 Star-Lord 充电宝 20000mAh 65W",
         "price": 199.0, "original_price": 259.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "20000mAh/65W PD快充/可充笔记本/双USB-C+USB-A/数显屏",
         "brand": "倍思", "category": "充电宝",
         "description": "倍思65W PD充电宝，不仅能快充手机，65W还能给MacBook等笔记本补电，20000mAh超大容量，数显屏精准显示剩余电量，三口同充旅行出差全场景覆盖。"},
        {"product_id": "jd_oppo_supervooc_10000", "title": "OPPO 超级闪充充电宝 10000mAh 50W",
         "price": 149.0, "original_price": 189.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "10000mAh/50W超级闪充/轻薄180g/USB-C双向快充/OPPO专属",
         "brand": "OPPO", "category": "充电宝",
         "description": "OPPO超级闪充充电宝，50W闪充速度极快，10000mAh轻薄机身仅180g，放口袋不沉，USB-C双向快充既能快速充手机也能快速给自身充电，OPPO系用户首选。"},
        {"product_id": "jd_zimi_pb20pro", "title": "紫米 Pro 充电宝 20000mAh 45W",
         "price": 169.0, "original_price": 219.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "20000mAh/45W PD/双向快充/三口输出/LCD电量屏/航空级铝合金",
         "brand": "紫米", "category": "充电宝",
         "description": "紫米Pro充电宝航空级铝合金外壳质感出众，45W PD快充，LCD屏精准显示电量，三口同充，小米生态品质保障，颜值与功能兼备，商务人士出行首选。"},
        {"product_id": "jd_romoss_sense10", "title": "罗马仕 sense10+ 充电宝 10000mAh 轻薄",
         "price": 59.0, "original_price": 89.0, "rating": 4.7, "sales": "月销4.6万",
         "key_specs": "10000mAh/22.5W快充/轻薄设计195g/双口/适合日常随身",
         "brand": "罗马仕", "category": "充电宝",
         "description": "罗马仕sense10+超薄充电宝，仅195g轻松放入口袋，10000mAh日常出行够用，22.5W快充效率高，双口设计，价格亲民性价比超高，日常通勤必备的随身充电宝。"},
    ],
    "蓝牙音箱": [
        {"product_id": "jd_jbl_charge5", "title": "JBL Charge 5 蓝牙音箱 黑色",
         "price": 999.0, "original_price": 1199.0, "rating": 4.9, "sales": "月销1.8万",
         "key_specs": "40W/IPX7防水/20h续航/可充电手机/户外/低频加强/360°立体声",
         "brand": "JBL", "category": "蓝牙音箱",
         "description": "JBL Charge 5旗舰便携音箱，40W大功率震撼低音，IPX7防水随意户外使用，20小时超长续航，独特充电宝功能可给手机充电，户外派对露营必备高品质音箱。"},
        {"product_id": "jd_sony_srs_xb43", "title": "索尼 SRS-XB43 重低音蓝牙音箱",
         "price": 1299.0, "original_price": "1599.0", "rating": 4.8, "sales": "月销9800",
         "key_specs": "EXTRA BASS超重低音/IP67/24h续航/Party Connect多设备串联/灯光",
         "brand": "索尼", "category": "蓝牙音箱",
         "description": "索尼SRS-XB43 EXTRA BASS重低音震撼，IP67防水防尘，24小时超长续航，Party Connect最多100台音箱同步，内置炫彩灯光，派对神器，低音爱好者首选。"},
        {"product_id": "jd_xiaomi_speaker_outdoor", "title": "小米 户外蓝牙音箱 30W 防水",
         "price": 299.0, "original_price": "399.0", "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "30W/IPX7防水/20h续航/360°全向声场/米家联动/轻量780g",
         "brand": "小米", "category": "蓝牙音箱",
         "description": "小米户外蓝牙音箱30W大功率，360°全向声场户外听感出色，IPX7防水淋雨无惧，20小时长续航，米家联动语音控制，780g轻量便携，高性价比户外音箱。"},
        {"product_id": "jd_bose_soundlink_flex", "title": "Bose SoundLink Flex 蓝牙音箱",
         "price": 1299.0, "original_price": 1499.0, "rating": 4.9, "sales": "月销6800",
         "key_specs": "IP67防水防尘/12h续航/立放躺放均佳音质/手势控制/PositionIQ",
         "brand": "Bose", "category": "蓝牙音箱",
         "description": "Bose SoundLink Flex专为户外设计，IP67防水可在水中浮起，PositionIQ自动适应放置角度输出最佳音质，12小时续航，Bose顶级调音，便携音箱中音质天花板。"},
        {"product_id": "jd_harman_onyx5", "title": "哈曼卡顿 Onyx Studio 5 蓝牙音箱",
         "price": 1599.0, "original_price": 1999.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "60W/360°立体声/8h续航/可充电/双声道/家用高端",
         "brand": "哈曼卡顿", "category": "蓝牙音箱",
         "description": "哈曼卡顿Onyx Studio 5经典圆形设计颜值出众，60W大功率360°无死角立体声，高端客厅音箱级音质，可充电式设计移动使用，家居装饰与音质的完美结合。"},
        {"product_id": "jd_jbl_go3_mini", "title": "JBL Go 3 迷你蓝牙音箱 蓝色",
         "price": 149.0, "original_price": 199.0, "rating": 4.7, "sales": "月销5.6万",
         "key_specs": "4.2W/IPX67防水/5h续航/掌心大小/USB-C充电/多色可选",
         "brand": "JBL", "category": "蓝牙音箱",
         "description": "JBL Go 3超迷你音箱，掌心大小随身携带，IPX67全防水，5小时续航日常足够，USB-C充电，4.2W音量在小空间表现出色，多色可选颜值高，百元入门音箱首选。"},
    ],
    "路由器": [
        {"product_id": "jd_tplink_xdr6090", "title": "TP-Link XDR6090 易展版 WiFi6 路由器",
         "price": 599.0, "original_price": 799.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "WiFi6/6000Mbps/4天线/易展Mesh/带机量200/2.4G+5G双频",
         "brand": "TP-Link", "category": "路由器",
         "description": "TP-Link XDR6090 WiFi6千兆路由器，6000Mbps理论速率，支持易展Mesh轻松扩展覆盖，4根高增益天线信号强，带机200台满足家庭办公，大户型三室必备。"},
        {"product_id": "jd_huawei_ax3_pro", "title": "华为 AX3 Pro 路由器 WiFi6+ 双核",
         "price": 299.0, "original_price": 399.0, "rating": 4.8, "sales": "月销3.6万",
         "key_specs": "WiFi6+/3000Mbps/双核芯片/支持华为Mesh/128MB内存/防蹭网",
         "brand": "华为", "category": "路由器",
         "description": "华为AX3 Pro WiFi6+路由器，双核芯片处理能力强，3000Mbps高速，华为Mesh组网轻松覆盖全屋，手机一键配网，防蹭网功能保障安全，华为生态用户优选。"},
        {"product_id": "jd_xiaomi_ax6000", "title": "小米 AX6000 路由器 WiFi6 旗舰",
         "price": 699.0, "original_price": 899.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "WiFi6/6000Mbps/4×4 MIMO/160MHz频宽/512MB内存/小米Mesh",
         "brand": "小米", "category": "路由器",
         "description": "小米AX6000旗舰WiFi6路由器，6000Mbps顶级速率，160MHz超宽频带，512MB大内存运行稳定，支持小米Mesh全屋覆盖，游戏低延迟，发烧级家用路由首选。"},
        {"product_id": "jd_netgear_rbk863s", "title": "Netgear Orbi RBK863S Mesh WiFi6 套装",
         "price": 3299.0, "original_price": 3999.0, "rating": 4.9, "sales": "月销2800",
         "key_specs": "三路由套装/WiFi6/6Gbps/覆盖700㎡/8条流/2.5G回程",
         "brand": "Netgear", "category": "路由器",
         "description": "Netgear Orbi RBK863S三路由Mesh套装，覆盖700㎡别墅大宅，2.5G有线回程极低延迟，WiFi6超高速，8条数据流同时处理，企业级稳定，大宅高端路由首选。"},
        {"product_id": "jd_tplink_xtr10890", "title": "TP-Link XTR10890 WiFi7 旗舰路由器",
         "price": 1999.0, "original_price": 2499.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "WiFi7/19Gbps/三频/MLO多链路/4K QAM/超低延迟",
         "brand": "TP-Link", "category": "路由器",
         "description": "TP-Link XTR10890 WiFi7旗舰路由器，19Gbps理论峰值速率，MLO多链路并行传输降低延迟，三频并发，4K QAM高效编码，游戏直播4K视频同时跑不卡顿。"},
        {"product_id": "jd_xiaomi_ax3000t", "title": "小米 AX3000T 路由器 WiFi6 入门",
         "price": 149.0, "original_price": 199.0, "rating": 4.7, "sales": "月销8.6万",
         "key_specs": "WiFi6/3000Mbps/双频/带机128台/小米Mesh/OFDMA/简单易用",
         "brand": "小米", "category": "路由器",
         "description": "小米AX3000T WiFi6入门路由器，150元价位WiFi6性能出色，3000Mbps双频，OFDMA多设备并发不拥堵，支持Mesh组网，小米App简单配置，性价比最强WiFi6路由。"},
    ],
    "台式电脑": [
        {"product_id": "jd_lenovo_tianyi510s", "title": "联想 天逸510S 台式电脑主机 i5-12400",
         "price": 3299.0, "original_price": 3999.0, "rating": 4.8, "sales": "月销1.2万",
         "key_specs": "i5-12400/16GB/512GB SSD/核显/Win11/WiFi/蓝牙/紧凑机箱",
         "brand": "联想", "category": "台式电脑",
         "description": "联想天逸510S台式主机，i5-12400六核处理器日常办公游戏流畅，16GB内存512GB固态，Win11正版系统，紧凑机箱节省桌面空间，家用办公性价比入门首选。"},
        {"product_id": "jd_dell_optiplex3000", "title": "戴尔 OptiPlex 3000 迷你主机 i5-12500T",
         "price": 4299.0, "original_price": 4999.0, "rating": 4.8, "sales": "月销6800",
         "key_specs": "i5-12500T/16GB/256GB SSD/核显/Win11 Pro/超迷你/2L机箱",
         "brand": "戴尔", "category": "台式电脑",
         "description": "戴尔OptiPlex 3000超迷你主机仅2L体积，i5-12500T低功耗高性能，企业级可靠性，Win11 Pro正版，可壁挂或VESA固定，办公室商务台式机空间利用极致。"},
        {"product_id": "jd_xiaomi_desktop_pro", "title": "小米 台式电脑 主机 i7-13700H",
         "price": 5999.0, "original_price": 6999.0, "rating": 4.8, "sales": "月销4800",
         "key_specs": "i7-13700H/32GB/1TB SSD/RTX 4060/Win11/小米生态/设计创作",
         "brand": "小米", "category": "台式电脑",
         "description": "小米台式电脑Pro搭载i7-13700H处理器+RTX 4060独显，32GB大内存1TB固态，设计创作游戏均流畅，小米生态联动，外观简洁，6000元价位综合性能强劲之选。"},
        {"product_id": "jd_apple_mac_mini_m4", "title": "苹果 Mac mini M4 芯片 16GB 256GB",
         "price": 4299.0, "original_price": 4599.0, "rating": 4.9, "sales": "月销8900",
         "key_specs": "M4芯片/10核CPU+10核GPU/16GB统一内存/256GB/Thunderbolt4/超迷你",
         "brand": "苹果", "category": "台式电脑",
         "description": "苹果Mac mini M4芯片性能强劲，10核CPU+10核GPU，16GB统一内存流畅运行专业软件，Thunderbolt4高速接口，体积如书本超紧凑，macOS生态苹果用户最佳台式选择。"},
        {"product_id": "jd_asus_rog_strix_g16", "title": "华硕 ROG STRIX GT15 台式游戏主机",
         "price": 8999.0, "original_price": 10999.0, "rating": 4.8, "sales": "月销2800",
         "key_specs": "i9-13900KF/32GB DDR5/2TB SSD/RTX 4070 Ti/RGB光效/游戏主机",
         "brand": "华硕ROG", "category": "台式电脑",
         "description": "华硕ROG GT15游戏台式机，i9-13900KF顶级CPU+RTX 4070 Ti旗舰显卡，32GB DDR5高频内存，2TB大容量，RGB炫彩灯效，高帧率游戏体验顶级，游戏主机旗舰之选。"},
        {"product_id": "jd_lenovo_xiaoxin_610i", "title": "联想 小新 610i 台式电脑 i3-12100 一体机",
         "price": 2499.0, "original_price": 2999.0, "rating": 4.7, "sales": "月销9200",
         "key_specs": "i3-12100/8GB/256GB SSD/核显/Win11/标配键盘鼠标/入门办公",
         "brand": "联想", "category": "台式电脑",
         "description": "联想小新610i入门台式电脑，i3-12100四核日常办公上网流畅，标配无线键鼠开箱即用，Win11正版，256GB固态启动快，8GB内存日常够用，2500元家庭入门台式首选。"},
    ],
    "打印机": [
        {"product_id": "jd_hp_neverstop1200a", "title": "惠普 NeverStop 1200a 激光打印机",
         "price": 899.0, "original_price": 1099.0, "rating": 4.8, "sales": "月销1.6万",
         "key_specs": "激光/A4黑白/补粉式/每分钟21页/USB/免墨盒/低成本",
         "brand": "惠普", "category": "打印机",
         "description": "惠普NeverStop 1200a补粉式激光打印机，创新补粉设计告别高价墨盒，打印成本极低，每分钟21页高速输出，A4黑白激光，办公学习打文件最省钱的选择。"},
        {"product_id": "jd_epson_l805", "title": "爱普生 L805 彩色喷墨打印机 照片级",
         "price": 1399.0, "original_price": 1699.0, "rating": 4.8, "sales": "月销8800",
         "key_specs": "6色喷墨/照片级/无线WiFi/PictBridge/磨砂黑墨/高光照片",
         "brand": "爱普生", "category": "打印机",
         "description": "爱普生L805六色照片打印机，磨砂黑墨支持高光哑光两种照片纸，WiFi无线打印，PictBridge直接从相机打印，照片色彩还原度高，摄影爱好者出片必备打印神器。"},
        {"product_id": "jd_canon_pixma_g3820", "title": "佳能 PIXMA G3820 多功能打印机 连供",
         "price": 799.0, "original_price": 999.0, "rating": 4.8, "sales": "月销1.2万",
         "key_specs": "彩色喷墨/连供墨水/打印复印扫描/WiFi无线/A4/超低打印成本",
         "brand": "佳能", "category": "打印机",
         "description": "佳能G3820连供多功能打印机，大容量墨仓超低打印成本，彩色打印每页约0.07元，打印复印扫描三合一，WiFi无线，手机直接打印，家庭学生办公高频用户首选。"},
        {"product_id": "jd_brother_dcp_b7535dw", "title": "兄弟 DCP-B7535DW 激光多功能打印机",
         "price": 1299.0, "original_price": 1599.0, "rating": 4.8, "sales": "月销9600",
         "key_specs": "黑白激光/打印复印扫描/自动双面/WiFi/有线/30页/分/家用办公",
         "brand": "兄弟", "category": "打印机",
         "description": "兄弟DCP-B7535DW激光三合一打印机，自动双面打印节省纸张，30页/分高速，WiFi+有线双连接，墨粉打印成本低，办公文件量大之选，家庭办公室均适用。"},
        {"product_id": "jd_hp_laserjet_mfp137fnw", "title": "惠普 LaserJet MFP 137fnw 激光打印机",
         "price": 1099.0, "original_price": 1399.0, "rating": 4.7, "sales": "月销7200",
         "key_specs": "黑白激光/打印复印扫描传真/WiFi/有线/USB/20页/分/A4",
         "brand": "惠普", "category": "打印机",
         "description": "惠普MFP 137fnw四合一激光打印机，集打印复印扫描传真于一体，WiFi无线手机直接打印，黑白激光打印成本低，20页/分，中小型办公室家庭多功能首选。"},
        {"product_id": "jd_xiaomi_inkjet_printer", "title": "小米 米家喷墨打印机 彩色 连供",
         "price": 599.0, "original_price": 799.0, "rating": 4.7, "sales": "月销2.4万",
         "key_specs": "彩色喷墨/连供墨水/WiFi/打印复印扫描/手机APP/轻量小巧",
         "brand": "小米", "category": "打印机",
         "description": "小米米家喷墨打印机，连供墨水超大容量打印成本低，彩色三合一，WiFi手机一键打印，米家App轻松操控，外观简洁小巧，学生党家庭轻量使用高性价比之选。"},
    ],
    "香水": [
        {"product_id": "jd_chanel_n5_edp100", "title": "香奈儿 N°5 香水 女士 EDP 100ml",
         "price": 1080.0, "original_price": 1280.0, "rating": 4.9, "sales": "月销3800",
         "key_specs": "100ml/EDP浓香/花香醛香/持香8h/经典百年香/送礼首选",
         "brand": "香奈儿", "category": "香水",
         "description": "香奈儿N°5百年经典香水，醛香花香馥郁优雅，EDP浓度持香达8小时，100ml大瓶日常使用，女性香水代名词，送礼自用均是顶级选择，彰显品味与气质。"},
        {"product_id": "jd_dior_sauvage_edt100", "title": "迪奥 Sauvage 旷野男士淡香水 100ml",
         "price": 880.0, "original_price": 1080.0, "rating": 4.9, "sales": "月销5600",
         "key_specs": "100ml/EDT淡香/胡椒柑橘木质香/持香6h/男士经典/大众好评",
         "brand": "迪奥", "category": "香水",
         "description": "迪奥旷野男士香水，胡椒柑橘清新开场，白桦木龙涎香留白，EDT浓度清新适合日常，持香约6小时，男士香水销量冠军，无论约会还是商务场合都适用，送男友必入。"},
        {"product_id": "jd_jomalone_peony_blush100", "title": "祖玛珑 牡丹与胭红麂绒 香水 100ml",
         "price": 1050.0, "original_price": 1200.0, "rating": 4.8, "sales": "月销2800",
         "key_specs": "100ml/EDC/牡丹玫瑰麂绒/轻盈可叠香/英国品牌/优雅日常",
         "brand": "祖玛珑", "category": "香水",
         "description": "祖玛珑牡丹与胭红麂绒，牡丹玫瑰女性花香搭配温暖麂绒底调，馥郁而不浓烈，EDC轻盈适合日常，可与其他祖玛珑叠香创造个性气味，英国高端香水品牌优雅首选。"},
        {"product_id": "jd_lancome_la_vie_est_belle", "title": "兰蔻 美好人生 女士香水 EDP 50ml",
         "price": 599.0, "original_price": 749.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "50ml/EDP/鸢尾花杏仁香草/持香7h/标志性弧形瓶/女士经典",
         "brand": "兰蔻", "category": "香水",
         "description": "兰蔻美好人生标志性弧形香水瓶，鸢尾花清新花香搭配杏仁香草温暖甜香，EDP浓度持香约7小时，50ml实惠包装，兰蔻经典女香，送礼专属外包装精美，节日礼物首选。"},
        {"product_id": "jd_versace_eros_edt50", "title": "范思哲 爱神男士香水 EDT 50ml",
         "price": 398.0, "original_price": 498.0, "rating": 4.8, "sales": "月销6800",
         "key_specs": "50ml/EDT/薄荷苹果香草/清新木质/持香5h/性价比男香",
         "brand": "范思哲", "category": "香水",
         "description": "范思哲爱神EDT男士香水，薄荷苹果清新前调，香草雪松温暖收尾，清新而有个性，持香5小时日常通勤适合，价格亲民品牌感强，男士香水入门高性价比推荐。"},
        {"product_id": "jd_armani_acqua_di_gio", "title": "阿玛尼 寄情水男士香水 EDT 100ml",
         "price": 698.0, "original_price": 899.0, "rating": 4.8, "sales": "月销3200",
         "key_specs": "100ml/EDT/海洋柑橘香/清新通透/持香6h/男士经典香/日常百搭",
         "brand": "阿玛尼", "category": "香水",
         "description": "阿玛尼寄情水海洋系男香经典之作，柑橘海洋清新通透，广藿香木质收尾，清爽而不单调，持香约6小时，百搭不出错的男士香水，夏季通勤约会全场景适用。"},
    ],
    "彩妆": [
        {"product_id": "jd_opi_infinite_shine_nail_polish", "title": "OPI Infinite Shine 指甲油 15ml",
         "price": 79.0, "original_price": 99.0, "rating": 4.8, "sales": "月销7600",
         "key_specs": "15ml/高显色/快干/多色可选/持久亮泽", "brand": "OPI", "category": "彩妆",
         "product_type": "nail_polish",
         "description": "OPI Infinite Shine 指甲油，15ml，高显色快干配方，多色可选。"},
        {"product_id": "jd_ysl_rouge_volupte_shine", "title": "圣罗兰 莹亮纯唇膏 #1 口红",
         "price": 350.0, "original_price": 420.0, "rating": 4.9, "sales": "月销1.2万",
         "key_specs": "3.2g/滋润显色/玻璃唇效果/24色可选/轻奢礼盒包装",
         "brand": "圣罗兰", "category": "彩妆",
         "description": "圣罗兰莹亮纯唇膏高光泽玻璃唇效果，质地滋润不干唇，显色度高，24种颜色满足不同肤色，标志性方形金管包装精美，送礼自用均是女性彩妆顶级之选。"},
        {"product_id": "jd_armani_luminous_silk", "title": "阿玛尼 丝绒粉底液 #3 30ml",
         "price": 560.0, "original_price": 680.0, "rating": 4.8, "sales": "月销8600",
         "key_specs": "30ml/中遮瑕/哑光丝绒质感/持妆12h/适合混合油皮/轻薄透气",
         "brand": "阿玛尼", "category": "彩妆",
         "description": "阿玛尼丝绒粉底液素颜奶奶同款，哑光丝绒质感上脸如滤镜，中遮瑕遮住瑕疵自然不假，持妆12小时不脱妆，混合油皮特别友好，彩妆界粉底天花板，好气色必入。"},
        {"product_id": "jd_huaxizi_highlight", "title": "花西子 百鸟朝凤 东方彩妆礼盒",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "眼影盘+高光腮红/东方雕刻工艺/国货精品/礼盒装/适合国风妆",
         "brand": "花西子", "category": "彩妆",
         "description": "花西子百鸟朝凤彩妆礼盒，东方雕花工艺精美绝伦，集眼影高光腮红于一体，国风颜色温暖适合东方肤色，礼盒包装精美适合送礼，国货彩妆颜值与品质双高之选。"},
        {"product_id": "jd_mac_lipstick_ruby_woo", "title": "MAC Ruby Woo 子弹头口红 经典红",
         "price": 198.0, "original_price": 238.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "3g/正红色/哑光质地/显白/经典款/中百搭/持色4h",
         "brand": "MAC", "category": "彩妆",
         "description": "MAC Ruby Woo正红经典款，显白百搭正红哑光唇色，提气色神奇效果，持色约4小时，独特子弹头包装质感好，彩妆入门口红首选，约会面试重要场合必带战衣。"},
        {"product_id": "jd_givenchy_prisme_libre", "title": "纪梵希 高级定制散粉 N°01 定妆",
         "price": 420.0, "original_price": 520.0, "rating": 4.8, "sales": "月销6200",
         "key_specs": "4色混合/提亮肤色/丝滑质感/持妆/明星同款/四色棱镜",
         "brand": "纪梵希", "category": "彩妆",
         "description": "纪梵希四宫格散粉，四色混合使用提亮肤色，丝滑质感轻盈不粉感，定妆持久全天不脱，明星红毯御用，颜值超高适合自用送礼，让妆容如高定般精致完美。"},
        {"product_id": "jd_perfect_diary_eyeshadow", "title": "完美日记 小金钻眼影盘 12色 大地色",
         "price": 59.0, "original_price": 89.0, "rating": 4.7, "sales": "月销5.6万",
         "key_specs": "12色/大地色系/珠光+哑光混合/不飞粉/显色/国货平价彩妆",
         "brand": "完美日记", "category": "彩妆",
         "description": "完美日记小金钻眼影盘12色大地色系，珠光哑光搭配，颜色低调百搭日常不出错，显色粉质细腻不飞粉，59元国货平价彩妆，化妆入门者高性价比第一眼影盘。"},
    ],
    "床品": [
        {"product_id": "jd_shuixing_4set_cotton", "title": "水星家纺 纯棉四件套 1.8m床 简约白",
         "price": 299.0, "original_price": 399.0, "rating": 4.8, "sales": "月销3.2万",
         "key_specs": "纯棉/四件套（被套200×230+枕套×2+床单）/适合1.8m床/全棉亲肤",
         "brand": "水星家纺", "category": "床品",
         "description": "水星家纺纯棉四件套，100%全棉亲肤透气，200×230cm被套适合1.8m床，简约白色百搭，全棉材质吸汗不闷热，下水不缩水不褪色，国民家纺品牌好口碑。"},
        {"product_id": "jd_fuanna_4set_silk", "title": "富安娜 60支长绒棉四件套 1.8m 粉色",
         "price": 699.0, "original_price": 899.0, "rating": 4.8, "sales": "月销1.8万",
         "key_specs": "60支长绒棉/四件套/细腻柔滑/1.8m床/印花工艺/高端床品",
         "brand": "富安娜", "category": "床品",
         "description": "富安娜60支长绒棉四件套，纱线细腻手感柔滑如丝，精密纺织密度高，印花鲜艳持久，比普通纯棉更柔软亲肤，1.8m床完美适配，高端床品追求舒睡体验首选。"},
        {"product_id": "jd_luolai_4set_bamboo", "title": "罗莱 竹棉四件套 1.5m床 清新绿",
         "price": 399.0, "original_price": 529.0, "rating": 4.7, "sales": "月销1.5万",
         "key_specs": "竹棉混纺/四件套/清凉吸湿/抑菌/适合1.5m床/夏季推荐",
         "brand": "罗莱", "category": "床品",
         "description": "罗莱竹棉四件套，竹纤维天然抑菌，清凉透气比纯棉更吸湿排汗，夏天睡觉不黏腻，清新绿色清爽视觉，适合1.5m床，有抑菌需求和爱出汗人群的夏季床品首选。"},
        {"product_id": "jd_nanjiren_4set_flannel", "title": "南极人 法兰绒四件套 1.8m床 格子",
         "price": 159.0, "original_price": 219.0, "rating": 4.7, "sales": "月销6.8万",
         "key_specs": "法兰绒/四件套/冬季保暖/超柔/加厚/适合1.8m床/秋冬必备",
         "brand": "南极人", "category": "床品",
         "description": "南极人法兰绒四件套，超细纤维加厚绒感柔软蓬松，保暖性极佳秋冬盖上暖意十足，格子纹路百搭，150元亲民价格，冬天换上懒得起床的温暖睡眠首选。"},
        {"product_id": "jd_mercury_silk_4set", "title": "水星家纺 仿真丝四件套 1.8m 浅紫",
         "price": 499.0, "original_price": 699.0, "rating": 4.7, "sales": "月销9200",
         "key_specs": "冰丝仿真丝/四件套/夏季清凉/光滑/适合1.8m床/高颜值",
         "brand": "水星家纺", "category": "床品",
         "description": "水星家纺仿真丝冰丝四件套，表面光滑凉爽，夏天睡觉清凉不黏身，高光泽感颜值出众，浅紫色高雅迷人，洗涤方便不需特殊护理，高颜值夏季床品日常使用首选。"},
        {"product_id": "jd_bliss_goose_duvet", "title": "博洋家纺 95白鹅绒被 1.5kg 冬被",
         "price": 699.0, "original_price": 999.0, "rating": 4.8, "sales": "月销4800",
         "key_specs": "95%白鹅绒/1.5kg/保暖度800+/轻量/防钻绒/冬季单人被",
         "brand": "博洋家纺", "category": "床品",
         "description": "博洋95白鹅绒被，充绒量1.5kg保暖度达800+，轻量柔软无压迫感，高密织物防绒毛钻出，秋冬睡眠温暖如云，单人双人均适用，一条好鹅绒被睡眠质量提升一档。"},
    ],
    "数据线": [
        {"product_id": "jd_ugreen_usb_c_3_5mm_adapter", "title": "UGREEN USB-C转3.5mm耳机音频转接器",
         "price": 69.0, "original_price": 89.0, "rating": 4.8, "sales": "月销2.6万",
         "key_specs": "USB-C转3.5mm/DAC芯片/耳机麦克风兼容/编织线", "brand": "UGREEN", "category": "数据线",
         "description": "UGREEN USB-C转3.5mm音频转接器，内置DAC芯片，兼容耳机和麦克风。"},
        {"product_id": "jd_anker_usbc_cable_240w", "title": "Anker 240W USB-C 数据线 2m 编织",
         "price": 79.0, "original_price": 99.0, "rating": 4.9, "sales": "月销4.2万",
         "key_specs": "240W/USB-C双头/2m/编织线/支持笔记本快充/E-Marker芯片",
         "brand": "Anker", "category": "数据线",
         "description": "Anker 240W编织数据线，E-Marker芯片支持最高240W快充，给笔记本手机均可，2m长度够用，编织耐弯折使用寿命长，USB-C双头通用，一条线搞定所有USB-C设备充电。"},
        {"product_id": "jd_baseus_cable_66w", "title": "倍思 USB-C to Lightning 充电线 1m 66W",
         "price": 39.0, "original_price": "59.0", "rating": 4.8, "sales": "月销8.6万",
         "key_specs": "1m/66W快充/USB-C转Lightning/苹果认证MFi/尼龙编织/黑色",
         "brand": "倍思", "category": "数据线",
         "description": "倍思MFi认证USB-C转Lightning充电线，苹果官方认证不降速，66W快充iPhone充满更快，尼龙编织耐用防缠绕，1m长度日常使用，苹果用户充电必备，性价比佳。"},
        {"product_id": "jd_xiaomi_cable_6a", "title": "小米 6A 数据线 USB-C 1m 白色",
         "price": 29.0, "original_price": "45.0", "rating": 4.8, "sales": "月销12万",
         "key_specs": "6A/USB-C/1m/最高240W/兼容小米华为OPPO/白色简约",
         "brand": "小米", "category": "数据线",
         "description": "小米6A超强数据线，支持最高240W快充，粗壮线芯低阻抗，兼容小米华为OPPO三星等主流快充协议，1m长度适中，29元超高性价比，全面替代原装线的首选。"},
        {"product_id": "jd_apple_usbc_to_lightning", "title": "苹果 原装 USB-C to Lightning 数据线 1m",
         "price": 149.0, "original_price": 179.0, "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "1m/苹果原装/USB-C转Lightning/支持PD快充/iPhone/iPad",
         "brand": "苹果", "category": "数据线",
         "description": "苹果原装USB-C转Lightning数据线，原装品质稳定可靠，支持PD快速充电，与苹果设备完美兼容不限速，1m适合桌面使用，iPhone iPad AirPods均可使用，官方原装首选。"},
        {"product_id": "jd_ugreen_3in1_cable", "title": "绿联 三合一充电线 1.5m USB-C Lightning Micro",
         "price": 49.0, "original_price": "69.0", "rating": 4.7, "sales": "月销3.8万",
         "key_specs": "三合一/1.5m/USB-C+Lightning+Micro/尼龙/快充/旅行必备",
         "brand": "绿联", "category": "数据线",
         "description": "绿联三合一充电线一线搞定三种设备，USB-C Lightning Micro三头，旅行出差只带一条线，1.5m长度充电舒适，尼龙编织耐用，快充支持，一家人不同设备通用神线。"},
        {"product_id": "jd_baseus_100w_cable", "title": "倍思 100W USB-C PD 快充线 2m",
         "price": 59.0, "original_price": 79.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "100W PD/USB-C/2m/编织/笔记本手机充电/广泛兼容",
         "brand": "倍思", "category": "数据线",
         "description": "倍思100W PD快充线，给笔记本充电够用，给手机闪充速度快，2m长度坐在沙发充电够得着，编织线耐弯折，100W功率广泛兼容苹果三星华为各品牌，一线多用最省钱。"},
    ],
    "冲锋衣": [
        {"product_id": "jd_northface_resolve_jacket", "title": "北面 Resolve 2 防水冲锋衣 男款 黑色 L",
         "price": 799.0, "original_price": 999.0, "rating": 4.8, "sales": "月销8800",
         "key_specs": "防水/DryVent技术/可折叠/轻量/连帽/户外徒步/男款",
         "brand": "北面", "category": "冲锋衣",
         "description": "北面Resolve 2防水冲锋衣，DryVent防水透气面料阻挡雨水，可折叠收纳成拳头大小，连帽设计防风，日常通勤户外徒步两用，北面经典入门款，品牌感十足性价比高。"},
        {"product_id": "jd_arcteryx_beta_lt", "title": "始祖鸟 Beta LT 冲锋衣 男款 绿色 M",
         "price": 4500.0, "original_price": 5000.0, "rating": 4.9, "sales": "月销1600",
         "key_specs": "GORE-TEX/三层压胶/轻量335g/专业户外/防水防风/登山攀岩",
         "brand": "始祖鸟", "category": "冲锋衣",
         "description": "始祖鸟Beta LT顶级冲锋衣，GORE-TEX三层压胶工艺，防水性能业界顶尖，仅335g超轻量，面对极端天气登山攀岩从容应对，始祖鸟品质经典，户外爱好者终极追求。"},
        {"product_id": "jd_mammut_convey_jacket", "title": "猛犸象 Convey HS Hooded 冲锋衣 男款",
         "price": 1999.0, "original_price": 2499.0, "rating": 4.8, "sales": "月销2800",
         "key_specs": "GORE-TEX/2.5层/轻量/可压缩/登山滑雪/防水防风透气",
         "brand": "猛犸象", "category": "冲锋衣",
         "description": "猛犸象Convey HS GORE-TEX 2.5层冲锋衣，轻量可压缩，防水防风透气性出色，适合登山滑雪等技术型户外运动，猛犸象专业户外品牌，高性能冲锋衣中间价位首选。"},
        {"product_id": "jd_columbia_watertight", "title": "哥伦比亚 Watertight II 防水夹克 男款",
         "price": 699.0, "original_price": 899.0, "rating": 4.7, "sales": "月销6200",
         "key_specs": "Omni-Tech防水/折叠/轻量/连帽/日常户外/男款多色",
         "brand": "哥伦比亚", "category": "冲锋衣",
         "description": "哥伦比亚Watertight II采用Omni-Tech防水透气面料，折叠收纳轻巧，连帽设计，适合日常户外轻量探险，不极端环境下性价比优秀，多色可选百搭时尚。"},
        {"product_id": "jd_decathlon_mh500_jacket", "title": "迪卡侬 MH500 防水徒步冲锋衣 男款",
         "price": 399.0, "original_price": 499.0, "rating": 4.7, "sales": "月销1.5万",
         "key_specs": "防水2000mm/透气/连帽/2L材质/徒步登山/入门款",
         "brand": "迪卡侬", "category": "冲锋衣",
         "description": "迪卡侬MH500防水冲锋衣，2000mm防水柱应对中等雨量，透气排汗舒适，连帽防风，适合徒步登山等一般户外活动，400元入门价格高性价比，户外运动新手必备。"},
        {"product_id": "jd_black_ice_g8000_jacket", "title": "黑冰 G8000 GTX 冲锋衣 女款 红色 M",
         "price": 1299.0, "original_price": 1599.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "GORE-TEX/三层/女款修身/轻量/防水防风/滑雪登山/国货品牌",
         "brand": "黑冰", "category": "冲锋衣",
         "description": "黑冰G8000国货GORE-TEX冲锋衣女款，三层防水性能专业，修身剪裁女性穿着有型，轻量设计长时间运动不累，适合滑雪登山专业户外，国产品牌GORE-TEX高性价比之选。"},
    ],
    "登山鞋": [
        {"product_id": "jd_salomon_x_ultra4", "title": "萨洛蒙 X ULTRA 4 低帮登山鞋 男款",
         "price": 899.0, "original_price": 1099.0, "rating": 4.9, "sales": "月销6800",
         "key_specs": "GTX防水/Contagrip外底/低帮/360g轻量/徒步多地形/男款",
         "brand": "萨洛蒙", "category": "登山鞋",
         "description": "萨洛蒙X Ultra 4顶级徒步鞋，GORE-TEX防水内里保持干爽，Contagrip多地形外底抓地力强，低帮灵活360g超轻，石子土路泥地均适应，徒步爱好者首选专业登山鞋。"},
        {"product_id": "jd_columbia_redmond_v3", "title": "哥伦比亚 Redmond V3 防水登山鞋 男款",
         "price": 499.0, "original_price": 699.0, "rating": 4.7, "sales": "月销1.2万",
         "key_specs": "Omni-Tech防水/高帮/抓地橡胶外底/稳定性好/徒步/男款",
         "brand": "哥伦比亚", "category": "登山鞋",
         "description": "哥伦比亚Redmond V3防水高帮登山鞋，Omni-Tech防水过溪不湿脚，高帮设计保护踝关节，抓地橡胶外底防滑，适合各类徒步地形，500元高性价比登山鞋，户外入门首选。"},
        {"product_id": "jd_meindl_xs_pro", "title": "迈德林 XS Pro GTX 登山靴 男款",
         "price": 1599.0, "original_price": 1999.0, "rating": 4.9, "sales": "月销2100",
         "key_specs": "GORE-TEX/中帮/皮革面/专业登山/承重/德国手工/稳固耐用",
         "brand": "迈德林", "category": "登山鞋",
         "description": "迈德林XS Pro德国手工登山靴，皮革面经久耐用，GORE-TEX防水，中帮支撑脚踝，专业承重设计适合重装徒步，德国品质工艺精湛，专业登山者长线路重装首选。"},
        {"product_id": "jd_decathlon_quechua_500", "title": "迪卡侬 Quechua NH500 徒步鞋 男款",
         "price": 199.0, "original_price": 259.0, "rating": 4.6, "sales": "月销2.8万",
         "key_specs": "低帮/防滑/透气/轻量/日常徒步/入门款/男款",
         "brand": "迪卡侬", "category": "登山鞋",
         "description": "迪卡侬NH500入门徒步鞋，轻量低帮设计灵活，防滑外底应对一般山路，透气面料长途行走不闷脚，200元亲民价格，适合周末轻徒步入门爱好者，经济实惠好选择。"},
        {"product_id": "jd_scarpa_terra_gtx", "title": "斯卡帕 Terra GTX 中帮登山鞋 男款",
         "price": 1299.0, "original_price": 1599.0, "rating": 4.8, "sales": "月销3200",
         "key_specs": "GORE-TEX/中帮/Vibram外底/意大利设计/多地形/轻量",
         "brand": "斯卡帕", "category": "登山鞋",
         "description": "斯卡帕Terra GTX意大利设计登山鞋，GORE-TEX防水，Vibram黄金大底抓地性能卓越，中帮支撑适合复杂地形，轻量设计，意大利做工精细，专业户外中端旗舰之选。"},
        {"product_id": "jd_merrell_moab3_gtx", "title": "迈乐 MOAB 3 GTX 登山鞋 男款 橄榄绿",
         "price": 699.0, "original_price": 899.0, "rating": 4.8, "sales": "月销8900",
         "key_specs": "GORE-TEX防水/Vibram外底/缓震/低帮/全地形/男款",
         "brand": "迈乐", "category": "登山鞋",
         "description": "迈乐MOAB 3 GTX低帮登山鞋，Vibram外底抓地防滑，GORE-TEX全天候防水，M Select CUSHION缓震减少疲劳，舒适性出众可长途穿着，综合表现均衡高性价比专业鞋款。"},
    ],
    "睡袋": [
        {"product_id": "jd_mobi_garden_sleeping_bag", "title": "牧高笛 夏季户外睡袋 成人 10℃",
         "price": 199.0, "original_price": 259.0, "rating": 4.8, "sales": "月销9800",
         "key_specs": "10℃适温/中空棉/1.5kg/可拼接/压缩包/春夏露营/单人",
         "brand": "牧高笛", "category": "睡袋",
         "description": "牧高笛夏季户外睡袋，10℃舒适适温适合春夏露营，中空棉保暖轻量，1.5kg重量压缩后体积小，两个可拼接成双人，配备压缩收纳包，亲子露营春秋使用。"},
        {"product_id": "jd_thenorth_face_cat", "title": "北面 Cat's Meow 20°F 羽绒睡袋",
         "price": 1499.0, "original_price": 1799.0, "rating": 4.9, "sales": "月销4200",
         "key_specs": "-7℃极限/550蓬松度羽绒/轻量900g/压缩包/三季户外",
         "brand": "北面", "category": "睡袋",
         "description": "北面Cat's Meow羽绒睡袋，-7℃极限温标，550蓬松度优质羽绒，保暖性强，仅900g超轻量压缩后如足球大小，三季户外登山露营均适用，北面品质保障高性能睡袋。"},
        {"product_id": "jd_blackice_sl400_down", "title": "黑冰 SL400 鹅绒睡袋 -5℃ 轻量",
         "price": 699.0, "original_price": "899.0", "rating": 4.8, "sales": "月销3600",
         "key_specs": "-5℃适温/90白鹅绒/600g轻量/压缩包/三季/国货品牌",
         "brand": "黑冰", "category": "睡袋",
         "description": "黑冰SL400白鹅绒睡袋，90%白鹅绒填充，600g超轻量，-5℃舒适适温三季可用，压缩收纳体积小，国产高端羽绒睡袋，品质媲美进口，高性价比专业睡袋之选。"},
        {"product_id": "jd_decathlon_sleeping_bag_500", "title": "迪卡侬 MH500 睡袋 5℃ 成人",
         "price": 149.0, "original_price": 199.0, "rating": 4.7, "sales": "月销2.1万",
         "key_specs": "5℃适温/化纤棉/1.3kg/可机洗/防潮底面/春夏秋露营/入门款",
         "brand": "迪卡侬", "category": "睡袋",
         "description": "迪卡侬MH500化纤棉睡袋，5℃适温春夏秋三季可用，防潮底面直接铺地使用，化纤材质可机洗易护理，150元入门款露营睡袋首选，新手露营性价比之王。"},
        {"product_id": "jd_tanluhu_down_minus10", "title": "探路者 鸭绒睡袋 -10℃ 轻量户外",
         "price": 399.0, "original_price": "499.0", "rating": 4.7, "sales": "月销5600",
         "key_specs": "-10℃极限/650g鸭绒/轻量/压缩包/冬季高山/单人",
         "brand": "探路者", "category": "睡袋",
         "description": "探路者-10℃鸭绒睡袋，650g优质鸭绒填充，极寒冬季户外低温应对，轻量压缩小巧便携，高山露营雪地徒步均可，400元价位国产鸭绒睡袋高性价比首选。"},
        {"product_id": "jd_kelty_cosmic_20", "title": "科尔蒂 Cosmic 20°F 羽绒睡袋 轻量",
         "price": 899.0, "original_price": 1099.0, "rating": 4.8, "sales": "月销2800",
         "key_specs": "-7℃/600蓬松羽绒/轻量/梯形型/拉链设计/三季户外",
         "brand": "科尔蒂", "category": "睡袋",
         "description": "科尔蒂Cosmic 20°F轻量羽绒睡袋，600蓬松度羽绒保暖效果好，梯形设计保留足部空间舒适，拉链设计通风调节，压缩后小巧，三季户外徒步露营均适用，美国户外品牌品质。"},
    ],
    "调味品": [
        {"product_id": "jd_kikkoman_dark_soy", "title": "Kikkoman 特级黑酱油 500ml", "price": 32.9, "original_price": 39.9, "rating": 4.8, "sales": "月销1.8万", "key_specs": "500ml/酿造酱油/浓口/蘸食烹饪", "brand": "Kikkoman", "category": "调味品", "description": "Kikkoman浓口黑酱油，适合炒菜、腌制和蘸食。"},
        {"product_id": "jd_abc_kecap_manis", "title": "ABC Kecap Manis 印尼甜酱油 600ml", "price": 29.9, "original_price": 36.9, "rating": 4.7, "sales": "月销9200", "key_specs": "600ml/印尼甜酱油/浓稠/烧烤蘸料", "brand": "ABC", "category": "调味品", "description": "ABC Kecap Manis印尼甜酱油，甜香浓稠。"},
        {"product_id": "jd_heinz_white_vinegar", "title": "Heinz 蒸馏白醋 1L", "price": 26.9, "original_price": 32.9, "rating": 4.8, "sales": "月销1.2万", "key_specs": "1L/蒸馏白醋/食品级/烹饪清洁两用", "brand": "Heinz", "category": "调味品", "description": "Heinz食品级蒸馏白醋，可用于烹饪和日常清洁。"},
    ],
    "主食粮油": [
        {"product_id": "jd_tilda_basmati_10kg", "title": "Tilda Basmati 巴斯马蒂香米 10kg", "price": 299.0, "original_price": 349.0, "rating": 4.8, "sales": "月销6800", "key_specs": "10kg/巴斯马蒂香米/长粒/家庭装", "brand": "Tilda", "category": "主食粮油", "description": "Tilda巴斯马蒂长粒香米10kg家庭装。"},
        {"product_id": "jd_bio_barley_1kg", "title": "Bio Organic Pearl Barley 大麦 1kg", "price": 39.9, "original_price": 49.9, "rating": 4.7, "sales": "月销5200", "key_specs": "1kg/珍珠大麦/有机/煮粥炖汤", "brand": "Bio", "category": "主食粮油", "description": "有机珍珠大麦，适合煮粥、炖汤和沙拉。"},
        {"product_id": "jd_barilla_pasta_stock", "title": "Barilla 意大利面囤货装 5kg", "price": 89.0, "original_price": 109.0, "rating": 4.8, "sales": "月销7600", "key_specs": "5kg/常温储存/长保质期/家庭囤货", "brand": "Barilla", "category": "主食粮油", "description": "Barilla意大利面大包装，适合长期常温储存。"},
    ],
    "饮料": [
        {"product_id": "jd_volvic_water_500_24", "title": "Volvic 天然矿泉水 500ml×24瓶", "price": 89.0, "original_price": 109.0, "rating": 4.8, "sales": "月销2.4万", "key_specs": "500ml×24/天然矿泉水/整箱", "brand": "Volvic", "category": "饮料", "description": "Volvic天然矿泉水500ml整箱装。"},
        {"product_id": "jd_redbull_250_24", "title": "Red Bull 能量饮料 250ml×24罐", "price": 139.0, "original_price": 159.0, "rating": 4.8, "sales": "月销3.1万", "key_specs": "250ml×24/能量饮料/整箱", "brand": "Red Bull", "category": "饮料", "description": "Red Bull能量饮料整箱装。"},
        {"product_id": "jd_xiangpiaopiao_milk_tea", "title": "香飘飘 速溶奶茶混合口味 20杯", "price": 59.9, "original_price": 79.0, "rating": 4.7, "sales": "月销4.5万", "key_specs": "20杯/速溶奶茶/混合口味/囤货装", "brand": "香飘飘", "category": "饮料", "description": "香飘飘速溶奶茶20杯囤货装。"},
    ],
    "速冻食品": [
        {"product_id": "jd_synear_buns_breakfast", "title": "思念 速冻早餐包子组合 1.2kg", "price": 39.9, "original_price": 49.9, "rating": 4.8, "sales": "月销2.9万", "key_specs": "1.2kg/包子组合/蒸制即食/早餐", "brand": "思念", "category": "速冻食品", "description": "思念速冻包子早餐组合。"},
        {"product_id": "jd_sanquan_dumpling_breakfast", "title": "三全 速冻水饺早餐装 1kg", "price": 32.9, "original_price": 42.9, "rating": 4.7, "sales": "月销3.6万", "key_specs": "1kg/速冻水饺/多口味/早餐", "brand": "三全", "category": "速冻食品", "description": "三全速冻水饺早餐家庭装。"},
    ],
    "水产食品": [
        {"product_id": "jd_fresh_salmon_500g", "title": "Fresh Atlantic Salmon 三文鱼 500g", "price": 129.0, "original_price": 159.0, "rating": 4.8, "sales": "月销8800", "key_specs": "500g/冷鲜三文鱼/当日加工/冷链", "brand": "Ocean Fresh", "category": "水产食品", "description": "冷鲜大西洋三文鱼500g。"},
        {"product_id": "jd_dried_cod_snack_200g", "title": "Dried Cod 鳕鱼干零食 200g", "price": 49.9, "original_price": 59.9, "rating": 4.7, "sales": "月销1.1万", "key_specs": "200g/鳕鱼干/即食/独立包装", "brand": "Sea Best", "category": "水产食品", "description": "即食鳕鱼干零食200g。"},
    ],
    "马克杯": [
        {"product_id": "jd_le_creuset_mug_dark", "title": "Le Creuset 深色陶瓷马克杯 400ml", "price": 169.0, "original_price": 199.0, "rating": 4.8, "sales": "月销6200", "key_specs": "400ml/陶瓷/深灰色/厚实杯壁/大容量", "brand": "Le Creuset", "category": "马克杯", "description": "深灰色大容量陶瓷马克杯，杯壁厚实。"},
        {"product_id": "jd_denby_beige_mug", "title": "Denby 米色陶瓷马克杯 350ml", "price": 139.0, "original_price": 169.0, "rating": 4.8, "sales": "月销4100", "key_specs": "350ml/陶瓷/米色/耐用/男士简约风", "brand": "Denby", "category": "马克杯", "description": "米色简约陶瓷马克杯，适合日常咖啡和茶饮。"},
    ],
    "多功能工具": [
        {"product_id": "jd_leatherman_wave_plus", "title": "Leatherman Wave+ 多功能钳 18合1", "price": 899.0, "original_price": 999.0, "rating": 4.9, "sales": "月销3600", "key_specs": "18合1/不锈钢/钳子/刀具/螺丝批/便携套", "brand": "Leatherman", "category": "多功能工具", "description": "Leatherman Wave+ 18合1多功能钳。"},
        {"product_id": "jd_victorinox_swiss_tool", "title": "Victorinox SwissTool Spirit X 多功能工具", "price": 1099.0, "original_price": 1299.0, "rating": 4.9, "sales": "月销2200", "key_specs": "24功能/瑞士制造/不锈钢/便携皮套", "brand": "Victorinox", "category": "多功能工具", "description": "Victorinox SwissTool Spirit X瑞士多功能工具。"},
        {"product_id": "jd_gerber_suspension_nxt", "title": "Gerber Suspension NXT 多功能钳 15合1", "price": 329.0, "original_price": 399.0, "rating": 4.7, "sales": "月销5100", "key_specs": "15合1/弹簧钳/不锈钢/口袋夹", "brand": "Gerber", "category": "多功能工具", "description": "Gerber Suspension NXT 15合1便携多功能钳。"},
    ],
    "default": [
        {"product_id": "jd_default_001", "title": "热销商品推荐款 A",
         "price": 299.0, "original_price": 399.0, "rating": 4.7, "sales": "月销5000",
         "key_specs": "高性价比/好评如潮/京东自营", "brand": "品牌A", "category": "通用",
         "description": "热销商品，质量可靠，性价比高。"},
        {"product_id": "jd_default_002", "title": "热销商品推荐款 B",
         "price": 499.0, "original_price": 599.0, "rating": 4.8, "sales": "月销3000",
         "key_specs": "品质优选/用户好评/正品保障", "brand": "品牌B", "category": "通用",
         "description": "优质商品，品牌保障，适合追求品质的用户。"},
    ],
    "VR头显": [
        {"product_id": "jd_meta_quest3", "title": "Meta Quest 3 VR一体机 128GB",
         "price": 3699.0, "original_price": 3999.0, "rating": 4.8, "sales": "月销3200",
         "key_specs": "4K+显示/骁龙XR2 Gen2/彩色混合现实/手势追踪/128GB",
         "brand": "Meta", "category": "VR头显",
         "description": "Meta Quest 3旗舰VR一体机，4K+高清显示，骁龙XR2 Gen2处理器，支持全彩色混合现实，手势追踪无需手柄，VR/MR双模沉浸体验。"},
        {"product_id": "jd_pico4_pro", "title": "PICO 4 Pro 全功能VR头显 256GB",
         "price": 3499.0, "original_price": 3999.0, "rating": 4.7, "sales": "月销2800",
         "key_specs": "4K+MicroOLED/骁龙XR2+ Gen1/面部眼动追踪/256GB/混合现实",
         "brand": "PICO", "category": "VR头显",
         "description": "PICO 4 Pro采用4K+ MicroOLED显示屏，搭载面部和眼动追踪，骁龙XR2+ Gen1处理器，256GB大容量，支持混合现实模式。"},
        {"product_id": "jd_xiaomi_vr_s3", "title": "小米VR 一体机 轻量版 S3",
         "price": 1999.0, "original_price": 2499.0, "rating": 4.7, "sales": "月销4100",
         "key_specs": "2K分辨率/骁龙XR1/6DoF追踪/轻量320g/米家联动/入门款",
         "brand": "小米", "category": "VR头显",
         "description": "小米VR S3入门级一体机，2K显示，6DoF六自由度追踪，仅320g超轻，米家生态联动，性价比入门VR首选。"},
        {"product_id": "jd_meta_quest3s", "title": "Meta Quest 3S VR一体机 128GB 入门版",
         "price": 2499.0, "original_price": 2899.0, "rating": 4.7, "sales": "月销4800",
         "key_specs": "LCD显示/骁龙XR2 Gen2/彩色混合现实/手势追踪/128GB/入门价格",
         "brand": "Meta", "category": "VR头显",
         "description": "Meta Quest 3S入门版，骁龙XR2 Gen2高性能处理器，支持彩色混合现实，手势追踪无需手柄，Quest 3同款芯片入门价格，性价比VR首选。"},
        {"product_id": "jd_valve_index_pc", "title": "Valve Index PC VR 完整套装",
         "price": 8999.0, "original_price": 9999.0, "rating": 4.8, "sales": "月销800",
         "key_specs": "1440×1600×2/144Hz/精确手指追踪/SteamVR/双基站/Knuckles手柄",
         "brand": "Valve", "category": "VR头显",
         "description": "Valve Index PC VR旗舰套装，1440×1600分辨率144Hz超高刷新，Knuckles手柄精确五指追踪，双基站Room-scale追踪精准，连接高配PC享受顶级VR体验。"},
        {"product_id": "jd_bytedance_pico_g3", "title": "PICO G3 VR一体机 企业版 256GB",
         "price": 4499.0, "original_price": 5299.0, "rating": 4.7, "sales": "月销1500",
         "key_specs": "4K Pancake/骁龙XR2 Gen2/6DoF/256GB/企业培训适用/眼动追踪",
         "brand": "PICO", "category": "VR头显",
         "description": "PICO G3企业版VR头显，4K Pancake光学组件清晰度高，眼动追踪技术支持注视点渲染，骁龙XR2 Gen2处理器，256GB大容量，适合企业培训沉浸教学场景。"},
    ],
    "折叠椅": [
        {"product_id": "jd_helinox_chair_one", "title": "Helinox Chair One 超轻折叠椅",
         "price": 799.0, "original_price": 998.0, "rating": 4.9, "sales": "月销3200",
         "key_specs": "超轻960g/铝合金/承重145kg/折叠收纳/10s展开",
         "brand": "Helinox", "category": "折叠椅",
         "description": "Helinox Chair One顶级轻量折叠椅，仅960g，铝合金架承重145kg，10秒快速展开，徒步露营必备神器。"},
        {"product_id": "jd_coleman_chair", "title": "Coleman 折叠椅 带扶手杯架 户外",
         "price": 199.0, "original_price": 259.0, "rating": 4.7, "sales": "月销1.5万",
         "key_specs": "钢管/带杯架/承重113kg/折叠/牛津布/轻量",
         "brand": "Coleman", "category": "折叠椅",
         "description": "Coleman经典折叠椅，自带杯架，牛津布坐面耐磨，钢管框架稳固，露营野餐家庭首选。"},
        {"product_id": "jd_naturehike_chair", "title": "挪客 NatureHike 折叠椅 超轻便携",
         "price": 289.0, "original_price": 359.0, "rating": 4.8, "sales": "月销8600",
         "key_specs": "铝合金/1.2kg/承重150kg/可调角度/附收纳袋",
         "brand": "挪客", "category": "折叠椅",
         "description": "挪客超轻折叠椅，铝合金材质仅1.2kg，承重150kg，可调背靠角度，附收纳袋，户外徒步露营理想选择。"},
        {"product_id": "jd_decathlon_fc_chair", "title": "迪卡侬 MH500 徒步折叠椅",
         "price": 149.0, "original_price": 199.0, "rating": 4.6, "sales": "月销2.1万",
         "key_specs": "铝合金/1.4kg/承重100kg/简洁设计/入门款",
         "brand": "迪卡侬", "category": "折叠椅",
         "description": "迪卡侬MH500徒步折叠椅，铝合金轻量设计，100kg承重，简洁实用，入门级户外椅性价比之选。"},
        {"product_id": "jd_director_chair_pro", "title": "专业导演椅 铝合金 高背可折叠",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销5600",
         "key_specs": "铝合金/帆布高背/扶手/可折叠/承重120kg/导演椅风格",
         "brand": "威盛达", "category": "折叠椅",
         "description": "专业导演椅，铝合金框架稳固耐用，高背帆布靠背支撑全背部，扶手设计休息舒适，可折叠收纳，拍摄现场、影视剧组、户外活动导演专用。"},
        {"product_id": "jd_coleman_beach_chair", "title": "Coleman 沙滩椅 低靠背 躺椅款",
         "price": 249.0, "original_price": 299.0, "rating": 4.7, "sales": "月销8900",
         "key_specs": "铝合金/低靠/可调背角/杯架/防水涂层/轻量1.5kg",
         "brand": "Coleman", "category": "折叠椅",
         "description": "Coleman经典沙滩椅，低重心设计贴近地面，可调节靠背角度从坐到躺随意切换，附带杯架，防水涂层耐沙耐晒，沙滩海边露营必备。"},
        {"product_id": "jd_naturehike_recliner", "title": "挪客 铝合金躺椅 可折叠午休",
         "price": 499.0, "original_price": 649.0, "rating": 4.8, "sales": "月销3800",
         "key_specs": "铝合金/全躺/角度可调/防水牛津布/附头枕/承重150kg",
         "brand": "挪客", "category": "折叠椅",
         "description": "挪客铝合金折叠躺椅，可调节从90°坐姿到180°平躺，铝合金框架承重150kg，防水牛津布面料户外适用，附可拆头枕，午休露营两用。"},
    ],
    "帐篷": [
        {"product_id": "jd_mobi_garden_tent", "title": "牧高笛 凉山1V2 双人帐篷 速开",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销8900",
         "key_specs": "双人/速开30s/防水2000mm/双层/4季/收纳袋",
         "brand": "牧高笛", "category": "帐篷",
         "description": "牧高笛凉山双人速开帐篷，30秒快速搭建，2000mm防水，双层透气，4季通用，露营野餐均适用。"},
        {"product_id": "jd_naturehike_tent", "title": "挪客 云尚 Plus 超轻帐篷 2人",
         "price": 599.0, "original_price": 799.0, "rating": 4.8, "sales": "月销5600",
         "key_specs": "超轻1.3kg/铝合金杆/防水3000mm/双门双窗/2人",
         "brand": "挪客", "category": "帐篷",
         "description": "挪客云尚Plus超轻双人帐篷，仅1.3kg，铝合金支撑杆，3000mm高防水，双门双窗通风良好，徒步背包旅行首选。"},
        {"product_id": "jd_blackdeer_tent", "title": "黑鹿 双人速开帐篷 免搭建 折叠",
         "price": 299.0, "original_price": 399.0, "rating": 4.7, "sales": "月销1.3万",
         "key_specs": "免搭建/折叠/防风/防晒/2人/户外野营",
         "brand": "黑鹿", "category": "帐篷",
         "description": "黑鹿双人免搭建折叠帐篷，弹簧自动弹开即用，防风防晒，价格亲民，适合新手露营者。"},
        {"product_id": "jd_naturehike_tarp_4x4", "title": "挪客 天幕帐篷 4×4m 防晒遮雨",
         "price": 399.0, "original_price": 549.0, "rating": 4.8, "sales": "月销1.5万",
         "key_specs": "4×4m/UPF50+防晒/3000mm防雨/铝合金杆/多点固定/轻量",
         "brand": "挪客", "category": "帐篷",
         "description": "挪客4×4m天幕帐，UPF50+高防晒指数，3000mm防水遮雨，铝合金撑杆轻量，16㎡遮蔽面积一家人阴凉下野餐烧烤，露营标配单品。"},
        {"product_id": "jd_mobi_solo_tent", "title": "牧高笛 独行侠 单人超轻帐篷",
         "price": 799.0, "original_price": 999.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "单人/超轻1.1kg/铝合金杆/3000mm/双层/挡雨前庭",
         "brand": "牧高笛", "category": "帐篷",
         "description": "牧高笛独行侠单人超轻帐篷，仅1.1kg适合轻量化徒步，铝合金杆稳固，3000mm高防水，双层设计防结露，前庭空间放置装备，solo徒步神器。"},
        {"product_id": "jd_blackice_t2_ultralight", "title": "黑冰 T2 超轻双人帐篷 碳纤杆",
         "price": 1799.0, "original_price": 2299.0, "rating": 4.9, "sales": "月销1800",
         "key_specs": "碳纤杆/双人/超轻1.2kg/4000mm防水/大前庭/抗风强",
         "brand": "黑冰", "category": "帐篷",
         "description": "黑冰T2碳纤杆超轻双人帐篷，碳纤维杆仅1.2kg，4000mm高防水，大前庭收纳装备，抗强风结构，国产高端轻量化帐篷代表，高山穿越首选。"},
    ],
    "显示器": [
        {"product_id": "jd_dell_s2722dc", "title": "戴尔 S2722DC 27寸 2K IPS USB-C显示器",
         "price": 1699.0, "original_price": 1999.0, "rating": 4.9, "sales": "月销8500",
         "key_specs": "27寸/2K/IPS/USB-C 65W充电/75Hz/广色域/超薄边框",
         "brand": "戴尔", "category": "显示器",
         "description": "戴尔S2722DC，27寸2K IPS广色域，USB-C接口支持65W快充，一线连接笔记本，办公创意两用旗舰显示器。"},
        {"product_id": "jd_lg_27gp850", "title": "LG 27GP850 27寸 2K 165Hz 电竞显示器",
         "price": 1899.0, "original_price": 2299.0, "rating": 4.9, "sales": "月销7200",
         "key_specs": "27寸/2K/IPS/165Hz/1ms/HDR400/G-Sync兼容",
         "brand": "LG", "category": "显示器",
         "description": "LG 27GP850，27寸2K IPS，165Hz高刷新率，1ms响应，HDR400，G-Sync兼容，办公游戏双优选择。"},
        {"product_id": "jd_xiaomi_27_1080p", "title": "小米 23.8寸 IPS全面屏 办公显示器",
         "price": 799.0, "original_price": 999.0, "rating": 4.8, "sales": "月销1.4万",
         "key_specs": "23.8寸/1080P/IPS/75Hz/超薄边框/低蓝光/HDMI+VGA",
         "brand": "小米", "category": "显示器",
         "description": "小米23.8寸全面屏显示器，1080P IPS广色域，低蓝光护眼认证，超薄边框，性价比极高的入门办公显示器。"},
        {"product_id": "jd_samsung_32_4k", "title": "三星 32寸 4K UHD 专业显示器 U32J590",
         "price": 2499.0, "original_price": 2999.0, "rating": 4.8, "sales": "月销4600",
         "key_specs": "32寸/4K UHD/VA/60Hz/HDR10/量子点/USB Hub",
         "brand": "三星", "category": "显示器",
         "description": "三星U32J590，32寸4K UHD分辨率，量子点广色域技术，HDR10高动态范围，内置USB Hub，专业设计创意工作首选。"},
        {"product_id": "jd_asus_proart_pa278cv", "title": "华硕 ProArt PA278CV 27寸 2K 专业显示器",
         "price": 2299.0, "original_price": 2799.0, "rating": 4.9, "sales": "月销5600",
         "key_specs": "27寸/2K/IPS/100%sRGB/Delta E<2/USB-C 90W/色准专业/75Hz",
         "brand": "华硕", "category": "显示器",
         "description": "华硕ProArt PA278CV专业创意显示器，100%sRGB广色域，出厂色准Delta E<2，USB-C 90W直连笔记本，2K分辨率细腻，图像摄影视频剪辑设计师专属高色准工作站。"},
        {"product_id": "jd_aoc_u27u2d_4k_usbc", "title": "AOC U27U2D 27寸 4K USB-C 设计显示器",
         "price": 1899.0, "original_price": 2399.0, "rating": 4.8, "sales": "月销4200",
         "key_specs": "27寸/4K UHD/IPS/USB-C 65W/HDR400/广色域/60Hz/办公设计两用",
         "brand": "AOC", "category": "显示器",
         "description": "AOC U27U2D 27寸4K UHD显示器，USB-C 65W一线连笔记本，4K超高清细腻画质，IPS广视角，HDR400高亮度，适合设计师和需要高分辨率内容创作的专业用户。"},
    ],
    "泡脚桶": [
        {"product_id": "jd_leravan_footbath", "title": "乐范 智能泡脚桶 恒温加热 按摩",
         "price": 299.0, "original_price": 399.0, "rating": 4.8, "sales": "月销2.3万",
         "key_specs": "恒温加热/气泡按摩/滚轮/自动保温/折叠/LCD显示",
         "brand": "乐范", "category": "泡脚桶",
         "description": "乐范智能泡脚桶，恒温加热保持水温，气泡按摩+滚轮足底穴位刺激，折叠收纳省空间，LCD显示温度。"},
        {"product_id": "jd_medisana_fb300", "title": "美帝莎 FB300 足浴盆 气泡震动按摩",
         "price": 199.0, "original_price": 269.0, "rating": 4.7, "sales": "月销1.8万",
         "key_specs": "气泡/震动/红外线加热/足部按摩/独立控温",
         "brand": "美帝莎", "category": "泡脚桶",
         "description": "美帝莎FB300足浴盆，气泡震动双重按摩，红外线辅助加热，独立温控，缓解足部疲劳，日常家用首选。"},
        {"product_id": "jd_xiaomi_foot_spa", "title": "小米有品 折叠泡脚桶 轻巧便携",
         "price": 129.0, "original_price": 169.0, "rating": 4.7, "sales": "月销3.5万",
         "key_specs": "折叠/轻量/恒温/简洁操作/收纳方便/出行必备",
         "brand": "小米有品", "category": "泡脚桶",
         "description": "小米有品折叠泡脚桶，超轻折叠设计方便收纳出行，恒温加热，操作简洁，商务出差旅行必备。"},
        {"product_id": "jd_leravan_deep_bucket", "title": "乐范 深桶泡脚桶 加高40cm 全腿浸泡",
         "price": 399.0, "original_price": 499.0, "rating": 4.8, "sales": "月销1.6万",
         "key_specs": "桶深40cm/全腿浸泡/恒温/气泡按摩/加热400W/LCD显示",
         "brand": "乐范", "category": "泡脚桶",
         "description": "乐范深桶泡脚桶，桶深40cm实现全小腿浸泡，相比普通款泡脚效果提升50%，恒温精准保持水温，气泡按摩足底穴位，解决普通泡脚桶太浅痛点。"},
        {"product_id": "jd_xiaomi_constant_temp_spa", "title": "小米 智能恒温泡脚桶 精准控温",
         "price": 349.0, "original_price": 449.0, "rating": 4.8, "sales": "月销2.1万",
         "key_specs": "智能恒温/米家APP/40-48℃精控/气泡按摩/折叠/足部按摩辊",
         "brand": "小米", "category": "泡脚桶",
         "description": "小米智能恒温泡脚桶，米家APP精准设定40-48℃水温，智能加热保持恒温不烫不凉，气泡涌动按摩足底，折叠收纳省空间，精致生活泡脚仪式感。"},
        {"product_id": "jd_skg_foot_spa_pro", "title": "SKG 足浴盆专业款 磁疗+气泡+震动",
         "price": 499.0, "original_price": 699.0, "rating": 4.8, "sales": "月销9800",
         "key_specs": "磁疗/气泡/震动按摩/恒温/足底滚轮/定时/LCD",
         "brand": "SKG", "category": "泡脚桶",
         "description": "SKG专业足浴盆，磁疗+气泡+震动三重按摩疗法，足底滚轮深度穴位刺激，恒温加热，定时自动关机，高端足浴体验居家可享，腿脚酸痛缓解利器。"},
    ],
    "洗碗机": [
        {"product_id": "jd_midea_wd8_builtin", "title": "美的 RX600 嵌入式洗碗机 15套",
         "price": 3499.0, "original_price": 3999.0, "rating": 4.8, "sales": "月销6800",
         "key_specs": "嵌入式/15套/热风烘干/智能除菌/WiFi/延时预约",
         "brand": "美的", "category": "洗碗机",
         "description": "美的RX600嵌入式洗碗机，15套大容量，热风烘干彻底，高温除菌99.99%，WiFi智控，适合家庭装修嵌入安装。"},
        {"product_id": "jd_haier_dw6_countertop", "title": "海尔 台式洗碗机 6套 小型家用",
         "price": 1299.0, "original_price": 1699.0, "rating": 4.8, "sales": "月销1.2万",
         "key_specs": "台式/6套/不需改水路/热风烘干/5种洗程/除菌",
         "brand": "海尔", "category": "洗碗机",
         "description": "海尔台式洗碗机，无需改水路直接接水龙头，6套容量适合1-2人，热风烘干，5种洗程，小户型首选。"},
        {"product_id": "jd_bosch_sms4htw00c", "title": "博世 SMS4HTW00C 13套 独立式洗碗机",
         "price": 4999.0, "original_price": 5999.0, "rating": 4.9, "sales": "月销3800",
         "key_specs": "独立式/13套/热交换烘干/静音46dB/9种程序/德国工艺",
         "brand": "博世", "category": "洗碗机",
         "description": "博世独立式洗碗机，德国精密工艺，13套容量，热交换烘干省电，46dB超静音，9种程序，品质之选。"},
        {"product_id": "jd_midea_wd15_builtin", "title": "美的 WX15 嵌入式洗碗机 15套 大容量",
         "price": 4299.0, "original_price": 4999.0, "rating": 4.8, "sales": "月销5600",
         "key_specs": "嵌入式/15套/热风烘干/高温75℃除菌/三层喷臂/WiFi/一级能效",
         "brand": "美的", "category": "洗碗机",
         "description": "美的WX15嵌入式洗碗机，15套超大容量应对大家庭，三层喷臂360°全覆盖，75℃高温除菌99.99%，热风烘干彻底，WiFi远程控制，一级能效节水省电。"},
        {"product_id": "jd_siemens_sn55zs49", "title": "西门子 SN55ZS49KI 13套 嵌入式洗碗机",
         "price": 6999.0, "original_price": 8299.0, "rating": 4.9, "sales": "月销2800",
         "key_specs": "嵌入式/13套/75℃热风烘干/44dB超静音/7种程序/德国品质/Home Connect",
         "brand": "西门子", "category": "洗碗机",
         "description": "西门子SN55ZS49KI嵌入式洗碗机，德国制造高标准，44dB超静音夜间洗也不打扰，75℃高温热风烘干干燥无水渍，Home Connect APP智控，厨房精装首选。"},
        {"product_id": "jd_haier_dw15_builtin_15set", "title": "海尔 EW15026D 嵌入式洗碗机 15套 大家庭",
         "price": 3999.0, "original_price": 4699.0, "rating": 4.8, "sales": "月销4800",
         "key_specs": "嵌入式/15套/热风烘干/高温75℃/自清洁/WiFi/一级能效/5种程序",
         "brand": "海尔", "category": "洗碗机",
         "description": "海尔EW15026D嵌入式洗碗机，15套超大容量适合多人家庭，75℃高温热风烘干除菌，自清洁功能保持机器洁净，WiFi智控，一级节能，嵌入安装整洁厨房，国产洗碗机高性价比选择。"},
    ],
    "破壁机": [
        {"product_id": "jd_joyoung_l18_d908", "title": "九阳 L18-D908 破壁机 加热全自动",
         "price": 699.0, "original_price": 899.0, "rating": 4.8, "sales": "月销2.8万",
         "key_specs": "2200W/加热/全自动清洗/8叶不锈钢刀/1.75L/静音",
         "brand": "九阳", "category": "破壁机",
         "description": "九阳D908破壁机，2200W强力电机，加热保温功能，全自动清洗，8叶刀头彻底破壁，静音设计不扰邻。"},
        {"product_id": "jd_midea_mj_bng50e51", "title": "美的 MJ-BNG50E51 破壁机 免手洗",
         "price": 499.0, "original_price": 699.0, "rating": 4.7, "sales": "月销3.6万",
         "key_specs": "1500W/免手洗/静音/加热/预约/6叶刀/1.5L",
         "brand": "美的", "category": "破壁机",
         "description": "美的BNG50E51破壁机，免手洗一键清洁，加热保温多功能，预约定时，静音运行，适合早餐豆浆米糊。"},
        {"product_id": "jd_vitamix_e310", "title": "Vitamix E310 专业破壁料理机",
         "price": 3299.0, "original_price": 3999.0, "rating": 4.9, "sales": "月销1600",
         "key_specs": "2HP电机/1.4L/10档调速/自动清洗/专业级/美国原装",
         "brand": "Vitamix", "category": "破壁机",
         "description": "Vitamix E310专业破壁机，2HP强力电机，10档精确调速，可处理冰块坚果，自动清洗程序，美国专业品牌旗舰之选。"},
        {"product_id": "jd_bear_mini_blender", "title": "小熊 迷你便携破壁机 300ml 随行杯",
         "price": 199.0, "original_price": 259.0, "rating": 4.7, "sales": "月销5.8万",
         "key_specs": "300ml随行杯/USB充电/六叶刀/不锈钢杯体/轻量280g/出行便携",
         "brand": "小熊", "category": "破壁机",
         "description": "小熊迷你随行破壁机，300ml一杯刚好，USB充电随时随地使用，六叶不锈钢刀头破碎果蔬效果好，280g超轻，上班带一杯新鲜果汁，办公室健康饮食首选。"},
        {"product_id": "jd_joyoung_mini_q1", "title": "九阳 Q1 Mini 迷你破壁机 350ml",
         "price": 279.0, "original_price": 359.0, "rating": 4.7, "sales": "月销4.2万",
         "key_specs": "350ml/无线充电/降噪设计/六叶刀/不锈钢内胆/自清洁",
         "brand": "九阳", "category": "破壁机",
         "description": "九阳Q1 Mini迷你破壁机，350ml精准一人份，无线充电底座随时补电，降噪外壳运行安静，自清洁功能免手洗，公司宿舍单人健康饮食首选。"},
        {"product_id": "jd_nutribullet_900w", "title": "NutriBullet Pro 900W 营养破壁机 随行杯",
         "price": 599.0, "original_price": 799.0, "rating": 4.8, "sales": "月销2.8万",
         "key_specs": "900W/700ml/不锈钢刀头/唇形杯盖/随行杯/高密封防漏/简单操作",
         "brand": "NutriBullet", "category": "破壁机",
         "description": "NutriBullet Pro 900W营养破壁机，一键启动无需复杂操作，700ml大容量随行杯满足家庭早餐，不锈钢刀头破碎完全，唇形杯盖密封防漏直接喝，简洁高效好用。"},
    ],
}

MOCK_COVERAGE_PRODUCTS: Dict[str, List[Dict]] = {
    "收纳柜": [
        {"product_id": "jd_homcom_tall_black_cabinet", "title": "HOMCOM 黑色高款收纳柜 180cm", "price": 899.0, "original_price": 1099.0, "rating": 4.7, "sales": "月销4200", "key_specs": "黑色/高180cm/双门/5层隔板/防倾倒", "brand": "HOMCOM", "category": "收纳柜", "product_type": "tall_black_cabinet", "description": "黑色高款双门收纳柜，内部五层隔板，适合客厅、卧室或玄关收纳。"},
        {"product_id": "jd_ikea_brimnes_black_wardrobe", "title": "IKEA BRIMNES 黑色衣柜 190cm", "price": 1299.0, "original_price": 1499.0, "rating": 4.8, "sales": "月销3600", "key_specs": "黑色/高190cm/双门/挂衣区+隔板", "brand": "IKEA", "category": "收纳柜", "product_type": "black_wardrobe", "description": "黑色双门衣柜，包含挂衣区和可调隔板。"},
        {"product_id": "jd_vidaxl_tall_black_cabinet", "title": "vidaXL 黑色高柜 180cm", "price": 799.0, "original_price": 999.0, "rating": 4.6, "sales": "月销2800", "key_specs": "黑色/高180cm/4层隔板/窄款", "brand": "vidaXL", "category": "收纳柜", "product_type": "tall_black_cabinet", "description": "窄款黑色高柜，四层隔板设计，适合小空间收纳。"},
    ],
    "零食": [
        {"product_id": "jd_dutch_rice_tart", "title": "Dutch Bakery Rijsttaartje 6枚 米糕", "price": 39.0, "original_price": 49.0, "rating": 4.7, "sales": "月销6200", "key_specs": "6枚/米粉烘焙/独立包装/荷兰风味", "brand": "Dutch Bakery", "category": "零食", "description": "荷兰风味rijsttaartje米糕，米粉烘焙，6枚独立包装。"},
        {"product_id": "jd_tianjin_mahua", "title": "桂发祥 十八街麻花 500g", "price": 49.0, "original_price": 59.0, "rating": 4.8, "sales": "月销2.1万", "key_specs": "500g/传统油炸糕点/独立包装", "brand": "桂发祥", "category": "零食", "description": "天津传统十八街麻花，酥脆香甜，500g礼盒装。"},
    ],
    "剃须刀": [
        {"product_id": "jd_philips_qp420_50", "title": "Philips OneBlade QP420/50 双刀头替换装", "price": 139.0, "original_price": 169.0, "rating": 4.8, "sales": "月销7600", "key_specs": "QP420/50/2枚刀头/OneBlade兼容", "brand": "Philips", "category": "剃须刀", "product_type": "shaver_blade", "description": "Philips OneBlade QP420/50原装双刀头替换装。"},
    ],
    "空调": [
        {"product_id": "jd_ecoflow_wave2_camping_ac", "title": "EcoFlow WAVE 2 便携露营空调", "price": 4999.0, "original_price": 5699.0, "rating": 4.7, "sales": "月销1800", "key_specs": "便携/露营/电池供电可选/制冷制热/14.5kg", "brand": "EcoFlow", "category": "空调", "description": "便携式露营空调，可搭配电池在帐篷和房车环境使用。"},
    ],
    "人体工学椅": [
        {"product_id": "jd_gtplayer_compact_lock_chair", "title": "GTPLAYER 紧凑电竞椅 可锁定脚轮", "price": 699.0, "original_price": 899.0, "rating": 4.7, "sales": "月销5200", "key_specs": "紧凑型/电竞椅/可锁定脚轮/赛车模拟器适用", "brand": "GTPLAYER", "category": "人体工学椅", "description": "紧凑型电竞椅，脚轮可锁定，减少赛车模拟器使用时椅子移动。"},
    ],
    "装饰摆件": [
        {"product_id": "jd_marble_egg_set", "title": "天然大理石装饰蛋 3件套", "price": 199.0, "original_price": 249.0, "rating": 4.7, "sales": "月销2100", "key_specs": "天然大理石/3件套/桌面摆件", "brand": "StoneCraft", "category": "装饰摆件", "product_type": "marble_egg", "description": "天然大理石手工打磨装饰蛋三件套。"},
    ],
    "餐具": [
        {"product_id": "jd_black_cutlery_3pc", "title": "Echtwerk 黑色不锈钢刀叉勺 3件套", "price": 129.0, "original_price": 159.0, "rating": 4.8, "sales": "月销4300", "key_specs": "黑色/不锈钢/刀叉勺各1件", "brand": "Echtwerk", "category": "餐具", "product_type": "cutlery_set", "description": "黑色哑光不锈钢餐具，包含餐刀、餐叉和餐勺各一件。"},
        {"product_id": "jd_wood_cutlery_3pc", "title": "Miyazaki 榉木刀叉勺 3件套", "price": 99.0, "original_price": 129.0, "rating": 4.7, "sales": "月销3600", "key_specs": "榉木/刀叉勺各1件/便携", "brand": "Miyazaki", "category": "餐具", "product_type": "cutlery_set", "description": "天然榉木餐具三件套，包含刀、叉、勺。"},
    ],
    "扫地机": [
        {"product_id": "jd_aiper_seagull_pool_robot", "title": "Aiper Seagull SE 无线泳池清洁机器人", "price": 1599.0, "original_price": 1899.0, "rating": 4.7, "sales": "月销1900", "key_specs": "泳池清洁/无线/自动吸污/90分钟续航", "brand": "Aiper", "category": "扫地机", "product_type": "pool_robot", "description": "无线泳池清洁机器人，自动清理池底碎屑和污物。"},
    ],
    "户外泳池": [
        {"product_id": "jd_bestway_steel_pro_pool", "title": "Bestway Steel Pro 金属框泳池 3.0m", "price": 899.0, "original_price": 1099.0, "rating": 4.7, "sales": "月销2500", "key_specs": "3.0m/金属框架/非充气/加厚PVC", "brand": "Bestway", "category": "户外泳池", "product_type": "metal_frame_pool", "description": "中型非充气金属框架泳池，结构稳固。"},
    ],
    "面条": [
        {"product_id": "jd_nissin_noodles_5pack", "title": "Nissin 出前一丁面条 5包装", "price": 29.0, "original_price": 35.0, "rating": 4.8, "sales": "月销3.2万", "key_specs": "5包/方便面/即食面", "brand": "Nissin", "category": "面条", "product_type": "noodles", "description": "经典即食面五包装，适合快速料理。"},
    ],
    "营养补充剂": [
        {"product_id": "jd_optimum_serious_mass", "title": "Optimum Nutrition Serious Mass 2.7kg 增肌粉", "price": 399.0, "original_price": 469.0, "rating": 4.8, "sales": "月销4800", "key_specs": "2.7kg/每份2勺/增肌粉/蛋白质+碳水", "brand": "Optimum Nutrition", "category": "营养补充剂", "product_type": "mass_gainer", "description": "Serious Mass增肌粉，包装建议每份2勺，实际可食用天数取决于每日用量。"},
    ],
    "护肤品": [
        {"product_id": "jd_koriderm_barrier_cream", "title": "Koriderm Barrier Repair Cream 50ml", "price": 169.0, "original_price": 199.0, "rating": 4.7, "sales": "月销2300", "key_specs": "50ml/屏障修护面霜/保湿", "brand": "Koriderm", "category": "护肤品", "description": "Koriderm屏障修护保湿面霜50ml。"},
    ],
}

for _coverage_category, _coverage_products in MOCK_COVERAGE_PRODUCTS.items():
    MOCK_PRODUCTS.setdefault(_coverage_category, []).extend(_coverage_products)


# ─────────────────────────────────────────────────────────────────────────────
# 搭配商品池（按风格/场景分组，供 scenario_related_recall 直接查询）
# ─────────────────────────────────────────────────────────────────────────────
MATCHING_PRODUCTS: Dict[str, Dict[str, List[Dict]]] = {
    "nordic": {  # 北欧风
        "茶几": [
            {"product_id": "jd_match_table_01", "title": "宜家 LACK 茶几 白色极简 55×55cm",
             "price": 199.0, "rating": 4.7, "sales": "月销8500",
             "key_specs": "白色/简约/55×55cm/钢腿/蜂窝板", "brand": "宜家", "category": "茶几",
             "description": "北欧风格极简茶几，白色烤漆面板，纤细钢腿，适合小户型。"},
            {"product_id": "jd_match_table_01b", "title": "北欧白橡木圆形茶几 实木腿 80cm",
             "price": 699.0, "rating": 4.8, "sales": "月销4200",
             "key_specs": "白橡木/圆形80cm/实木腿/简约/承重40kg", "brand": "源氏木语", "category": "茶几",
             "description": "白橡木实木圆形茶几，天然木纹温润，圆形设计安全无锐角，适合有小孩的家庭，北欧风格百搭。"},
            {"product_id": "jd_match_table_01c", "title": "北欧风藤编茶几 竹木结合 60×60cm",
             "price": 459.0, "rating": 4.7, "sales": "月销3100",
             "key_specs": "竹木+藤编/60×60cm/轻量/自然纹理/承重30kg", "brand": "竹趣", "category": "茶几",
             "description": "竹木藤编茶几，自然材质与北欧风高度契合，手工编织藤面透气美观，轻量好移动，卧室客厅皆宜。"},
        ],
        "落地灯": [
            {"product_id": "jd_match_lamp_01", "title": "欧普照明 北欧风落地灯 客厅简约",
             "price": 299.0, "rating": 4.8, "sales": "月销1.2万",
             "key_specs": "E27/三档调光/160cm/亚麻灯罩", "brand": "欧普", "category": "落地灯",
             "description": "北欧风亚麻灯罩落地灯，三档调光，温馨氛围，适合客厅角落。"},
            {"product_id": "jd_match_lamp_01b", "title": "飞利浦 北欧风落地灯 可调色温",
             "price": 399.0, "rating": 4.8, "sales": "月销7800",
             "key_specs": "LED/2700-6500K/无级调光/160cm/APP控制", "brand": "飞利浦", "category": "落地灯",
             "description": "飞利浦智能落地灯，无级调光调色温，APP语音双控，北欧简约外形，白天暖光夜间冷光轻松切换。"},
            {"product_id": "jd_match_lamp_01c", "title": "米家 智能落地灯 Pro 极简立柱",
             "price": 499.0, "rating": 4.8, "sales": "月销6200",
             "key_specs": "LED/16M色/2700-6500K/语音控制/米家联动/铝合金立柱", "brand": "小米", "category": "落地灯",
             "description": "小米米家智能落地灯Pro，铝合金极简立柱，1600万色RGB调节，语音/APP/手动三控，HomeKit接入，北欧极简风格完美配套。"},
        ],
        "地毯": [
            {"product_id": "jd_match_rug_01", "title": "北欧编织地毯 几何图案 160×230cm",
             "price": 399.0, "rating": 4.7, "sales": "月销3500",
             "key_specs": "PP材质/几何图案/防滑/易清洁/160×230cm", "brand": "优家", "category": "地毯",
             "description": "北欧风几何编织地毯，耐磨防滑，多种尺寸可选。"},
            {"product_id": "jd_match_rug_01b", "title": "北欧纯棉针织地毯 米白色 120×180cm",
             "price": 259.0, "rating": 4.7, "sales": "月销5100",
             "key_specs": "100%棉/针织/120×180cm/可机洗/柔软", "brand": "棉致", "category": "地毯",
             "description": "纯棉针织地毯，触感柔软亲肤，米白色百搭北欧风格，可整机洗涤，客厅卧室均适用。"},
            {"product_id": "jd_match_rug_01c", "title": "北欧极简羊毛混纺地毯 200×300cm 大尺寸",
             "price": 899.0, "rating": 4.8, "sales": "月销2800",
             "key_specs": "羊毛混纺/200×300cm/短绒/防滑/可干洗/加厚", "brand": "卡兰多", "category": "地毯",
             "description": "羊毛混纺大地毯，200×300cm覆盖大客厅，短绒触感柔软，防滑底布牢固，浅灰/米白/浅蓝北欧配色可选，品质感出众。"},
        ],
        "装饰画": [
            {"product_id": "jd_match_art_01", "title": "北欧抽象装饰画 三联壁画 无框",
             "price": 168.0, "rating": 4.6, "sales": "月销5200",
             "key_specs": "无框/30×40cm×3/防水画布", "brand": "艺家", "category": "装饰画",
             "description": "北欧极简风格抽象三联装饰画，防水画布，直接悬挂。"},
            {"product_id": "jd_match_art_01b", "title": "北欧风植物叶片装饰画 实木框 40×60cm",
             "price": 228.0, "rating": 4.8, "sales": "月销8900",
             "key_specs": "实木框/40×60cm/高清打印/防潮/挂钩", "brand": "木质印象", "category": "装饰画",
             "description": "北欧绿植叶片装饰画，实木相框精致，高清微喷工艺色彩饱满，为客厅带来自然清新气息。"},
            {"product_id": "jd_match_art_01c", "title": "北欧莫兰迪色系装饰画 双联 50×70cm",
             "price": 298.0, "rating": 4.7, "sales": "月销4600",
             "key_specs": "莫兰迪色/双联/50×70cm/铝合金细边框/高清微喷", "brand": "艺创", "category": "装饰画",
             "description": "莫兰迪灰绿色北欧双联装饰画，铝合金细边框轻奢质感，高清微喷色彩还原度高，竖版构图适合沙发背景墙。"},
        ],
        "抱枕": [
            {"product_id": "jd_match_pillow_01", "title": "北欧风棉麻抱枕套 4件套 45×45cm",
             "price": 129.0, "rating": 4.7, "sales": "月销1.8万",
             "key_specs": "棉麻/45×45cm/4件套/可拆洗/北欧几何", "brand": "棉致", "category": "抱枕",
             "description": "北欧几何图案棉麻抱枕套，质感细腻，可拆洗枕套方便维护，4件套不同图案层次丰富，沙发装饰首选。"},
            {"product_id": "jd_match_pillow_01b", "title": "北欧ins风抱枕 含芯 双面设计 50×50cm",
             "price": 79.0, "rating": 4.7, "sales": "月销3.2万",
             "key_specs": "含芯/50×50cm/双面设计/可拆洗/PP棉填充", "brand": "素眠", "category": "抱枕",
             "description": "ins网红抱枕含芯，双面不同图案增加层次感，PP棉填充饱满不塌陷，可拆洗枕套，北欧/现代风格沙发必备点缀。"},
        ],
        "绿植": [
            {"product_id": "jd_match_plant_01", "title": "龟背竹 北欧风格植物 盆栽 含陶瓷盆",
             "price": 168.0, "rating": 4.8, "sales": "月销2.3万",
             "key_specs": "龟背竹/陶瓷白色花盆/高40-60cm/耐阴/净化空气", "brand": "绿之家", "category": "绿植",
             "description": "龟背竹北欧网红植物，叶形优雅大方，耐阴好养活，白色陶瓷盆简约百搭，摆放客厅书房氛围感满分。"},
            {"product_id": "jd_match_plant_01b", "title": "琴叶榕 北欧风大型盆栽 含编织花盆 高80-100cm",
             "price": 258.0, "rating": 4.7, "sales": "月销1.4万",
             "key_specs": "琴叶榕/编织草编盆/高80-100cm/耐阴/净化", "brand": "绿植工坊", "category": "绿植",
             "description": "琴叶榕北欧高颜值大型盆栽，叶片宽大厚实，配草编花盆自然质朴，80-100cm高度成为客厅视觉焦点，耐阴养护简单。"},
        ],
        "置物架": [
            {"product_id": "jd_match_rack_01", "title": "北欧风铁艺置物架 墙角三角架 3层",
             "price": 199.0, "rating": 4.7, "sales": "月销6400",
             "key_specs": "铁艺/白色/3层/墙角款/免打孔/承重10kg", "brand": "铁艺之家", "category": "置物架",
             "description": "北欧风铁艺墙角置物架，白色线条简约，3层空间摆放绿植摆件，免打孔安装，充分利用角落空间。"},
            {"product_id": "jd_match_rack_01b", "title": "北欧实木隔板墙壁挂架 松木 60cm 3块装",
             "price": 159.0, "rating": 4.7, "sales": "月销4800",
             "key_specs": "松木/60cm/3块/浮动搁板/承重8kg/含膨胀螺丝", "brand": "木趣家", "category": "置物架",
             "description": "松木实木浮动搁板，自然木纹温润，3块组合层次错落，可摆放绿植相框书本，北欧原木风墙面布置必备。"},
        ],
        "窗帘": [
            {"product_id": "jd_match_curtain_01", "title": "北欧简约棉麻窗帘 遮光 定制尺寸",
             "price": 89.0, "rating": 4.7, "sales": "月销3.1万",
             "key_specs": "棉麻混纺/80%遮光/多尺寸/北欧色系/免洗", "brand": "布帘家", "category": "窗帘",
             "description": "北欧简约棉麻窗帘，80%遮光保证睡眠质量，棉麻质感自然垂坠，莫兰迪色系百搭北欧装修风格。"},
            {"product_id": "jd_match_curtain_01b", "title": "北欧亚麻提花窗帘 全遮光 双层",
             "price": 129.0, "rating": 4.8, "sales": "月销2.1万",
             "key_specs": "亚麻提花/99%全遮光/双层/打孔/多色/免熨烫", "brand": "梦洁", "category": "窗帘",
             "description": "亚麻提花全遮光双层窗帘，99%遮光率彻底隔绝光线，提花工艺立体纹理高档质感，免熨烫免安装滑轨，卧室客厅均适用。"},
        ],
        "餐椅": [
            {"product_id": "jd_match_diningchair_01", "title": "北欧风实木餐椅 布艺坐垫 2把装",
             "price": 698.0, "rating": 4.8, "sales": "月销5600",
             "key_specs": "白橡木腿/布艺坐垫/可拆洗/靠背/2把/承重120kg", "brand": "源氏木语", "category": "餐椅",
             "description": "白橡木腿北欧餐椅，布艺坐垫可拆洗，靠背贴合背部曲线，2把套装实惠，搭配北欧实木餐桌完美协调。"},
            {"product_id": "jd_match_diningchair_01b", "title": "北欧塑料椅 PP一体成型 多色可选",
             "price": 258.0, "rating": 4.7, "sales": "月销8900",
             "key_specs": "PP一体成型/金属细腿/防滑脚垫/可叠放/多色", "brand": "憩美", "category": "餐椅",
             "description": "北欧ins风PP一体成型餐椅，超轻便携可叠放收纳，金属细腿优雅纤细，多色可选自由搭配，适合小户型餐厅阳台。"},
        ],
    },
    "modern": {  # 现代简约
        "收纳柜": [
            {"product_id": "jd_match_vasagle_black_cabinet", "title": "VASAGLE 现代黑色高款边柜 165cm", "price": 999.0, "original_price": 1199.0, "rating": 4.8, "sales": "月销3100", "key_specs": "黑色/高165cm/双门+开放格/现代简约", "brand": "VASAGLE", "category": "收纳柜", "product_type": "tall_black_cabinet", "description": "现代黑色高款边柜，双门与开放格组合，适合客厅和餐厅收纳。"},
            {"product_id": "jd_match_sobuy_black_cabinet", "title": "SoBuy 黑色高款收纳柜 170cm", "price": 759.0, "original_price": 929.0, "rating": 4.7, "sales": "月销2600", "key_specs": "黑色/高170cm/窄款/可调隔板/现代风", "brand": "SoBuy", "category": "收纳柜", "product_type": "tall_black_cabinet", "description": "黑色窄款高柜，可调隔板适应不同高度物品。"},
        ],
        "茶几": [
            {"product_id": "jd_match_table_02", "title": "现代简约钢化玻璃茶几 黑色金属腿",
             "price": 359.0, "rating": 4.8, "sales": "月销6200",
             "key_specs": "钢化玻璃/黑色金属腿/60×60cm", "brand": "木月", "category": "茶几",
             "description": "现代简约风格钢化玻璃茶几，稳固耐用，易清洁。"},
            {"product_id": "jd_match_table_02b", "title": "现代轻奢大理石茶几 圆形 80cm",
             "price": 899.0, "rating": 4.8, "sales": "月销3800",
             "key_specs": "仿大理石台面/金色不锈钢腿/圆形80cm/防水", "brand": "米优", "category": "茶几",
             "description": "轻奢大理石纹茶几，金色不锈钢腿优雅精致，圆形无锐角，仿大理石面耐刮防水，提升客厅档次。"},
            {"product_id": "jd_match_table_02c", "title": "现代简约烤漆茶几 哑光黑 长方形 120×60cm",
             "price": 599.0, "rating": 4.7, "sales": "月销4400",
             "key_specs": "哑光烤漆/120×60cm/金属腿/底层储物/现代风", "brand": "曲美", "category": "茶几",
             "description": "哑光烤漆长方形茶几，低调沉稳质感，底层镂空搁板增加收纳，金属细腿轻盈不压迫，现代简约风客厅必备。"},
        ],
        "落地灯": [
            {"product_id": "jd_match_lamp_02", "title": "简约弧形落地灯 客厅卧室阅读灯",
             "price": 349.0, "rating": 4.8, "sales": "月销9800",
             "key_specs": "弧形/LED/三色调光/高度可调", "brand": "松下", "category": "落地灯",
             "description": "现代弧形设计落地灯，LED光源，三色调光，适合阅读和氛围营造。"},
            {"product_id": "jd_match_lamp_02b", "title": "现代极简落地灯 细杆磨砂 160cm",
             "price": 498.0, "rating": 4.8, "sales": "月销5500",
             "key_specs": "磨砂铝材/细杆/LED20W/无极调光/160cm", "brand": "雅格", "category": "落地灯",
             "description": "极简细杆落地灯，磨砂铝合金质感高级，无极调光0%-100%任意调节，造型克制优雅，现代简约客厅必备。"},
            {"product_id": "jd_match_lamp_02c", "title": "现代落地灯 球形灯罩 金属底座 黑色",
             "price": 268.0, "rating": 4.7, "sales": "月销7100",
             "key_specs": "球形乳白灯罩/黑色金属底座/E27/150cm/散光柔和", "brand": "奥朵", "category": "落地灯",
             "description": "球形乳白灯罩落地灯，漫射光线柔和不刺眼，黑色金属底座稳重时尚，150cm适合大多数户型，沙发旁阅读灯首选。"},
        ],
        "地毯": [
            {"product_id": "jd_match_rug_02", "title": "现代简约纯色短绒地毯 灰色 160×230cm",
             "price": 349.0, "rating": 4.7, "sales": "月销4800",
             "key_specs": "PP短绒/防滑/可机洗/160×230cm/哑光质感", "brand": "优家", "category": "地毯",
             "description": "现代简约纯色短绒地毯，低调哑光质感，耐脏耐磨，可机洗，适配现代简约客厅。"},
            {"product_id": "jd_match_rug_02b", "title": "现代简约条纹地毯 黑白 200×290cm",
             "price": 498.0, "rating": 4.7, "sales": "月销3300",
             "key_specs": "涤纶/黑白条纹/200×290cm/低绒/防滑底/耐磨", "brand": "皮尔卡丹", "category": "地毯",
             "description": "黑白条纹现代地毯，经典配色永不过时，低绒设计耐踩耐磨易清洁，防滑底安全稳固，现代风格客厅卧室两用。"},
        ],
        "装饰画": [
            {"product_id": "jd_match_art_02", "title": "现代简约黑白线条装饰画 无框 40×60cm",
             "price": 128.0, "rating": 4.7, "sales": "月销6300",
             "key_specs": "无框/40×60cm/防水画布/极简线条", "brand": "艺家", "category": "装饰画",
             "description": "黑白极简线条装饰画，无框设计轻盈，防水画布材质，适合现代简约风格客厅或卧室。"},
            {"product_id": "jd_match_art_02b", "title": "现代抽象油画 橙金配色 手绘 50×70cm",
             "price": 388.0, "rating": 4.8, "sales": "月销2900",
             "key_specs": "手绘/亚麻布/50×70cm/实木框/橙金色系", "brand": "艺创", "category": "装饰画",
             "description": "纯手绘抽象油画，橙金暖色调为空间注入活力，亚麻布手工绘制，实木内框，每幅独一无二的艺术品。"},
            {"product_id": "jd_match_art_02c", "title": "现代风城市建筑装饰画 黑白摄影 组合",
             "price": 198.0, "rating": 4.7, "sales": "月销4100",
             "key_specs": "黑白摄影/铝合金细框/40×60cm×2/防潮/可组合", "brand": "都市印象", "category": "装饰画",
             "description": "城市建筑黑白摄影装饰画，铝合金细边框现代感强，两幅组合对称挂法，现代简约风格客厅沙发墙首选。"},
        ],
        "收纳架": [
            {"product_id": "jd_match_shelf_02", "title": "现代简约落地书架 置物架 5层",
             "price": 299.0, "rating": 4.8, "sales": "月销8100",
             "key_specs": "钢木结构/5层/承重30kg/免打孔/140cm高", "brand": "佳佰", "category": "收纳架",
             "description": "钢木结合落地书架，工业简约风格，5层大容量，免打孔安装，适合客厅或书房。"},
            {"product_id": "jd_match_shelf_02b", "title": "现代简约悬浮墙面书架 隔板 组合套装",
             "price": 259.0, "rating": 4.7, "sales": "月销5500",
             "key_specs": "白色/悬浮搁板/3块组合/60cm/承重15kg/含膨胀螺丝", "brand": "百意", "category": "收纳架",
             "description": "现代悬浮隔板书架，打孔固定悬空效果简洁，白色烤漆与墙面融合，3块自由组合错落美观，书房客厅均适用。"},
        ],
        "沙发垫": [
            {"product_id": "jd_match_sofapad_02", "title": "现代简约四季沙发垫 防滑 全套",
             "price": 198.0, "rating": 4.7, "sales": "月销1.1万",
             "key_specs": "冰丝/防滑/全套含靠背/多尺寸/可机洗", "brand": "慕思", "category": "沙发垫",
             "description": "现代简约冰丝沙发垫，夏季凉爽透气，四季可用，防滑底面不跑位，全套含坐垫靠背，一键焕新沙发颜值。"},
            {"product_id": "jd_match_sofapad_02b", "title": "现代简约绒面沙发套 全包弹力 通用",
             "price": 159.0, "rating": 4.7, "sales": "月销2.2万",
             "key_specs": "弹力绒/全包/防滑/1-4人座通用/可机洗/多色", "brand": "护沙", "category": "沙发垫",
             "description": "弹力绒全包沙发套，一套包裹焕新旧沙发，弹力面料贴合各尺寸，防滑底固定不位移，可机洗护理方便。"},
        ],
        "镜子": [
            {"product_id": "jd_match_mirror_02", "title": "现代简约圆形挂镜 金属边框 60cm",
             "price": 268.0, "rating": 4.8, "sales": "月销7200",
             "key_specs": "圆形/60cm/铝合金框/防爆/可挂可靠墙", "brand": "美德丽", "category": "镜子",
             "description": "圆形极简挂镜，细边铝合金框轻奢质感，防爆玻璃安全耐用，玄关客厅卧室通用，视觉扩大空间感。"},
            {"product_id": "jd_match_mirror_02b", "title": "现代全身镜 落地镜 大尺寸 45×150cm",
             "price": 398.0, "rating": 4.8, "sales": "月销1.3万",
             "key_specs": "45×150cm/铝合金边框/防爆/可悬挂可落地/旋转支架", "brand": "百意", "category": "镜子",
             "description": "现代简约全身镜，45×150cm大尺寸穿衣方便，铝合金细边框精致，防爆安全，旋转支架可调角度，卧室必备。"},
        ],
        "香薰": [
            {"product_id": "jd_match_aroma_02", "title": "网易严选 无火香薰扩香石 居家氛围",
             "price": 89.0, "rating": 4.7, "sales": "月销4.8万",
             "key_specs": "石膏扩香石/无酒精/天然精油/持续30天/多香型", "brand": "网易严选", "category": "香薰",
             "description": "无火香薰扩香石，石膏材质渗透持续扩散香气，无酒精安全，天然植物精油香型，放置桌面卫生间玄关均可，持续30天香气。"},
            {"product_id": "jd_match_aroma_02b", "title": "观夏 昆仑煮雪 香薰蜡烛 200g",
             "price": 198.0, "rating": 4.9, "sales": "月销8600",
             "key_specs": "大豆蜡/天然精油/200g/45h燃烧/玻璃容器/礼盒装", "brand": "观夏", "category": "香薰",
             "description": "观夏国产香薰品牌旗舰产品，大豆蜡环保，天然精油配方，200g可燃45小时，玻璃容器精致，送礼自用皆宜。"},
        ],
    },
    "mid_century": {  # 中古复古
        "茶几": [
            {"product_id": "jd_match_table_03", "title": "中古风实木圆形茶几 胡桃木色 60cm",
             "price": 899.0, "rating": 4.8, "sales": "月销3200",
             "key_specs": "胡桃木色/圆形60cm/实木腿/复古榫卯/承重50kg", "brand": "木偶记", "category": "茶几",
             "description": "中古复古风实木茶几，胡桃木深色纹理沉稳，圆形台面无锐角，实木腿稳固耐用，传统榫卯工艺百年传承。"},
            {"product_id": "jd_match_table_03b", "title": "中古风椭圆茶几 黑胡桃实木 100×60cm",
             "price": 1299.0, "rating": 4.8, "sales": "月销2100",
             "key_specs": "黑胡桃实木/椭圆/100×60cm/黄铜脚垫/复古五金", "brand": "木偶记", "category": "茶几",
             "description": "黑胡桃实木椭圆茶几，深木纹自然沉稳，黄铜五金细节复古精致，椭圆形设计空间流线感强，中古风格客厅核心搭配。"},
        ],
        "落地灯": [
            {"product_id": "jd_match_lamp_03", "title": "中古铜色落地灯 复古工业风 可调向",
             "price": 568.0, "rating": 4.8, "sales": "月销4100",
             "key_specs": "铜色金属/可调向/E27/暖光/160cm/复古设计", "brand": "古铜灯饰", "category": "落地灯",
             "description": "中古铜色落地灯，黄铜质感灯头可360°调向，E27灯口兼容多种光源，暖黄光营造复古氛围，书房客厅皆宜。"},
            {"product_id": "jd_match_lamp_03b", "title": "中古风三脚架落地灯 木腿+铜色灯罩",
             "price": 698.0, "rating": 4.8, "sales": "月销2800",
             "key_specs": "榉木三脚架/铜色锥形灯罩/E27/160cm/复古工艺", "brand": "古木灯坊", "category": "落地灯",
             "description": "三脚架落地灯，榉木实木腿复古质感，铜色锥形灯罩纯正中古风格，E27灯口可换暖黄球泡，客厅阅读角必备氛围单品。"},
        ],
        "地毯": [
            {"product_id": "jd_match_rug_03", "title": "中古波斯风地毯 复古花纹 160×230cm",
             "price": 599.0, "rating": 4.8, "sales": "月销2600",
             "key_specs": "仿波斯/复古花纹/160×230cm/加厚/防滑", "brand": "波斯印象", "category": "地毯",
             "description": "中古波斯风格地毯，传统花纹复古优雅，加厚绒面脚感舒适，防滑底面安全，为客厅注入历史感与艺术气息。"},
            {"product_id": "jd_match_rug_03b", "title": "中古土耳其风格地毯 复古红棕 200×290cm",
             "price": 899.0, "rating": 4.7, "sales": "月销1900",
             "key_specs": "土耳其纹/红棕配色/200×290cm/机洗/高密度绒面", "brand": "东方印象", "category": "地毯",
             "description": "土耳其复古花纹地毯，红棕暖色调与胡桃木家具完美呼应，高密度绒面触感奢华，大尺寸覆盖客厅主区，可机洗护理方便。"},
        ],
        "装饰画": [
            {"product_id": "jd_match_art_03", "title": "中古风复古海报装饰画 做旧 实木框",
             "price": 198.0, "rating": 4.7, "sales": "月销4800",
             "key_specs": "做旧工艺/实木框/30×40cm/复古海报", "brand": "旧时光", "category": "装饰画",
             "description": "中古复古海报装饰画，做旧工艺还原年代质感，实木相框精致，适合打造复古书房或客厅氛围角。"},
            {"product_id": "jd_match_art_03b", "title": "中古风植物标本装饰画 做旧金框 三联",
             "price": 298.0, "rating": 4.8, "sales": "月销3600",
             "key_specs": "做旧金色框/植物标本/三联30×40cm×3/高清微喷", "brand": "旧时光", "category": "装饰画",
             "description": "植物标本风格三联装饰画，做旧金框复古质感，高清微喷工艺色彩细腻，与中古胡桃木家具风格一致，书房餐厅皆宜。"},
        ],
        "台灯": [
            {"product_id": "jd_match_tablelamp_03", "title": "中古黄铜台灯 复古蘑菇灯 床头灯",
             "price": 358.0, "rating": 4.8, "sales": "月销3900",
             "key_specs": "黄铜/蘑菇造型/调光/E14/暖光/床头", "brand": "古铜灯饰", "category": "台灯",
             "description": "黄铜蘑菇台灯，复古造型精致小巧，无级调光适合睡前氛围光，黄铜底座沉稳，与中古家具搭配相得益彰。"},
            {"product_id": "jd_match_tablelamp_03b", "title": "中古风绿色陶瓷台灯 鼓形灯罩 复古",
             "price": 458.0, "rating": 4.8, "sales": "月销2700",
             "key_specs": "陶瓷底座/绿色釉面/鼓形亚麻灯罩/E27/调光开关", "brand": "陶光", "category": "台灯",
             "description": "复古绿色陶瓷台灯，釉面瓷底座手工质感，搭配亚麻鼓形灯罩，暖黄灯光营造复古书房氛围，与中古家具及装饰画构成完整风格组合。"},
        ],
        "收纳柜": [
            {"product_id": "jd_match_cabinet_03", "title": "中古风实木斗柜 3斗 胡桃木色",
             "price": 1299.0, "rating": 4.9, "sales": "月销1800",
             "key_specs": "胡桃木色/3抽屉/实木腿/铜拉手/W80×D40×H75cm", "brand": "木偶记", "category": "收纳柜",
             "description": "中古风实木斗柜，胡桃木深色纹理，3个宽抽屉收纳衣物配件，铜质拉手细节精致，卧室客厅均适合摆放。"},
            {"product_id": "jd_match_cabinet_03b", "title": "中古风实木边柜 2门 胡桃木 电视柜",
             "price": 1899.0, "rating": 4.8, "sales": "月销1400",
             "key_specs": "胡桃木/2门+开放格/铜拉手/150×40×55cm/实木腿", "brand": "木偶记", "category": "收纳柜",
             "description": "中古风实木两门边柜，胡桃木色沉稳大气，铜质拉手精致复古，上方开放格可陈列摆件，可用作电视柜或餐边柜，空间感强。"},
        ],
        "摆件": [
            {"product_id": "jd_match_ornament_03", "title": "中古风黄铜摆件套装 花瓶+烛台 3件",
             "price": 268.0, "rating": 4.8, "sales": "月销2900",
             "key_specs": "黄铜/花瓶+烛台/3件套/桌面摆设/复古质感", "brand": "铜意", "category": "摆件",
             "description": "黄铜复古摆件3件套，花瓶+烛台高低错落，哑光黄铜表面质感厚重，搭配干花插花更显复古格调，茶几书架摆放皆宜。"},
        ],
    },
    "camera": {  # 相机摄影搭配
        "三脚架": [
            {"product_id": "jd_match_tripod_01", "title": "思锐 A-3204X 铝合金三脚架",
             "price": 399.0, "rating": 4.8, "sales": "月销4500",
             "key_specs": "铝合金/最大承重8kg/最高165cm/球形云台", "brand": "思锐", "category": "三脚架",
             "description": "思锐经典铝合金三脚架，稳定性强，适合风景和人像摄影。"},
            {"product_id": "jd_match_tripod_01b", "title": "百诺 C2573F 碳纤维三脚架",
             "price": 1299.0, "rating": 4.9, "sales": "月销2100",
             "key_specs": "碳纤维/承重12kg/折叠42cm/球形云台B2/专业级", "brand": "百诺", "category": "三脚架",
             "description": "百诺碳纤维专业三脚架，轻量坚固，B2球形云台快装板设计，适合长焦重型镜头使用，旅拍神器。"},
            {"product_id": "jd_match_tripod_01c", "title": "峰腾 MT-08 迷你桌面三脚架 轻便",
             "price": 129.0, "rating": 4.7, "sales": "月销6800",
             "key_specs": "铝合金/桌面款/22cm/球形云台/手机夹/便携180g", "brand": "峰腾", "category": "三脚架",
             "description": "峰腾迷你桌面三脚架，22cm小巧携带方便，球形云台360°旋转，附手机夹可固定手机/相机，vlog自拍桌面拍摄神器。"},
        ],
        "摄影包": [
            {"product_id": "jd_match_bag_01", "title": "乐摄宝 Flipside 400 AW III 双肩摄影包",
             "price": 699.0, "rating": 4.9, "sales": "月销2800",
             "key_specs": "防雨/可放15.6寸笔记本/24L容量/防盗背取", "brand": "乐摄宝", "category": "摄影包",
             "description": "乐摄宝经典双肩摄影包，防雨设计，背取式开口，适合旅行摄影师。"},
            {"product_id": "jd_match_bag_01b", "title": "思锐 SWIFT X25 单肩摄影包 斜挎",
             "price": 299.0, "rating": 4.7, "sales": "月销5600",
             "key_specs": "单肩斜挎/防雨/可放微单/快取设计/轻量", "brand": "思锐", "category": "摄影包",
             "description": "思锐单肩斜挎摄影包，侧开快取设计拍摄无延迟，防雨面料保护器材，适合微单和小型单反日常街拍。"},
            {"product_id": "jd_match_bag_01c", "title": "乐摄宝 NOVA 2 腰包 快取摄影腰包",
             "price": 199.0, "rating": 4.7, "sales": "月销4200",
             "key_specs": "腰包/侧开快取/微单+2镜头/防水/轻量0.4kg", "brand": "乐摄宝", "category": "摄影包",
             "description": "乐摄宝腰包，侧开设计不摘下就能取相机，防水面料，仅0.4kg，适合轻装徒步、骑行、活动摄影，快取首选。"},
        ],
        "清洁套装": [
            {"product_id": "jd_match_clean_01", "title": "JJC 相机清洁套装 10件套",
             "price": 89.0, "rating": 4.7, "sales": "月销1.5万",
             "key_specs": "气吹+镜头笔+清洁液+擦拭布/10件", "brand": "JJC", "category": "清洁套装",
             "description": "相机镜头清洁必备套装，包含气吹、镜头笔、清洁液等，维护光学设备。"},
            {"product_id": "jd_match_clean_01b", "title": "VSGO 专业相机清洁套装 传感器清洁棒",
             "price": 168.0, "rating": 4.8, "sales": "月销8900",
             "key_specs": "传感器清洁棒×8/清洁液/镜头纸/气吹/防静电", "brand": "VSGO", "category": "清洁套装",
             "description": "VSGO专业级相机传感器清洁套装，含8支一次性清洁棒+防静电清洁液，精准清除传感器灰尘，全画幅APS-C均适用，摄影师必备。"},
        ],
        "存储卡": [
            {"product_id": "jd_match_sdcard_01", "title": "SanDisk Extreme Pro SD卡 128GB V30",
             "price": 149.0, "rating": 4.9, "sales": "月销8.2万",
             "key_specs": "128GB/200MB/s读速/V30/4K视频/防水防震", "brand": "SanDisk", "category": "存储卡",
             "description": "SanDisk至尊超极速SD卡，200MB/s极速读取，V30规格支持4K视频录制，防水防震防X光，专业摄影必备。"},
            {"product_id": "jd_match_sdcard_01b", "title": "索尼 SF-M256T CFexpress A型 256GB",
             "price": 899.0, "rating": 4.9, "sales": "月销3400",
             "key_specs": "CFexpress A型/256GB/800MB/s读速/支持4K120p", "brand": "索尼", "category": "存储卡",
             "description": "索尼CFexpress A型存储卡，800MB/s超高速读取，256GB大容量，支持A7系列相机4K 120p高帧率录制，专业高速影像记录必备。"},
        ],
        "滤镜": [
            {"product_id": "jd_match_filter_01", "title": "保谷 CPL偏振镜 67mm 超薄框",
             "price": 199.0, "rating": 4.8, "sales": "月销6300",
             "key_specs": "CPL偏振/67mm/超薄框/多层镀膜/铝合金", "brand": "保谷", "category": "滤镜",
             "description": "保谷超薄CPL偏振镜，消除水面玻璃反光，增加天空蓝色饱和度，多层镀膜透光率高，超薄框不暗角，风景必备。"},
            {"product_id": "jd_match_filter_01b", "title": "NiSi 可调ND减光镜 77mm 1.5-5档",
             "price": 398.0, "rating": 4.8, "sales": "月销4100",
             "key_specs": "可调ND/77mm/1.5-5档/真彩色不偏色/双层镀膜", "brand": "NiSi", "category": "滤镜",
             "description": "NiSi可调ND减光镜，1.5-5档连续可调，真彩色镀膜不偏色，慢门拍水流云彩必备，77mm大口径适配多款镜头。"},
        ],
        "快门线": [
            {"product_id": "jd_match_remote_01", "title": "品色 NW-880 无线快门线 佳能/尼康通用",
             "price": 79.0, "rating": 4.7, "sales": "月销2.8万",
             "key_specs": "无线100m/定时/B门/多相机通用/防误触", "brand": "品色", "category": "快门线",
             "description": "品色无线快门遥控器，100m有效距离，支持B门长曝光和定时拍摄，兼容佳能尼康索尼多品牌，夜景星空必备。"},
        ],
        "闪光灯": [
            {"product_id": "jd_match_flash_01", "title": "神牛 V1 圆头机顶闪光灯 TTL",
             "price": 999.0, "rating": 4.8, "sales": "月销3800",
             "key_specs": "76Ws/TTL/圆形灯头/磁吸配件/2.4G无线/锂电", "brand": "神牛", "category": "闪光灯",
             "description": "神牛V1圆头闪光灯，圆形灯头光线柔和均匀，TTL全自动测光，内置2.4G无线主控，锂电快充，人像摄影利器。"},
            {"product_id": "jd_match_flash_01b", "title": "神牛 TT685II 机顶闪光灯 佳能/尼康",
             "price": 499.0, "rating": 4.8, "sales": "月销6200",
             "key_specs": "60Ws/TTL/2.4G无线/旋转跳闪/高速同步/入门性价比", "brand": "神牛", "category": "闪光灯",
             "description": "神牛TT685II入门机顶闪光灯，60Ws足够日常使用，TTL自动测光，2.4G无线引闪，支持高速同步，性价比入门人像闪光灯首选。"},
        ],
        "云台": [
            {"product_id": "jd_match_gimbal_01", "title": "大疆 RS 3 Mini 单反微单稳定器 折叠",
             "price": 1099.0, "rating": 4.8, "sales": "月销5600",
             "key_specs": "折叠/承重2kg/三轴稳定/自动轴锁/蓝牙快连/9h续航", "brand": "大疆", "category": "云台",
             "description": "大疆RS 3 Mini折叠云台稳定器，仅795g超轻，承重2kg覆盖主流微单，自动轴锁方便携带，蓝牙快连一键启动，视频创作者必备。"},
        ],
    },
    "fitness": {  # 健身运动搭配
        "瑜伽垫": [
            {"product_id": "jd_match_yoga_01", "title": "lululemon The Mat 5mm 天然橡胶瑜伽垫",
             "price": 899.0, "rating": 4.9, "sales": "月销1800",
             "key_specs": "天然橡胶/5mm/183×61cm/防滑纹", "brand": "lululemon", "category": "瑜伽垫",
             "description": "lululemon顶级瑜伽垫，天然橡胶材质，抓地力强，适合高强度训练。"},
            {"product_id": "jd_match_yoga_01b", "title": "奥义 天然橡胶瑜伽垫 加厚6mm",
             "price": 198.0, "rating": 4.8, "sales": "月销3.2万",
             "key_specs": "天然橡胶/6mm/183×68cm/防滑/吸汗", "brand": "奥义", "category": "瑜伽垫",
             "description": "奥义天然橡胶加厚瑜伽垫，6mm厚度膝盖保护，宽版68cm更大活动空间，天然橡胶防滑耐磨，性价比之选。"},
            {"product_id": "jd_match_yoga_01c", "title": "迪卡侬 8mm 加厚防滑瑜伽垫 NBR",
             "price": 149.0, "rating": 4.7, "sales": "月销4.1万",
             "key_specs": "NBR/8mm超厚/183×61cm/防滑/减震/适合初学者", "brand": "迪卡侬", "category": "瑜伽垫",
             "description": "迪卡侬8mm加厚NBR瑜伽垫，超厚减震保护关节，防滑纹路稳固支撑，价格亲民适合健身新手入门使用。"},
        ],
        "运动水壶": [
            {"product_id": "jd_match_bottle_01", "title": "特百惠 Hydration 运动水壶 700ml",
             "price": 99.0, "rating": 4.8, "sales": "月销3.2万",
             "key_specs": "Tritan材质/700ml/防漏/一键开盖", "brand": "特百惠", "category": "运动水壶",
             "description": "Tritan耐摔材质，一键开盖设计，适合健身房和户外运动。"},
            {"product_id": "jd_match_bottle_01b", "title": "富光 运动吸管水壶 1L 大容量 防漏",
             "price": 69.0, "rating": 4.7, "sales": "月销5.8万",
             "key_specs": "Tritan/1L/吸管+直饮双盖/防漏/耐摔/刻度线", "brand": "富光", "category": "运动水壶",
             "description": "富光大容量运动水壶，1L满足长时间健身补水，吸管和直饮两种盖子随时切换，防漏耐摔，刻度线监测饮水量。"},
        ],
        "运动毛巾": [
            {"product_id": "jd_match_towel_01", "title": "Columbia 速干运动毛巾 细纤维",
             "price": 79.0, "rating": 4.7, "sales": "月销5600",
             "key_specs": "细纤维/速干/30×100cm/抗菌", "brand": "Columbia", "category": "运动毛巾",
             "description": "哥伦比亚速干运动毛巾，细纤维材质，吸汗透气，适合健身后擦拭。"},
            {"product_id": "jd_match_towel_01b", "title": "Keep 运动毛巾 冷感速干 75×35cm",
             "price": 49.0, "rating": 4.7, "sales": "月销2.1万",
             "key_specs": "冷感纤维/速干/75×35cm/轻量/附挂扣", "brand": "Keep", "category": "运动毛巾",
             "description": "Keep冷感运动毛巾，冷感纤维遇汗自动降温，吸水速干，轻量小巧附挂扣可挂在包包，健身随行必备。"},
        ],
        "哑铃": [
            {"product_id": "jd_match_dumbbell_01", "title": "奥义 可调节哑铃 10kg×2 男女通用",
             "price": 299.0, "rating": 4.8, "sales": "月销1.5万",
             "key_specs": "可调节2-10kg/包胶/防滑/2只/收纳方便", "brand": "奥义", "category": "哑铃",
             "description": "奥义可调节哑铃，2-10kg多档可调适合不同训练需求，包胶防滑保护地板，一对入门级家庭健身首选。"},
            {"product_id": "jd_match_dumbbell_01b", "title": "Keep 固定哑铃 5kg×2 烤漆铸铁",
             "price": 129.0, "rating": 4.7, "sales": "月销2.8万",
             "key_specs": "5kg×2/烤漆铸铁/防滑包胶/入门/女性友好", "brand": "Keep", "category": "哑铃",
             "description": "Keep入门哑铃，5kg适合女性和健身新手，烤漆铸铁耐用，防滑包胶手感舒适，居家锻炼手臂肩部必备。"},
        ],
        "弹力带": [
            {"product_id": "jd_match_band_01", "title": "奥义 弹力带套装 5条装 深蹲翘臀",
             "price": 59.0, "rating": 4.8, "sales": "月销4.6万",
             "key_specs": "5条/乳胶/5种阻力/防滚动/便携收纳袋", "brand": "奥义", "category": "弹力带",
             "description": "奥义弹力带5条套装，5种阻力级别从轻到重循序渐进，乳胶材质弹性强不变形，防滚动宽版贴合腿部，深蹲臀部训练神器。"},
            {"product_id": "jd_match_band_01b", "title": "Keep 弹力带 3条装 轻中重阻力",
             "price": 39.0, "rating": 4.7, "sales": "月销3.2万",
             "key_specs": "3条/乳胶/轻中重/防滑/适合初学者", "brand": "Keep", "category": "弹力带",
             "description": "Keep弹力带3条装，轻中重三档覆盖健身全阶段，乳胶弹性持久耐用，不滚动宽版贴合舒适，初学者居家健身入门首选。"},
        ],
        "运动跳绳": [
            {"product_id": "jd_match_skippingrope_01", "title": "Keep 智能跳绳 计数 无绳磁力",
             "price": 99.0, "rating": 4.8, "sales": "月销8.9万",
             "key_specs": "智能计数/无绳磁力版/App联动/可调长度/室内专属", "brand": "Keep", "category": "跳绳",
             "description": "Keep智能跳绳，App实时同步数据记录运动量，无绳磁力版适合室内有限空间，自动计数无需手动记录。"},
            {"product_id": "jd_match_skippingrope_01b", "title": "火速 培林钢丝竞速跳绳 专业级",
             "price": 39.0, "rating": 4.8, "sales": "月销6.2万",
             "key_specs": "培林轴承/钢丝绳/可调节/竞速/防缠绕", "brand": "火速", "category": "跳绳",
             "description": "培林轴承钢丝跳绳，极速顺滑旋转，可调长度适配不同身高，竞速训练必备，性价比极高。"},
        ],
        "泡沫轴": [
            {"product_id": "jd_match_foamroll_01", "title": "奥义 EPP高密度泡沫轴 45cm 肌肉放松",
             "price": 79.0, "rating": 4.8, "sales": "月销2.1万",
             "key_specs": "EPP高密度/45cm/颗粒按摩纹/1kg/耐压800kg", "brand": "奥义", "category": "泡沫轴",
             "description": "奥义EPP高密度泡沫轴，颗粒按摩纹深层放松肌筋膜，耐压800kg不变形，训练前热身训练后拉伸均适用。"},
        ],
        "运动手环": [
            {"product_id": "jd_match_sportsband_01", "title": "小米手环8 Pro 运动健康追踪",
             "price": 299.0, "rating": 4.8, "sales": "月销5.6万",
             "key_specs": "1.74寸AMOLED/血氧心率/150+运动/14天续航/防水", "brand": "小米", "category": "运动手环",
             "description": "小米手环8 Pro，全天血氧心率监测，150+运动模式覆盖健身跑步游泳，14天续航减少充电烦恼，健身数据记录必备。"},
            {"product_id": "jd_match_sportsband_01b", "title": "华为手环8 NFC版 智能健身追踪",
             "price": 349.0, "rating": 4.8, "sales": "月销3.8万",
             "key_specs": "1.47寸AMOLED/血氧心率睡眠/100+运动/NFC/14天续航", "brand": "华为", "category": "运动手环",
             "description": "华为手环8 NFC版，血氧心率睡眠全面监测，100+专业运动模式，NFC门禁公交支付，14天续航，华为生态用户运动伴侣。"},
        ],
    },
    "treadmill": {  # 跑步机搭配
        "运动垫": [
            {"product_id": "jd_match_mat_01", "title": "澳洲狮 跑步机专用减震垫 185×90cm",
             "price": 199.0, "rating": 4.8, "sales": "月销2.1万",
             "key_specs": "NBR材质/185×90cm/8mm厚/防滑防震", "brand": "澳洲狮", "category": "运动垫",
             "description": "跑步机专用减震垫，有效降低噪音，保护地板，185×90cm完美适配大多数跑步机。"},
            {"product_id": "jd_match_mat_01b", "title": "奥义 跑步机减震垫 200×100cm 加大加厚",
             "price": 259.0, "rating": 4.7, "sales": "月销1.3万",
             "key_specs": "NBR/200×100cm/10mm/超厚减震/防滑纹/易清洁", "brand": "奥义", "category": "运动垫",
             "description": "奥义加大加厚跑步机垫，200×100cm覆盖面积更大保护地板全面，10mm超厚NBR大幅降低震动噪音，适合公寓楼层隔音需求。"},
        ],
        "风扇": [
            {"product_id": "jd_match_fan_01", "title": "戴森 TP07 塔式风扇 无叶设计",
             "price": 2899.0, "rating": 4.9, "sales": "月销3500",
             "key_specs": "无叶/AM技术/270°摆头/净化PM2.5", "brand": "戴森", "category": "风扇",
             "description": "戴森塔式无叶风扇，气流平稳静音，适合运动时使用，附带空气净化功能。"},
            {"product_id": "jd_match_fan_01b", "title": "艾美特 落地扇 静音直流变频",
             "price": 399.0, "rating": 4.7, "sales": "月销1.2万",
             "key_specs": "直流变频/12档风速/遥控/静音26dB/定时/摆头", "brand": "艾美特", "category": "风扇",
             "description": "艾美特直流变频落地扇，12档风速精细调节，最低静音26dB，遥控操作，运动降温或日常使用均舒适。"},
            {"product_id": "jd_match_fan_01c", "title": "小米 DC变频落地扇 1X 智能",
             "price": 299.0, "rating": 4.8, "sales": "月销2.8万",
             "key_specs": "DC变频/100档风速/米家APP/语音控制/静音/定时", "brand": "小米", "category": "风扇",
             "description": "小米DC变频落地扇，100档无级风速调节，米家APP远程控制，运动时手机随时调风速，低至28dB静音，高性价比智能风扇。"},
        ],
        "运动水壶": [
            {"product_id": "jd_match_bottle_02", "title": "特百惠 运动水壶 1L 大容量",
             "price": 129.0, "rating": 4.8, "sales": "月销2.8万",
             "key_specs": "Tritan/1L/防漏/刻度线", "brand": "特百惠", "category": "运动水壶",
             "description": "1L大容量运动水壶，适合长时间锻炼补水，Tritan耐摔材质安全无味。"},
            {"product_id": "jd_match_bottle_02b", "title": "Stanley 运动水壶 1L 不锈钢保温",
             "price": 199.0, "rating": 4.8, "sales": "月销1.8万",
             "key_specs": "304不锈钢/1L/12h保冷/防漏/宽口易清洗/终身保修", "brand": "Stanley", "category": "运动水壶",
             "description": "Stanley不锈钢运动水壶，12小时保冷让跑步过程中喝到冰凉饮料，宽口设计方便加冰块清洗，终身保修品质保证。"},
        ],
        "运动耳机": [
            {"product_id": "jd_match_earphone_trd", "title": "Jabra Elite 4 Active 防水运动耳机",
             "price": 299.0, "rating": 4.8, "sales": "月销9500",
             "key_specs": "IP57防水/主动降噪/7h续航/4麦克风/运动稳固", "brand": "Jabra", "category": "运动耳机",
             "description": "Jabra Elite 4 Active专为运动设计，IP57防水防汗，跑步时稳固不掉落，降噪让你专注训练。"},
            {"product_id": "jd_match_earphone_trd_b", "title": "韶音 OpenRun Pro 骨传导运动耳机",
             "price": 999.0, "rating": 4.8, "sales": "月销2.1万",
             "key_specs": "骨传导/IP55/10h续航/快充5min/开放耳不入耳", "brand": "韶音", "category": "运动耳机",
             "description": "韶音OpenRun Pro骨传导耳机，不入耳设计跑步时能听到环境声更安全，IP55防水，10小时续航，5分钟快充补足1.5小时，跑步神器。"},
        ],
        "心率带": [
            {"product_id": "jd_match_heartrate_01", "title": "Polar H10 心率带 专业运动监测",
             "price": 499.0, "rating": 4.9, "sales": "月销4200",
             "key_specs": "ECG精度/蓝牙5.0/ANT+/防水/可连跑步机App", "brand": "Polar", "category": "心率带",
             "description": "Polar H10专业心率带，ECG心电精度远超光学手环，双模蓝牙ANT+连接跑步机和运动App，游泳跑步综合运动监测。"},
        ],
        "运动手环": [
            {"product_id": "jd_match_band_trd", "title": "小米手环8 Pro 运动健身追踪",
             "price": 299.0, "rating": 4.8, "sales": "月销5.6万",
             "key_specs": "1.74寸AMOLED/血氧心率/150+运动模式/14天续航/防水", "brand": "小米", "category": "运动手环",
             "description": "小米手环8 Pro，1.74寸大屏显示，全天血氧心率监测，150+运动模式覆盖跑步游泳骑行，14天超长续航。"},
            {"product_id": "jd_match_band_trd_b", "title": "Garmin Forerunner 165 跑步智能手表",
             "price": 1699.0, "rating": 4.9, "sales": "月销6800",
             "key_specs": "AMOLED/GPS/心率血氧/训练建议/7天续航/跑步专项分析", "brand": "Garmin", "category": "运动手环",
             "description": "Garmin Forerunner 165跑步专项GPS手表，内置GPS精准轨迹，训练负荷分析和恢复建议，AMOLED高清屏，7天续航，跑者进阶必备。"},
        ],
        "防护膝盖": [
            {"product_id": "jd_match_kneepad_01", "title": "李宁 跑步护膝 半月板保护 2只装",
             "price": 89.0, "rating": 4.7, "sales": "月销3.4万",
             "key_specs": "弹力编织/加压支撑/透气/男女通用/S-XL", "brand": "李宁", "category": "护膝",
             "description": "李宁跑步护膝，弹力编织加压设计保护半月板，透气面料长跑不闷热，男女通用多尺寸可选，跑步马拉松必备。"},
            {"product_id": "jd_match_kneepad_01b", "title": "迪卡侬 跑步护膝 髌骨加压 减震",
             "price": 69.0, "rating": 4.7, "sales": "月销2.8万",
             "key_specs": "髌骨加压圈/硅胶垫/透气/单只装/轻薄", "brand": "迪卡侬", "category": "护膝",
             "description": "迪卡侬跑步护膝，硅胶髌骨加压圈精准保护膝关节，减少跑步冲击，轻薄透气不影响活动，性价比运动护膝入门首选。"},
        ],
    },
    "office": {  # 居家办公搭配
        "台灯": [
            {"product_id": "jd_match_office_lamp_01", "title": "明基 WiT MindDuo 护眼台灯 白色",
             "price": 699.0, "rating": 4.9, "sales": "月销6800",
             "key_specs": "无蓝光/无频闪/宽照面/自动感应/AA级", "brand": "明基", "category": "台灯",
             "description": "明基MindDuo护眼台灯，宽大照明面积，无蓝光无频闪，感应调光，长时间办公保护眼睛。"},
            {"product_id": "jd_match_office_lamp_01b", "title": "飞利浦 66161 DC调光台灯 无频闪",
             "price": 179.0, "rating": 4.8, "sales": "月销2.3万",
             "key_specs": "DC直流调光/无频闪/无蓝光/AA级/5档色温/触控", "brand": "飞利浦", "category": "台灯",
             "description": "飞利浦66161 DC调光台灯，直流调光从根本消除频闪，无蓝光认证，5档色温满足工作学习休息，性价比护眼台灯首选。"},
        ],
        "键盘": [
            {"product_id": "jd_match_keyboard_01", "title": "Keychron K2 V2 机械键盘 热插拔 三模",
             "price": 499.0, "rating": 4.9, "sales": "月销9800",
             "key_specs": "75%配列/热插拔/蓝牙+USB/RGB/Mac Win双系统", "brand": "Keychron", "category": "键盘",
             "description": "Keychron K2 V2，75%紧凑布局节省桌面，三模无线，铝合金机身坚固，Mac/Win双系统键位，居家办公旗舰之选。"},
            {"product_id": "jd_match_keyboard_01b", "title": "罗技 MK470 无线薄膜键盘 静音办公",
             "price": 249.0, "rating": 4.8, "sales": "月销2.3万",
             "key_specs": "剪刀脚/无线/静音/1年续航/轻薄/Mac Win兼容", "brand": "罗技", "category": "键盘",
             "description": "罗技MK470无线薄膜键盘，剪刀脚按键手感舒适，静音打字不扰人，1年超长电池续航，轻薄设计节省桌面空间。"},
        ],
        "鼠标": [
            {"product_id": "jd_match_mouse_01", "title": "罗技 MX Master 3S 无线鼠标 人体工学",
             "price": 499.0, "rating": 4.9, "sales": "月销8600",
             "key_specs": "8K DPI/电磁滚轮/静音/人体工学/多设备切换", "brand": "罗技", "category": "鼠标",
             "description": "罗技MX Master 3S旗舰鼠标，电磁滚轮极速翻页，静音点击，人体工学右手设计，多设备无缝切换。"},
            {"product_id": "jd_match_mouse_01b", "title": "雷蛇 DeathAdder V3 人体工学鼠标 59g",
             "price": 349.0, "rating": 4.8, "sales": "月销7400",
             "key_specs": "30K DPI/59g超轻/人体工学/Focus Pro传感器/有线", "brand": "雷蛇", "category": "鼠标",
             "description": "雷蛇DeathAdder V3，59g超轻人体工学设计减轻手腕疲劳，Focus Pro 30K传感器精准响应，适合长时间办公和游戏。"},
        ],
        "显示器": [
            {"product_id": "jd_match_monitor_01", "title": "LG 27GP850 27寸 2K IPS 165Hz 电竞显示器",
             "price": 1899.0, "rating": 4.9, "sales": "月销7200",
             "key_specs": "27寸/2K/IPS/165Hz/1ms/HDR400/USB-C", "brand": "LG", "category": "显示器",
             "description": "LG 27GP850，27寸2K高分辨率，IPS广色域，165Hz高刷新，1ms响应，办公游戏两不误，支持USB-C一线连接。"},
            {"product_id": "jd_match_monitor_01b", "title": "小米 23.8寸 IPS 显示器 全面屏 办公款",
             "price": 799.0, "rating": 4.8, "sales": "月销1.4万",
             "key_specs": "23.8寸/1080P/IPS/75Hz/超薄边框/低蓝光", "brand": "小米", "category": "显示器",
             "description": "小米23.8寸全面屏显示器，IPS广色域色彩准确，低蓝光认证护眼，超薄边框视野开阔，性价比极高的办公首选。"},
            {"product_id": "jd_match_monitor_01c", "title": "戴尔 S2722DC 27寸 2K USB-C显示器",
             "price": 1699.0, "rating": 4.9, "sales": "月销8500",
             "key_specs": "27寸/2K/IPS/USB-C 65W充电/75Hz/广色域/超薄边框", "brand": "戴尔", "category": "显示器",
             "description": "戴尔S2722DC，27寸2K IPS，USB-C接口支持65W快充一线连接笔记本，广色域色彩准确，办公创意旗舰首选。"},
        ],
        "桌面收纳": [
            {"product_id": "jd_match_deskorg_01", "title": "得力 桌面收纳盒套装 6件套 办公整理",
             "price": 89.0, "rating": 4.7, "sales": "月销5.6万",
             "key_specs": "6件套/笔筒+文件架+抽屉/透明/防滑底", "brand": "得力", "category": "桌面收纳",
             "description": "得力桌面收纳套装，笔筒文件架抽屉组合，透明材质一目了然，防滑底座稳固，办公桌面整洁必备。"},
            {"product_id": "jd_match_deskorg_01b", "title": "北欧风木质桌面收纳架 多格置物",
             "price": 128.0, "rating": 4.8, "sales": "月销3.2万",
             "key_specs": "松木/多格/笔筒+书立+置物盒/天然木纹/无漆环保", "brand": "木趣家", "category": "桌面收纳",
             "description": "松木桌面收纳架，天然木纹无漆环保，多格组合摆放手机笔记本本子杂物，简约北欧风格，办公书房颜值升级必备。"},
        ],
        "鼠标垫": [
            {"product_id": "jd_match_mousepad_01", "title": "罗技 G240 专业游戏鼠标垫 布面大号",
             "price": 99.0, "rating": 4.8, "sales": "月销3.2万",
             "key_specs": "340×280mm/布面/防滑橡胶底/耐用/易清洁", "brand": "罗技", "category": "鼠标垫",
             "description": "罗技G240布面鼠标垫，精密纹理控制移动速度，防滑橡胶底座稳固，机洗不变形，游戏办公两用。"},
            {"product_id": "jd_match_mousepad_01b", "title": "电竞超大鼠标垫 900×400mm 全桌覆盖",
             "price": 79.0, "rating": 4.7, "sales": "月销4.8万",
             "key_specs": "900×400mm/布面/3mm厚/防滑底/包边耐用/多色", "brand": "雷神", "category": "鼠标垫",
             "description": "超大900×400mm全桌鼠标垫，同时覆盖键盘鼠标区域，布面丝滑，3mm厚底垫腕部，防滑橡胶底不位移，桌面整洁颜值高。"},
        ],
        "人体工学椅": [
            {"product_id": "jd_match_chair_01", "title": "西昊 M57 人体工学椅 入门款",
             "price": 799.0, "rating": 4.7, "sales": "月销2.1万",
             "key_specs": "2D扶手/腰托/透气网背/可躺120°", "brand": "西昊", "category": "椅子",
             "description": "西昊M57入门款，高性价比，腰托扶手配置齐全，透气网背久坐舒适，居家办公好伙伴。"},
            {"product_id": "jd_match_chair_01b", "title": "西昊 Doro C300 人体工学椅 4D扶手",
             "price": 1499.0, "rating": 4.9, "sales": "月销1.2万",
             "key_specs": "4D扶手/独立腰托/透气网背/可躺130°/5年保修", "brand": "西昊", "category": "椅子",
             "description": "西昊C300，4D全向扶手精准支撑手臂，独立腰托贴合脊椎，全透气网面久坐不闷热，5年保修，居家办公旗舰之选。"},
        ],
        "桌面升降架": [
            {"product_id": "jd_match_riser_01", "title": "北弧 显示器支架 铝合金 旋转升降",
             "price": 199.0, "rating": 4.8, "sales": "月销6800",
             "key_specs": "铝合金/升降旋转/17-32寸/承重8kg/VESA/含USB Hub", "brand": "北弧", "category": "显示器支架",
             "description": "北弧铝合金显示器支架，高度旋转俯仰全自由调节，承重8kg，含2口USB Hub方便接外设，节省桌面空间提升颈椎健康。"},
            {"product_id": "jd_match_riser_01b", "title": "乐歌 笔记本支架 桌面增高 铝合金折叠",
             "price": 149.0, "rating": 4.8, "sales": "月销4.5万",
             "key_specs": "铝合金/折叠便携/6档高度/防滑散热/通用笔记本", "brand": "乐歌", "category": "笔记本支架",
             "description": "乐歌铝合金折叠笔记本支架，6档高度调节找到最舒适视角，防滑硅胶垫固定，散热镂空设计降温，折叠薄片携带方便。"},
        ],
    },
    "outdoor": {  # 户外露营搭配
        "帐篷": [
            {"product_id": "jd_match_tent_01", "title": "牧高笛 凉山1V2 双人帐篷 速开",
             "price": 399.0, "rating": 4.8, "sales": "月销8900",
             "key_specs": "双人/速开30s/防水2000mm/双层/4季通用", "brand": "牧高笛", "category": "帐篷",
             "description": "牧高笛凉山速开帐篷，30秒快速搭建，2000mm防水，双层透气结构，2-3人露营野餐均适用。"},
            {"product_id": "jd_match_tent_01b", "title": "挪客 云尚Plus 超轻双人帐篷 1.3kg",
             "price": 599.0, "rating": 4.8, "sales": "月销5600",
             "key_specs": "铝合金杆/1.3kg/3000mm防水/双门双窗/2人", "brand": "挪客", "category": "帐篷",
             "description": "挪客云尚Plus仅1.3kg超轻，铝合金支撑杆3000mm高防水，双门双窗通风良好，徒步背包客首选帐篷。"},
            {"product_id": "jd_match_tent_01c", "title": "牧高笛 冷山Air 3人帐篷 充气速搭",
             "price": 1299.0, "rating": 4.8, "sales": "月销3200",
             "key_specs": "充气框架/30s速搭/3人/3000mm/双层/含气泵", "brand": "牧高笛", "category": "帐篷",
             "description": "牧高笛充气帐篷，无需撑杆打气30秒立起来，3人宽敞，3000mm高防水，家庭露营轻松设营神器。"},
        ],
        "睡袋": [
            {"product_id": "jd_match_sleepbag_01", "title": "探路者 鸭绒睡袋 -5℃ 户外成人",
             "price": 599.0, "rating": 4.8, "sales": "月销5600",
             "key_specs": "-5℃极限/-15℃舒适/650g鸭绒/可拼接/压缩包", "brand": "探路者", "category": "睡袋",
             "description": "探路者鸭绒睡袋，-5℃舒适适温，650g优质鸭绒填充保暖性强，两个可拼接成双人袋，压缩后体积小便于携带。"},
            {"product_id": "jd_match_sleepbag_01b", "title": "迪卡侬 棉睡袋 10℃ 单人 轻量",
             "price": 199.0, "rating": 4.7, "sales": "月销3.1万",
             "key_specs": "10℃舒适/棉填充/1.3kg/压缩袋/拉链全开/单人", "brand": "迪卡侬", "category": "睡袋",
             "description": "迪卡侬棉睡袋，10℃适温春秋季露营，棉填充亲肤舒适，拉链全开可当被子用，价格实惠是露营入门首选。"},
        ],
        "折叠椅": [
            {"product_id": "jd_match_campchair_01", "title": "Helinox Chair One 超轻折叠椅 户外",
             "price": 799.0, "rating": 4.9, "sales": "月销3200",
             "key_specs": "超轻960g/铝合金/折叠/承重145kg/收纳袋", "brand": "Helinox", "category": "折叠椅",
             "description": "Helinox Chair One顶级轻量折叠椅，仅960g轻盈，铝合金架稳固承重145kg，10秒快速展开，徒步露营必备神器。"},
            {"product_id": "jd_match_campchair_01b", "title": "Coleman 折叠椅 带扶手杯架 户外露营",
             "price": 199.0, "rating": 4.7, "sales": "月销1.5万",
             "key_specs": "钢管/带杯架/承重113kg/折叠/牛津布", "brand": "Coleman", "category": "折叠椅",
             "description": "Coleman经典折叠椅，自带杯架方便喝饮料，牛津布坐面耐脏耐磨，钢管框架稳固，性价比高的露营椅之选。"},
            {"product_id": "jd_match_campchair_01c", "title": "挪客 蛋卷椅 铝合金折叠椅 带头枕",
             "price": 399.0, "rating": 4.8, "sales": "月销6800",
             "key_specs": "铝合金/带头枕/1.8kg/可躺/承重120kg/收纳袋", "brand": "挪客", "category": "折叠椅",
             "description": "挪客蛋卷椅，可调靠背角度适合小憩，带头枕托住颈部，铝合金轻量，承重120kg，营地休闲必备舒适座椅。"},
        ],
        "户外灯": [
            {"product_id": "jd_match_camplight_01", "title": "Black Diamond Moji 帐篷营地灯",
             "price": 169.0, "rating": 4.8, "sales": "月销4100",
             "key_specs": "100流明/可调光/磁吸/IPX4/3节AA电池/轻量", "brand": "Black Diamond", "category": "户外灯",
             "description": "Black Diamond Moji营地灯，100流明照亮帐篷，磁吸底座随处悬挂，无级调光，IPX4防水，AA电池方便更换。"},
            {"product_id": "jd_match_camplight_01b", "title": "Goal Zero Crush Light 折叠营地灯",
             "price": 129.0, "rating": 4.7, "sales": "月销5600",
             "key_specs": "折叠收纳/太阳能+USB充电/150流明/防水/轻量50g", "brand": "Goal Zero", "category": "户外灯",
             "description": "Goal Zero折叠营地灯，太阳能和USB双充电方式，150流明照亮帐篷，折叠后仅一张CD大小极省空间，50g超轻，徒步必带。"},
            {"product_id": "jd_match_camplight_01c", "title": "NPET 充电营地灯 暖白冷白双色 挂绳",
             "price": 79.0, "rating": 4.7, "sales": "月销2.8万",
             "key_specs": "USB充电/暖白冷白/300流明/挂绳/防水/超长续航", "brand": "NPET", "category": "户外灯",
             "description": "NPET USB充电营地灯，暖白冷白两种色温，300流明够亮，自带挂绳悬挂帐篷顶，防水防尘，超长续航露营全程覆盖，性价比超高。"},
        ],
        "保温壶": [
            {"product_id": "jd_match_thermos_outdoor", "title": "Stanley 探险系列 保温壶 1L 军绿色",
             "price": 399.0, "rating": 4.9, "sales": "月销7800",
             "key_specs": "1L/18/8不锈钢/24h保温/耐摔/终身保修", "brand": "Stanley", "category": "保温壶",
             "description": "Stanley经典探险保温壶1L，24小时保温，18/8不锈钢坚固耐摔，终身保修承诺，军绿色户外风十足，露营徒步必带。"},
            {"product_id": "jd_match_thermos_outdoor_b", "title": "虎牌 MTH-A080 户外保温壶 800ml",
             "price": 279.0, "rating": 4.8, "sales": "月销4600",
             "key_specs": "800ml/真空双层/24h保温/一键开盖/防摔涂层/轻量", "brand": "虎牌", "category": "保温壶",
             "description": "虎牌户外保温壶，24小时实测保温效果优秀，一键弹盖单手操作，防摔涂层耐磨，800ml容量满足户外全天补水需求。"},
        ],
        "防潮垫": [
            {"product_id": "jd_match_groundpad_01", "title": "牧高笛 XPE防潮垫 加厚1cm 折叠",
             "price": 89.0, "rating": 4.7, "sales": "月销2.8万",
             "key_specs": "XPE材质/1cm厚/折叠/180×60cm/防水/可擦洗", "brand": "牧高笛", "category": "防潮垫",
             "description": "牧高笛XPE防潮垫，加厚1cm隔绝地面寒气，折叠便携不占空间，防水易擦洗，露营野餐均适用。"},
            {"product_id": "jd_match_groundpad_01b", "title": "挪客 自充气防潮垫 3cm 双人加宽",
             "price": 299.0, "rating": 4.8, "sales": "月销8900",
             "key_specs": "自充气/3cm/130×200cm双人/可机洗/R值3.4/打包袋", "brand": "挪客", "category": "防潮垫",
             "description": "挪客自充气双人防潮垫，打开气阀自动充气，3cm厚度R值3.4保暖性强，130cm宽够两人睡，比XPE垫舒适度大幅提升。"},
        ],
        "背包": [
            {"product_id": "jd_match_backpack_outdoor", "title": "Gregory Baltoro 65 登山包 65L",
             "price": 2599.0, "rating": 4.9, "sales": "月销1800",
             "key_specs": "65L/符合人体曲线背架/雨罩/隔层/防水", "brand": "Gregory", "category": "背包",
             "description": "Gregory Baltoro 65专业登山包，Response A3背负系统完美贴合背部曲线，65L大容量多隔层，附带防雨罩，多日徒步首选。"},
            {"product_id": "jd_match_backpack_outdoor_b", "title": "牧高笛 登山包 40L 轻量徒步",
             "price": 499.0, "rating": 4.7, "sales": "月销4200",
             "key_specs": "40L/防泼水/透气背架/雨罩/多隔层/1.2kg", "brand": "牧高笛", "category": "背包",
             "description": "牧高笛40L徒步登山包，防泼水面料，透气背架减少背部出汗，多功能隔层整理方便，1.2kg轻量不给你增加负担，一日或周末徒步理想之选。"},
        ],
        "炊具": [
            {"product_id": "jd_match_cookware_01", "title": "MSR PocketRocket 2 超轻户外炉头",
             "price": 299.0, "rating": 4.8, "sales": "月销6800",
             "key_specs": "73g超轻/折叠/通用气罐/1L水3.5min沸腾/高海拔", "brand": "MSR", "category": "炉头",
             "description": "MSR PocketRocket 2超轻户外炉头，仅73g，折叠收纳成拇指大小，3.5分钟烧开1L水，高海拔低温性能稳定，背包客神器。"},
            {"product_id": "jd_match_cookware_01b", "title": "火枫 蜘蛛II 一体炉套锅 户外烹饪",
             "price": 399.0, "rating": 4.8, "sales": "月销4500",
             "key_specs": "一体炉+锅套装/防风/集热技术/1.3L锅/含收纳袋", "brand": "火枫", "category": "套锅",
             "description": "火枫蜘蛛II一体炉套锅，集热技术提升燃烧效率节省气罐，防风性能好，1.3L锅足够两人用，收纳后紧凑，露营烹饪全套解决方案。"},
        ],
    },
}


MATCHING_PRODUCT_ALIASES = {
    "jd_match_yoga_01": "jd_lululemon_themat",
    "jd_match_dumbbell_01b": "jd_keep_dumbbell_5kg",
    "jd_match_band_01b": "jd_keep_band_3pack",
    "jd_match_earphone_trd": "jd_jabra_elite4_active",
    "jd_match_office_lamp_01b": "jd_philips_dc_study",
    "jd_match_keyboard_01": "jd_keychron_k2_v2",
    "jd_match_monitor_01": "jd_lg_27gp850",
    "jd_match_monitor_01c": "jd_dell_s2722dc",
    "jd_match_campchair_01": "jd_helinox_chair_one",
    "jd_match_band_trd": "jd_match_sportsband_01",
}


def _synchronize_matching_product_aliases() -> None:
    products_by_id = {
        str(product["product_id"]): product
        for products in MOCK_PRODUCTS.values()
        for product in products
    }
    for style_pool in MATCHING_PRODUCTS.values():
        for products in style_pool.values():
            for product in products:
                products_by_id.setdefault(str(product["product_id"]), product)
    for style_pool in MATCHING_PRODUCTS.values():
        for products in style_pool.values():
            for index, product in enumerate(products):
                canonical_id = MATCHING_PRODUCT_ALIASES.get(str(product["product_id"]))
                if not canonical_id:
                    continue
                canonical = products_by_id[canonical_id]
                products[index] = {
                    **canonical,
                    "product_id": canonical_id,
                    "category": product.get("category", canonical.get("category", "")),
                }


_synchronize_matching_product_aliases()


# ─────────────────────────────────────────────────────────────────────────────
# 工具执行函数
# ─────────────────────────────────────────────────────────────────────────────
def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    site_context: Any = None,
) -> Dict[str, Any]:
    """根据工具名分发执行，返回 Mock 结果"""
    handlers = {
        "sku_recall":             _sku_recall,
        "similar_sku_recommend":  _similar_sku_recommend,
        "calculate_budget":       _calculate_budget,
        "scenario_related_recall": _scenario_related_recall,
    }
    handler = handlers.get(tool_name)
    if not handler:
        return {"status": "ERROR", "message": f"未知工具: {tool_name}"}
    try:
        if tool_name in {
            "sku_recall", "similar_sku_recommend", "scenario_related_recall",
            "calculate_budget",
        }:
            return handler(site_context=site_context, **arguments)
        return handler(**arguments)
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


def _similar_sku_recommend(
    original_desc: str,
    pain_point: str,
    category: str,
    max_price: float = 0,
    min_price: float = 0,
    page_size: int = 5,
    site_context: Any = None,
) -> Dict:
    """相似品替换推荐：基于痛点搜索同类更好的商品"""
    max_price = float(max_price or 0)
    min_price = float(min_price or 0)
    page_size = int(page_size or 5)
    site_config = resolve_site_config(site_context)
    price_unit = str(site_config["currency_symbol"]) if site_config else "元"
    language = site_config["site_lang_code"] if site_config else "zh_CN"
    constraints = []
    if min_price > 0:
        constraints.append({
            "zh_CN": f"{min_price:g}元以上",
            "en_GB": f"over {price_unit}{min_price:g}",
            "de_DE": f"über {price_unit}{min_price:g}",
            "fr_FR": f"plus de {price_unit}{min_price:g}",
            "nl_NL": f"boven {price_unit}{min_price:g}",
        }[language])
    if max_price > 0:
        constraints.append({
            "zh_CN": f"{max_price:g}元以内",
            "en_GB": f"under {price_unit}{max_price:g}",
            "de_DE": f"unter {price_unit}{max_price:g}",
            "fr_FR": f"moins de {price_unit}{max_price:g}",
            "nl_NL": f"onder {price_unit}{max_price:g}",
        }[language])
    recall_query = " ".join([category, pain_point, *constraints]).strip()
    result = _sku_recall(query=recall_query, site_context=site_context)
    products = result["products"][:page_size]
    reason_templates = {
        "zh_CN": f"针对「{pain_point}」问题，从{len(products)}款{category}中筛选推荐",
        "en_GB": f"Selected {len(products)} {category} alternatives for the issue: {pain_point}",
        "de_DE": f"{len(products)} Alternativen für {category} zum Problem „{pain_point}“ ausgewählt",
        "fr_FR": f"{len(products)} alternatives de type {category} sélectionnées pour le problème « {pain_point} »",
        "nl_NL": f"{len(products)} alternatieven voor {category} geselecteerd voor het probleem ‘{pain_point}’",
    }
    return {
        "status":        "SUCCESS",
        "original_desc": original_desc,
        "pain_point":    pain_point,
        "category":      category,
        "count":         len(products),
        "products":      products,
        "recommend_reason": reason_templates[language],
    }


def normalize_recall_query(query: str) -> Dict[str, Any]:
    """Normalize a multilingual shopping query into deterministic retrieval constraints."""
    normalized_query = _normalize_search_text(query)
    category = None
    category_aliases = {
        category_key: list(aliases)
        for category_key, aliases in QUERY_LEVEL_MOCK_CATEGORY_ALIASES.items()
    }
    for category_key, aliases in MULTILINGUAL_CATEGORY_ALIASES.items():
        category_aliases.setdefault(category_key, []).extend(aliases)
    for category_key, display_names in CATEGORY_DISPLAY_NAMES.items():
        category_aliases.setdefault(category_key, []).extend(
            [category_key, *display_names.values()]
        )

    category = _longest_alias_match(
        normalized_query,
        list(category_aliases.items()),
    )
    if category is None and (
        re.search(r"\bmulti[- ]?tools?\b", normalized_query)
        or re.search(r"\bmultifunktion\w*(?:tool|werkzeug)\w*\b", normalized_query)
    ):
        category = "多功能工具"

    screen_size = None
    screen_size_min = None
    screen_size_max = None
    screen_unit = r"(?:-?\s*inch(?:es)?|in\b|寸|zoll|pouces?)"
    size_range_match = re.search(
        rf"\b(\d{{2,3}}(?:\.\d+)?)\s*[-–—~]\s*"
        rf"(\d{{2,3}}(?:\.\d+)?)\s*{screen_unit}",
        normalized_query,
    )
    if size_range_match:
        screen_size_min, screen_size_max = sorted(
            (float(size_range_match.group(1)), float(size_range_match.group(2)))
        )
    else:
        size_min_match = re.search(
            rf"(?:at least|minimum|minum|mindestens|au moins|minstens|ten minste|至少)\s*"
            rf"(\d{{2,3}}(?:\.\d+)?)\s*{screen_unit}",
            normalized_query,
        )
        if size_min_match:
            screen_size_min = float(size_min_match.group(1))
        else:
            size_match = re.search(
                rf"\b(\d{{2,3}}(?:\.\d+)?)\s*{screen_unit}",
                normalized_query,
            )
            if size_match:
                screen_size = float(size_match.group(1))
            elif category == "电视":
                bare_tv_size = re.search(
                    r"(?:tv|television|televiseur|fernseher|televisie|电视)"
                    r"(?:\s+[a-z]+){0,3}\s+(\d{2,3})\b",
                    normalized_query,
                )
                if bare_tv_size and 40 <= float(bare_tv_size.group(1)) <= 100:
                    screen_size = float(bare_tv_size.group(1))

    constraints = []
    for constraint, aliases in MULTILINGUAL_CONSTRAINT_ALIASES.items():
        if any(_normalize_search_text(alias) in normalized_query for alias in aliases):
            constraints.append(constraint)

    brand = None
    for canonical_brand, aliases in BRAND_ALIASES.items():
        candidates = [canonical_brand, *aliases]
        if any(_search_alias_matches(normalized_query, alias) for alias in candidates):
            brand = canonical_brand
            break

    return {
        "raw_query": query,
        "normalized_query": normalized_query,
        "category": category,
        "brand": brand,
        "screen_size_inch": screen_size,
        "screen_size_min_inch": screen_size_min,
        "screen_size_max_inch": screen_size_max,
        "constraints": constraints,
    }


def is_generic_product_discovery_query(query: str) -> bool:
    normalized_query = _normalize_search_text(query)
    markers = (
        "bestseller", "best seller", "best selling", "top seller",
        "popular products", "trending products", "what is popular",
        "best deal", "best deals", "deal of the day", "deals today",
        "cheapest and best deal", "bonnes affaires", "meilleures ventes",
        "topseller", "angebote heute", "beste deal", "populaire producten",
        "热销商品", "畅销商品", "爆款", "今日好价", "最划算",
    )
    return any(_search_alias_matches(normalized_query, marker) for marker in markers)


def _filter_products_by_requested_screen_size(
    products: List[Dict[str, Any]],
    query: str,
) -> List[Dict[str, Any]]:
    intent = normalize_recall_query(query)
    requested_size = intent["screen_size_inch"]
    requested_min = intent["screen_size_min_inch"]
    requested_max = intent["screen_size_max_inch"]
    if requested_size is None and requested_min is None and requested_max is None:
        return products

    filtered = []
    for product in products:
        source = (
            f"{product.get('title', '')} {product.get('sku_name', '')} "
            f"{product.get('key_specs', '')}"
        )
        match = re.search(
            r"(?:^|\D)(\d{2,3}(?:\.\d+)?)\s*(?:寸|inch(?:es)?|in\b|zoll|pouces?|\")",
            source,
            re.IGNORECASE,
        )
        if not match:
            continue
        product_size = float(match.group(1))
        if requested_size is not None and product_size != requested_size:
            continue
        if requested_min is not None and product_size < requested_min:
            continue
        if requested_max is not None and product_size > requested_max:
            continue
        filtered.append(product)
    return filtered


def _filter_catalog_products_by_price(
    products: List[Dict[str, Any]],
    query: str,
    site_context: Any = None,
) -> List[Dict[str, Any]]:
    min_price, max_price = parse_requested_price_bounds(query)
    if not min_price and not max_price:
        return products
    site_config = resolve_site_config(site_context)
    if site_config and not re.search(r"(?:元|rmb|cny|[¥￥])", query, re.IGNORECASE):
        price_rate = float(site_config["price_rate"])
        if min_price > 0:
            min_price /= price_rate
        if max_price > 0:
            max_price /= price_rate
    filtered = []
    for product in products:
        price = float(product.get("price", product.get("final_price", 0)) or 0)
        if min_price > 0 and price < min_price:
            continue
        if max_price > 0 and price > max_price:
            continue
        filtered.append(product)
    return filtered


def _requested_measurements(text: str) -> List[tuple[str, float]]:
    normalized = _normalize_search_text(text).replace(",", ".")
    measurements = []
    pattern = re.compile(
        r"(?<![\d.])(\d+(?:\.\d+)?)\s*-?\s*"
        r"(millilit(?:er|re)s?|ml|lit(?:er|re)s?|l|毫升|升|mm|millimeters?|millimetres?|kg|kilograms?|kilogrammes?|g|grams?|grammes?)\b",
        re.IGNORECASE,
    )
    for value_text, unit_text in pattern.findall(normalized):
        value = float(value_text)
        unit = unit_text.lower()
        if unit in {"l", "liter", "liters", "litre", "litres", "升"}:
            measurements.append(("volume_ml", value * 1000))
        elif unit in {"ml", "milliliter", "milliliters", "millilitre", "millilitres", "毫升"}:
            measurements.append(("volume_ml", value))
        elif unit in {"mm", "millimeter", "millimeters", "millimetre", "millimetres"}:
            measurements.append(("length_mm", value))
        elif unit in {"kg", "kilogram", "kilograms", "kilogramme", "kilogrammes"}:
            measurements.append(("weight_g", value * 1000))
        else:
            measurements.append(("weight_g", value))
    return measurements


def _parse_localized_number(value_text: str) -> float:
    value_text = value_text.strip().replace(" ", "")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", value_text):
        return float(value_text.replace(".", "").replace(",", ""))
    if "," in value_text and "." not in value_text:
        value_text = value_text.replace(",", ".")
    return float(value_text)


def _minimum_product_specs(text: str) -> List[tuple[str, float]]:
    normalized = _normalize_search_text(text)
    minimum_cue = (
        r"(?:at least|minimum(?: of)?|mindestens|au moins|minstens|ten minste|"
        r"至少|不低于)"
    )
    unit_pattern = r"(?:mah|ma\s*(?:hours?|stunden)|w(?:att)?|gb|gbyte|go|btu|hz)"
    pattern = re.compile(
        rf"{minimum_cue}\s*(\d[\d.,]*)\s*({unit_pattern})\b",
        re.IGNORECASE,
    )
    requirements = []
    for value_text, unit_text in pattern.findall(normalized):
        value = _parse_localized_number(value_text)
        compact_unit = re.sub(r"\s+", "", unit_text.lower())
        if compact_unit.startswith("ma"):
            requirements.append(("capacity_mah", value))
        elif compact_unit.startswith("w"):
            requirements.append(("power_w", value))
        elif compact_unit in {"gb", "gbyte", "go"}:
            requirements.append(("storage_gb", value))
        elif compact_unit == "btu":
            requirements.append(("cooling_btu", value))
        else:
            requirements.append(("refresh_hz", value))
    suffix_pattern = re.compile(
        rf"(\d[\d.,]*)\s*({unit_pattern})\s*(?:\+|plus|or more|and above|以上)",
        re.IGNORECASE,
    )
    for value_text, unit_text in suffix_pattern.findall(normalized):
        value = _parse_localized_number(value_text)
        compact_unit = re.sub(r"\s+", "", unit_text.lower())
        kind = {
            "btu": "cooling_btu",
            "hz": "refresh_hz",
            "mah": "capacity_mah",
            "gb": "storage_gb",
            "gbyte": "storage_gb",
            "go": "storage_gb",
        }.get(compact_unit, "power_w")
        if (kind, value) not in requirements:
            requirements.append((kind, value))
    for value_text in re.findall(r"(?<!\d)(\d{3})\s*hz\b", normalized, re.IGNORECASE):
        value = float(value_text)
        if value >= 100 and ("refresh_hz", value) not in requirements:
            requirements.append(("refresh_hz", value))
    return requirements


def _available_product_specs(product: Dict[str, Any]) -> List[tuple[str, float]]:
    source = _normalize_search_text(
        f"{product.get('title', '')} {product.get('sku_name', '')} {product.get('key_specs', '')} "
        f"{product.get('description', '')}"
    )
    pattern = re.compile(
        r"(?<![\d.])(\d[\d.,]*)\s*(mah|w(?:att)?|gb|go|btu|hz)\b",
        re.IGNORECASE,
    )
    available = []
    for value_text, unit_text in pattern.findall(source):
        value = _parse_localized_number(value_text)
        unit = unit_text.lower()
        if unit == "mah":
            available.append(("capacity_mah", value))
        elif unit.startswith("w"):
            available.append(("power_w", value))
        elif unit in {"gb", "go"}:
            available.append(("storage_gb", value))
        elif unit == "btu":
            available.append(("cooling_btu", value))
        else:
            available.append(("refresh_hz", value))
    return available


def _exact_product_specs(text: str) -> List[tuple[str, float]]:
    if _minimum_product_specs(text):
        return []
    normalized = _normalize_search_text(text)
    pattern = re.compile(
        r"(?<![\d.])(\d[\d.,]*)\s*(mah|w(?:att)?|gb|gbyte|go|btu|hz)\b",
        re.IGNORECASE,
    )
    requested = []
    for value_text, unit_text in pattern.findall(normalized):
        value = _parse_localized_number(value_text)
        unit = unit_text.lower()
        if unit == "mah":
            requested.append(("capacity_mah", value))
        elif unit.startswith("w"):
            requested.append(("power_w", value))
        elif unit in {"gb", "gbyte", "go"}:
            requested.append(("storage_gb", value))
        elif unit == "btu":
            requested.append(("cooling_btu", value))
        elif unit != "hz":
            requested.append(("refresh_hz", value))
    return requested


def _filter_products_by_minimum_specs(
    products: List[Dict[str, Any]],
    query: str,
) -> List[Dict[str, Any]]:
    requirements = _minimum_product_specs(query)
    if not requirements:
        return products
    filtered = []
    for product in products:
        available = _available_product_specs(product)
        if all(
            any(
                available_kind == required_kind and available_value >= required_value
                for available_kind, available_value in available
            )
            for required_kind, required_value in requirements
        ):
            filtered.append(product)
    return filtered


def _filter_products_by_exact_specs(
    products: List[Dict[str, Any]],
    query: str,
) -> List[Dict[str, Any]]:
    requested = _exact_product_specs(query)
    if not requested:
        return products
    filtered = []
    for product in products:
        available = _available_product_specs(product)
        if all(
            any(
                available_kind == requested_kind
                and abs(available_value - requested_value) < 0.01
                for available_kind, available_value in available
            )
            for requested_kind, requested_value in requested
        ):
            filtered.append(product)
    return filtered


@lru_cache(maxsize=1)
def _raw_products_by_sku() -> Dict[str, Dict[str, Any]]:
    raw_by_sku = {}
    for catalog_products in MOCK_PRODUCTS.values():
        for product in catalog_products:
            raw_by_sku[_contract_sku_id(str(product.get("product_id", "")))] = product
    for style_pool in MATCHING_PRODUCTS.values():
        for catalog_products in style_pool.values():
            for product in catalog_products:
                raw_by_sku[_contract_sku_id(str(product.get("product_id", "")))] = product
    return raw_by_sku


def invalid_requested_spec_product_ids(
    query: str,
    products: Sequence[Dict[str, Any]],
) -> List[str]:
    minimum_requirements = _minimum_product_specs(query)
    exact_requirements = _exact_product_specs(query)
    if not minimum_requirements and not exact_requirements:
        return []
    raw_by_sku = _raw_products_by_sku()
    invalid = []
    for product in products:
        sku_id = str(product.get("sku_id", ""))
        source = raw_by_sku.get(sku_id) or product
        available = _available_product_specs(source)
        minimum_valid = all(
            any(
                available_kind == required_kind and available_value >= required_value
                for available_kind, available_value in available
            )
            for required_kind, required_value in minimum_requirements
        )
        exact_valid = all(
            any(
                available_kind == required_kind
                and abs(available_value - required_value) < 0.01
                for available_kind, available_value in available
            )
            for required_kind, required_value in exact_requirements
        )
        if not minimum_valid or not exact_valid:
            invalid.append(sku_id)
    return invalid


def _filter_products_by_requested_measurements(
    products: List[Dict[str, Any]],
    query: str,
) -> List[Dict[str, Any]]:
    requested = _requested_measurements(query)
    if not requested:
        return products
    filtered = []
    for product in products:
        source = f"{product.get('title', '')} {product.get('sku_name', '')} {product.get('key_specs', '')}"
        available = _requested_measurements(source)
        if all(
            any(kind == available_kind and abs(value - available_value) < 0.01
                for available_kind, available_value in available)
            for kind, value in requested
        ):
            filtered.append(product)
    return filtered


def _product_query_match_score(query: str, product: Dict[str, Any]) -> int:
    normalized_query = _normalize_search_text(query)
    normalized_source = _normalize_search_text(
        f"{product.get('title', '')} {product.get('key_specs', '')} {product.get('description', '')}"
    )
    score = 0
    for query_aliases, source_markers in PRODUCT_ATTRIBUTE_ALIASES:
        if any(_normalize_search_text(alias) in normalized_query for alias in query_aliases):
            if any(_normalize_search_text(marker) in normalized_source for marker in source_markers):
                score += 10
    for token in re.findall(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", normalized_query):
        if len(token) >= 3 and token in normalized_source:
            score += 1
    return score


def parse_requested_price_bounds(text: str) -> tuple[float, float]:
    normalized = text.lower().replace(",", "")
    min_price = 0.0
    max_price = 0.0
    range_match = re.search(
        r"(?:[¥￥$€£]\s*)?(\d+(?:\.\d+)?)\s*(?:元|块|rmb|cny)?\s*[-~至到]\s*"
        r"(?:[¥￥$€£]\s*)?(\d+(?:\.\d+)?)",
        normalized,
    )
    if range_match:
        range_text = range_match.group(0)
        context_start = max(0, range_match.start() - 24)
        context_end = min(len(normalized), range_match.end() + 24)
        range_context = normalized[context_start:context_end]
        has_currency = bool(re.search(
            r"[¥￥$€£]|\b(?:rmb|cny|eur|euro|euros|gbp|pounds?)\b|元|块",
            range_text,
        ))
        has_price_context = bool(re.search(
            r"预算|价格|价位|price|budget|preis|prix|prij[sz]",
            range_context,
        ))
        if has_currency or has_price_context:
            min_price, max_price = sorted(map(float, range_match.groups()))

    upper_patterns = [
        r"(?:预算|不超过|不高于|低于|最多|under|below|up to|moins de|max(?:imum)?|maximal|unter|bis|maximaal|onder|tot)\s*(?:de|dem|der)?\s*(?:<=?|≤)?\s*(?:[¥￥$€£]\s*)?(\d+(?:\.\d+)?)",
        r"(?:budget(?: de)?|budget van)\s*(?:[¥￥$€£]\s*)?(\d+(?:\.\d+)?)",
        r"(?:[¥￥$€£]\s*)?(\d+(?:\.\d+)?)\s*(?:元|块|rmb|cny)?\s*(?:以内|以下|封顶|max)",
        r"(?:<=|≤|<)\s*(?:[¥￥$€£]\s*)?(\d+(?:\.\d+)?)",
        r"max[_\s-]*price\s*[:=]?\s*(\d+(?:\.\d+)?)",
        r"几百元",
    ]
    lower_patterns = [
        r"(?:至少|不低于|高于|over|above|plus de|au moins|über|uber|mindestens|ab|boven|minstens)\s*(?:>=?|≥)?\s*(?:[¥￥$€£]\s*)?(\d+(?:\.\d+)?)",
        r"(?:[¥￥$€£]\s*)?(\d+(?:\.\d+)?)\s*(?:元|块|rmb|cny)?\s*(?:以上|起|min)",
        r"(?:>=|≥|>)\s*(?:[¥￥$€£]\s*)?(\d+(?:\.\d+)?)",
    ]
    for pattern in upper_patterns:
        match = re.search(pattern, normalized)
        if match:
            max_price = 999.0 if pattern == r"几百元" else float(match.group(1))
            break
    for pattern in lower_patterns:
        match = re.search(pattern, normalized)
        if match:
            min_price = float(match.group(1))
            break
    return min_price, max_price


def invalid_requested_range_product_ids(
    query: str,
    products: Sequence[Dict[str, Any]],
    site_context: Any = None,
) -> List[str]:
    intent = normalize_recall_query(query)
    requested_size = intent["screen_size_inch"]
    requested_size_min = intent["screen_size_min_inch"]
    requested_size_max = intent["screen_size_max_inch"]
    min_price, max_price = parse_requested_price_bounds(query)
    if not any((requested_size, requested_size_min, requested_size_max, min_price, max_price)):
        return []

    raw_by_sku = _raw_products_by_sku()
    site_config = resolve_site_config(site_context)
    invalid = []
    for product in products:
        sku_id = str(product.get("sku_id", ""))
        raw_source = raw_by_sku.get(sku_id)
        source = raw_source or product
        source_text = (
            f"{source.get('title', '')} {source.get('sku_name', '')} "
            f"{source.get('key_specs', '')}"
        )
        size_match = re.search(r"(?:^|\D)(\d{2,3}(?:\.\d+)?)\s*(?:寸|inch(?:es)?|zoll|pouces?)", source_text, re.IGNORECASE)
        product_size = float(size_match.group(1)) if size_match else None
        product_price = float(
            source.get("price", 0) if raw_source
            else source.get("final_price", source.get("price", 0))
        )
        product_min_price = min_price
        product_max_price = max_price
        if (
            raw_source
            and site_config
            and not re.search(r"(?:元|rmb|cny|[¥￥])", query, re.IGNORECASE)
        ):
            price_rate = float(site_config["price_rate"])
            if product_min_price > 0:
                product_min_price /= price_rate
            if product_max_price > 0:
                product_max_price /= price_rate
        size_invalid = (
            (requested_size is not None and product_size != requested_size)
            or (requested_size_min is not None and (product_size is None or product_size < requested_size_min))
            or (requested_size_max is not None and (product_size is None or product_size > requested_size_max))
        )
        price_invalid = (
            (product_min_price > 0 and product_price < product_min_price)
            or (product_max_price > 0 and product_price > product_max_price)
        )
        if size_invalid or price_invalid:
            invalid.append(sku_id)
    return invalid


def _localized_screen_size(value: float, language: str) -> str:
    unit = {
        "zh_CN": "英寸",
        "en_GB": "inch",
        "de_DE": "Zoll",
        "fr_FR": "pouces",
        "nl_NL": "inch",
    }.get(language, "inch")
    return f"{value:g} {unit}"


def _synthetic_attribute_variants(
    query: str,
    mock_category: str,
    language: str,
) -> List[List[str]]:
    """Project query constraints into contract-visible product titles."""
    normalized = _normalize_search_text(query).replace(",", ".")
    variants: List[List[str]] = [[], [], []]

    intent = normalize_recall_query(query)
    size_values: List[float] = []
    if intent["screen_size_inch"] is not None:
        size_values = [intent["screen_size_inch"]] * 3
    elif intent["screen_size_min_inch"] is not None and intent["screen_size_max_inch"] is not None:
        lower = intent["screen_size_min_inch"]
        upper = intent["screen_size_max_inch"]
        size_values = [lower, round((lower + upper) / 2), upper]
    elif intent["screen_size_min_inch"] is not None:
        lower = intent["screen_size_min_inch"]
        size_values = [lower, lower + 5, lower + 10]
    if size_values and mock_category in {"特殊电视", "曲面显示器"}:
        for index, value in enumerate(size_values):
            variants[index].append(_localized_screen_size(value, language))

    bed_size = re.search(
        r"(?<!\d)(\d{2,3})\s*[*x×]\s*(\d{2,3})\s*(?:cm|厘米)?(?!\d)",
        normalized,
        re.IGNORECASE,
    )
    if bed_size and mock_category in {"床笠", "床垫", "床品"}:
        label = f"{bed_size.group(1)}×{bed_size.group(2)} cm"
        for labels in variants:
            labels.append(label)

    btu_match = re.search(r"(?<!\d)(\d{4,5})\s*btu\b", normalized, re.IGNORECASE)
    if btu_match and mock_category == "便携空调":
        requested_btu = int(btu_match.group(1))
        context = normalized[max(0, btu_match.start() - 24):btu_match.end() + 20]
        is_minimum = bool(re.search(
            r"(?:at least|minimum|better|more than|plus|\+|mindestens|au moins|minstens|至少|以上)",
            context,
            re.IGNORECASE,
        ))
        btu_values = (
            [requested_btu, requested_btu + 1000, requested_btu + 3000]
            if is_minimum else [requested_btu] * 3
        )
        for index, value in enumerate(btu_values):
            variants[index].append(f"{value:g} BTU")

    refresh_match = re.search(r"(?<!\d)(\d{2,3})\s*hz\b", normalized, re.IGNORECASE)
    if refresh_match:
        refresh = float(refresh_match.group(1))
        minimum_refresh = any(
            kind == "refresh_hz" and value == refresh
            for kind, value in _minimum_product_specs(query)
        )
        refresh_values = [refresh, refresh + 24, refresh + 45] if minimum_refresh else [refresh] * 3
        for index, value in enumerate(refresh_values):
            variants[index].append(f"{value:g}Hz")

    for kind, value in _requested_measurements(query):
        if kind == "volume_ml":
            label = f"{value / 1000:g}L" if value >= 1000 else f"{value:g}ml"
        elif kind == "length_mm":
            label = f"{value:g}mm"
        else:
            label = f"{value / 1000:g}kg" if value >= 1000 else f"{value:g}g"
        for labels in variants:
            if label not in labels:
                labels.append(label)

    feature_labels = [
        (("steam", "stoom", "dampf", "vapeur", "蒸汽"), {"zh_CN": "蒸汽", "en_GB": "steam", "de_DE": "Dampf", "fr_FR": "vapeur", "nl_NL": "stoom"}),
        (("sulfate free", "without sulfates", "sans sulfate", "sulfatfrei", "zonder sulfaten", "无硫酸盐"), {"zh_CN": "无硫酸盐", "en_GB": "sulfate-free", "de_DE": "sulfatfrei", "fr_FR": "sans sulfate", "nl_NL": "zonder sulfaten"}),
        (("waterproof", "wasserdicht", "étanche", "waterdicht", "防水"), {"zh_CN": "防水", "en_GB": "waterproof", "de_DE": "wasserdicht", "fr_FR": "étanche", "nl_NL": "waterdicht"}),
        (("wireless", "kabellos", "sans fil", "draadloos", "无线"), {"zh_CN": "无线", "en_GB": "wireless", "de_DE": "kabellos", "fr_FR": "sans fil", "nl_NL": "draadloos"}),
        (("rgb",), {"zh_CN": "RGB", "en_GB": "RGB", "de_DE": "RGB", "fr_FR": "RGB", "nl_NL": "RGB"}),
        (("black", "schwarz", "noir", "zwart", "黑色"), {"zh_CN": "黑色", "en_GB": "black", "de_DE": "schwarz", "fr_FR": "noir", "nl_NL": "zwart"}),
        (("wooden", "wood", "holz", "bois", "houten", "木质", "木制"), {"zh_CN": "木质", "en_GB": "wooden", "de_DE": "Holz", "fr_FR": "bois", "nl_NL": "houten"}),
    ]
    for markers, labels in feature_labels:
        if any(_normalize_search_text(marker) in normalized for marker in markers):
            label = labels.get(language, labels["en_GB"])
            for variant_labels in variants:
                if label not in variant_labels:
                    variant_labels.append(label)
    return variants


def _synthetic_query_products(
    query: str,
    site_context: Any = None,
) -> List[Dict[str, Any]]:
    """Create deterministic query-level candidates for otherwise unknown categories."""
    display_query = re.sub(r"https?://\S+", "", str(query or "")).strip(" ,，。;；")
    normalized_query = _normalize_search_text(display_query)
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", normalized_query))
    if (has_cjk and len(normalized_query) < 2) or (not has_cjk and len(normalized_query) < 4):
        return []

    mock_category = _longest_alias_match(
        normalized_query,
        list(QUERY_LEVEL_MOCK_CATEGORY_ALIASES.items()),
    )
    if not mock_category:
        return []

    promotion_markers = (
        "coupon", "promo code", "discount code", "buy 2 get 1", "buy 3 get 1",
        "2送1", "3送1", "优惠券", "korting", "gutschein", "code promo",
    )
    if any(marker in normalized_query for marker in promotion_markers):
        return []

    site_config = resolve_site_config(site_context)
    language = site_config["site_lang_code"] if site_config else "zh_CN"
    variants = {
        "zh_CN": ("标准款", "精选款", "升级款"),
        "en_GB": ("Standard", "Choice", "Plus"),
        "de_DE": ("Standard", "Auswahl", "Plus"),
        "fr_FR": ("Standard", "Sélection", "Plus"),
        "nl_NL": ("Standaard", "Selectie", "Plus"),
    }[language]

    display_names = QUERY_LEVEL_MOCK_CATEGORY_DISPLAY[mock_category]
    localized_category = (
        display_names.get(language)
        or display_names.get("en_GB")
        or mock_category
    )
    if re.search(r"[\u4e00-\u9fff]", display_query) or len(display_query) > 70:
        display_query = localized_category
    attribute_variants = _synthetic_attribute_variants(query, mock_category, language)
    if any(attribute_variants):
        display_query = localized_category

    seed = int(hashlib.sha1(normalized_query.encode("utf-8")).hexdigest()[:8], 16)
    min_price, max_price = parse_requested_price_bounds(display_query)
    if max_price > 0:
        lower = min_price if min_price > 0 else max(0.99, max_price * 0.35)
        upper = max(max_price, lower)
        price_points = [
            lower + (upper - lower) * ratio
            for ratio in (0.15, 0.5, 0.85)
        ]
    elif min_price > 0:
        price_points = [min_price * ratio for ratio in (1.05, 1.2, 1.4)]
    else:
        range_min, range_max = QUERY_LEVEL_MOCK_PRICE_RANGES[mock_category]
        spread = range_max - range_min
        offset = (seed % 1000) / 1000
        base = range_min + spread * (0.08 + offset * 0.18)
        price_points = [base, base + spread * 0.22, base + spread * 0.48]

    products = []
    for index, (variant, final_price) in enumerate(zip(variants, price_points), 1):
        final_price = max(0.99, round(final_price, 2))
        original_price = round(final_price * (1.12 + index * 0.03), 2)
        raw_id = f"query_{normalized_query}_{index}"
        sku_id = _contract_sku_id(raw_id)
        sales_count = 800 + (seed // (index * 7) % 9200)
        if site_config:
            sales = _localized_sales(f"月销{sales_count}", site_config)
        else:
            sales = f"月销{sales_count}"
        title_parts = [display_query]
        normalized_title = _normalize_search_text(display_query)
        for attribute in attribute_variants[index - 1]:
            if _normalize_search_text(attribute) not in normalized_title:
                title_parts.append(attribute)
        title_parts.append(f"— {variant}")
        products.append({
            "sku_id": sku_id,
            "sku_name": " ".join(title_parts)[:140],
            "brand_name": "Joybuy Select",
            "final_price": f"{final_price:.2f}",
            "price": f"{original_price:.2f}",
            "img_url": f"mock/products/{sku_id}.jpg",
            "good": None,
            "sales": sales,
            "keyword": query,
        })
    return products


def _sku_recall(
    query: str,
    site_context: Any = None,
) -> Dict:
    """按真实 Joybuy 契约返回商品召回结果。"""
    def empty_result() -> Dict[str, Any]:
        return {
            "success": True,
            "query": query,
            "count": 0,
            "sku_list": [],
            "sku_map": {},
            "products": [],
            "recall_intent": {
                "is_get_comment": False,
                "use_bad_comment": False,
                "get_history_price": False,
            },
            "executed_queries": [query],
            "brand_boost_targets": [],
        }

    site_config = resolve_site_config(site_context)

    # 无货检测：query包含无货关键词，直接返回空（模拟线上无货场景）
    query_lower = query.lower().strip()
    for no_stock_kw in NO_STOCK_KEYWORDS:
        if no_stock_kw in query_lower or query_lower in no_stock_kw:
            return empty_result()

    if is_generic_product_discovery_query(query) and not normalize_recall_query(query)["category"]:
        candidates = [
            product
            for category, category_products in MOCK_PRODUCTS.items()
            if category != "default"
            for product in category_products
        ]
        normalized_query = _normalize_search_text(query)
        wants_deal = any(
            marker in normalized_query
            for marker in ("deal", "cheap", "affaire", "angebot", "划算", "好价")
        )

        def discovery_score(product: Dict[str, Any]) -> tuple[float, int]:
            price = float(product.get("price", 0) or 0)
            original_price = float(product.get("original_price", price) or price)
            discount = (original_price - price) / original_price if original_price > 0 else 0
            sales = _parse_sales_count(str(product.get("sales", "")))
            return (discount if wants_deal else float(sales), sales)

        candidates.sort(key=discovery_score, reverse=True)
        products = []
        seen_categories = set()
        for product in candidates:
            category = str(product.get("category", ""))
            if not category or category in seen_categories:
                continue
            seen_categories.add(category)
            products.append(product)
            if len(products) == 5:
                break
        real_products = [
            _contract_product(product, str(product["category"]), query, site_context)
            for product in products
        ]
        sku_list = [product["sku_id"] for product in real_products]
        return {
            "success": True,
            "query": query,
            "count": len(real_products),
            "sku_list": sku_list,
            "sku_map": {product["sku_id"]: product for product in real_products},
            "products": real_products,
            "recall_intent": {
                "is_get_comment": False,
                "use_bad_comment": False,
                "get_history_price": False,
            },
            "executed_queries": [query],
            "brand_boost_targets": [],
        }

    # 关键词匹配规则：(category_key, [触发关键词列表])
    KEYWORD_RULES = [
        ("运动耳机",   ["运动耳机", "跑步耳机", "骨传导", "健身耳机"]),
        ("降噪耳机",   ["降噪耳机", "anc耳机", "消噪耳机", "降噪"]),
        ("蓝牙耳机",   ["蓝牙耳机", "无线耳机", "真无线", "tws"]),
        ("颈椎按摩仪", ["颈椎", "按摩仪", "肩颈", "颈部按摩", "颈椎按摩"]),
        ("咖啡机",     ["咖啡机", "胶囊咖啡", "意式咖啡", "美式咖啡", "espresso"]),
        ("跑步鞋",     ["跑步鞋", "运动鞋", "慢跑鞋", "跑鞋", "训练鞋"]),
        ("台灯",       ["台灯", "护眼灯", "学习灯", "护眼台灯", "led台灯"]),
        ("投影仪",     ["投影仪", "投影机", "激光电视", "家庭影院", "激光投影"]),
        ("洗衣液",     ["洗衣液", "洗涤剂", "洗护", "洗衣粉", "衣物清洁"]),
        ("跑步机",     ["跑步机", "跑台", "家用跑步机", "折叠跑步机"]),
        ("哑铃",       ["哑铃", "可调哑铃", "固定哑铃", "哑铃组合"]),
        ("瑜伽垫",     ["瑜伽垫", "健身垫", "瑜伽地垫", "防滑垫"]),
        ("跳绳",       ["跳绳", "智能跳绳", "竞速跳绳", "计数跳绳"]),
        ("运动垫",     ["运动垫", "跑步机垫", "减震垫", "地垫", "健身地垫"]),
        ("运动耳机",   ["运动耳机", "跑步耳机", "骨传导", "防水耳机", "健身耳机"]),
        ("弹力带",     ["弹力带", "阻力带", "弹力绳", "拉力带", "健身带"]),
        ("家居搭配",   ["茶几", "落地灯", "地毯", "家居搭配", "客厅搭配", "装饰画", "抱枕", "窗帘", "沙发垫"]),
        ("摄影装备",   ["摄影装备", "相机配件", "摄影器材", "相机清洁", "闪光灯", "云台", "存储卡", "滤镜", "快门线"]),
        ("三脚架",     ["三脚架", "相机三脚架", "单反三脚架", "摄影三脚架", "便携三脚架"]),
        ("摄影包",     ["摄影包", "相机包", "单反摄影包", "相机背包", "摄影背包"]),
        ("保温杯",     ["保温杯", "保温壶", "热水杯", "露营保温"]),
        ("人体工学椅", ["人体工学椅", "人体工学", "办公椅", "电脑椅", "工学椅"]),
        ("扫地机",     ["扫地机", "扫地机器人", "扫拖机器人", "拖地机器人"]),
        ("键盘鼠标",   ["键盘", "鼠标", "键鼠", "机械键盘", "无线键盘", "无线鼠标", "鼠标垫"]),
        ("热水壶",     ["热水壶", "电热水壶", "烧水壶", "电水壶", "煮水壶", "速热水壶"]),
        ("空气净化器", ["空气净化器", "净化器", "空净", "除甲醛", "pm2.5净化"]),
        ("吸尘器",     ["吸尘器", "无线吸尘器", "手持吸尘器", "戴森吸尘器", "家用吸尘器"]),
        ("VR头显",     ["vr", "vr头显", "vr眼镜", "ar眼镜", "元宇宙", "虚拟现实", "quest", "pico"]),
        ("折叠椅",     ["折叠椅", "露营椅", "户外折叠椅", "便携椅", "野营椅"]),
        ("帐篷",       ["帐篷", "露营帐篷", "户外帐篷", "野营帐篷", "速开帐篷"]),
        ("显示器",     ["显示器", "电脑显示器", "电竞显示器", "4k显示器", "外接屏"]),
        ("泡脚桶",     ["泡脚桶", "足浴盆", "泡脚盆", "足浴桶", "泡脚"]),
        ("洗碗机",     ["洗碗机", "嵌入式洗碗机", "台式洗碗机", "家用洗碗机"]),
        ("破壁机",     ["破壁机", "破壁料理机", "豆浆机", "料理机", "搅拌机"]),
        ("卷发棒",     ["卷发棒", "卷发器", "美发造型器", "美发棒", "电卷棒", "airwrap", "护发造型"]),
        ("掌机",       ["掌机", "掌上游戏机", "游戏掌机", "switch", "任天堂", "steam deck", "psp"]),
        ("跑步鞋",     ["跑步鞋", "跑鞋", "慢跑鞋", "运动跑鞋"]),
        ("电视",       ["电视", "智能电视", "4k电视", "液晶电视", "oled电视", "激光电视", "大屏电视", "智慧屏"]),
        ("冰箱",       ["冰箱", "对开门冰箱", "多门冰箱", "双门冰箱", "法式冰箱", "嵌入式冰箱", "保鲜冰箱"]),
        ("洗衣机",     ["洗衣机", "滚筒洗衣机", "波轮洗衣机", "洗烘一体", "全自动洗衣机", "变频洗衣机"]),
        ("行车记录仪", ["行车记录仪", "行驶记录仪", "记录仪", "车载摄像头", "4k记录仪", "前后双录"]),
        ("笔记本电脑", ["笔记本", "笔记本电脑", "轻薄本", "游戏本", "商务本", "macbook", "thinkpad", "创作本", "本本"]),
        ("手机",       ["手机", "智能手机", "苹果手机", "华为手机", "小米手机", "iphone", "galaxy", "huawei mate", "mate 60", "mate 70", "find x"]),
        ("平板电脑",   ["平板", "平板电脑", "ipad", "matepad", "小米平板", "tab", "tablet"]),
        ("智能手表",   ["智能手表", "手表", "apple watch", "watch", "手环", "运动手表", "galaxy watch"]),
        ("电动牙刷",   ["电动牙刷", "声波牙刷", "电牙刷", "usmile", "欧乐b", "飞利浦牙刷"]),
        ("剃须刀",     ["剃须刀", "电动剃须刀", "剃须", "braun", "博朗", "飞科", "刮胡刀"]),
        ("吹风机",     ["吹风机", "电吹风", "戴森吹风", "高速吹风", "徕芬", "laifen"]),
        ("微波炉",     ["微波炉", "格兰仕", "微蒸烤", "光波炉"]),
        ("电饭煲",     ["电饭煲", "电饭锅", "ih电饭煲", "象印", "虎牌", "压力煲"]),
        ("按摩椅",     ["按摩椅", "太空舱按摩椅", "全身按摩", "奥佳华", "荣泰", "家用按摩椅"]),
        ("空调",       ["空调", "变频空调", "柜机", "挂机", "格力", "美的空调", "制冷制热", "冷暖空调"]),
        ("书桌",       ["书桌", "电脑桌", "升降桌", "学习桌", "工作台", "办公桌"]),
        ("净水器",     ["净水器", "净水机", "直饮机", "ro净水", "反渗透", "厨下净水"]),
        ("背包",       ["背包", "双肩包", "书包", "旅行包", "登山包", "通勤包"]),
        ("护肤品",     ["护肤品", "精华", "面霜", "乳液", "防晒", "护肤", "sk2", "sk-ii", "兰蔻", "雅诗兰黛", "海蓝之谜", "薇诺娜", "珀莱雅"]),
        ("洗发水",     ["洗发水", "洗发露", "氨基酸洗发", "防脱洗发", "去屑洗发", "护发素", "飘柔", "潘婷"]),
        ("儿童玩具",   ["玩具", "儿童玩具", "乐高", "lego", "积木", "芭比", "拼图", "遥控车", "婴儿玩具"]),
        ("宠物用品",   ["宠物", "猫粮", "狗粮", "猫砂", "宠物玩具", "宠物零食", "猫咪", "狗狗", "饮水机"]),
        ("厨具",       ["厨具", "炒锅", "不粘锅", "高压锅", "刀具", "菜刀", "锅", "料理棒", "电磁炉", "烤盘"]),
        ("汽车用品",   ["汽车用品", "车载", "行车记录", "车充", "手机支架", "车内", "汽车", "燃油宝"]),
        ("运动服装",   ["运动服", "运动裤", "运动短袖", "运动T恤", "瑜伽裤", "速干衣", "压缩裤", "跑步服", "lululemon"]),
        ("零食",       ["零食", "坚果", "薯片", "饼干", "糖果", "牛肉干", "膨化食品", "巧克力", "果冻"]),
        ("文具",       ["文具", "中性笔", "圆珠笔", "荧光笔", "笔记本", "彩铅", "铅笔", "订书机", "便利贴"]),
        ("电烤箱",     ["烤箱", "电烤箱", "嵌入式烤箱", "烘焙烤箱", "家用烤箱"]),
        ("面包机",     ["面包机", "全自动面包机", "吐司机", "揉面机"]),
        ("充电宝",     ["充电宝", "移动电源", "快充充电宝", "大容量充电宝", "anker", "倍思充电"]),
        ("蓝牙音箱",   ["蓝牙音箱", "音箱", "jbl", "bose音箱", "小米音箱", "户外音箱", "便携音箱"]),
        ("路由器",     ["路由器", "wifi6", "mesh路由", "无线路由", "华为路由", "小米路由", "tplink"]),
        ("台式电脑",   ["台式电脑", "台式机", "主机", "mac mini", "一体机", "rog", "游戏主机"]),
        ("打印机",     ["打印机", "激光打印", "喷墨打印", "惠普打印", "爱普生", "佳能打印", "兄弟打印"]),
        ("香水",       ["香水", "edp", "edt", "香奈儿", "迪奥香水", "祖玛珑", "兰蔻香水", "男士香水", "女士香水"]),
        ("彩妆",       ["彩妆", "口红", "粉底", "眼影", "腮红", "圣罗兰", "阿玛尼彩妆", "花西子", "mac口红", "完美日记"]),
        ("床品",       ["床品", "四件套", "被套", "床单", "枕套", "羽绒被", "睡眠", "水星家纺", "富安娜"]),
        ("数据线",     ["数据线", "充电线", "type-c线", "lightning线", "usb线", "编织线"]),
        ("冲锋衣",     ["冲锋衣", "防水夹克", "户外外套", "北面冲锋", "始祖鸟", "gore-tex", "防风衣"]),
        ("登山鞋",     ["登山鞋", "徒步鞋", "户外鞋", "萨洛蒙", "迈乐", "哥伦比亚鞋"]),
        ("睡袋",       ["睡袋", "户外睡袋", "羽绒睡袋", "露营睡袋", "牧高笛睡袋"]),
    ]

    query_lower = query.lower()
    normalized_intent = normalize_recall_query(query)
    matched_key = normalized_intent["category"] or "default"
    if matched_key == "default":
        keyword_match = _longest_alias_match(
            normalized_intent["normalized_query"],
            [
                (category_key, keywords)
                for category_key, keywords in KEYWORD_RULES
                if category_key in MOCK_PRODUCTS
            ],
        )
        if keyword_match:
            matched_key = keyword_match

    if matched_key == "default" and normalized_intent["category"]:
        matched_key = normalized_intent["category"]

    if matched_key == "default":
        alias_match = _longest_alias_match(
            normalized_intent["normalized_query"],
            list(MULTILINGUAL_CATEGORY_ALIASES.items()),
        )
        if alias_match:
            matched_key = alias_match

    # 兜底：遍历品类名本身
    if matched_key == "default":
        for key in MOCK_PRODUCTS:
            if key == "default":
                continue
            if key in query_lower or any(part in query_lower for part in key.split()):
                matched_key = key
                break

    if matched_key == "default":
        synthetic_products = _synthetic_query_products(query, site_context)
        if not synthetic_products:
            return empty_result()
        sku_list = [product["sku_id"] for product in synthetic_products]
        return {
            "success": True,
            "query": query,
            "count": len(synthetic_products),
            "sku_list": sku_list,
            "sku_map": {
                product["sku_id"]: product for product in synthetic_products
            },
            "products": synthetic_products,
            "recall_intent": {
                "is_get_comment": False,
                "use_bad_comment": False,
                "get_history_price": False,
            },
            "executed_queries": [query],
            "brand_boost_targets": [],
        }

    products = list(MOCK_PRODUCTS.get(matched_key, []))
    if not products:
        matching_products_by_sku = {}
        for style_pool in MATCHING_PRODUCTS.values():
            for pool_key, pool_products in style_pool.items():
                for product in pool_products:
                    if pool_key != matched_key and product.get("category") != matched_key:
                        continue
                    matching_products_by_sku.setdefault(product["product_id"], product)
        products = list(matching_products_by_sku.values())

    if not products:
        if matched_key in QUERY_LEVEL_MOCK_CATEGORY_ALIASES:
            synthetic_products = _synthetic_query_products(query, site_context)
            if synthetic_products:
                sku_list = [product["sku_id"] for product in synthetic_products]
                return {
                    "success": True,
                    "query": query,
                    "count": len(synthetic_products),
                    "sku_list": sku_list,
                    "sku_map": {
                        product["sku_id"]: product for product in synthetic_products
                    },
                    "products": synthetic_products,
                    "recall_intent": {
                        "is_get_comment": False,
                        "use_bad_comment": False,
                        "get_history_price": False,
                    },
                    "executed_queries": [query],
                    "brand_boost_targets": [],
                }
        return empty_result()

    for product_markers in _specialized_product_marker_groups(query):
        products = [
            product
            for product in products
            if any(
                _normalize_search_text(marker)
                in _normalize_search_text(
                    f"{product.get('title', '')} {product.get('description', '')} {product.get('key_specs', '')}"
                )
                for marker in product_markers
            )
        ]

    if matched_key == "空调" and "quiet" in normalized_intent["constraints"]:
        quiet_markers = ("low-noise", "low noise", "quiet", "silent", "静音", "低噪", "leise", "silencieux", "stille")
        products = [
            product
            for product in products
            if any(
                marker in _normalize_search_text(
                    f"{product.get('title', '')} {product.get('description', '')} {product.get('key_specs', '')}"
                )
                for marker in quiet_markers
            )
        ]

    brand = normalized_intent["brand"]
    if brand:
        products = [product for product in products if product.get("brand") == brand]

    products = _filter_products_by_requested_screen_size(products, query)

    for constraint in normalized_intent["constraints"]:
        markers = CONSTRAINT_PRODUCT_MARKERS.get(constraint, [])
        if not markers:
            continue
        matching_products = [
            product
            for product in products
            if any(
                _normalize_search_text(marker)
                in _normalize_search_text(
                    f"{product.get('title', '')} {product.get('key_specs', '')} {product.get('description', '')}"
                )
                for marker in markers
            )
        ]
        if constraint in HARD_RETRIEVAL_CONSTRAINTS:
            products = matching_products
        elif matching_products:
            matching_ids = {product["product_id"] for product in matching_products}
            products = matching_products + [
                product for product in products if product["product_id"] not in matching_ids
            ]

    products = _filter_products_by_requested_measurements(products, query)
    products = _filter_products_by_minimum_specs(products, query)
    products = _filter_products_by_exact_specs(products, query)
    products.sort(key=lambda product: _product_query_match_score(query, product), reverse=True)

    products = _filter_catalog_products_by_price(products, query, site_context)

    real_products = [
        _contract_product(product, matched_key, query, site_context)
        for product in products
    ]
    sku_list = [product["sku_id"] for product in real_products]

    return {
        "success": True,
        "query": query,
        "count": len(real_products),
        "sku_list": sku_list,
        "sku_map": {product["sku_id"]: product for product in real_products},
        "products": real_products,
        "recall_intent": {
            "is_get_comment": False,
            "use_bad_comment": False,
            "get_history_price": False,
        },
        "executed_queries": [query],
        "brand_boost_targets": [],
    }





def _calculate_budget(
    items: List[Dict],
    total_budget: float,
    site_context: Any = None,
) -> Dict:
    """预算计算"""
    normalized_items = []
    for item in items:
        try:
            price = float(item.get("price", 0) or 0)
        except (TypeError, ValueError):
            price = 0.0
        normalized_items.append({"name": str(item.get("name", "")), "price": price})
    total_budget = float(total_budget or 0)
    total = sum(item["price"] for item in normalized_items)
    remaining = total_budget - total
    site_config = resolve_site_config(site_context)
    currency_symbol = str(site_config["currency_symbol"]) if site_config else "¥"
    currency_code = str(site_config["currency_code"]) if site_config else "CNY"
    language = site_config["site_lang_code"] if site_config else "zh_CN"
    summary_templates = {
        "zh_CN": f"合计{currency_symbol}{total:.2f}，{'剩余' if remaining >= 0 else '超出'}{currency_symbol}{abs(remaining):.2f}",
        "en_GB": f"Total {currency_symbol}{total:.2f}; {currency_symbol}{abs(remaining):.2f} {'remaining' if remaining >= 0 else 'over budget'}",
        "de_DE": f"Gesamt {currency_symbol}{total:.2f}; {currency_symbol}{abs(remaining):.2f} {'übrig' if remaining >= 0 else 'über Budget'}",
        "fr_FR": f"Total {currency_symbol}{total:.2f} ; {currency_symbol}{abs(remaining):.2f} {'restants' if remaining >= 0 else 'au-dessus du budget'}",
        "nl_NL": f"Totaal {currency_symbol}{total:.2f}; {currency_symbol}{abs(remaining):.2f} {'over' if remaining >= 0 else 'boven budget'}",
    }
    return {
        "status":      "SUCCESS",
        "total_price": round(total, 2),
        "budget":      total_budget,
        "remaining":   round(remaining, 2),
        "in_budget":   remaining >= 0,
        "currency_code": currency_code,
        "currency_symbol": currency_symbol,
        "items":       normalized_items,
        "summary":     summary_templates[language],
    }


def _scenario_related_recall(
    main_item: str,
    need_items,  # 兼容 List[str] 和 str（模型有时传逗号分隔字符串）
    style: str = "nordic",
    site_context: Any = None,
) -> Dict:
    """场景关联搭配推荐，也支持无货替代品召回（need_items传替代搜索词）"""
    # 兼容字符串格式的 need_items（如 "茶几, 装饰画"）
    if isinstance(need_items, str):
        need_items = [x.strip() for x in need_items.replace("，", ",").split(",") if x.strip()]
    # 英文key → 中文展示名
    style_map = {
        "nordic":      "北欧简约",
        "mid_century": "中古复古",
        "modern":      "现代简约",
        "industrial":  "工业风",
        "camera":      "相机摄影",
        "fitness":     "健身运动",
        "treadmill":   "跑步机搭配",
        "office":      "居家办公",
        "outdoor":     "户外露营",
        "substitute":  "替代品推荐",
    }
    # 中文别名 → 英文key（模型可能传中文）
    style_alias = {
        "北欧": "nordic", "北欧风": "nordic", "北欧简约": "nordic",
        "中古": "mid_century", "中古复古": "mid_century", "复古": "mid_century",
        "现代": "modern", "现代简约": "modern", "简约": "modern",
        "工业风": "industrial",
        "相机": "camera", "摄影": "camera",
        "健身": "fitness", "运动": "fitness",
        "跑步机": "treadmill",
        "办公": "office", "居家办公": "office",
        "户外": "outdoor", "露营": "outdoor",
    }
    # 如果传入中文，映射到英文key
    style_key = style_alias.get(style, style)
    site_config = resolve_site_config(site_context)
    language = site_config["site_lang_code"] if site_config else "zh_CN"
    localized_styles = {
        "en_GB": {"nordic": "Nordic", "mid_century": "mid-century", "modern": "modern", "industrial": "industrial", "camera": "photography", "fitness": "fitness", "treadmill": "treadmill", "office": "home office", "outdoor": "outdoor", "substitute": "alternative"},
        "de_DE": {"nordic": "nordisch", "mid_century": "Mid-Century", "modern": "modern", "industrial": "Industrial", "camera": "Fotografie", "fitness": "Fitness", "treadmill": "Laufband", "office": "Homeoffice", "outdoor": "Outdoor", "substitute": "Alternative"},
        "fr_FR": {"nordic": "nordique", "mid_century": "mid-century", "modern": "moderne", "industrial": "industriel", "camera": "photographie", "fitness": "fitness", "treadmill": "tapis de course", "office": "bureau à domicile", "outdoor": "plein air", "substitute": "alternative"},
        "nl_NL": {"nordic": "Scandinavisch", "mid_century": "mid-century", "modern": "modern", "industrial": "industrieel", "camera": "fotografie", "fitness": "fitness", "treadmill": "loopband", "office": "thuiswerk", "outdoor": "outdoor", "substitute": "alternatief"},
    }
    style_cn = style_map.get(style_key, style)
    style_display = localized_styles.get(language, {}).get(style_key, style_cn)
    is_substitute = (style_key == "substitute")

    def match_reason() -> str:
        if language == "en_GB":
            return f"Alternative to {main_item}" if is_substitute else f"Matches {main_item} in a {style_display} style"
        if language == "de_DE":
            return f"Alternative zu {main_item}" if is_substitute else f"Passt im Stil {style_display} zu {main_item}"
        if language == "fr_FR":
            return f"Alternative à {main_item}" if is_substitute else f"S'accorde avec {main_item} dans un style {style_display}"
        if language == "nl_NL":
            return f"Alternatief voor {main_item}" if is_substitute else f"Past bij {main_item} in {style_display}e stijl"
        return f"作为「{main_item}」的替代推荐" if is_substitute else f"{style_cn}风格搭配，与{main_item}协调统一"

    matched = []
    style_pool = MATCHING_PRODUCTS.get(style_key, {})

    def pool_for_need(need: str) -> Dict[str, List[Dict]]:
        normalized_need = _normalize_search_text(need)
        style_markers = {
            "nordic": ["nordic", "nordisch", "nordique", "scandinavisch", "北欧"],
            "modern": ["modern", "moderne", "现代"],
            "mid_century": ["mid-century", "mid century", "中古", "复古"],
        }
        for candidate_style, markers in style_markers.items():
            if any(_normalize_search_text(marker) in normalized_need for marker in markers):
                return MATCHING_PRODUCTS.get(candidate_style, style_pool)
        return style_pool

    for need in need_items[:4]:
        found = None
        found_category = None
        constraint_query = " ".join(
            part for part in (str(main_item).strip(), str(need).strip()) if part
        )
        need_category = normalize_recall_query(constraint_query).get("category") or str(need)

        if not is_substitute:
            # 搭配模式：先查搭配池
            for key, products in pool_for_need(str(need)).items():
                if key == need_category or key in str(need) or str(need) in key:
                    candidates = _filter_products_by_requested_measurements(products, constraint_query)
                    candidates = _filter_products_by_minimum_specs(candidates, constraint_query)
                    candidates = _filter_products_by_exact_specs(candidates, constraint_query)
                    candidates = _filter_products_by_requested_screen_size(candidates, constraint_query)
                    candidates = _filter_catalog_products_by_price(candidates, constraint_query, site_context)
                    if candidates:
                        found = max(
                            candidates,
                            key=lambda product: _product_query_match_score(constraint_query, product),
                        )
                        found_category = key
                    break

        # fallback 到 sku_recall（搭配找不到 or 替代模式）
        if not found:
            results = _sku_recall(query=constraint_query, site_context=site_context)
            if results["products"]:
                for p in results["products"][:2]:
                    matched.append({**p, "match_reason": match_reason()})
                continue  # 已处理，跳过后面的 found 逻辑

        if found:
            category = str(found_category or found.get("category") or need)
            formatted = _contract_product(found, category, constraint_query, site_context)
            matched.append({**formatted, "match_reason": match_reason()})

    # 去重（可能同一商品出现多次）
    seen = set()
    deduped = []
    for p in matched:
        pid = p.get("sku_id") or p.get("product_id", "")
        if pid not in seen:
            seen.add(pid)
            deduped.append(p)

    return {
        "status":    "SUCCESS",
        "main_item": main_item,
        "style":     style_display,
        "is_substitute": is_substitute,
        "count":     len(deduped),
        "products":  deduped,
    }
