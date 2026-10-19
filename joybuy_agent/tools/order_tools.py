# -*- coding: utf-8 -*-
"""
订单相关工具：
- OrderQuerySkill    — 查询订单/物流/售后（对应 task_service_tools.query_order_detail / query_logistics_track）
- ShoppingPlaceOrderTool — 下单操作（对应 task_service_tools 下单 + 操作指引）
"""
from __future__ import annotations
import random
from typing import Any, Dict, List

# ─────────────────────────────────────────────
# 订单 Mock 池（10条）
# ─────────────────────────────────────────────
ORDER_MOCK_POOL: List[Dict[str, Any]] = [
    {
        "order_id": "ORDER-001",
        "product_name": "索尼WF-C700N 真无线降噪耳机",
        "product_id": "jd_10007001",
        "price": 399.0,
        "status": "已签收",
        "logistics": "顺丰快递 TRACKING-001 已于2026-06-23 14:30签收",
        "afs_eligible": True,
        "days_since_receipt": 5,
    },
    {
        "order_id": "ORDER-002",
        "product_name": "小米米家颈椎按摩仪 热敷款",
        "product_id": "jd_11223344",
        "price": 349.0,
        "status": "运输中",
        "logistics": "京东快递 TRACKING-002 已从北京分拣中心发出，预计明天送达",
        "afs_eligible": False,
        "days_since_receipt": 0,
    },
    {
        "order_id": "ORDER-003",
        "product_name": "苏泊尔钛系列不粘炒锅 32cm",
        "product_id": "jd_10009001",
        "price": 459.0,
        "status": "待发货",
        "logistics": "订单已生成，等待商家发货",
        "afs_eligible": False,
        "days_since_receipt": 0,
    },
    {
        "order_id": "ORDER-004",
        "product_name": "石头扫地机器人G20S Pro",
        "product_id": "jd_10005001",
        "price": 2999.0,
        "status": "已签收",
        "logistics": "顺丰快递 TRACKING-003 已于2026-06-05 10:20签收",
        "afs_eligible": True,
        "days_since_receipt": 22,
    },
    {
        "order_id": "ORDER-005",
        "product_name": "西昊 Doro C300 人体工学椅",
        "product_id": "jd_10006001",
        "price": 1499.0,
        "status": "已签收",
        "logistics": "德邦快递 TRACKING-004 已于2026-05-28 16:45签收",
        "afs_eligible": True,
        "days_since_receipt": 30,
    },
]

# ─────────────────────────────────────────────
# 操作场景模板（place_order 场景的操作步骤）
# ─────────────────────────────────────────────
OPERATION_TEMPLATES: Dict[str, str] = {
    "refund": (
        "## 申请退款/退货流程\n\n"
        "**操作路径**：京东 App → 我的订单 → 找到该订单 → 申请售后 → 选择「退货退款」\n\n"
        "**注意事项**：\n"
        "- 收货后 7 天内可无理由退货（大家电 3 天）\n"
        "- 填写退货原因 → 等待商家审核（1-2个工作日）\n"
        "- 审核通过后按页面指引打包发货\n"
        "- 退款 3-5 个工作日到账"
    ),
    "logistics": (
        "## 物流查询\n\n"
        "**已为你查询到最新物流信息**（见上方）\n\n"
        "**如果物流停滞超过3天**：\n"
        "- 京东 App → 我的订单 → 找到该订单 → 联系商家 → 催单\n"
        "- 或直接拨打顺丰客服：95338\n"
        "- 京东自营商品可申请「物流补偿」"
    ),
    "exchange": (
        "## 申请换货流程\n\n"
        "**操作路径**：京东 App → 我的订单 → 申请售后 → 选择「换货」\n\n"
        "**步骤**：\n"
        "1. 选择换货原因（颜色/规格/质量问题）\n"
        "2. 上传商品照片（建议拍外包装+商品全貌）\n"
        "3. 提交申请，等待商家审核\n"
        "4. 审核通过：原商品寄回 → 新商品发出（3-5天）\n\n"
        "⚠️ 换货需在收货后 **7天内** 申请"
    ),
    "price_protection": (
        "## 价保申请流程\n\n"
        "**操作路径**：京东 App → 我的订单 → 更多操作 → 价格保护\n\n"
        "**京东价保规则**：\n"
        "- 购买后 **30天内**，如商品降价可申请差价补偿\n"
        "- 仅限京东自营商品（第三方不适用）\n"
        "- 价保差价以「京东购物券」形式退还\n"
        "- 促销期降价不在价保范围内（如618/双11）"
    ),
    "invoice": (
        "## 申请发票流程\n\n"
        "**操作路径**：京东 App → 我的订单 → 开发票 → 选择「增值税专用发票」\n\n"
        "**填写内容**：\n"
        "| 字段 | 说明 |\n"
        "|---|---|\n"
        "| 发票抬头 | 公司全称（与营业执照一致）|\n"
        "| 税号 | 统一社会信用代码（18位）|\n"
        "| 地址 | 企业注册地址 |\n"
        "| 电话 | 企业联系电话 |\n"
        "| 开户行 | 企业银行开户行 |\n"
        "| 账号 | 企业银行账号 |\n\n"
        "⚠️ 增值税专用发票开具后 **不可修改**，请仔细核对"
    ),
    "cancel": (
        "## 取消订单流程\n\n"
        "**操作路径**：京东 App → 我的订单 → 找到该订单 → 取消订单\n\n"
        "**注意**：\n"
        "- 「待发货」状态可直接取消\n"
        "- 「运输中」状态需先拒收，再申请退款\n"
        "- 「已签收」状态只能申请退货（7天内）\n"
        "- 取消后款项 1-3 个工作日原路退回"
    ),
    "place_order": (
        "## 下单流程\n\n"
        "**操作路径**：商品详情页 → 选择规格/颜色 → 立即购买 → 确认收货地址 → 选择支付方式 → 提交订单\n\n"
        "**支付建议**：\n"
        "- 余额/白条：最快，无需跳转\n"
        "- 微信/支付宝：需要跳转 App\n"
        "- 银行卡：需输入密码，略慢\n\n"
        "**抢购技巧**（限量款）：\n"
        "- 提前加入购物车\n"
        "- 确认收货地址和支付方式\n"
        "- 发售瞬间点击「立即购买」\n"
        "- 10秒内完成支付"
    ),
}


class OrderQuerySkill:
    """
    OrderQuerySkill — 订单查询/售后操作工具。

    对应真实项目的：
    - task_service_tools.query_order_detail（订单详情）
    - task_service_tools.query_logistics_track（物流追踪）
    - task_service_tools.query_afs_service_detail（售后服务）
    """

    NAME = "OrderQuerySkill"

    def __call__(self, ctx: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._mock_call(params)

    def _mock_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        order_id = params.get("order_id", "")
        action = params.get("action", "query")
        issue_type = params.get("issue_type", "")

        # 按 order_id 查找
        order = None
        for o in ORDER_MOCK_POOL:
            if order_id and (order_id in o["order_id"] or o["order_id"] in order_id):
                order = o
                break
        if order is None:
            order = ORDER_MOCK_POOL[0]

        # 确定操作模板
        tmpl_key = "place_order"
        if issue_type or action in ("refund", "return"):
            tmpl_key = "refund" if "refund" in (issue_type + action) else "exchange"
        elif action == "logistics" or "logistic" in issue_type:
            tmpl_key = "logistics"
        elif action in ("exchange", "replace"):
            tmpl_key = "exchange"
        elif "price" in issue_type or action == "price_protection":
            tmpl_key = "price_protection"
        elif "invoice" in issue_type or "发票" in str(params):
            tmpl_key = "invoice"
        elif action in ("cancel", "取消"):
            tmpl_key = "cancel"

        operation_guide = OPERATION_TEMPLATES.get(tmpl_key, OPERATION_TEMPLATES["place_order"])

        return {
            "status": "SUCCESS",
            "products": [
                {
                    "product_id": order["product_id"],
                    "title": f"{order['product_name']} — 订单 {order['order_id']}",
                    "price": order["price"],
                    "is_jd_self": True,
                    "rating": 5.0,
                    "key_specs": (
                        f"订单状态:{order['status']}/"
                        f"{order['logistics'][:30]}/"
                        f"操作指引已生成"
                    ),
                    "sales": "—",
                }
            ],
            "order_detail": order,
            "operation_guide": operation_guide,
        }


class ShoppingPlaceOrderTool:
    """
    ShoppingPlaceOrderTool — 下单/预约/抢购工具。

    对应真实项目的：下单意图识别 + 商品详情确认 + 下单引导。
    """

    NAME = "ShoppingPlaceOrderTool"

    def __call__(self, ctx: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._mock_call(params)

    def _mock_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        product_id = params.get("product_id", "")
        action = params.get("action", "place_order")

        # 生成虚拟订单号
        order_id = f"TRACKING-005-{random.randint(1000000, 9999999)}"

        # 决定操作模板
        if action in ("prepare_for_release", "reservation"):
            tmpl_key = "place_order"
        elif action == "early_payoff":
            guide = (
                "## 提前还款操作\n\n"
                "**操作路径**：京东 App → 我的 → 京东白条 → 找到分期订单 → 提前还款\n\n"
                "**说明**：提前还款**无违约金**，额度立刻恢复。\n"
                "还清后可节省剩余期数利息（年化约6%）。"
            )
            tmpl_key = None
        else:
            tmpl_key = "place_order"

        if tmpl_key:
            guide = OPERATION_TEMPLATES.get(tmpl_key, OPERATION_TEMPLATES["place_order"])

        return {
            "status": "SUCCESS",
            "products": [
                {
                    "product_id": product_id or "jd_order_guide",
                    "title": f"操作指引 — {action}",
                    "price": 0,
                    "is_jd_self": True,
                    "rating": 5.0,
                    "key_specs": f"操作已完成/订单{order_id}/操作指引见回复",
                    "sales": "—",
                }
            ],
            "order_id": order_id,
            "operation_guide": guide,
        }
