#!/usr/bin/env bash
set -euo pipefail

# One-command SFT setup/run script in the venv style.
# Works on Linux and usually also in Windows Git Bash if `python` points to
# Python 3.11+ and CUDA PyTorch wheels are available.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_venv.sh"

ROOT_DIR="$(repo_root_from_gpu_script)"
LLAMA_FACTORY_DIR="${LLAMA_FACTORY_DIR:-${ROOT_DIR}/LLaMA-Factory}"
JOYBUY_LF_DIR="${JOYBUY_LF_DIR:-${LLAMA_FACTORY_DIR}/llamafactory}"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv-joybuy-sft}"
PYTHON_BIN="${PYTHON_BIN:-python}"
CUDA_INDEX_URL="${CUDA_INDEX_URL:-https://download.pytorch.org/whl/cu121}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-${ROOT_DIR}/.cache/pip}"
PIP_NO_CACHE_DIR="${PIP_NO_CACHE_DIR:-0}"
MODEL_PATH="${MODEL_PATH:-${ROOT_DIR}/models/Qwen3-0.6B}"

BASE_TRAIN_YAML="${BASE_TRAIN_YAML:-${JOYBUY_LF_DIR}/lora_qwen3_0.6b.yaml}"
TRAIN_YAML="${TRAIN_YAML:-}"
RUN_TRAIN="${RUN_TRAIN:-1}"

[[ -d "${LLAMA_FACTORY_DIR}" ]] || die "Missing LLaMA-Factory dir: ${LLAMA_FACTORY_DIR}"
[[ -f "${BASE_TRAIN_YAML}" ]] || die "Missing base train yaml: ${BASE_TRAIN_YAML}"

create_and_activate_venv "${VENV_DIR}" "${PYTHON_BIN}"
hash -r
require_python_at_least 3 11
show_gpu
mkdir -p "${PIP_CACHE_DIR}"
export PIP_CACHE_DIR
export PIP_NO_CACHE_DIR

if [[ -z "${TRAIN_YAML}" ]]; then
  GENERATED_DIR="${ROOT_DIR}/.cache/generated"
  mkdir -p "${GENERATED_DIR}"
  TRAIN_YAML="${GENERATED_DIR}/lora_qwen3_0.6b.server.yaml"
  sed \
    -e "s#^model_name_or_path:.*#model_name_or_path: ${MODEL_PATH}#g" \
    -e "s#^dataset_dir:.*#dataset_dir: ${ROOT_DIR}/sft_data/ready_to_run/react_sft#g" \
    -e "s#^output_dir:.*#output_dir: ${LLAMA_FACTORY_DIR}/output/joybuy_qwen3_0.6b_lora#g" \
    "${BASE_TRAIN_YAML}" > "${TRAIN_YAML}"
fi

[[ -f "${TRAIN_YAML}" ]] || die "Missing train yaml: ${TRAIN_YAML}"
if [[ ! -d "${MODEL_PATH}" && "${MODEL_PATH}" == /* ]]; then
  die "Missing model dir: ${MODEL_PATH}. Set MODEL_PATH=/path/to/Qwen3-0.6B"
fi
log "Using train yaml: ${TRAIN_YAML}"
log "Using model path: ${MODEL_PATH}"

if [[ "${FORCE_INSTALL:-0}" == "1" || ! -f "${VENV_DIR}/.install_markers/sft_deps" ]]; then
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install torch torchvision torchaudio --index-url "${CUDA_INDEX_URL}"
  cd "${LLAMA_FACTORY_DIR}"
  python -m pip install -e ".[torch,metrics]"
  python -c "import llamafactory; print('llamafactory import ok')"
  mkdir -p "${VENV_DIR}/.install_markers"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${VENV_DIR}/.install_markers/sft_deps"
else
  log "Dependencies already installed: ${VENV_DIR}/.install_markers/sft_deps"
  python -c "import llamafactory; print('llamafactory import ok')" || {
    warn "Install marker exists but llamafactory is missing. Reinstalling deps."
    FORCE_INSTALL=1 exec "$0"
  }
fi

python -m llamafactory.cli version

if [[ "${RUN_TRAIN}" == "1" ]]; then
  log "Starting SFT: ${TRAIN_YAML}"
  cd "${JOYBUY_LF_DIR}"
  python -m llamafactory.cli train "${TRAIN_YAML}"
else
  log "SFT env is ready. Set RUN_TRAIN=1 to train."
fi
