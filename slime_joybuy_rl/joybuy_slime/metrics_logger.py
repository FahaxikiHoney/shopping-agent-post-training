"""JSONL metrics logging helpers for Joybuy RL rollouts."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict


_LOCK = threading.Lock()


def log_rollout_metric(
    task: Dict[str, Any],
    response: str,
    reward_result: Dict[str, Any],
    *,
    path: str | None = None,
) -> None:
    output_path = path or os.getenv("JOYBUY_RL_METRICS_PATH")
    if not output_path:
        return

    detail = reward_result.get("reward_detail") or {}
    judge = detail.get("llm_judge") or {}
    record = {
        "time": time.time(),
        "task_id": task.get("task_id") or task.get("sample_id") or "",
        "query": task.get("query") or task.get("user_query") or "",
        "site_code": task.get("site_code") or "",
        "scenario_type": task.get("scenario_type") or "",
        "reward": reward_result.get("reward"),
        "reward_type": detail.get("reward_type"),
        "raw_reward": detail.get("raw_reward"),
        "reward_after_llm_judge": detail.get("reward_after_llm_judge"),
        "judge_score": judge.get("score"),
        "judge_adjustment": judge.get("adjustment"),
        "judge_error": judge.get("error"),
        "tool_call_count": detail.get("tool_call_count"),
        "product_count": detail.get("product_count"),
        "card_count": detail.get("card_count"),
        "response_chars": len(response or ""),
        "has_think": "<think>" in (response or "").lower(),
        "issues": detail.get("issues") or [],
    }
    path_obj = Path(output_path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with _LOCK:
        with path_obj.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
