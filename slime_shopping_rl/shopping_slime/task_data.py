"""Build Slime JSONL task data from existing Shopping SFT files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def iter_llamafactory_sharegpt(path: Path) -> Iterable[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    for index, item in enumerate(data):
        conversations = item.get("conversations") or []
        query = ""
        for turn in conversations:
            if turn.get("from") in {"human", "user"}:
                query = str(turn.get("value") or turn.get("content") or "").strip()
                break
        if query:
            yield {
                "prompt": [{"role": "user", "content": query}],
                "label": "",
                "metadata": {
                    "source_name": "shopping_mock",
                    "task_id": item.get("trajectory_id") or f"shopping_{index}",
                    "query": query,
                    "site_code": item.get("site_code") or "UK-Site",
                    "scenario_type": item.get("scenario_type") or "search_recommend",
                },
            }


def write_jsonl(records: Iterable[Dict[str, Any]], output: Path, limit: int = 0) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
            if limit and count >= limit:
                break
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="LLaMA-Factory sharegpt JSON file")
    parser.add_argument("--output", required=True, help="Slime JSONL output path")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    count = write_jsonl(
        iter_llamafactory_sharegpt(Path(args.input)),
        Path(args.output),
        args.limit,
    )
    print(f"wrote {count} tasks to {args.output}")


if __name__ == "__main__":
    main()
