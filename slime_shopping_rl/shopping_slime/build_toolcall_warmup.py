"""Build a tool-call-only warmup SFT set from Shopping ReAct data."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from shopping_agent.react.agent import SYSTEM_PROMPT_TRAIN


TOOL_CALL_RE = re.compile(r"<tool_call>\s*([\s\S]*?)\s*</tool_call>", re.IGNORECASE)


def build_records(input_path: Path, limit: int = 0) -> List[Dict[str, Any]]:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{input_path} must contain a JSON array")

    records: List[Dict[str, Any]] = []
    for item in data:
        conversations = item.get("conversations") or []
        user_query = ""
        first_tool_answer = ""
        for turn in conversations:
            role = turn.get("from")
            content = str(turn.get("value") or "")
            if role == "human" and not content.startswith("<tool_response>") and not user_query:
                user_query = content.strip()
            if role == "gpt" and "<tool_call>" in content:
                first_tool_answer = normalize_tool_answer(content)
                break
        if not user_query or not first_tool_answer:
            continue
        records.append({
            "conversations": [
                {"from": "system", "value": SYSTEM_PROMPT_TRAIN},
                {"from": "human", "value": user_query},
                {"from": "gpt", "value": first_tool_answer},
            ],
            "_meta": {
                "source": "toolcall_warmup",
                "user_query": user_query,
            },
        })
        if limit and len(records) >= limit:
            break
    return records


def normalize_tool_answer(content: str) -> str:
    think = ""
    think_match = re.search(r"<think>\s*([\s\S]*?)\s*</think>", content, re.IGNORECASE)
    if think_match:
        think = think_match.group(1).strip()

    calls = []
    for match in TOOL_CALL_RE.finditer(content):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        name = str(payload.get("name") or "")
        arguments = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
        if name == "sku_recall":
            query = str(arguments.get("query") or "").strip()
            if not query:
                continue
            arguments = {"query": query}
        calls.append({"name": name, "arguments": arguments})

    if not calls:
        return ""
    parts = []
    if think:
        parts.append(f"<think>\n{think}\n</think>")
    for call in calls[:2]:
        parts.append(
            "<tool_call>\n"
            + json.dumps(call, ensure_ascii=False)
            + "\n</tool_call>"
        )
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    records = build_records(Path(args.input), args.limit)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(records)} warmup records to {output}")


if __name__ == "__main__":
    main()
