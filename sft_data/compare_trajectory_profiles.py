#!/usr/bin/env python3
"""Compare observable statistics of real and Mock shopping trajectories."""
from __future__ import annotations

import argparse
import glob
import json
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


def visible_text(text: str) -> str:
    return re.sub(r"<think>[\s\S]*?</think>", "", text or "", flags=re.I).strip()


def language_group(text: str) -> str:
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[а-яА-Я]", text):
        return "ru"
    return "latin"


def average(values: Iterable[float]) -> float:
    values = list(values)
    return round(statistics.mean(values), 3) if values else 0.0


def load_real(real_dir: str) -> List[Dict[str, Any]]:
    trajectories = []
    for path in glob.glob(str(Path(real_dir) / "*.jsonl")):
        with open(path, encoding="utf-8") as file:
            for line in file:
                try:
                    trajectories.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return trajectories


def load_mock(mock_file: str) -> List[Dict[str, Any]]:
    trajectories = []
    with open(mock_file, encoding="utf-8") as file:
        for line in file:
            try:
                trajectories.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return trajectories


def summarize_texts(queries: List[str], responses: List[str]) -> Dict[str, Any]:
    responses = [visible_text(text) for text in responses]
    card_counts = [len(re.findall(r"\[product:\d+\]", text)) for text in responses]
    click_counts = [len(re.findall(r"<ClickText>", text)) for text in responses]
    return {
        "query_language": dict(Counter(language_group(text) for text in queries)),
        "response_language": dict(Counter(language_group(text) for text in responses)),
        "average_query_chars": average(len(text) for text in queries),
        "average_visible_response_chars": average(len(text) for text in responses),
        "median_visible_response_chars": statistics.median(map(len, responses)) if responses else 0,
        "average_product_cards": average(card_counts),
        "no_product_card_rate": average(count == 0 for count in card_counts),
        "clicktext_rate": average(count > 0 for count in click_counts),
    }


def summarize_real(trajectories: List[Dict[str, Any]]) -> Dict[str, Any]:
    arguments = Counter()
    outputs = Counter()
    products = Counter()
    tools = Counter()
    sku_counts = []
    for trajectory in trajectories:
        for event in trajectory.get("runtime_events", []):
            content = ((event.get("payload") or {}).get("content") or {})
            callee = content.get("callee")
            if event.get("event_type") == "tool_call":
                tools[callee] += 1
                if callee == "sku_recall":
                    arguments[tuple(sorted(content.get("arguments") or {}))] += 1
            elif event.get("event_type") == "observation" and callee == "sku_recall":
                output = content.get("output") or {}
                outputs[tuple(sorted(output))] += 1
                sku_counts.append(int(output.get("count", 0)))
                for product in output.get("products", []):
                    products[tuple(sorted(product))] += 1

    queries = [item.get("request", {}).get("query", "") for item in trajectories]
    responses = [
        ((((item.get("final") or {}).get("response") or {}).get("output") or {}).get("display_text") or "")
        for item in trajectories
    ]
    return {
        "trajectory_count": len(trajectories),
        "text_profile": summarize_texts(queries, responses),
        "average_llm_calls": average(len(item.get("llm_calls") or []) for item in trajectories),
        "tools": dict(tools),
        "sku_argument_keysets": {",".join(keys): count for keys, count in arguments.items()},
        "sku_output_keysets": {",".join(keys): count for keys, count in outputs.items()},
        "sku_product_keysets": {",".join(keys): count for keys, count in products.items()},
        "sku_empty_rate": average(count == 0 for count in sku_counts),
        "sku_average_count": average(sku_counts),
    }


def summarize_mock(trajectories: List[Dict[str, Any]]) -> Dict[str, Any]:
    arguments = Counter()
    outputs = Counter()
    products = Counter()
    tools = Counter()
    sku_counts = []
    for trajectory in trajectories:
        pending_sku_calls = set()
        for message in trajectory.get("messages", []):
            if message.get("role") == "assistant":
                for tool_call in message.get("tool_calls") or []:
                    function = tool_call.get("function") or {}
                    name = function.get("name")
                    tools[name] += 1
                    if name == "sku_recall":
                        pending_sku_calls.add(tool_call.get("id"))
                        try:
                            args = json.loads(function.get("arguments") or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        arguments[tuple(sorted(args))] += 1
            elif message.get("role") == "tool" and message.get("tool_call_id") in pending_sku_calls:
                try:
                    output = json.loads(message.get("content") or "{}")
                except json.JSONDecodeError:
                    continue
                outputs[tuple(sorted(output))] += 1
                sku_counts.append(int(output.get("count", 0)))
                for product in output.get("products", []):
                    products[tuple(sorted(product))] += 1

    queries = [item.get("user_query", "") for item in trajectories]
    responses = [item.get("final_response", "") for item in trajectories]
    return {
        "trajectory_count": len(trajectories),
        "text_profile": summarize_texts(queries, responses),
        "average_react_steps": average(item.get("total_steps", 0) for item in trajectories),
        "tools": dict(tools),
        "sku_argument_keysets": {",".join(keys): count for keys, count in arguments.items()},
        "sku_output_keysets": {",".join(keys): count for keys, count in outputs.items()},
        "sku_product_keysets": {",".join(keys): count for keys, count in products.items()},
        "sku_empty_rate": average(count == 0 for count in sku_counts),
        "sku_average_count": average(sku_counts),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-dir", default="sft_data/training-data/data/trajectories")
    parser.add_argument("--mock-file", default="sft_data/trajectories_react.jsonl")
    parser.add_argument("--output")
    args = parser.parse_args()

    report = {
        "real": summarize_real(load_real(args.real_dir)),
        "mock": summarize_mock(load_mock(args.mock_file)),
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
