#!/usr/bin/env python3
"""Compare real sku_recall traces with the local Mock implementation."""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shopping_agent.react.tools import execute_tool


def load_real_calls(real_dir: str) -> Iterable[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    for path in glob.glob(str(Path(real_dir) / "*.jsonl")):
        with open(path, encoding="utf-8") as file:
            for line in file:
                try:
                    trajectory = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pending = []
                for event in trajectory.get("runtime_events", []):
                    content = ((event.get("payload") or {}).get("content") or {})
                    if content.get("callee") != "sku_recall":
                        continue
                    if event.get("event_type") == "tool_call":
                        pending.append(content.get("arguments") or {})
                    elif event.get("event_type") == "observation" and pending:
                        arguments = pending.pop(0)
                        output = content.get("output") or {}
                        yield trajectory.get("trajectory_id", ""), arguments, output


def keyset_counter(items: Iterable[Dict[str, Any]]) -> Counter:
    return Counter(tuple(sorted(item)) for item in items)


def build_report(real_dir: str) -> Dict[str, Any]:
    calls = list(load_real_calls(real_dir))
    real_arguments = [arguments for _, arguments, _ in calls]
    real_outputs = [output for _, _, output in calls]
    mock_outputs = [
        execute_tool("sku_recall", {"query": str(arguments.get("query", ""))})
        for arguments in real_arguments
    ]

    real_counts = [int(output.get("count", 0)) for output in real_outputs]
    mock_counts = [int(output.get("count", 0)) for output in mock_outputs]
    real_product_keys = keyset_counter(
        product for output in real_outputs for product in output.get("products", [])
    )
    mock_product_keys = keyset_counter(
        product for output in mock_outputs for product in output.get("products", [])
    )

    return {
        "call_count": len(calls),
        "real_argument_keysets": {
            ",".join(keys): count for keys, count in keyset_counter(real_arguments).items()
        },
        "real_output_keysets": {
            ",".join(keys): count for keys, count in keyset_counter(real_outputs).items()
        },
        "mock_output_keysets": {
            ",".join(keys): count for keys, count in keyset_counter(mock_outputs).items()
        },
        "real_product_keysets": {
            ",".join(keys): count for keys, count in real_product_keys.items()
        },
        "mock_product_keysets": {
            ",".join(keys): count for keys, count in mock_product_keys.items()
        },
        "real_zero_rate": sum(count == 0 for count in real_counts) / len(real_counts),
        "mock_zero_rate": sum(count == 0 for count in mock_counts) / len(mock_counts),
        "real_average_count": mean(real_counts),
        "mock_average_count": mean(mock_counts),
        "both_hit": sum(real > 0 and mock > 0 for real, mock in zip(real_counts, mock_counts)),
        "real_hit_mock_miss": sum(real > 0 and mock == 0 for real, mock in zip(real_counts, mock_counts)),
        "real_miss_mock_hit": sum(real == 0 and mock > 0 for real, mock in zip(real_counts, mock_counts)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--real-dir",
        default="sft_data/training-data/data/trajectories",
    )
    parser.add_argument("--output")
    args = parser.parse_args()

    report = build_report(args.real_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
