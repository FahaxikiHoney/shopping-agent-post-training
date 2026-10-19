#!/usr/bin/env bash
set -euo pipefail

# Start the Joybuy reward HTTP service. It can optionally call an
# OpenAI-compatible LLM judge through environment variables.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_venv.sh"

ROOT_DIR="$(repo_root_from_gpu_script)"
load_optional_env_file "${ROOT_DIR}/.env.judge"
load_optional_env_file "${ROOT_DIR}/slime_joybuy_rl/.env.judge"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv-joybuy-sft}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8791}"
MAX_STEPS="${MAX_STEPS:-5}"
TOOL_COST="${TOOL_COST:-0.01}"
JOYBUY_RL_METRICS_PATH="${JOYBUY_RL_METRICS_PATH:-${ROOT_DIR}/slime_joybuy_rl/output/rollout_metrics.jsonl}"
export JOYBUY_RL_METRICS_PATH

create_and_activate_venv "${VENV_DIR}" "${PYTHON_BIN}"
hash -r
require_python_at_least 3 11
export PYTHONPATH="${ROOT_DIR}/slime_joybuy_rl:${ROOT_DIR}:${PYTHONPATH:-}"

EXTRA_ARGS=()
if [[ "${USE_LLM_JUDGE:-0}" == "1" ]]; then
  [[ -n "${JUDGE_API_KEY:-${TENCENTMAAS_API_KEY:-}}" ]] || die "Set JUDGE_API_KEY or TENCENTMAAS_API_KEY before USE_LLM_JUDGE=1"
  EXTRA_ARGS+=(--use-llm-judge)
fi

cd "${ROOT_DIR}"
python -m slime_joybuy_rl.joybuy_slime.rollout_service \
  --host "${HOST}" \
  --port "${PORT}" \
  --max-steps "${MAX_STEPS}" \
  --tool-cost "${TOOL_COST}" \
  "${EXTRA_ARGS[@]}"
