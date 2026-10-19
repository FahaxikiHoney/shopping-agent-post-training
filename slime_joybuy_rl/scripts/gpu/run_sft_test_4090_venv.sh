#!/usr/bin/env bash
set -euo pipefail

# Standalone SFT inference test. Run this after SFT finishes so you can inspect
# the model's actual tool-call and final-answer outputs.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_venv.sh"

ROOT_DIR="$(repo_root_from_gpu_script)"
VENV_DIR="${VENV_DIR:-${ROOT_DIR}/.venv-joybuy-sft}"
MODEL_PATH="${MODEL_PATH:-${ROOT_DIR}/models/Qwen3-0.6B}"
ADAPTER_PATH="${ADAPTER_PATH:-${ROOT_DIR}/LLaMA-Factory/output/joybuy_qwen3_0.6b_lora}"
INPUT_FILE="${INPUT_FILE:-${ROOT_DIR}/LLaMA-Factory/llamafactory/test_joybuy_react.json}"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/slime_joybuy_rl/output}"
LIMIT="${LIMIT:-10}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-512}"
NO_REPEAT_NGRAM_SIZE="${NO_REPEAT_NGRAM_SIZE:-6}"
STRICT_TOOL_FIRST="${STRICT_TOOL_FIRST:-0}"
PYTHON_BIN="${PYTHON_BIN:-python3.11}"

create_and_activate_venv "${VENV_DIR}" "${PYTHON_BIN}"
hash -r
require_python_at_least 3 11
export PYTHONPATH="${ROOT_DIR}/slime_joybuy_rl:${ROOT_DIR}:${PYTHONPATH:-}"

[[ -d "${MODEL_PATH}" ]] || die "Missing model dir: ${MODEL_PATH}"
[[ -d "${ADAPTER_PATH}" ]] || die "Missing adapter dir: ${ADAPTER_PATH}"
[[ -f "${INPUT_FILE}" ]] || die "Missing input file: ${INPUT_FILE}"
mkdir -p "${OUTPUT_DIR}"

if [[ ! -f "${ADAPTER_PATH}/adapter_config.json" ]]; then
  LATEST_CHECKPOINT="$(
    find "${ADAPTER_PATH}" -maxdepth 1 -type d -name 'checkpoint-*' 2>/dev/null \
      | sed -E 's#.*checkpoint-([0-9]+)$#\1 &#' \
      | sort -n \
      | tail -n 1 \
      | cut -d' ' -f2-
  )"
  if [[ -n "${LATEST_CHECKPOINT}" && -f "${LATEST_CHECKPOINT}/adapter_config.json" ]]; then
    warn "ADAPTER_PATH has no adapter_config.json; using latest checkpoint: ${LATEST_CHECKPOINT}"
    ADAPTER_PATH="${LATEST_CHECKPOINT}"
  else
    die "No adapter_config.json found in ${ADAPTER_PATH} or its checkpoint-* dirs"
  fi
fi

log "Using adapter path: ${ADAPTER_PATH}"

EXTRA_ARGS=()
if [[ "${STRICT_TOOL_FIRST}" == "1" ]]; then
  EXTRA_ARGS+=(--strict-tool-first)
fi

python "${ROOT_DIR}/slime_joybuy_rl/joybuy_slime/sft_smoke_test.py" \
  --model-path "${MODEL_PATH}" \
  --adapter-path "${ADAPTER_PATH}" \
  --input "${INPUT_FILE}" \
  --limit "${LIMIT}" \
  --max-new-tokens "${MAX_NEW_TOKENS}" \
  --no-repeat-ngram-size "${NO_REPEAT_NGRAM_SIZE}" \
  --output-jsonl "${OUTPUT_DIR}/sft_test_outputs.jsonl" \
  --output-md "${OUTPUT_DIR}/sft_test_outputs.md" \
  "${EXTRA_ARGS[@]}" \
  "$@"

log "Open report: ${OUTPUT_DIR}/sft_test_outputs.md"
