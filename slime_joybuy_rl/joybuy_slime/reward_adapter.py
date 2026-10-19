"""Reward adapter that maps model completions to JoybuyMockEnv rewards."""

from __future__ import annotations

import re
from typing import Any, Dict

from joybuy_agent.react.environment import JoybuyMockEnv

try:
    from .action_parser import parse_actions
    from .llm_judge import apply_optional_llm_judge
except ImportError:  # Slime may load hook files with joybuy_slime on PYTHONPATH.
    from joybuy_slime.action_parser import parse_actions
    from joybuy_slime.llm_judge import apply_optional_llm_judge


def evaluate_completion(
    task: Dict[str, Any] | str,
    completion: str,
    *,
    max_steps: int = 5,
    tool_cost: float = 0.01,
    thinking_limit_tokens: int = 256,
    thinking_penalty_scale: float = 0.2,
) -> Dict[str, Any]:
    """Run a decoded completion through JoybuyMockEnv and return reward details.

    This function is intentionally framework-neutral so it can be used from:
    - Slime custom data generation,
    - a custom reward-model HTTP service,
    - local smoke tests.
    """
    env = JoybuyMockEnv(max_steps=max_steps, tool_cost=tool_cost)
    env.reset(task)

    terminal: Dict[str, Any] | None = None
    for action in parse_actions(completion):
        terminal = env.step(action)
        if terminal.get("done"):
            break

    if terminal is None or not terminal.get("done"):
        terminal = env.step({"type": "final", "content": _fallback_final(completion)})

    raw_reward = float(terminal.get("reward", 0.0))
    penalty = thinking_length_penalty(
        completion,
        limit_tokens=thinking_limit_tokens,
        scale=thinking_penalty_scale,
    )
    reward = round(raw_reward - penalty, 4)
    detail = dict(terminal.get("reward_detail") or {})
    detail.update({
        "raw_reward": raw_reward,
        "thinking_length_penalty": round(penalty, 4),
        "reward_after_penalty": reward,
    })
    result = {
        "reward": reward,
        "reward_detail": detail,
        "trajectory": terminal.get("trajectory"),
        "done": bool(terminal.get("done")),
    }
    return apply_optional_llm_judge(task, completion, result)


def thinking_length_penalty(
    text: str,
    *,
    limit_tokens: int = 256,
    scale: float = 0.2,
) -> float:
    """Approximate oxygen-style thinking length penalty.

    We estimate tokens as CJK chars plus whitespace-separated non-CJK chunks.
    The penalty is linear after the limit and capped by `scale`.
    """
    think_blocks = re.findall(r"<think>\s*([\s\S]*?)\s*</think>", text or "", re.IGNORECASE)
    if not think_blocks:
        return 0.0
    token_count = sum(_rough_token_count(block) for block in think_blocks)
    if token_count <= limit_tokens:
        return 0.0
    overflow_ratio = (token_count - limit_tokens) / max(limit_tokens, 1)
    return min(scale, scale * overflow_ratio)


def _rough_token_count(text: str) -> int:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text or ""))
    non_cjk = re.sub(r"[\u4e00-\u9fff]", " ", text or "")
    words = len(re.findall(r"\S+", non_cjk))
    return cjk + words


def _fallback_final(completion: str) -> str:
    cleaned = re.sub(r"<tool_call>[\s\S]*?</tool_call>", "", completion or "", flags=re.IGNORECASE)
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned or "Sorry, I could not complete the task."
