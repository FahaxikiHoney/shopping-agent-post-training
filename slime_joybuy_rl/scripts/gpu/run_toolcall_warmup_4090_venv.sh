#!/usr/bin/env bash
set -euo pipefail

# Tool-call-only SFT warmup. Use this when the model emits product cards before
# calling tools. It trains only the first assistant tool-call turn.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_venv.sh"

ROOT_DIR="$(repo_root_from_gpu_script)"
LLAMA_FACTORY_DIR="${LLAMA_FACTORY_DIR:-${ROOT_DIR}/LLaMA-Factory}"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv-joybuy-sft}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
MODEL_PATH="${MODEL_PATH:-${ROOT_DIR}/models/Qwen3-0.6B}"
SOURCE_DATA="${SOURCE_DATA:-${LLAMA_FACTORY_DIR}/llamafactory/train_joybuy_react.json}"
WARMUP_DATA="${WARMUP_DATA:-${LLAMA_FACTORY_DIR}/data/train_joybuy_toolcall_warmup.json}"
WARMUP_YAML="${WARMUP_YAML:-${ROOT_DIR}/.cache/generated/lora_qwen3_0.6b_toolcall_warmup.yaml}"
OUTPUT_DIR="${OUTPUT_DIR:-${LLAMA_FACTORY_DIR}/output/joybuy_qwen3_0.6b_toolcall_warmup}"
LORA_RANK="${LORA_RANK:-64}"
LORA_ALPHA="${LORA_ALPHA:-128}"
GRAD_ACCUM_STEPS="${GRAD_ACCUM_STEPS:-8}"

create_and_activate_venv "${VENV_DIR}" "${PYTHON_BIN}"
hash -r
require_python_at_least 3 11
export PYTHONPATH="${ROOT_DIR}/slime_joybuy_rl:${ROOT_DIR}:${PYTHONPATH:-}"

[[ -d "${MODEL_PATH}" ]] || die "Missing model dir: ${MODEL_PATH}"
[[ -f "${SOURCE_DATA}" ]] || die "Missing source data: ${SOURCE_DATA}"
mkdir -p "$(dirname "${WARMUP_DATA}")" "$(dirname "${WARMUP_YAML}")"

python "${ROOT_DIR}/slime_joybuy_rl/joybuy_slime/build_toolcall_warmup.py" \
  --input "${SOURCE_DATA}" \
  --output "${WARMUP_DATA}" \
  --limit "${LIMIT:-0}"

python - "$LLAMA_FACTORY_DIR/data/dataset_info.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
data["joybuy_toolcall_warmup"] = {
    "file_name": "train_joybuy_toolcall_warmup.json",
    "formatting": "sharegpt",
    "columns": {"messages": "conversations"},
    "tags": {
        "role_tag": "from",
        "content_tag": "value",
        "user_tag": "human",
        "assistant_tag": "gpt",
        "system_tag": "system",
        "observation_tag": "human",
    },
}
path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
PY

cat > "${WARMUP_YAML}" <<YAML
model_name_or_path: ${MODEL_PATH}
stage: sft
do_train: true
finetuning_type: lora
lora_rank: ${LORA_RANK}
lora_alpha: ${LORA_ALPHA}
lora_dropout: 0.05
lora_target: q_proj,v_proj,k_proj,o_proj,gate_proj,up_proj,down_proj
dataset_dir: ${LLAMA_FACTORY_DIR}/data
dataset: joybuy_toolcall_warmup
template: qwen3
cutoff_len: 2048
train_on_prompt: false
val_size: 0.0
num_train_epochs: ${EPOCHS:-8}
per_device_train_batch_size: 1
gradient_accumulation_steps: ${GRAD_ACCUM_STEPS}
learning_rate: ${LR:-1.0e-4}
lr_scheduler_type: cosine
warmup_ratio: 0.05
optim: adamw_torch
fp16: true
bf16: false
gradient_checkpointing: true
dataloader_num_workers: 0
logging_steps: 1
disable_tqdm: false
plot_loss: true
report_to: none
output_dir: ${OUTPUT_DIR}
save_strategy: steps
save_steps: 20
save_total_limit: 3
overwrite_output_dir: true
YAML

log "Starting tool-call warmup: ${WARMUP_YAML}"
cd "${LLAMA_FACTORY_DIR}"
python -m llamafactory.cli train "${WARMUP_YAML}"

log "Warmup adapter: ${OUTPUT_DIR}"
