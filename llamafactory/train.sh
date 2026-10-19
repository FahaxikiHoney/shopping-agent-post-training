#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODEL_PATH="${MODEL_PATH:-${REPO_ROOT}/models/Qwen3-0.6B}"
exec python "${REPO_ROOT}/scripts/run_module.py" sft --model-path "${MODEL_PATH}" "$@"
