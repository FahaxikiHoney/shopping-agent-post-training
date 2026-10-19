#!/usr/bin/env bash
set -euo pipefail

# Example only: tune paths and parallelism on your Linux training machine.
# Slime uses Megatron for training and SGLang for rollout. The SFT HF checkpoint
# below should be your LLaMA-Factory merged model, or a base checkpoint plus the
# converted Megatron actor/ref checkpoint required by your Slime setup.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

HF_CHECKPOINT="${HF_CHECKPOINT:-/path/to/shopping_qwen3_0.6b_merged}"
MEGATRON_REF="${MEGATRON_REF:-/path/to/megatron/ref_ckpt}"
MEGATRON_SAVE="${MEGATRON_SAVE:-/path/to/output/shopping_slime_grpo}"
TRAIN_DATA="${TRAIN_DATA:-${ROOT_DIR}/data/shopping_slime_tasks.jsonl}"

python -m slime.train \
  --hf-checkpoint "${HF_CHECKPOINT}" \
  --ref-load "${MEGATRON_REF}" \
  --load "${MEGATRON_SAVE}" \
  --save "${MEGATRON_SAVE}" \
  --train-data "${TRAIN_DATA}" \
  --input-key prompt \
  --label-key label \
  --apply-chat-template \
  --metadata-key metadata \
  --advantage-estimator grpo \
  --n-samples-per-prompt 8 \
  --normalize-advantages \
  --rollout-function-path "${ROOT_DIR}/shopping_slime/custom_generate.py" \
  --rollout-num-gpus 1 \
  --rollout-num-gpus-per-engine 1 \
  --sglang-context-length 8192 \
  --temperature 0.8 \
  --top-p 0.95 \
  --max-response-length 2048 \
  --micro-batch-size 1 \
  --global-batch-size 8 \
  "$@"
