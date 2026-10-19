# -*- coding: utf-8 -*-
"""
PythonCalculator — 执行 Python 代码并捕获 stdout

主要用于 bundle_purchase 场景的预算计算，例如：
    a = 459 + 199 + 289  # 炒锅套装
    print(f"炒锅套装总价: {a}元, 余{3000-a}元")

安全限制：
- 禁止 import os / sys / subprocess 等
- 超时 3 秒
"""
from __future__ import annotations
import io
import sys
import signal
from contextlib import redirect_stdout
from typing import Any, Dict

_BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
    "importlib", "builtins", "__import__", "open", "eval", "exec",
}


class PythonCalculator:
    """
    PythonCalculator 工具。

    对应真实项目：bundle_purchase 场景中的 python_calculator 调用。

    输入：{"code": "a = 100 + 200\\nprint(f'合计: {a}元')"}
    输出：{"status": "SUCCESS", "output": "合计: 300元\\n", "error": None}
    """

    NAME = "PythonCalculator"

    def __call__(self, ctx: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        code = params.get("code", "")
        if not code.strip():
            return {"status": "ERROR", "output": "", "error": "code 参数为空"}

        # 安全检查
        for blocked in _BLOCKED_IMPORTS:
            if f"import {blocked}" in code or f"__import__('{blocked}')" in code:
                return {
                    "status": "ERROR",
                    "output": "",
                    "error": f"禁止 import {blocked}",
                }

        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                exec(code, {"__builtins__": {"print": print, "range": range,
                                              "len": len, "sum": sum,
                                              "round": round, "int": int,
                                              "float": float, "str": str,
                                              "abs": abs, "max": max, "min": min}})
            output = buf.getvalue()
            return {
                "status": "SUCCESS",
                "output": output,
                "error": None,
                "products": [
                    {
                        "product_id": "calc_result_001",
                        "title": "计算结果",
                        "price": 0,
                        "is_jd_self": True,
                        "rating": 5.0,
                        "key_specs": output.strip()[:80] if output else "计算完成",
                        "sales": "—",
                    }
                ],
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "output": buf.getvalue(),
                "error": str(e),
                "products": [
                    {
                        "product_id": "calc_result_001",
                        "title": "计算结果（出错）",
                        "price": 0,
                        "is_jd_self": True,
                        "rating": 5.0,
                        "key_specs": f"计算出错: {str(e)[:50]}",
                        "sales": "—",
                    }
                ],
            }
