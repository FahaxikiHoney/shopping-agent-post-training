#!/usr/bin/env bash
set -euo pipefail

# Merge the SFT LoRA adapter into a Hugging Face checkpoint for Slime rollout.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_venv.sh"

ROOT_DIR="$(repo_root_from_gpu_script)"
LLAMA_FACTORY_DIR="${LLAMA_FACTORY_DIR:-${ROOT_DIR}/LLaMA-Factory}"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv-joybuy-sft}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL_PATH="${MODEL_PATH:-${ROOT_DIR}/models/Qwen3-0.6B}"
ADAPTER_PATH="${ADAPTER_PATH:-${LLAMA_FACTORY_DIR}/output/joybuy_qwen3_0.6b_lora_from_warmup_r64}"
EXPORT_DIR="${EXPORT_DIR:-${LLAMA_FACTORY_DIR}/output/joybuy_qwen3_0.6b_sft_merged}"
EXPORT_YAML="${EXPORT_YAML:-${ROOT_DIR}/.cache/generated/export_qwen3_0.6b_sft_merged.yaml}"
EXPORT_DEVICE="${EXPORT_DEVICE:-cpu}"

create_and_activate_venv "${VENV_DIR}" "${PYTHON_BIN}"
hash -r
require_python_at_least 3 11

[[ -d "${LLAMA_FACTORY_DIR}" ]] || die "Missing LLaMA-Factory dir: ${LLAMA_FACTORY_DIR}"
[[ -d "${MODEL_PATH}" ]] || die "Missing model dir: ${MODEL_PATH}"
[[ -d "${ADAPTER_PATH}" ]] || die "Missing adapter dir: ${ADAPTER_PATH}"
[[ -f "${ADAPTER_PATH}/adapter_config.json" ]] || die "Missing adapter_config.json in ${ADAPTER_PATH}"
mkdir -p "$(dirname "${EXPORT_YAML}")" "${EXPORT_DIR}"

cat > "${EXPORT_YAML}" <<YAML
model_name_or_path: ${MODEL_PATH}
adapter_name_or_path: ${ADAPTER_PATH}
template: qwen3
trust_remote_code: true
export_dir: ${EXPORT_DIR}
export_size: 5
export_device: ${EXPORT_DEVICE}
export_legacy_format: false
YAML

log "Exporting merged SFT model: ${EXPORT_YAML}"
log "Base model: ${MODEL_PATH}"
log "Adapter: ${ADAPTER_PATH}"
log "Export dir: ${EXPORT_DIR}"
cd "${LLAMA_FACTORY_DIR}"
python -m llamafactory.cli export "${EXPORT_YAML}"
log "Merged HF checkpoint: ${EXPORT_DIR}"
