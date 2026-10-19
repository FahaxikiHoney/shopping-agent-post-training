# -*- coding: utf-8 -*-
"""
SkuRepurchaseRecall — 对应真实项目的 sku_recall_history + 历史购买记录

真实项目：
    sku_recall_history(history_sku_index, is_history_sku, recall_intent, oxy_request)
    从 shared_data["shopping_recall_scratch_state"] 取历史购买记录

本工具：从 REPURCHASE_MOCK_POOL 按 category_keyword 匹配，返回
    - history_product: 历史购买的商品（标注购买时间）
    - recommend_products: 推荐复购/升级款
"""
from __future__ import annotations
from typing import Any, Dict, List


# ─────────────────────────────────────────────
# 历史购买订单 Mock 池（10条）
# ─────────────────────────────────────────────
REPURCHASE_MOCK_POOL: List[Dict[str, Any]] = [
    {
        "order_id": "ORDER-001",
        "purchase_months_ago": 2,
        "category_keyword": "洗发水",
        "product": {
            "product_id": "jd_rep_001",
            "title": "海飞丝 去屑洗发水 滋养型 400ml（2月前购买）",
            "price": 49.9, "is_jd_self": True, "rating": 4.8,
            "key_specs": "你2月前购买/订单ORDER-001/去屑控油/400ml",
            "sales": "月销12万",
        },
        "recommend": [
            {"product_id": "jd_rep_001n", "title": "海飞丝 2024新款深层修护洗发水 530ml",
             "price": 59.9, "is_jd_self": True, "rating": 4.9,
             "key_specs": "深层修护/同品牌新款/大瓶装更划算",
             "sales": "月销3.5万"},
            {"product_id": "jd_rep_001c", "title": "润妍护发素 深层补水 300ml 配套使用",
             "price": 39.9, "is_jd_self": True, "rating": 4.7,
             "key_specs": "海飞丝同系列/护发素/修护干燥受损发",
             "sales": "月销2.1万"},
        ],
    },
    {
        "order_id": "ORDER-002",
        "purchase_months_ago": 3,
        "category_keyword": "猫粮",
        "product": {
            "product_id": "jd_rep_002",
            "title": "皇家猫粮 室内成猫 2kg 原味（3月前购买）",
            "price": 129.0, "is_jd_self": True, "rating": 4.8,
            "key_specs": "你3月前购买/订单ORDER-002/室内成猫/2kg",
            "sales": "月销6.8万",
        },
        "recommend": [
            {"product_id": "jd_rep_002n", "title": "皇家猫粮 肠胃敏感成猫 2kg 新口味",
             "price": 149.0, "is_jd_self": True, "rating": 4.9,
             "key_specs": "肠胃敏感配方/益生元/同品牌新款",
             "sales": "月销4.2万"},
            {"product_id": "jd_rep_002c", "title": "皇家宠物零食 冻干鸡肉粒 50g",
             "price": 39.9, "is_jd_self": True, "rating": 4.8,
             "key_specs": "冻干零食/纯鸡肉/低卡/配合猫粮使用",
             "sales": "月销3.1万"},
        ],
    },
    {
        "order_id": "ORDER-003",
        "purchase_months_ago": 1,
        "category_keyword": "维生素C",
        "product": {
            "product_id": "jd_rep_003",
            "title": "汤臣倍健 维生素C片 100片（1月前购买）",
            "price": 69.9, "is_jd_self": True, "rating": 4.9,
            "key_specs": "你1月前购买/订单ORDER-003/VC 500mg/100片装",
            "sales": "月销8.5万",
        },
        "recommend": [
            {"product_id": "jd_rep_003n", "title": "汤臣倍健 维生素C+锌 复合版 100片",
             "price": 89.9, "is_jd_self": True, "rating": 4.8,
             "key_specs": "VC+锌复合/同品牌升级款/增强免疫力更全面",
             "sales": "月销3.2万"},
        ],
    },
    {
        "order_id": "ORDER-004",
        "purchase_months_ago": 2,
        "category_keyword": "面膜",
        "product": {
            "product_id": "jd_rep_004",
            "title": "森田药妆 玻尿酸补水面膜 10片装（2月前购买）",
            "price": 59.9, "is_jd_self": True, "rating": 4.8,
            "key_specs": "你2月前购买/订单ORDER-004/玻尿酸/10片",
            "sales": "月销15万",
        },
        "recommend": [
            {"product_id": "jd_rep_004n", "title": "森田 烟酰胺美白淡斑面膜 10片 新款",
             "price": 69.9, "is_jd_self": True, "rating": 4.7,
             "key_specs": "烟酰胺/美白提亮/同品牌新功效款",
             "sales": "月销5.6万"},
            {"product_id": "jd_rep_004b", "title": "森田 补水面膜 30片大容量装",
             "price": 129.0, "is_jd_self": True, "rating": 4.8,
             "key_specs": "大容量30片/单价更低/坚持用效果更好",
             "sales": "月销4.1万"},
        ],
    },
    {
        "order_id": "ORDER-005",
        "purchase_months_ago": 4,
        "category_keyword": "蛋白粉",
        "product": {
            "product_id": "jd_rep_005",
            "title": "Optimum Nutrition 金标乳清蛋白 巧克力 908g（4月前购买）",
            "price": 299.0, "is_jd_self": True, "rating": 4.9,
            "key_specs": "你4月前购买/订单ORDER-005/乳清蛋白24g/瓶",
            "sales": "月销2.1万",
        },
        "recommend": [
            {"product_id": "jd_rep_005n", "title": "ON金标乳清蛋白 香草奶油 908g 新口味",
             "price": 299.0, "is_jd_self": True, "rating": 4.9,
             "key_specs": "香草新口味/同规格/换个口味不腻",
             "sales": "月销1.8万"},
            {"product_id": "jd_rep_005c", "title": "ON金标 肌酸粉 300g 训练补充",
             "price": 199.0, "is_jd_self": True, "rating": 4.8,
             "key_specs": "一水肌酸/增肌提力/配合蛋白粉效果更佳",
             "sales": "月销6500"},
        ],
    },
    {
        "order_id": "ORDER-006",
        "purchase_months_ago": 2,
        "category_keyword": "纸尿裤",
        "product": {
            "product_id": "jd_rep_006",
            "title": "花王 Merries 纸尿裤 M 号 56片（2月前购买）",
            "price": 139.0, "is_jd_self": True, "rating": 4.9,
            "key_specs": "你2月前购买/订单ORDER-006/花王M号/6-11kg",
            "sales": "月销11万",
        },
        "recommend": [
            {"product_id": "jd_rep_006l", "title": "花王 Merries 纸尿裤 L 号 54片",
             "price": 149.0, "is_jd_self": True, "rating": 4.9,
             "key_specs": "L号9-14kg/宝宝长大需升级/同品牌",
             "sales": "月销8.2万"},
            {"product_id": "jd_rep_006m", "title": "花王 Merries 纸尿裤 M 号 112片大包装",
             "price": 258.0, "is_jd_self": True, "rating": 4.9,
             "key_specs": "M号双倍装/更划算/同款大包",
             "sales": "月销4.5万"},
        ],
    },
    {
        "order_id": "ORDER-007",
        "purchase_months_ago": 1,
        "category_keyword": "咖啡豆",
        "product": {
            "product_id": "jd_rep_007",
            "title": "Lavazza Crema e Gusto 咖啡豆 1kg 意式浓郁（1月前购买）",
            "price": 189.0, "is_jd_self": True, "rating": 4.8,
            "key_specs": "你1月前购买/订单ORDER-007/意式拼配/1kg",
            "sales": "月销1.8万",
        },
        "recommend": [
            {"product_id": "jd_rep_007n", "title": "Lavazza Qualita Oro 精品咖啡豆 1kg 果味新款",
             "price": 219.0, "is_jd_self": True, "rating": 4.9,
             "key_specs": "果味花香/轻度烘焙/同品牌升级款",
             "sales": "月销9800"},
            {"product_id": "jd_rep_007s", "title": "星巴克 早餐综合咖啡豆 500g 换个风味",
             "price": 179.0, "is_jd_self": True, "rating": 4.7,
             "key_specs": "星巴克/早餐综合/中度烘焙/换个口味",
             "sales": "月销3.2万"},
        ],
    },
    {
        "order_id": "ORDER-008",
        "purchase_months_ago": 3,
        "category_keyword": "洗衣液",
        "product": {
            "product_id": "jd_rep_008",
            "title": "蓝月亮 深层洁净洗衣液 3kg 普通款（3月前购买）",
            "price": 59.9, "is_jd_self": True, "rating": 4.8,
            "key_specs": "你3月前购买/订单ORDER-008/蓝月亮/3kg装",
            "sales": "月销25万",
        },
        "recommend": [
            {"product_id": "jd_rep_008n", "title": "蓝月亮 花香柔顺护理洗衣液 3kg 2024新香型",
             "price": 69.9, "is_jd_self": True, "rating": 4.7,
             "key_specs": "花香新香型/柔顺护理/同品牌升级款",
             "sales": "月销6.8万"},
            {"product_id": "jd_rep_008b", "title": "蓝月亮 洗衣液 10kg 超大容量装",
             "price": 169.0, "is_jd_self": True, "rating": 4.8,
             "key_specs": "10kg超大装/性价比最高/减少购买频率",
             "sales": "月销4.5万"},
        ],
    },
    {
        "order_id": "ORDER-009",
        "purchase_months_ago": 2,
        "category_keyword": "打印纸",
        "product": {
            "product_id": "jd_rep_009",
            "title": "传美 A4打印纸 70g 500张/包 5包装（2月前购买）",
            "price": 89.9, "is_jd_self": True, "rating": 4.7,
            "key_specs": "你2月前购买/订单ORDER-009/A4/70g/2500张",
            "sales": "月销30万",
        },
        "recommend": [
            {"product_id": "jd_rep_009n", "title": "传美 A4复印纸 80g 500张 10包装",
             "price": 189.0, "is_jd_self": True, "rating": 4.8,
             "key_specs": "80g加厚/5000张超大量/按箱买更省",
             "sales": "月销18万"},
        ],
    },
    {
        "order_id": "ORDER-010",
        "purchase_months_ago": 1,
        "category_keyword": "矿泉水",
        "product": {
            "product_id": "jd_rep_010",
            "title": "农夫山泉 天然矿泉水 550ml 24瓶装（1月前购买）",
            "price": 29.9, "is_jd_self": True, "rating": 4.9,
            "key_specs": "你1月前购买/订单ORDER-010/550ml/24瓶",
            "sales": "月销50万",
        },
        "recommend": [
            {"product_id": "jd_rep_010n", "title": "农夫山泉 天然矿泉水 1.5L 12瓶装",
             "price": 35.9, "is_jd_self": True, "rating": 4.9,
             "key_specs": "1.5L大瓶/家用备用/桶装更环保",
             "sales": "月销22万"},
            {"product_id": "jd_rep_010e", "title": "农夫山泉 东方树叶 茶饮料 500ml 15瓶",
             "price": 39.9, "is_jd_self": True, "rating": 4.8,
             "key_specs": "同品牌茶饮料/零糖零卡/喝水的健康升级",
             "sales": "月销8.9万"},
        ],
    },
]


class SkuRepurchaseRecall:
    """
    SkuRepurchaseRecall 工具。

    对应真实项目：sku_recall_history（从历史购买记录中取回商品）。

    返回结构：
    {
        "status": "SUCCESS",
        "products": [历史商品（第一个）+ 推荐复购款]
    }
    第一个 product 的 title 和 key_specs 中标注「X月前购买/订单号」。
    """

    NAME = "SkuRepurchaseRecall"

    def __call__(self, ctx: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._mock_call(params)

    def _mock_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        keyword = params.get("category_keyword", "").lower()
        time_range = params.get("time_range", "")  # "last_3_months" 等
        max_months = self._parse_time_range(time_range)

        # 按 category_keyword 匹配
        matched = None
        for record in REPURCHASE_MOCK_POOL:
            rk = record["category_keyword"].lower()
            if keyword in rk or rk in keyword:
                if record["purchase_months_ago"] <= max_months:
                    matched = record
                    break

        # fallback：取第一条
        if not matched:
            matched = REPURCHASE_MOCK_POOL[0]

        products = [matched["product"]] + matched.get("recommend", [])
        return {
            "status": "SUCCESS",
            "products": products,
            "order_id": matched["order_id"],
            "purchase_months_ago": matched["purchase_months_ago"],
        }

    @staticmethod
    def _parse_time_range(tr: str) -> int:
        """将 time_range 字符串解析为月数"""
        if not tr:
            return 12
        if "1_month" in tr or "last_month" in tr:
            return 1
        if "2_month" in tr:
            return 2
        if "3_month" in tr:
            return 3
        if "6_month" in tr:
            return 6
        if "year" in tr or "12_month" in tr:
            return 12
        return 12
