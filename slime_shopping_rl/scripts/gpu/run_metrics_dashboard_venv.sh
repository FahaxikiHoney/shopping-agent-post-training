#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_venv.sh"

ROOT_DIR="$(repo_root_from_gpu_script)"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv-shopping-sft}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8792}"
METRICS_PATH="${METRICS_PATH:-${ROOT_DIR}/slime_shopping_rl/output/rollout_metrics.jsonl}"

create_and_activate_venv "${VENV_DIR}" "${PYTHON_BIN}"
hash -r
require_python_at_least 3 11
export PYTHONPATH="${ROOT_DIR}/slime_shopping_rl:${ROOT_DIR}:${PYTHONPATH:-}"

cd "${ROOT_DIR}"
python -m slime_shopping_rl.shopping_slime.metrics_dashboard \
  --host "${HOST}" \
  --port "${PORT}" \
  --metrics-path "${METRICS_PATH}"
