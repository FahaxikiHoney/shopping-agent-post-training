#!/bin/bash

# ============================================================
# Shopping Agent SFT 完整流程
#
# 1. LoRA SFT
# 2. 合并 LoRA
# 3. 测试集评估
#
# Model: Qwen3-0.6B
# Environment: Windows + Git Bash + Conda
# ============================================================


# ============================================================
# 路径配置
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MODEL_PATH="${MODEL_PATH:-${ROOT_DIR}/models/Qwen3-0.6B}"
LLAMAFACTORY="${LLAMAFACTORY:-${ROOT_DIR}/LLaMA-Factory}"
SHOPPING_DIR="${ROOT_DIR}/sft_data/ready_to_run/react_sft"

# YAML
TRAIN_YAML="${SHOPPING_DIR}/lora_qwen3_0.6b.yaml"

# 数据
TRAIN_DATA="${SHOPPING_DIR}/train_shopping_react.json"
EVAL_DATA="${SHOPPING_DIR}/eval_shopping_react.json"
TEST_DATA="${SHOPPING_DIR}/test_shopping_react.json"

# dataset_info.json 仍然保持在官方 data 目录
DATASET_INFO="${SHOPPING_DIR}/dataset_info.json"

# 输出目录
OUTPUT_LORA="${OUTPUT_LORA:-${LLAMAFACTORY}/output/shopping_qwen3_0.6b_lora}"

OUTPUT_MERGED="${OUTPUT_MERGED:-${LLAMAFACTORY}/output/shopping_qwen3_0.6b_merged}"


# ============================================================
# 日志颜色
# ============================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

err() {
    echo -e "${RED}[ERR]${NC} $1"
    exit 1
}


echo ""
echo "============================================================"
echo " Shopping Agent SFT 完整流程"
echo " Qwen3-0.6B + LoRA"
echo "============================================================"
echo ""


# ============================================================
# 0. 环境检查
# ============================================================

log "检查环境..."


# Base Model
[ -d "$MODEL_PATH" ] \
    || err "找不到模型: $MODEL_PATH"


# LLaMA-Factory 根目录
[ -d "$LLAMAFACTORY" ] \
    || err "找不到 LLaMA-Factory: $LLAMAFACTORY"


# YAML
[ -f "$TRAIN_YAML" ] \
    || err "找不到训练配置: $TRAIN_YAML"


# dataset_info
[ -f "$DATASET_INFO" ] \
    || err "找不到 dataset_info.json: $DATASET_INFO"


# train
[ -f "$TRAIN_DATA" ] \
    || err "找不到训练数据: $TRAIN_DATA"


# eval
[ -f "$EVAL_DATA" ] \
    || err "找不到评估数据: $EVAL_DATA"


# test
[ -f "$TEST_DATA" ] \
    || err "找不到测试数据: $TEST_DATA"


# llamafactory-cli
command -v llamafactory-cli >/dev/null 2>&1 \
    || err "找不到 llamafactory-cli，请先执行 conda activate llama-env"


log "环境检查通过"


echo ""
log "Python:"
which python

echo ""

log "LLaMA-Factory CLI:"
which llamafactory-cli

echo ""

log "GPU:"
nvidia-smi --query-gpu=name,memory.total,memory.free \
    --format=csv,noheader 2>/dev/null \
    || warn "nvidia-smi 未正常执行"


# ============================================================
# 切换到 LLaMA-Factory 项目根目录
# ============================================================

cd "$LLAMAFACTORY" \
    || err "无法进入 $LLAMAFACTORY"


mkdir -p "$OUTPUT_LORA"
mkdir -p "$OUTPUT_MERGED"


# ============================================================
# STEP 1: LoRA SFT
# ============================================================

echo ""
echo "============================================================"
echo " STEP 1/3  LoRA SFT"
echo ""
echo " Train : 875"
echo " Eval  : 100"
echo " Epoch : 3"
echo "============================================================"
echo ""


llamafactory-cli train "$TRAIN_YAML"


TRAIN_EXIT_CODE=$?


if [ $TRAIN_EXIT_CODE -ne 0 ]; then

    echo ""

    err "训练失败。

常见检查项：

1. CUDA OOM
   → 把 per_device_train_batch_size 从 4 改成 2

2. dataset_info.json 找不到
   → 检查 ${DATASET_INFO}

3. 数据集注册错误
   → 检查 shopping_react / shopping_react_eval

4. 数据文件路径错误
   → 检查 dataset_info.json 的 file_name

5. template 错误
   → template: qwen3

6. 数据格式错误
   → 检查 messages / sharegpt schema"
fi


echo ""
log "训练完成"

log "LoRA Adapter:"
echo "$OUTPUT_LORA"


# ============================================================
# STEP 2: 合并 LoRA
# ============================================================

echo ""
echo "============================================================"
echo " STEP 2/3  合并 LoRA"
echo ""
echo " 输出:"
echo " $OUTPUT_MERGED"
echo "============================================================"
echo ""


llamafactory-cli export \
    --model_name_or_path "$MODEL_PATH" \
    --adapter_name_or_path "$OUTPUT_LORA" \
    --template qwen3 \
    --finetuning_type lora \
    --export_dir "$OUTPUT_MERGED" \
    --export_size 4


MERGE_EXIT_CODE=$?


if [ $MERGE_EXIT_CODE -ne 0 ]; then
    err "LoRA 合并失败"
fi


echo ""
log "LoRA 合并完成"

log "Merged Model:"
echo "$OUTPUT_MERGED"


# ============================================================
# STEP 3: 测试集评估
# ============================================================

echo ""
echo "============================================================"
echo " STEP 3/3  Test Eval"
echo ""
echo " Test : 100"
echo "============================================================"
echo ""


EVAL_OUTPUT="${OUTPUT_MERGED}/eval_results"


mkdir -p "$EVAL_OUTPUT"


llamafactory-cli eval \
    --model_name_or_path "$OUTPUT_MERGED" \
    --template qwen3 \
    --finetuning_type full \
    --task clm \
    --dataset shopping_react_test \
    --dataset_dir "${SHOPPING_DIR}" \
    --per_device_eval_batch_size 4 \
    --output_dir "$EVAL_OUTPUT"


EVAL_EXIT_CODE=$?


if [ $EVAL_EXIT_CODE -ne 0 ]; then

    warn "测试集 eval 没有正常完成。"

    warn "不影响前面的 SFT 和 LoRA Merge。"

fi


# ============================================================
# 完成
# ============================================================

echo ""
echo "============================================================"
echo " 全部流程结束"
echo "============================================================"
echo ""


echo "LoRA Adapter:"
echo "  $OUTPUT_LORA"

echo ""

echo "Merged Model:"
echo "  $OUTPUT_MERGED"

echo ""

echo "Eval Result:"
echo "  $EVAL_OUTPUT"

echo ""


echo "------------------------------------------------------------"
echo "直接加载 LoRA 推理"
echo "------------------------------------------------------------"
echo ""

echo "llamafactory-cli chat \\"
echo "  --model_name_or_path $MODEL_PATH \\"
echo "  --adapter_name_or_path $OUTPUT_LORA \\"
echo "  --template qwen3 \\"
echo "  --finetuning_type lora"

echo ""


echo "------------------------------------------------------------"
echo "使用合并模型推理"
echo "------------------------------------------------------------"
echo ""

echo "llamafactory-cli chat \\"
echo "  --model_name_or_path $OUTPUT_MERGED \\"
echo "  --template qwen3 \\"
echo "  --finetuning_type full"

echo ""

echo "============================================================"
