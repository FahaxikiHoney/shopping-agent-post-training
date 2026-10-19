"""Optional OpenAI-compatible LLM judge for Joybuy RL rewards."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping


@dataclass(frozen=True)
class LLMJudgeConfig:
    api_key: str = ""
    api_base: str = "https://tokenhub.tencentmaas.com/v1"
    model: str = "deepseek/deepseek-v4-flash"
    timeout: float = 60.0
    enabled: bool = False
    adjustment_scale: float = 0.2

    @classmethod
    def from_env(cls) -> "LLMJudgeConfig":
        api_key = os.getenv("JUDGE_API_KEY") or os.getenv("TENCENTMAAS_API_KEY") or ""
        enabled = (os.getenv("USE_LLM_JUDGE") or "0") == "1"
        return cls(
            api_key=api_key,
            api_base=(os.getenv("JUDGE_API_BASE") or cls.api_base).rstrip("/"),
            model=os.getenv("JUDGE_MODEL") or cls.model,
            timeout=float(os.getenv("JUDGE_TIMEOUT") or cls.timeout),
            enabled=enabled and bool(api_key),
            adjustment_scale=float(os.getenv("JUDGE_ADJUSTMENT_SCALE") or cls.adjustment_scale),
        )


def apply_optional_llm_judge(
    task: Dict[str, Any] | str,
    completion: str,
    result: Dict[str, Any],
    *,
    config: LLMJudgeConfig | None = None,
    requester: Callable[[str, Mapping[str, str], Dict[str, Any], float], Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Add an LLM judge adjustment to an existing rule-reward result.

    Hard failures remain hard failures: the judge can make a negative rule
    reward more negative, but it cannot turn it positive.
    """
    config = config or LLMJudgeConfig.from_env()
    if not config.enabled:
        detail = dict(result.get("reward_detail") or {})
        detail.setdefault("llm_judge", {"enabled": False})
        return {**result, "reward_detail": detail}

    detail = dict(result.get("reward_detail") or {})
    try:
        judge = judge_completion(task, completion, result, config=config, requester=requester)
        base_reward = float(result.get("reward", 0.0))
        score = float(judge["score"])
        adjustment = round((score * 2.0 - 1.0) * config.adjustment_scale, 4)
        reward = round(max(-1.0, min(1.0, base_reward + adjustment)), 4)
        if base_reward < 0:
            reward = min(base_reward, reward)
        detail["llm_judge"] = {
            "enabled": True,
            "model": config.model,
            "score": score,
            "adjustment": adjustment,
            "reason": judge.get("reason", ""),
        }
        detail["reward_after_llm_judge"] = reward
        return {**result, "reward": reward, "reward_detail": detail}
    except Exception as exc:
        detail["llm_judge"] = {
            "enabled": True,
            "model": config.model,
            "error": str(exc),
        }
        return {**result, "reward_detail": detail}


def judge_completion(
    task: Dict[str, Any] | str,
    completion: str,
    result: Dict[str, Any],
    *,
    config: LLMJudgeConfig,
    requester: Callable[[str, Mapping[str, str], Dict[str, Any], float], Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    requester = requester or _post_json
    url = f"{config.api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": _judge_system_prompt()},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": task,
                        "completion": completion,
                        "rule_reward": result.get("reward"),
                        "rule_reward_detail": result.get("reward_detail"),
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "stream": False,
        "temperature": 0,
    }
    response = requester(url, headers, payload, config.timeout)
    content = _chat_content(response)
    return _parse_judge_json(content)


def _judge_system_prompt() -> str:
    return (
        "You are a strict shopping-agent reward judge. Return only JSON with keys "
        "score and reason. score must be a number from 0 to 1. Grade whether the "
        "assistant answer follows the user need, uses product cards correctly, is "
        "grounded in the tool/reward context, avoids unsupported claims, and is "
        "concise. Do not reward hidden thinking, malformed product cards, or "
        "recommendations without evidence."
    )


def _post_json(
    url: str,
    headers: Mapping[str, str],
    payload: Dict[str, Any],
    timeout: float,
) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"judge http {exc.code}: {body[:500]}") from exc


def _chat_content(response: Dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        raise ValueError("judge response has no choices")
    message = choices[0].get("message") or {}
    content = str(message.get("content") or "").strip()
    if not content:
        raise ValueError("judge response content is empty")
    return content


def _parse_judge_json(content: str) -> Dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        raise ValueError(f"judge did not return JSON: {content[:200]}")
    data = json.loads(match.group(0))
    score = max(0.0, min(1.0, float(data.get("score", 0.0))))
    reason = str(data.get("reason") or "")[:500]
    return {"score": score, "reason": reason}
