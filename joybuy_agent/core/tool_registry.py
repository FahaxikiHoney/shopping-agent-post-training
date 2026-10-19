# -*- coding: utf-8 -*-
"""
ToolRegistry — 对应真实项目的 FunctionHub（轻量版）

真实 FunctionHub：
  @hub.tool(description="...") 装饰器注册
  sync 函数自动包装为 async（loop.run_in_executor）
  await oxy_request.call(callee, arguments) 触发

本框架：
  registry.register(name, fn) 注册
  registry.call(name, ctx, params) 触发（同步）
"""
from __future__ import annotations
from typing import Any, Callable, Dict


class ToolRegistry:
    """
    工具注册中心。

    使用方式：
        registry = ToolRegistry()

        def my_tool(query: str, max_price: float = 0) -> dict:
            ...

        registry.register("SkuRecallShopping", my_tool)
        result = registry.call("SkuRecallShopping", ctx, {"query": "耳机"})
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, fn: Callable) -> None:
        """注册工具函数。对应真实项目的 @hub.tool(description=...) 装饰器。"""
        self._tools[name] = fn

    def call(self, name: str, ctx: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用已注册的工具。

        对应真实项目的：
            response = await oxy_request.call(callee=name, arguments=params)
            result = parse_json_dict_or_empty(response.output)

        Args:
            name:   工具注册名（如 "SkuRecallShopping"）
            ctx:    AgentContext
            params: 工具参数 dict

        Returns:
            工具函数的返回值 dict；出错时返回 {"status": "ERROR", "error": str}
        """
        fn = self._tools.get(name)
        if fn is None:
            return {"status": "ERROR", "error": f"未注册的工具: {name}"}
        try:
            return fn(ctx, params)
        except Exception as exc:
            return {"status": "ERROR", "error": str(exc), "_error_type": type(exc).__name__}

    def list_tools(self) -> list:
        return list(self._tools.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._tools
