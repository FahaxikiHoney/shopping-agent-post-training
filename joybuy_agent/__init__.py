# -*- coding: utf-8 -*-
"""
JoySage Agent Framework

轻量级购物 Agent 框架，对应真实 joybuy-chatbot 项目的 oxygent 架构。

对应关系：
  OxyRequest     ←→  AgentContext
  FunctionHub    ←→  ToolRegistry
  WorkflowAgent  ←→  ShoppingAgent
  @hub.tool()    ←→  registry.register()
"""
from joybuy_agent.core.context import AgentContext
from joybuy_agent.core.tool_registry import ToolRegistry
from joybuy_agent.core.agent import ShoppingAgent

__all__ = ["AgentContext", "ToolRegistry", "ShoppingAgent"]
