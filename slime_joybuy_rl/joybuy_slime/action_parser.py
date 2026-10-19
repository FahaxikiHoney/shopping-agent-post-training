"""Parse model text into Joybuy environment actions.

The SFT data teaches the model to emit OpenAI-style tool calls wrapped in
<tool_call>...</tool_call>. During RL rollout we keep that contract: a decoded
assistant chunk can either contain one or more tool calls, or be treated as the
final user-facing response.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List


TOOL_CALL_RE = re.compile(r"<tool_call>\s*([\s\S]*?)\s*</tool_call>", re.IGNORECASE)


def strip_thinking(text: str) -> str:
    """Remove <think> blocks before parsing actions."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text or "", flags=re.IGNORECASE).strip()


def parse_actions(text: str) -> List[Dict[str, Any]]:
    """Return environment actions from a model completion.

    Accepted tool-call shapes:
    - <tool_call>{"name": "sku_recall", "arguments": {"query": "..."}}</tool_call>
    - {"type": "tool_call", "name": "...", "arguments": {...}}

    If no valid tool call is found, the remaining text is a final action.
    """
    clean = strip_thinking(text)
    actions: List[Dict[str, Any]] = []

    for match in TOOL_CALL_RE.finditer(clean):
        action = _parse_tool_payload(match.group(1))
        if action:
            actions.append(action)

    if actions:
        return actions

    direct = _parse_tool_payload(clean)
    if direct:
        return [direct]

    return [{"type": "final", "content": clean}]


def _parse_tool_payload(payload: str) -> Dict[str, Any] | None:
    payload = (payload or "").strip()
    if not payload:
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None

    function = parsed.get("function") if isinstance(parsed.get("function"), dict) else {}
    name = parsed.get("name") or function.get("name")
    arguments = parsed.get("arguments", function.get("arguments", {}))
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    if not isinstance(name, str) or not isinstance(arguments, dict):
        return None
    return {"type": "tool_call", "name": name, "arguments": arguments}
