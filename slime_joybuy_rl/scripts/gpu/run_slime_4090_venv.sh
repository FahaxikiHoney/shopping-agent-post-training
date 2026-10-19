#!/usr/bin/env bash
set -euo pipefail

# Linux-only Slime RL setup/run script in the venv style.
# Prefer Docker for production runs, but this mirrors the convenient local
# venv workflow used by many 4090 boxes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_venv.sh"

ROOT_DIR="$(repo_root_from_gpu_script)"
load_optional_env_file "${ROOT_DIR}/.env.judge"
load_optional_env_file "${ROOT_DIR}/slime_joybuy_rl/.env.judge"
# Reuse the SFT venv by default. The project is small and AutoDL disk space is
# tight, so one environment is easier to maintain than separate SFT/RL venvs.
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv-joybuy-sft}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
CUDA_INDEX_URL="${CUDA_INDEX_URL:-https://download.pytorch.org/whl/cu121}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-${ROOT_DIR}/.cache/pip}"
PIP_NO_CACHE_DIR="${PIP_NO_CACHE_DIR:-1}"
INSTALL_TORCH="${INSTALL_TORCH:-0}"
SGLANG_PACKAGE="${SGLANG_PACKAGE:-sglang}"

THIRD_PARTY_DIR="${THIRD_PARTY_DIR:-${ROOT_DIR}/third_party}"
SLIME_DIR="${SLIME_DIR:-${THIRD_PARTY_DIR}/slime}"
MEGATRON_DIR="${MEGATRON_DIR:-${THIRD_PARTY_DIR}/Megatron-LM}"

HF_CHECKPOINT="${HF_CHECKPOINT:-${ROOT_DIR}/LLaMA-Factory/output/joybuy_qwen3_0.6b_merged}"
MEGATRON_REF="${MEGATRON_REF:-${ROOT_DIR}/checkpoints/megatron/joybuy_qwen3_0.6b_ref}"
MEGATRON_SAVE="${MEGATRON_SAVE:-${ROOT_DIR}/checkpoints/megatron/joybuy_qwen3_0.6b_grpo}"
TRAIN_DATA="${TRAIN_DATA:-${ROOT_DIR}/sft_data/ready_to_run/rl/joybuy_slime_tasks.jsonl}"
RUN_TRAIN="${RUN_TRAIN:-0}"
JOYBUY_RL_METRICS_PATH="${JOYBUY_RL_METRICS_PATH:-${ROOT_DIR}/slime_joybuy_rl/output/rollout_metrics.jsonl}"
export JOYBUY_RL_METRICS_PATH

mkdir -p "${THIRD_PARTY_DIR}" "$(dirname "${TRAIN_DATA}")" "${MEGATRON_SAVE}"

create_and_activate_venv "${VENV_DIR}" "${PYTHON_BIN}"
hash -r
require_python_at_least 3 10
show_gpu
mkdir -p "${PIP_CACHE_DIR}"
export PIP_CACHE_DIR
export PIP_NO_CACHE_DIR

clone_or_update "https://github.com/THUDM/slime.git" "${SLIME_DIR}"
clone_or_update "https://github.com/NVIDIA/Megatron-LM.git" "${MEGATRON_DIR}"

if [[ "${FORCE_INSTALL:-0}" == "1" || ! -f "${VENV_DIR}/.install_markers/slime_deps" ]]; then
  python -m pip install --upgrade pip setuptools wheel
  if [[ "${INSTALL_TORCH}" == "1" ]]; then
    python -m pip install torch torchvision torchaudio --index-url "${CUDA_INDEX_URL}"
  else
    python - <<'PY'
import torch
print(f"reuse torch {torch.__version__}, cuda={torch.version.cuda}")
PY
  fi
  cd "${SLIME_DIR}"
  python -m pip install --no-deps -e .
  python -m pip install "${SGLANG_PACKAGE}"
  python -c "import slime; print('slime import ok')"
  mkdir -p "${VENV_DIR}/.install_markers"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${VENV_DIR}/.install_markers/slime_deps"
else
  log "Dependencies already installed: ${VENV_DIR}/.install_markers/slime_deps"
  python -c "import slime; print('slime import ok')" || {
    warn "Install marker exists but slime is missing. Reinstalling deps."
    FORCE_INSTALL=1 exec "$0"
  }
fi

export PYTHONPATH="${MEGATRON_DIR}:${ROOT_DIR}/slime_joybuy_rl:${ROOT_DIR}:${PYTHONPATH:-}"

if [[ ! -f "${TRAIN_DATA}" ]]; then
  cd "${ROOT_DIR}"
  log "Building task data: ${TRAIN_DATA}"
  python slime_joybuy_rl/joybuy_slime/task_data.py \
    --input sft_data/ready_to_run/react_sft/train_joybuy_react.json \
    --output "${TRAIN_DATA}" \
    --limit "${TASK_LIMIT:-200}"
fi

cd "${ROOT_DIR}"
python -m unittest tests.test_slime_joybuy_adapter tests.test_react_environment -v

if [[ "${RUN_TRAIN}" == "1" ]]; then
  log "Starting Slime GRPO"
  HF_CHECKPOINT="${HF_CHECKPOINT}" \
  MEGATRON_REF="${MEGATRON_REF}" \
  MEGATRON_SAVE="${MEGATRON_SAVE}" \
  TRAIN_DATA="${TRAIN_DATA}" \
  bash "${ROOT_DIR}/slime_joybuy_rl/configs/joybuy_qwen3_0_6b_grpo.example.sh"
else
  log "Slime env is ready. Set RUN_TRAIN=1 to launch GRPO."
  log "HF_CHECKPOINT=${HF_CHECKPOINT}"
  log "MEGATRON_REF=${MEGATRON_REF}"
  log "MEGATRON_SAVE=${MEGATRON_SAVE}"
  log "TRAIN_DATA=${TRAIN_DATA}"
fi
