"""Slime custom_generate hook for Shopping multi-turn rollout.

Wire this file with Slime's `--custom-generate-function-path`.
It keeps the model-facing rollout on the SGLang router, while tool execution
and terminal reward come from ShoppingMockEnv.
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
from typing import Any, Dict, List

from transformers import AutoTokenizer

from shopping_agent.react.agent import SYSTEM_PROMPT_TRAIN
from shopping_agent.react.environment import ShoppingMockEnv
try:
    from .action_parser import parse_actions
    from .llm_judge import apply_optional_llm_judge
    from .metrics_logger import log_rollout_metric
    from .reward_adapter import thinking_length_penalty
except ImportError:
    from shopping_slime.action_parser import parse_actions
    from shopping_slime.llm_judge import apply_optional_llm_judge
    from shopping_slime.metrics_logger import log_rollout_metric
    from shopping_slime.reward_adapter import thinking_length_penalty


TOKENIZER = None


async def generate(args, sample, sampling_params):
    """Slime custom generation entrypoint."""
    global TOKENIZER
    if TOKENIZER is None:
        TOKENIZER = AutoTokenizer.from_pretrained(args.hf_checkpoint, trust_remote_code=True)

    metadata = dict(getattr(sample, "metadata", None) or {})
    task = {
        "query": metadata.get("query") or _prompt_to_query(getattr(sample, "prompt", "")),
        "site_code": metadata.get("site_code") or "UK-Site",
        "scenario_type": metadata.get("scenario_type") or "search_recommend",
        "task_id": metadata.get("task_id") or "",
    }
    env = ShoppingMockEnv(max_steps=int(getattr(args, "shopping_max_steps", 5)))
    observation = env.reset(task)
    messages: List[Dict[str, Any]] = list(observation["messages"])
    response_texts: List[str] = []
    terminal = None

    for _ in range(env.max_steps):
        prompt = _apply_chat_template(messages)
        output = await _sglang_generate(args, prompt, sampling_params)
        text = str(output.get("text") or "")
        response_texts.append(text)
        actions = parse_actions(text)
        if not actions:
            actions = [{"type": "final", "content": text}]

        for action in actions:
            terminal = env.step(action)
            if action["type"] == "tool_call":
                messages = list(terminal["messages"])
            if terminal.get("done"):
                break
        if terminal and terminal.get("done"):
            break

    if terminal is None or not terminal.get("done"):
        terminal = env.step({"type": "final", "content": "".join(response_texts)})

    response = "\n".join(response_texts)
    prompt_text = _apply_chat_template(env.messages[:2])
    prompt_ids = TOKENIZER(prompt_text, add_special_tokens=False)["input_ids"]
    response_ids = TOKENIZER(response, add_special_tokens=False)["input_ids"]

    sample.tokens = prompt_ids + response_ids
    sample.response_length = len(response_ids)
    sample.response = response
    reward_result = {
        "reward": float(terminal.get("reward", 0.0)) - thinking_length_penalty(response),
        "reward_detail": terminal.get("reward_detail") or {},
        "trajectory": terminal.get("trajectory"),
        "done": bool(terminal.get("done")),
    }
    reward_result = apply_optional_llm_judge(task, response, reward_result)
    log_rollout_metric(task, response, reward_result)
    sample.reward = float(reward_result.get("reward", 0.0))
    sample.metadata = {
        **metadata,
        "reward_detail": reward_result.get("reward_detail") or {},
        "trajectory": reward_result.get("trajectory"),
    }
    _set_completed_status(sample)
    return sample


def _apply_chat_template(messages: List[Dict[str, Any]]) -> str:
    return TOKENIZER.apply_chat_template(
        messages,
        tools=None,
        tokenize=False,
        add_generation_prompt=True,
    )


async def _sglang_generate(args, prompt: str, sampling_params) -> Dict[str, Any]:
    url = f"http://{args.sglang_router_ip}:{args.sglang_router_port}/generate"
    payload = {
        "text": prompt,
        "sampling_params": dict(sampling_params),
    }
    return await asyncio.to_thread(_post_json, url, payload)


def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _prompt_to_query(prompt: Any) -> str:
    if isinstance(prompt, list):
        for turn in prompt:
            if isinstance(turn, dict) and turn.get("role") == "user":
                return str(turn.get("content") or "")
    return str(prompt or "")


def _set_completed_status(sample) -> None:
    try:
        from slime.utils.types import Sample

        sample.status = Sample.Status.COMPLETED
    except Exception:
        sample.status = "completed"
