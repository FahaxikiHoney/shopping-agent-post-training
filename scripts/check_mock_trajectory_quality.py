#!/usr/bin/env python3
"""Run deterministic quality gates over Joybuy ReAct JSONL trajectories."""

import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from joybuy_agent.react.quality_gate import evaluate_trajectory, load_jsonl, summarize


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", help="JSONL paths or glob patterns")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    paths = []
    for pattern in args.inputs:
        matches = [Path(value) for value in glob.glob(pattern)]
        paths.extend(matches or [Path(pattern)])
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        parser.error(f"missing input files: {', '.join(missing)}")

    results = []
    for source, line_number, record in load_jsonl(paths):
        result = evaluate_trajectory(record)
        result["source"] = source
        result["line"] = line_number
        results.append(result)
        marker = "PASS" if result["passed"] else "FAIL"
        print(f"[{marker}] {source}:{line_number} {result['query'][:70]}")
        for issue in result["issues"]:
            print(f"  issue: {issue}")
        for warning in result["warnings"]:
            print(f"  warning: {warning}")

    report = {"summary": summarize(results), "results": results}
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
