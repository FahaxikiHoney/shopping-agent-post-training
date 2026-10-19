# -*- coding: utf-8 -*-
"""
shopping_agent/tools/__init__.py

统一注册所有工具到全局 ToolRegistry。

使用方式：
    from shopping_agent.tools import create_registry
    registry = create_registry()
    result = registry.call("SkuRecallShopping", ctx, {"query": "耳机"})
"""
from shopping_agent.core.tool_registry import ToolRegistry
from shopping_agent.tools.sku_recall import SkuRecallShopping
from shopping_agent.tools.sku_repurchase import SkuRepurchaseRecall
from shopping_agent.tools.order_tools import OrderQuerySkill, ShoppingPlaceOrderTool
from shopping_agent.tools.calculator import PythonCalculator


def create_registry() -> ToolRegistry:
    """创建并返回已注册所有工具的 ToolRegistry 实例。"""
    registry = ToolRegistry()

    sku_recall = SkuRecallShopping()
    registry.register("SkuRecallShopping", sku_recall)

    sku_repurchase = SkuRepurchaseRecall()
    registry.register("SkuRepurchaseRecall", sku_repurchase)

    order_query = OrderQuerySkill()
    registry.register("OrderQuerySkill", order_query)

    place_order = ShoppingPlaceOrderTool()
    registry.register("ShoppingPlaceOrderTool", place_order)

    calculator = PythonCalculator()
    registry.register("PythonCalculator", calculator)

    return registry


__all__ = [
    "create_registry",
    "SkuRecallShopping",
    "SkuRepurchaseRecall",
    "OrderQuerySkill",
    "ShoppingPlaceOrderTool",
    "PythonCalculator",
]
