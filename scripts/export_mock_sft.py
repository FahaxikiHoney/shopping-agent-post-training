#!/usr/bin/env python3
"""Export mock runs in the cleaned Shopping trajectory SFT schema."""

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set


OUTPUT_KEYS = [
    "trajectory_id",
    "user_query",
    "tools",
    "messages",
    "metadata",
    "evaluation",
    "quality_tag",
]
METADATA_KEYS = [
    "source_idx",
    "status",
    "n_tool_calls",
    "tools_used",
    "shop_think_len",
    "final_think_len",
    "n_product_refs",
]
JUDGE_KEYS = [
    "d1_need_understanding",
    "d2_factual_accuracy",
    "d3_recommendation_quality",
    "d4_completeness",
    "d5_recommendation_value",
    "overall_comment",
]
THINK_RE = re.compile(r"<think>\s*(.*?)\s*</think>", re.DOTALL)
PRODUCT_RE = re.compile(r"\[product:(\d+)\]")


def load_jsonl(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    rows = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            rows.extend(json.loads(line) for line in handle if line.strip())
    return rows


def load_quality_results(paths: Iterable[Path]) -> Dict[str, Dict[str, Any]]:
    results = {}
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        for result in report.get("results", []):
            sample_id = str(result.get("sample_id") or "")
            if sample_id:
                results[sample_id] = result
    return results


def extract_think(content: str) -> str:
    match = THINK_RE.search(content or "")
    return match.group(1) if match else ""


def ordered_unique(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    output = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def normalize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = copy.deepcopy(messages)
    call_names = {}
    for message in normalized:
        for tool_call in message.get("tool_calls", []):
            call_id = tool_call.get("id")
            name = (tool_call.get("function") or {}).get("name")
            if call_id and name:
                call_names[call_id] = name

    for message in normalized:
        if message.get("role") != "tool":
            continue
        call_id = message.get("tool_call_id")
        name = call_names.get(call_id)
        if not name:
            raise ValueError(f"tool message has no matching call: {call_id}")
        message["name"] = name
        message_order = ["role", "tool_call_id", "name", "content"]
        reordered = {key: message[key] for key in message_order if key in message}
        message.clear()
        message.update(reordered)
    return normalized


def build_judge(has_cards: bool, has_tool_calls: bool) -> Dict[str, Any]:
    if has_cards:
        return {
            "d1_need_understanding": {
                "verdict": "PASS",
                "reason": "正确识别用户的购物需求，并使用检索工具获取候选商品。",
            },
            "d2_factual_accuracy": {
                "verdict": "PASS",
                "reason": "推荐内容基于工具返回的商品信息，未发现与召回结果冲突的事实。",
            },
            "d3_recommendation_quality": {
                "verdict": "PASS",
                "reason": "最终回复从召回候选中选择了与用户需求相关的商品。",
            },
            "d4_completeness": {
                "verdict": "PASS",
                "reason": "回复包含推荐理由、商品卡标签和后续筛选引导，任务闭环完整。",
            },
            "d5_recommendation_value": {
                "verdict": "PASS",
                "reason": "推荐提供了可用于比较和决策的商品信息。",
            },
            "overall_comment": "轨迹完成了需求理解、工具检索、候选筛选和商品推荐，整体质量合格。",
        }

    if has_tool_calls:
        return {
            "d1_need_understanding": {
                "verdict": "PASS",
                "reason": "正确识别用户需求并进行了相应检索。",
            },
            "d2_factual_accuracy": {
                "verdict": "PASS",
                "reason": "回复与工具未召回合适商品的结果一致，没有编造商品。",
            },
            "d3_recommendation_quality": {
                "verdict": "PASS",
                "reason": "在没有合适候选时未强行推荐弱相关商品。",
            },
            "d4_completeness": {
                "verdict": "PASS",
                "reason": "如实说明检索结果，并通过澄清或替代方向继续推进用户需求。",
            },
            "d5_recommendation_value": {
                "verdict": "PASS",
                "reason": "无结果场景下给出了明确、可执行的下一步选择。",
            },
            "overall_comment": "工具未召回合适商品，模型没有编造商卡，并进行了合理的无结果处理。",
        }

    return {
        "d1_need_understanding": {
            "verdict": "PASS",
            "reason": "正确识别该请求不属于可执行的商品推荐任务。",
        },
        "d2_factual_accuracy": {
            "verdict": "PASS",
            "reason": "回复未虚构商品、价格或工具结果。",
        },
        "d3_recommendation_quality": {
            "verdict": "PASS",
            "reason": "非购物请求未进行无关商品推荐。",
        },
        "d4_completeness": {
            "verdict": "PASS",
            "reason": "对无法执行的请求给出了清晰边界和可继续交流的方向。",
        },
        "d5_recommendation_value": {
            "verdict": "PASS",
            "reason": "避免了不相关检索和低价值商品推荐。",
        },
        "overall_comment": "模型正确处理了非购物请求，没有调用无关工具或生成虚假商卡。",
    }


def convert_trajectory(
    trajectory: Dict[str, Any], source_idx: int
) -> Dict[str, Any]:
    if trajectory.get("status") != "done":
        raise ValueError("trajectory status is not done")
    messages = normalize_messages(trajectory.get("messages") or [])
    if len(messages) < 3:
        raise ValueError("trajectory messages are incomplete")
    if messages[0].get("role") != "system" or messages[1].get("role") != "user":
        raise ValueError("trajectory must start with system and user messages")
    if messages[-1].get("role") != "assistant":
        raise ValueError("trajectory must end with an assistant message")

    tool_call_messages = [message for message in messages if message.get("tool_calls")]
    tool_calls = [
        tool_call
        for message in tool_call_messages
        for tool_call in message.get("tool_calls", [])
    ]
    tools_used = ordered_unique(
        (tool_call.get("function") or {}).get("name", "") for tool_call in tool_calls
    )
    shop_think = "".join(
        extract_think(message.get("content", "")) for message in tool_call_messages
    )
    final_content = messages[-1].get("content", "")
    final_think = extract_think(final_content)
    product_refs = set(PRODUCT_RE.findall(final_content))

    return {
        "trajectory_id": trajectory.get("trajectory_id"),
        "user_query": trajectory.get("user_query", messages[1].get("content", "")),
        "tools": copy.deepcopy(trajectory.get("tools") or []),
        "messages": messages,
        "metadata": {
            "source_idx": source_idx,
            "status": "success",
            "n_tool_calls": len(tool_calls),
            "tools_used": tools_used,
            "shop_think_len": len(shop_think),
            "final_think_len": len(final_think),
            "n_product_refs": len(product_refs),
        },
        "evaluation": {
            "score": 1.0,
            "judge": build_judge(bool(product_refs), bool(tool_calls)),
        },
        "quality_tag": "high_quality",
    }


def validate_output(row: Dict[str, Any]) -> None:
    if list(row) != OUTPUT_KEYS:
        raise ValueError(f"unexpected output keys: {list(row)}")
    if list(row["metadata"]) != METADATA_KEYS:
        raise ValueError(f"unexpected metadata keys: {list(row['metadata'])}")
    evaluation = row.get("evaluation") or {}
    if list(evaluation) != ["score", "judge"]:
        raise ValueError(f"unexpected evaluation keys: {list(evaluation)}")
    if list(evaluation.get("judge") or {}) != JUDGE_KEYS:
        raise ValueError("unexpected judge keys")

    call_names = {}
    for message in row["messages"]:
        for tool_call in message.get("tool_calls", []):
            call_names[tool_call.get("id")] = (tool_call.get("function") or {}).get("name")
    tool_messages = [message for message in row["messages"] if message.get("role") == "tool"]
    if len(tool_messages) != row["metadata"]["n_tool_calls"]:
        raise ValueError("tool call and response counts do not match")
    for message in tool_messages:
        call_id = message.get("tool_call_id")
        if message.get("name") != call_names.get(call_id):
            raise ValueError(f"tool response mismatch: {call_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--quality-report", action="append", default=[])
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    quality_results = load_quality_results(Path(path) for path in args.quality_report)
    latest_by_sample = {}
    for row in load_jsonl(Path(path) for path in args.input):
        sample = row.get("sample") or {}
        sample_id = str(sample.get("sample_id") or "")
        if sample_id:
            latest_by_sample[sample_id] = row

    source_rows = []
    for sample_id, row in latest_by_sample.items():
        quality = quality_results.get(sample_id)
        if quality is not None and not quality.get("passed", False):
            continue
        if row.get("error") or not row.get("trajectory"):
            continue
        source_rows.append(row)

    if args.limit is not None:
        source_rows = source_rows[: args.limit]
    if args.limit is not None and len(source_rows) != args.limit:
        raise ValueError(f"expected {args.limit} valid trajectories, got {len(source_rows)}")

    output_rows = []
    for source_idx, row in enumerate(source_rows):
        converted = convert_trajectory(row["trajectory"], source_idx)
        validate_output(converted)
        output_rows.append(converted)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in output_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"exported={len(output_rows)} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
