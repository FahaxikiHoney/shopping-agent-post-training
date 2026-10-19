#!/usr/bin/env python3
"""Use an independent LLM judge to audit non-empty mock recall results."""

from __future__ import annotations

import argparse
import json
import re
import socket
import time
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from shopping_agent.llm.client import LLMClient
from shopping_agent.react.tools import execute_tool


SYSTEM_PROMPT = """You are a strict shopping-retrieval auditor.
Judge only from the user query and the returned real-contract product fields.

Use exactly one verdict for each sample:
- pass: every returned product clearly matches the requested product type and all visible hard constraints.
- warn: products are relevant candidates, but a subjective, dynamic, compatibility, freshness, quality, or unavailable attribute cannot be verified from the returned fields.
- fail: at least one returned product clearly violates the requested product type, accessory/subtype, brand/model, numeric limit, size, capacity, power, price, or another hard constraint.

Do not fail merely because ranking is broad or because a soft preference cannot be verified.
Return ONLY a JSON array. Every object must contain sample_id, verdict, reason, and offending_products (an array). Preserve sample_id exactly."""


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


def build_audit_item(row: Dict[str, Any]) -> Dict[str, Any]:
    result = execute_tool(
        "sku_recall",
        {"query": str(row.get("query") or "")},
        str(row.get("site_code") or ""),
    )
    return {
        "sample_id": row.get("sample_id"),
        "site_code": row.get("site_code"),
        "query": row.get("query"),
        "products": result.get("products") or [],
    }


def summarize(results: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    return {
        verdict: sum(1 for item in results if item.get("verdict") == verdict)
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
        json.dumps(
            {
                "model": model,
                "input": str(input_path),
                "complete": complete,
                "summary": summarize(results),
                "results": list(results),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit non-empty Shopping mock recall results with an independent LLM judge.",
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="GLM-5.2")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--retry-delay", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    rows = [
        row
        for row in json.loads(input_path.read_text(encoding="utf-8"))
        if int(row.get("current_count") or 0) > 0
    ]
    completed_by_id: Dict[str, Dict[str, Any]] = {}
    if args.resume and output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        completed_by_id = {
            str(item.get("sample_id")): item
            for item in existing.get("results") or []
        }

    pending = [row for row in rows if str(row.get("sample_id")) not in completed_by_id]
    client = LLMClient(model=args.model)

    for offset in range(0, len(pending), args.batch_size):
        batch_rows = pending[offset:offset + args.batch_size]
        payload = [build_audit_item(row) for row in batch_rows]
        expected_ids = {str(item["sample_id"]) for item in payload}
        prompt = "Audit these retrieval results:\n" + json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        last_error: Optional[BaseException] = None
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
                verdicts_by_id = {
                    str(item.get("sample_id")): item
                    for item in parsed
                }
                for audit_item in payload:
                    sample_id = str(audit_item["sample_id"])
                    completed_by_id[sample_id] = {
                        **audit_item,
                        **verdicts_by_id[sample_id],
                    }
                ordered = [
                    completed_by_id[str(row.get("sample_id"))]
                    for row in rows
                    if str(row.get("sample_id")) in completed_by_id
                ]
                write_report(output_path, args.model, input_path, ordered, False)
                print(
                    f"batch {offset // args.batch_size + 1}: "
                    f"audited {len(payload)} samples",
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
                last_error = error
                if attempt == args.retries:
                    raise
                delay = args.retry_delay * attempt
                print(f"retryable audit error: {error}; retrying in {delay}s", flush=True)
                time.sleep(delay)
        if last_error and not all(str(item["sample_id"]) in completed_by_id for item in payload):
            raise last_error

    ordered_results = [completed_by_id[str(row.get("sample_id"))] for row in rows]
    write_report(output_path, args.model, input_path, ordered_results, True)
    print(json.dumps({"summary": summarize(ordered_results)}, ensure_ascii=False))
    return 1 if any(item.get("verdict") == "fail" for item in ordered_results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
