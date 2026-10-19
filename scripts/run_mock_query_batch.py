#!/usr/bin/env python3
"""Run reproducible Joybuy Mock regressions from real-query JSONL inputs."""

import argparse
import json
import random
import sys
import time
import urllib.error
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from joybuy_agent.llm.client import LLMClient
from joybuy_agent.react.agent import ReActJoybuyAgent
from joybuy_agent.react.quality_gate import evaluate_trajectory, summarize


RETRYABLE_HTTP_CODES = {429, 502, 503, 504}


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


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def sample_identifier(sample: Dict[str, Any], fallback_index: int = 0) -> str:
    value = sample.get("sample_id") or sample.get("id")
    if value:
        return str(value)
    query = str(sample.get("query") or "")
    site_code = str(sample.get("site_code") or "")
    return f"row-{fallback_index}-{site_code}-{query}"


def select_samples(
    records: Sequence[Dict[str, Any]],
    sample_size: int,
    seed: int,
    balance_sites: bool = True,
) -> List[Dict[str, Any]]:
    unique_records = []
    seen_ids = set()
    for index, record in enumerate(records):
        identifier = sample_identifier(record, index)
        if identifier in seen_ids:
            continue
        seen_ids.add(identifier)
        unique_records.append(record)

    if sample_size <= 0 or sample_size >= len(unique_records):
        return list(unique_records)

    rng = random.Random(seed)
    if not balance_sites:
        return rng.sample(unique_records, sample_size)

    by_site: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in unique_records:
        by_site[str(record.get("site_code") or "UNKNOWN")].append(record)
    sites = sorted(by_site)
    base, remainder = divmod(sample_size, len(sites))
    selected = []
    selected_ids = set()
    for index, site in enumerate(sites):
        quota = base + (1 if index < remainder else 0)
        site_rows = list(by_site[site])
        rng.shuffle(site_rows)
        for record in site_rows[:quota]:
            selected.append(record)
            selected_ids.add(sample_identifier(record))

    if len(selected) < sample_size:
        remaining = [
            record
            for record in unique_records
            if sample_identifier(record) not in selected_ids
        ]
        rng.shuffle(remaining)
        selected.extend(remaining[: sample_size - len(selected)])
    rng.shuffle(selected)
    return selected


def requested_samples(
    records: Sequence[Dict[str, Any]],
    requested_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    by_id = {
        sample_identifier(record, index): record
        for index, record in enumerate(records)
    }
    missing = [identifier for identifier in requested_ids if identifier not in by_id]
    if missing:
        raise ValueError(f"unknown sample ids: {', '.join(missing)}")
    return [by_id[identifier] for identifier in requested_ids]


def completed_sample_ids(rows: Sequence[Dict[str, Any]]) -> Set[str]:
    completed = set()
    for row in rows:
        trajectory = row.get("trajectory")
        sample = row.get("sample") or {}
        if trajectory and trajectory.get("status") == "done":
            completed.add(sample_identifier(sample))
    return completed


def pending_samples(
    selected: Sequence[Dict[str, Any]],
    completed_ids: Set[str],
    rerun: bool = False,
) -> List[Dict[str, Any]]:
    if rerun:
        return list(selected)
    return [
        sample
        for index, sample in enumerate(selected)
        if sample_identifier(sample, index) not in completed_ids
    ]


def infer_scenario_type(
    sample: Dict[str, Any],
    requested_scenario: str,
) -> str:
    if requested_scenario != "auto":
        return requested_scenario
    reasons = [
        str(reason)
        for reason in [
            *(sample.get("query_difficulty_reasons") or []),
            *(sample.get("difficulty_reasons") or []),
        ]
    ]
    if "bundle" in reasons or "multi_category_bundle" in reasons:
        return "bundle_purchase"
    return "search_recommend"


def latest_rows_by_sample(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    order = []
    for index, row in enumerate(rows):
        identifier = sample_identifier(row.get("sample") or {}, index)
        if identifier not in latest:
            order.append(identifier)
        latest[identifier] = row
    return [latest[identifier] for identifier in order]


def quality_report(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    results = []
    execution_failures = []
    for row in rows:
        trajectory = row.get("trajectory")
        if not trajectory:
            execution_failures.append({
                "sample_id": sample_identifier(row.get("sample") or {}),
                "error": row.get("error"),
            })
            continue
        result = evaluate_trajectory(trajectory)
        result["sample_id"] = sample_identifier(row.get("sample") or {})
        results.append(result)
    return {
        "execution": {
            "total": len(rows),
            "completed": len(results),
            "failed": len(execution_failures),
            "failures": execution_failures,
        },
        "quality": summarize(results),
        "results": results,
    }


def run_sample(
    sample: Dict[str, Any],
    client: LLMClient,
    scenario_type: str,
    max_steps: int,
    retries: int,
    retry_delay: int,
) -> Dict[str, Any]:
    effective_scenario = infer_scenario_type(sample, scenario_type)
    attempts = 0
    last_error: Optional[BaseException] = None
    for attempt in range(1, retries + 1):
        attempts = attempt
        try:
            started = time.time()
            trajectory = ReActJoybuyAgent(
                llm=client,
                max_steps=max_steps,
                scenario_type=effective_scenario,
                site_context=str(sample.get("site_code") or ""),
            ).run(str(sample.get("query") or ""))
            return {
                "sample": sample,
                "trajectory": trajectory.to_sft_dict(),
                "elapsed_seconds": round(time.time() - started, 1),
                "attempts": attempts,
                "error": None,
            }
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in RETRYABLE_HTTP_CODES or attempt == retries:
                break
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt == retries:
                break
        except Exception as error:
            last_error = error
            break
        delay = retry_delay * attempt
        print(f"  retryable error: {last_error}; retrying in {delay}s", flush=True)
        time.sleep(delay)
    return {
        "sample": sample,
        "trajectory": None,
        "elapsed_seconds": None,
        "attempts": attempts,
        "error": {
            "type": type(last_error).__name__ if last_error else "UnknownError",
            "message": str(last_error or "retry loop ended without a trajectory"),
        },
    }


def derived_quality_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}_quality.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a reproducible, resumable Joybuy Mock query regression.",
    )
    parser.add_argument(
        "--input",
        default="sft_data/training-data/data/trajectory_inputs/queries_600.jsonl",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--sample-output")
    parser.add_argument("--quality-output")
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--sample-id", action="append", dest="sample_ids")
    parser.add_argument("--seed", type=int, default=20260817)
    parser.add_argument("--unbalanced", action="store_true")
    parser.add_argument("--model", default="GLM-5.2")
    parser.add_argument(
        "--scenario",
        default="auto",
        choices=["auto", "search_recommend", "bundle_purchase", "matching"],
    )
    parser.add_argument("--max-steps", type=int, default=7)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--retry-delay", type=int, default=15)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    if not input_path.exists():
        parser.error(f"missing input file: {input_path}")
    if output_path.exists() and not args.resume and not args.overwrite and not args.dry_run:
        parser.error("output exists; use --resume or --overwrite")

    records = load_jsonl(input_path)
    try:
        selected = (
            requested_samples(records, args.sample_ids)
            if args.sample_ids
            else select_samples(
                records,
                args.sample_size,
                args.seed,
                balance_sites=not args.unbalanced,
            )
        )
    except ValueError as error:
        parser.error(str(error))
    if args.sample_output:
        write_jsonl(Path(args.sample_output), selected)
    site_counts = defaultdict(int)
    for sample in selected:
        site_counts[str(sample.get("site_code") or "UNKNOWN")] += 1
    print(
        f"selected={len(selected)} seed={args.seed} sites={dict(sorted(site_counts.items()))}",
        flush=True,
    )
    if args.dry_run:
        return 0

    existing_rows = load_jsonl(output_path) if args.resume and output_path.exists() else []
    done_ids = completed_sample_ids(existing_rows)
    pending = pending_samples(selected, done_ids, rerun=args.rerun)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume and output_path.exists() else "w"
    client = LLMClient(model=args.model)
    new_rows = []
    with output_path.open(mode, encoding="utf-8") as handle:
        for index, sample in enumerate(pending, 1):
            identifier = sample_identifier(sample, index)
            print(f"[{index}/{len(pending)}] {identifier} {sample.get('site_code')} {sample.get('query')}", flush=True)
            row = run_sample(
                sample,
                client,
                args.scenario,
                args.max_steps,
                args.retries,
                args.retry_delay,
            )
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            new_rows.append(row)
            trajectory = row.get("trajectory") or {}
            print(
                f"  status={trajectory.get('status', 'error')} attempts={row['attempts']} "
                f"elapsed={row.get('elapsed_seconds')}",
                flush=True,
            )

    all_rows = latest_rows_by_sample([*existing_rows, *new_rows])
    write_jsonl(output_path, all_rows)
    report = quality_report(all_rows)
    quality_path = Path(args.quality_output) if args.quality_output else derived_quality_path(output_path)
    quality_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"execution": report["execution"], "quality": report["quality"]}, ensure_ascii=False, indent=2))
    return 1 if report["execution"]["failed"] or report["quality"]["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
