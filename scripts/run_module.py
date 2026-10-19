#!/usr/bin/env python3
"""One-command entry points for the ready-to-run project modules."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READY = ROOT / "sft_data" / "ready_to_run"
OUTPUT = ROOT / "sft_data" / "generated"


def run(command: list[str], *, env: dict[str, str] | None = None, cwd: Path = ROOT) -> int:
    print("$", " ".join(str(part) for part in command), flush=True)
    return subprocess.call(command, cwd=cwd, env=env)


def require_api() -> None:
    missing = [key for key in ("LLM_API_URL", "LLM_API_KEY") if not os.environ.get(key)]
    if missing:
        raise SystemExit("Set required environment variables: " + ", ".join(missing))


def require_bash() -> str:
    bash = shutil.which("bash")
    if not bash:
        raise SystemExit("This module needs bash (Linux/WSL or Git Bash on Windows).")
    return bash


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="module", required=True)

    mock = sub.add_parser("mock-data", help="Generate local mock ReAct trajectories; no API needed")
    mock.add_argument("--count", type=int, default=20)
    mock.add_argument("--scenario", default="all")
    mock.add_argument("--output", default=str(OUTPUT / "mock_sft.jsonl"))

    rollout = sub.add_parser("rollout", help="Run query batch against the configured LLM endpoint")
    rollout.add_argument("--input", default=str(READY / "query" / "queries_sample100.jsonl"))
    rollout.add_argument("--output", default=str(OUTPUT / "mock_rollouts.jsonl"))
    rollout.add_argument("--sample-size", type=int, default=10)
    rollout.add_argument("--model", default="GLM-5.2")
    rollout.add_argument("--overwrite", action="store_true")

    gate = sub.add_parser("gate", help="Run deterministic quality gate on an existing trajectory file")
    gate.add_argument("--input", default=str(READY / "trajectory" / "eval_trajectories_cleaned.jsonl"))
    gate.add_argument("--output", default=str(OUTPUT / "gate_report.json"))

    judge = sub.add_parser("judge", help="Run the five-dimension LLM judge")
    judge.add_argument("--input", default=str(READY / "trajectory" / "eval_trajectories_cleaned.jsonl"))
    judge.add_argument("--output", default=str(OUTPUT / "judge_results.jsonl"))
    judge.add_argument("--model", default="DeepSeek-R1")
    judge.add_argument("--count", type=int, default=0, help="0 evaluates all rows")
    judge.add_argument("--workers", type=int, default=3)
    judge.add_argument("--gate-only", action="store_true")

    export = sub.add_parser("export-sft", help="Filter completed batch rollouts into SFT JSONL")
    export.add_argument("--input", default=str(OUTPUT / "mock_rollouts.jsonl"))
    export.add_argument("--quality-report", default=str(OUTPUT / "mock_rollouts_quality.json"))
    export.add_argument("--output", default=str(OUTPUT / "filtered_trajectories.jsonl"))

    sft = sub.add_parser("sft", help="Set up the fork environment and run 875-row ReAct LoRA SFT")
    sft.add_argument("--model-path", default=os.environ.get("MODEL_PATH", str(ROOT / "models" / "Qwen3-0.6B")))

    rl = sub.add_parser("rl", help="Set up Slime dependencies and launch GRPO with ready RL data")
    rl.add_argument("--hf-checkpoint", default=os.environ.get("HF_CHECKPOINT"))
    rl.add_argument("--megatron-ref", default=os.environ.get("MEGATRON_REF"))
    rl.add_argument("--megatron-save", default=os.environ.get("MEGATRON_SAVE", str(ROOT / "checkpoints" / "megatron" / "shopping_grpo")))

    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    if args.module == "mock-data":
        return run([sys.executable, str(ROOT / "sft_data" / "llm_gen_oxygen.py"), "--mock", "-n", str(args.count), "--scenario", args.scenario, "--output", args.output])
    if args.module == "rollout":
        require_api()
        command = [sys.executable, str(ROOT / "scripts" / "run_mock_query_batch.py"), "--input", args.input, "--output", args.output, "--sample-size", str(args.sample_size), "--model", args.model]
        if args.overwrite:
            command.append("--overwrite")
        return run(command)
    if args.module == "gate":
        return run([sys.executable, str(ROOT / "scripts" / "check_mock_trajectory_quality.py"), args.input, "--output", args.output])
    if args.module == "judge":
        if not args.gate_only:
            require_api()
        command = [sys.executable, str(ROOT / "llm_evaluation" / "evaluate.py"), "--input", args.input, "--output", args.output, "--model", args.model, "-n", str(args.count), "-c", str(args.workers)]
        if args.gate_only:
            command.append("--gate-only")
        return run(command)
    if args.module == "export-sft":
        if not Path(args.input).is_file():
            raise SystemExit(f"Missing rollout input: {args.input}. Run `python scripts/run_module.py rollout ...` first, or pass --input.")
        if not Path(args.quality_report).is_file():
            raise SystemExit(f"Missing quality report: {args.quality_report}. The batch rollout creates this report; pass --quality-report if needed.")
        return run([sys.executable, str(ROOT / "scripts" / "export_mock_sft.py"), "--input", args.input, "--quality-report", args.quality_report, "--output", args.output])
    if args.module == "sft":
        env = os.environ.copy()
        env.update({"MODEL_PATH": args.model_path, "RUN_TRAIN": "1"})
        return run([require_bash(), str(ROOT / "slime_shopping_rl" / "scripts" / "gpu" / "run_sft_4090_venv.sh")], env=env)
    if args.module == "rl":
        if not args.hf_checkpoint or not args.megatron_ref:
            raise SystemExit("RL requires --hf-checkpoint and --megatron-ref (SFT HF checkpoint and converted Megatron reference checkpoint).")
        env = os.environ.copy()
        env.update({"HF_CHECKPOINT": args.hf_checkpoint, "MEGATRON_REF": args.megatron_ref, "MEGATRON_SAVE": args.megatron_save, "TRAIN_DATA": str(READY / "rl" / "shopping_slime_tasks.jsonl"), "RUN_TRAIN": "1"})
        return run([require_bash(), str(ROOT / "slime_shopping_rl" / "scripts" / "gpu" / "run_slime_4090_venv.sh")], env=env)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
