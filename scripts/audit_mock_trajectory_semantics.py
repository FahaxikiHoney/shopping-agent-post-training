#!/usr/bin/env python3
"""Audit complete Joybuy Mock trajectories with an independent LLM judge."""

from __future__ import annotations

import argparse
import json
import re
import socket
import time
import urllib.error
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from joybuy_agent.llm.client import LLMClient


SYSTEM_PROMPT = """You are a strict shopping-agent trajectory auditor.
Judge the final response only from the user query, site, tool calls, and tool results.

Use exactly one verdict per sample:
- pass: the response is useful and honest; every recommended product is relevant to the query; product facts are grounded in tool fields; empty or partial inventory is clearly acknowledged; the response language follows the query language (short ambiguous queries may use the site language).
- warn: the response is safe and relevant, but usefulness is limited by missing inventory, ambiguity, subjective preferences, dynamic data, or unavailable attributes. A clear disclaimer or clarification request prevents a fail.
- fail: the response recommends an irrelevant product, violates a hard constraint, invents unsupported product facts, makes an unqualified dynamic/current claim, uses the wrong response language, hides a missing bundle item, fabricates availability or external prices, or otherwise misrepresents tool results.

Do not fail merely because the response returns no products when the tools returned no suitable products. Do not require the Mock trajectory structure to match another system. Product titles, prices, sales labels, and currency may follow the site locale even when surrounding prose follows the query language.

Return ONLY a JSON array. Every object must contain sample_id, verdict, reason, and issue_tags (an array). Preserve sample_id exactly."""


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number} must contain a JSON object")
            rows.append(row)
    return rows


def extract_json_array(text: str) -> List[Dict[str, Any]]:
    candidates = [text.strip()]
    candidates.extend(re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, re.I))
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        candidates.append(text[start:end + 1])
    for candidate in reversed(candidates):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return value
    raise ValueError("model response does not contain a JSON array")


def _tool_result_by_call_id(messages: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    results = {}
    for message in messages:
        if message.get("role") != "tool":
            continue
        try:
            result = json.loads(message.get("content") or "{}")
        except (TypeError, json.JSONDecodeError):
            result = {"raw_content": str(message.get("content") or "")[:1000]}
        results[str(message.get("tool_call_id") or "")] = result
    return results


def _compact_tool_result(result: Dict[str, Any]) -> Dict[str, Any]:
    products = result.get("products") or []
    compact_products = []
    for product in products:
        compact_products.append({
            key: product.get(key)
            for key in (
                "sku_id", "sku_name", "brand_name", "final_price", "price",
                "sales", "keyword",
            )
            if key in product
        })
    compact = {
        key: result.get(key)
        for key in ("success", "status", "count", "summary", "within_budget")
        if key in result
    }
    if compact_products:
        compact["products"] = compact_products
    if result.get("items"):
        compact["items"] = result.get("items")
    return compact


def build_audit_item(row: Dict[str, Any]) -> Dict[str, Any]:
    sample = row.get("sample") or {}
    trajectory = row.get("trajectory") or {}
    messages = trajectory.get("messages") or []
    result_by_call = _tool_result_by_call_id(messages)
    tool_calls = []
    for message in messages:
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except (TypeError, json.JSONDecodeError):
                arguments = {"raw": str(function.get("arguments") or "")}
            tool_calls.append({
                "name": function.get("name"),
                "arguments": arguments,
                "result": _compact_tool_result(
                    result_by_call.get(str(call.get("id") or ""), {})
                ),
            })
    return {
        "sample_id": sample.get("sample_id") or sample.get("id"),
        "site_code": sample.get("site_code"),
        "query": sample.get("query") or trajectory.get("user_query"),
        "scenario_type": trajectory.get("scenario_type"),
        "tool_calls": tool_calls,
        "final_response": trajectory.get("final_response") or "",
    }


def summarize(results: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    return {
        verdict: sum(item.get("verdict") == verdict for item in results)
        for verdict in ("pass", "warn", "fail")
    }


def write_report(
    path: Path,
    model: str,
    input_path: Path,
    results: Sequence[Dict[str, Any]],
    complete: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "model": model,
            "input": str(input_path),
            "complete": complete,
            "summary": summarize(results),
            "results": list(results),
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _ordered_results(
    rows: Sequence[Dict[str, Any]],
    completed_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    ordered = []
    for row in rows:
        sample = row.get("sample") or {}
        sample_id = str(sample.get("sample_id") or sample.get("id") or "")
        if sample_id in completed_by_id:
            ordered.append(completed_by_id[sample_id])
    return ordered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit complete Joybuy Mock trajectories with an independent LLM judge.",
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="GLM-5.2")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--retries", type=int, default=6)
    parser.add_argument("--retry-delay", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    rows = [
        row for row in load_jsonl(input_path)
        if (row.get("trajectory") or {}).get("status") == "done"
    ]
    completed_by_id: Dict[str, Dict[str, Any]] = {}
    if args.resume and output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        completed_by_id = {
            str(item.get("sample_id")): item
            for item in existing.get("results") or []
        }

    pending = []
    for row in rows:
        item = build_audit_item(row)
        if str(item.get("sample_id")) not in completed_by_id:
            pending.append(item)

    client = LLMClient(model=args.model)
    for offset in range(0, len(pending), args.batch_size):
        payload = pending[offset:offset + args.batch_size]
        expected_ids = {str(item["sample_id"]) for item in payload}
        prompt = "Audit these complete shopping trajectories:\n" + json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        for attempt in range(1, args.retries + 1):
            try:
                content, thinking = client.generate(
                    SYSTEM_PROMPT,
                    prompt,
                    temperature=0.0,
                )
                parsed = extract_json_array(f"{content}\n{thinking}")
                actual_ids = {str(item.get("sample_id")) for item in parsed}
                if expected_ids != actual_ids:
                    raise ValueError(
                        f"sample id mismatch: missing={sorted(expected_ids - actual_ids)}, "
                        f"extra={sorted(actual_ids - expected_ids)}"
                    )
                verdicts = {str(item.get("sample_id")): item for item in parsed}
                for audit_item in payload:
                    sample_id = str(audit_item["sample_id"])
                    completed_by_id[sample_id] = {
                        **audit_item,
                        **verdicts[sample_id],
                    }
                write_report(
                    output_path,
                    args.model,
                    input_path,
                    _ordered_results(rows, completed_by_id),
                    False,
                )
                print(
                    f"batch {offset // args.batch_size + 1}: audited {len(payload)} trajectories",
                    flush=True,
                )
                break
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                socket.timeout,
                TimeoutError,
                ValueError,
            ) as error:
                if attempt == args.retries:
                    raise
                delay = args.retry_delay * attempt
                print(f"retryable audit error: {error}; retrying in {delay}s", flush=True)
                time.sleep(delay)

    ordered = _ordered_results(rows, completed_by_id)
    write_report(output_path, args.model, input_path, ordered, True)
    print(json.dumps({"summary": summarize(ordered)}, ensure_ascii=False))
    return 1 if any(item.get("verdict") == "fail" for item in ordered) else 0


if __name__ == "__main__":
    raise SystemExit(main())
