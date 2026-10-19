# 03 · SFT 与 LoRA

本项目用 SFT 让模型掌握多轮购物流程和结构化工具调用。集中可用的数据副本位于 `sft_data/ready_to_run/chatml/`（发布清理后 1297 train / 142 validation）。LoRA 配置为 `training/lora_sft.yaml`，数据注册文件在同目录。

## 1. 环境

需要 Python 3.11+、与本机 CUDA 匹配的 PyTorch、足够的 GPU 显存和单独下载的基座模型。先看 `LLaMA-Factory/pyproject.toml` 与其 README 的上游安装说明；本地 fork 自带 `LICENSE`。不要假定不同 CUDA/驱动版本可使用相同 wheel。

```powershell
# PowerShell，从开源仓库根目录
python -m venv .venv-sft
.\.venv-sft\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
# 按本机 CUDA 版本安装匹配的 PyTorch
python -m pip install torch torchvision torchaudio
```

在 fork 目录安装：

```powershell
cd LLaMA-Factory
python -m pip install -e ".[torch,metrics]"
llamafactory-cli version
cd ..
```

Linux/macOS 使用对应的 `source .venv-sft/bin/activate`。按 PyTorch 官方安装选择适合本机 CUDA 的 wheel。

## 2. 数据注册与配置

`sft_data/ready_to_run/chatml/dataset_info.json` 将 `shopping_train` 映射到 `train_chatml_v3.json`，`shopping_validation` 映射到 `val_chatml_v3.json`；格式为 ShareGPT，列名为 `messages`。LLaMA-Factory fork 会在 `dataset_dir` 下寻找注册文件和数据文件，因此配置指向 `sft_data/ready_to_run/chatml`。

从 `opensource/` 根目录调用配置；不要从 `LLaMA-Factory/` 子目录运行该相对路径配置。

运行前至少确认：

- `model_name_or_path` 指向已下载且许可允许使用的模型。
- `dataset` / `eval_dataset` 与 `sft_data/ready_to_run/chatml/dataset_info.json` 的 key 完全一致。
- `dataset_dir` 能找到配置里登记的 JSON 文件。
- `output_dir` 有足够空间且不在要提交的源代码目录中。
- `fp16`/`bf16` 与 GPU 支持一致；小 GPU 应降低 batch、序列长度或启用更省显存的策略。

## 3. 启动基础 LoRA SFT

```bash
llamafactory-cli train training/lora_sft.yaml
```

仓库的配置是可读模板，不保证对每种模型/显卡开箱即跑。LLaMA-Factory 会在输出目录生成 adapter、trainer state、日志和 checkpoint；这些文件不应提交到源码仓库。

## 4. 两阶段工具调用 SFT

`slime_joybuy_rl/scripts/gpu/run_toolcall_warmup_4090_venv.sh` 训练首轮工具调用 warmup；`run_full_sft_from_warmup_4090_venv.sh` 从 warmup adapter 接着训练完整轨迹。脚本可通过环境变量覆盖 `MODEL_PATH`、`SOURCE_DATA`、`OUTPUT_DIR`、LoRA rank、epoch 和学习率。

```bash
MODEL_PATH=/models/your-base-model \
SOURCE_DATA=/data/authorized_sharegpt.json \
OUTPUT_DIR=/models/output/toolcall-warmup \
bash slime_joybuy_rl/scripts/gpu/run_toolcall_warmup_4090_venv.sh
```

第二阶段前，确认 `WARMUP_ADAPTER_PATH` 是第一阶段产物，数据文件包含完整 tool-call/observation/final-answer 回合。具体支持参数以脚本变量为准。

## 5. 推理检查与合并

使用 `slime_joybuy_rl/scripts/gpu/run_sft_test_4090_venv.sh` 做独立 smoke inference，检查模型是否先调用工具、是否使用工具返回事实、是否能结束对话。需要 Slime 或普通 HF 部署时，可用 `export_sft_lora_merged_venv.sh` 合并 adapter；合并不是继续训练的必要条件。

## 6. 训练注意事项

- 不要把包含思维链的 SFT 文本默认公开为“模型真实推理”；其内容是训练标注文本。
- train/validation 应按任务或来源隔离，避免同一用户请求/轨迹的近重复样本跨集合泄漏。
- 记录基座模型 revision、数据文件 hash、配置、随机种子、软件版本和训练产物位置。
- 模型权重不包含在本仓库中；其许可、访问限制和使用条款由模型发布方决定。
