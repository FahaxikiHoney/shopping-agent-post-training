# -*- coding: utf-8 -*-
"""
AgentContext — 对应真实项目的 OxyRequest（轻量版）

真实 OxyRequest 关键字段：
  arguments    → 工具参数（本框架通过 registry.call 的 params 传递）
  shared_data  → trace 内共享暂存空间 ← 保留
  group_data   → session 级共享     ← 简化为 history
  caller/callee → 调用链标识        ← 省略（单线程无需）
  mas          → MAS 运行时         ← 省略（用 ToolRegistry 替代）
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentContext:
    """
    单次 Agent 调用的上下文容器。

    Attributes:
        user_query:   用户原始问题
        shared_data:  同一执行链内共享的暂存数据（对应 oxy_request.shared_data）
        history:      多轮对话历史 [{"role": "user"/"assistant", "content": str}]
        site_code:    站点标识（海外默认 "oversea"）
        currency_code: 货币代码
    """
    user_query: str
    shared_data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, str]] = field(default_factory=list)
    site_code: str = "oversea"
    currency_code: str = "USD"

    # ── shared_data 便捷方法（对应 oxy_request.get/set_shared_data）──

    def get(self, key: str, default: Any = None) -> Any:
        return self.shared_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.shared_data[key] = value
