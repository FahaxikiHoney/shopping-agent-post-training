#!/bin/bash
# 一键训练脚本
# 使用方式：bash train.sh
# 前置条件：已安装 LLaMA-Factory，已准备好数据文件

set -e

echo "=========================================="
echo " JoySage Shopping Agent LoRA SFT 训练"
echo " 模型：Qwen3.5-0.8B"
echo " 数据：2000条购物Agent轨迹"
echo "=========================================="

# ── 环境检查 ──────────────────────────────────
if ! command -v llamafactory-cli &> /dev/null; then
    echo "[ERROR] 未找到 llamafactory-cli，请先安装 LLaMA-Factory："
    echo "  git clone https://github.com/hiyouga/LLaMA-Factory"
    echo "  cd LLaMA-Factory && pip install -e '.[torch,metrics]'"
    exit 1
fi

# ── 准备数据文件 ──────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$SCRIPT_DIR/../sft_data"
TRAIN_DIR="$SCRIPT_DIR"

# 复制数据到训练目录（LLaMA-Factory 读取当前目录下的 data/）
mkdir -p "$TRAIN_DIR/data"
cp "$DATA_DIR/train_chatml.json" "$TRAIN_DIR/data/"
cp "$DATA_DIR/val_chatml.json"   "$TRAIN_DIR/data/"
cp "$TRAIN_DIR/dataset_info.json" "$TRAIN_DIR/data/"

echo "[OK] 数据文件已准备"
echo "  train: $(wc -l < $DATA_DIR/train_chatml.json) 行"

# ── 启动训练 ──────────────────────────────────
echo ""
echo "[START] 开始训练..."
echo ""

llamafactory-cli train \
    --config_file "$TRAIN_DIR/lora_sft.yaml" \
    --dataset_dir "$TRAIN_DIR/data"

echo ""
echo "[DONE] 训练完成！"
echo "模型保存在：$TRAIN_DIR/output/qwen3.5-0.8b-joybuy"
echo ""
echo "推理测试："
echo "  llamafactory-cli chat --model_name_or_path Qwen/Qwen3.5-0.8B \\"
echo "    --adapter_name_or_path $TRAIN_DIR/output/qwen3.5-0.8b-joybuy \\"
echo "    --template qwen --finetuning_type lora"
