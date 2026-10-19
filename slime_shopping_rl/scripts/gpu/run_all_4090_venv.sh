#!/usr/bin/env bash
set -euo pipefail

# Experimental single-venv pipeline for a Linux 4090 machine.
# It tries to install both LLaMA-Factory SFT and Slime RL into one Python 3.11
# venv. If dependency resolution gets messy, use the two-venv scripts instead.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_venv.sh"

ROOT_DIR="$(repo_root_from_gpu_script)"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv-shopping-posttrain}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
CUDA_INDEX_URL="${CUDA_INDEX_URL:-https://download.pytorch.org/whl/cu121}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-${ROOT_DIR}/.cache/pip}"
PIP_NO_CACHE_DIR="${PIP_NO_CACHE_DIR:-0}"

THIRD_PARTY_DIR="${THIRD_PARTY_DIR:-${ROOT_DIR}/third_party}"
SLIME_DIR="${SLIME_DIR:-${THIRD_PARTY_DIR}/slime}"
MEGATRON_DIR="${MEGATRON_DIR:-${THIRD_PARTY_DIR}/Megatron-LM}"

RUN_SFT="${RUN_SFT:-1}"
RUN_RL="${RUN_RL:-0}"

mkdir -p "${THIRD_PARTY_DIR}"

create_and_activate_venv "${VENV_DIR}" "${PYTHON_BIN}"
hash -r
require_python_at_least 3 11
show_gpu
mkdir -p "${PIP_CACHE_DIR}"
export PIP_CACHE_DIR
export PIP_NO_CACHE_DIR

clone_or_update "https://github.com/THUDM/slime.git" "${SLIME_DIR}"
clone_or_update "https://github.com/NVIDIA/Megatron-LM.git" "${MEGATRON_DIR}"

if [[ "${FORCE_INSTALL:-0}" == "1" || ! -f "${VENV_DIR}/.install_markers/posttrain_deps" ]]; then
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install torch torchvision torchaudio --index-url "${CUDA_INDEX_URL}"
  cd "${ROOT_DIR}/LLaMA-Factory"
  python -m pip install -e ".[torch,metrics]"
  cd "${SLIME_DIR}"
  python -m pip install -e .
  python -m pip install "sglang[all]"
  python -c "import llamafactory; print('llamafactory import ok')"
  mkdir -p "${VENV_DIR}/.install_markers"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${VENV_DIR}/.install_markers/posttrain_deps"
else
  log "Dependencies already installed: ${VENV_DIR}/.install_markers/posttrain_deps"
  python -c "import llamafactory; print('llamafactory import ok')" || {
    warn "Install marker exists but dependencies are missing. Reinstalling deps."
    FORCE_INSTALL=1 exec "$0"
  }
fi

export PYTHONPATH="${MEGATRON_DIR}:${ROOT_DIR}/slime_shopping_rl:${ROOT_DIR}:${PYTHONPATH:-}"

cd "${ROOT_DIR}"
python -m unittest tests.test_slime_shopping_adapter tests.test_react_environment -v

if [[ "${RUN_SFT}" == "1" ]]; then
  log "Starting SFT"
  cd "${ROOT_DIR}/LLaMA-Factory/llamafactory"
  python -m llamafactory.cli train lora_qwen3_0.6b.yaml
fi

cd "${ROOT_DIR}"
log "Building task data"
python slime_shopping_rl/shopping_slime/task_data.py \
  --input LLaMA-Factory/llamafactory/train_shopping_react.json \
  --output slime_shopping_rl/data/shopping_slime_tasks.jsonl \
  --limit "${TASK_LIMIT:-200}"

if [[ "${RUN_RL}" == "1" ]]; then
  log "Starting Slime GRPO"
  bash "${ROOT_DIR}/slime_shopping_rl/configs/shopping_qwen3_0_6b_grpo.example.sh"
else
  log "Single venv is ready. Set RUN_RL=1 after checkpoint conversion is ready."
fi
