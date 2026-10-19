#!/usr/bin/env python3
"""Basic release hygiene scan; review every hit manually."""
import argparse
import re
import sys
from pathlib import Path

PATTERNS = {
    "credential_literal": re.compile(
        r"(?i)\b(?:api[_-]?key|client_secret|password|access_token)\b\s*[:=]\s*['\"]([A-Za-z0-9_./+=-]{20,})['\"]"
    ),
    "private_ip": re.compile(r"\b(?:10\.\d{1,3}|192\.168\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
    "local_user_path": re.compile(r"(?i)(?:/Users/[A-Za-z0-9._-]+/|[A-Z]:\\Users\\[A-Za-z0-9._-]+\\)"),
    "email_address": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "cn_mobile_number": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "retailer_order_id": re.compile(
        r"(?i)(?<![A-Z0-9])\x4A\x44\s*20\d{6}[-_]\d{3,}(?!\d)|(?<!\d)20\d{6}[-_]\d{5,}(?!\d)"
    ),
    "shipping_tracking_id": re.compile(r"(?i)(?<![A-Z0-9])(?:SF|\x4A\x44|DB)\d{8,}(?!\d)"),
    "retailer_deep_link": re.compile(r"(?i)(?<![A-Z0-9])(?:\x6A\x64|shopping)://[^\s\]\[\"<>]+"),
}
SKIP = {".git", ".venv", "venv", "__pycache__"}
DEFAULT_PATHS = [
    "shopping_agent", "sft_data", "training", "scripts", "slime_shopping_rl",
    "llamafactory", "LLaMA-Factory/llamafactory", "trajectory_grader",
    "llm_evaluation", "docs", ".github", "README.md", "README_EN.md",
    "TRAINING.md", "AGENT_FRAMEWORK.md", "TOOL_DEFINITIONS.md",
    "DATASET_CARD.md", "REFERENCES.md", "CITATION.md", "CITATION.cff",
]

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths", nargs="*", default=DEFAULT_PATHS,
        help="paths to scan (defaults to project-owned code/data/docs; third-party LLaMA-Factory is excluded)",
    )
    args = parser.parse_args()
    hits = 0
    for root in map(Path, args.paths):
        files = [root] if root.is_file() else (p for p in root.rglob("*") if p.is_file())
        for path in files:
            if any(part in SKIP for part in path.parts) or path.suffix.lower() in {".png", ".jpg", ".pdf", ".bin", ".safetensors"}:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(lines, 1):
                for name, pattern in PATTERNS.items():
                    if pattern.search(line):
                        print(f"{path}:{n}: [{name}] {line[:180]}")
                        hits += 1
    print(f"Found {hits} candidate hit(s). Review manually; this heuristic is not exhaustive.")

if __name__ == "__main__":
    main()
