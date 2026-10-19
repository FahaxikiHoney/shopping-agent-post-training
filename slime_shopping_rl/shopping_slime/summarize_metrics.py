"""Summarize Shopping RL rollout metrics JSONL."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List


def load_records(path: Path) -> List[Dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def summarize(records: List[Dict[str, Any]], tail: int = 200) -> Dict[str, Any]:
    selected = records[-tail:] if tail else records
    rewards = [float(item["reward"]) for item in selected if item.get("reward") is not None]
    judge_scores = [float(item["judge_score"]) for item in selected if item.get("judge_score") is not None]
    return {
        "records": len(records),
        "window": len(selected),
        "reward_mean": round(mean(rewards), 4) if rewards else None,
        "judge_score_mean": round(mean(judge_scores), 4) if judge_scores else None,
        "success_rate": round(_rate(selected, "reward_type", "successful_recommendation"), 4),
        "missing_card_rate": round(_rate(selected, "reward_type", "missing_product_cards"), 4),
        "invalid_card_rate": round(_rate(selected, "reward_type", "invalid_product_cards"), 4),
        "judge_error_rate": round(sum(bool(item.get("judge_error")) for item in selected) / max(len(selected), 1), 4),
        "think_rate": round(sum(bool(item.get("has_think")) for item in selected) / max(len(selected), 1), 4),
        "reward_types": dict(Counter(str(item.get("reward_type")) for item in selected)),
    }


def _rate(records: List[Dict[str, Any]], key: str, value: str) -> float:
    return sum(item.get(key) == value for item in records) / max(len(records), 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--tail", type=int, default=200)
    args = parser.parse_args()
    print(json.dumps(summarize(load_records(Path(args.path)), tail=args.tail), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
