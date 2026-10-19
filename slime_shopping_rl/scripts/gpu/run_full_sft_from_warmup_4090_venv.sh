#!/usr/bin/env bash
set -euo pipefail

# Second-stage full trajectory SFT. Start from the tool-call warmup LoRA and
# continue training on complete Shopping ReAct trajectories.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_venv.sh"

ROOT_DIR="$(repo_root_from_gpu_script)"
LLAMA_FACTORY_DIR="${LLAMA_FACTORY_DIR:-${ROOT_DIR}/LLaMA-Factory}"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv-shopping-sft}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL_PATH="${MODEL_PATH:-${ROOT_DIR}/models/Qwen3-0.6B}"
WARMUP_ADAPTER_PATH="${WARMUP_ADAPTER_PATH:-${LLAMA_FACTORY_DIR}/output/shopping_qwen3_0.6b_toolcall_warmup}"
FULL_YAML="${FULL_YAML:-${ROOT_DIR}/.cache/generated/lora_qwen3_0.6b_full_from_warmup.yaml}"
OUTPUT_DIR="${OUTPUT_DIR:-${LLAMA_FACTORY_DIR}/output/shopping_qwen3_0.6b_lora_from_warmup}"
LORA_RANK="${LORA_RANK:-64}"
LORA_ALPHA="${LORA_ALPHA:-128}"
GRAD_ACCUM_STEPS="${GRAD_ACCUM_STEPS:-8}"

create_and_activate_venv "${VENV_DIR}" "${PYTHON_BIN}"
hash -r
require_python_at_least 3 11
export PYTHONPATH="${ROOT_DIR}/slime_shopping_rl:${ROOT_DIR}:${PYTHONPATH:-}"

[[ -d "${LLAMA_FACTORY_DIR}" ]] || die "Missing LLaMA-Factory dir: ${LLAMA_FACTORY_DIR}"
[[ -d "${MODEL_PATH}" ]] || die "Missing model dir: ${MODEL_PATH}"
[[ -d "${WARMUP_ADAPTER_PATH}" ]] || die "Missing warmup adapter dir: ${WARMUP_ADAPTER_PATH}"
[[ -f "${WARMUP_ADAPTER_PATH}/adapter_config.json" ]] || {
  latest_checkpoint="$(find "${WARMUP_ADAPTER_PATH}" -maxdepth 1 -type d -name 'checkpoint-*' | sort -V | tail -n 1 || true)"
  if [[ -n "${latest_checkpoint}" && -f "${latest_checkpoint}/adapter_config.json" ]]; then
    warn "Warmup root has no adapter_config.json. Using latest checkpoint: ${latest_checkpoint}"
    WARMUP_ADAPTER_PATH="${latest_checkpoint}"
  else
    die "No adapter_config.json found in warmup adapter or its checkpoints: ${WARMUP_ADAPTER_PATH}"
  fi
}

mkdir -p "$(dirname "${FULL_YAML}")"

cat > "${FULL_YAML}" <<YAML
model_name_or_path: ${MODEL_PATH}
adapter_name_or_path: ${WARMUP_ADAPTER_PATH}
stage: sft
do_train: true
finetuning_type: lora
lora_rank: ${LORA_RANK}
lora_alpha: ${LORA_ALPHA}
lora_dropout: 0.05
lora_target: q_proj,v_proj,k_proj,o_proj,gate_proj,up_proj,down_proj
dataset_dir: ${LLAMA_FACTORY_DIR}/data
dataset: shopping_react
eval_dataset: shopping_react_eval
template: qwen3
cutoff_len: 4096
train_on_prompt: false
val_size: 0.0
num_train_epochs: ${EPOCHS:-4}
per_device_train_batch_size: 1
gradient_accumulation_steps: ${GRAD_ACCUM_STEPS}
learning_rate: ${LR:-5.0e-5}
lr_scheduler_type: cosine
warmup_ratio: 0.05
optim: adamw_torch
fp16: true
bf16: false
gradient_checkpointing: true
dataloader_num_workers: 0
per_device_eval_batch_size: 1
eval_strategy: steps
eval_steps: 20
logging_steps: 1
disable_tqdm: false
plot_loss: true
report_to: none
output_dir: ${OUTPUT_DIR}
save_strategy: steps
save_steps: 20
save_total_limit: 3
load_best_model_at_end: true
metric_for_best_model: eval_loss
greater_is_better: false
overwrite_output_dir: true
YAML

log "Starting full trajectory SFT from warmup: ${FULL_YAML}"
log "Base model: ${MODEL_PATH}"
log "Warmup adapter: ${WARMUP_ADAPTER_PATH}"
log "Output adapter: ${OUTPUT_DIR}"
cd "${LLAMA_FACTORY_DIR}"
python -m llamafactory.cli train "${FULL_YAML}"

log "Full trajectory adapter: ${OUTPUT_DIR}"
