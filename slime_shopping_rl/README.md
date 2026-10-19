# Slime Agentic RL

本目录包含项目的 Slime rollout adapter、购物环境 reward、任务数据转换器、GRPO 配置模板和启动脚本。

## 已准备好的输入

- `../sft_data/ready_to_run/rl/shopping_slime_tasks.jsonl`：875 条 RL task，已转换完成，作为开源数据包的推荐入口；`data/shopping_slime_tasks.jsonl` 保留兼容副本。
- `data/seed_tasks.jsonl`：3 条轻量 smoke task。
- `data/shopping_slime_tasks.sample.jsonl`：5 条 task schema 示例。

任务转换实现：`shopping_slime/task_data.py`。要重新生成任务文件：

```bash
python slime_shopping_rl/shopping_slime/task_data.py \
  --input sft_data/ready_to_run/react_sft/train_shopping_react.json \
  --output sft_data/ready_to_run/rl/shopping_slime_tasks.jsonl
```

## 直接启动 GRPO

任务数据已经准备好；训练仍需要可用的 SFT/HF checkpoint、Megatron reference checkpoint，以及 Linux GPU 上的 Slime、Megatron-LM、SGLang、CUDA 环境。准备好后：

```bash
VENV_DIR=/data/venvs/shopping-rl \
THIRD_PARTY_DIR=/data/third_party \
HF_CHECKPOINT=/models/merged-sft \
MEGATRON_REF=/models/megatron-ref \
MEGATRON_SAVE=/data/checkpoints/shopping-grpo \
TRAIN_DATA=sft_data/ready_to_run/rl/shopping_slime_tasks.jsonl \
RUN_TRAIN=1 \
bash slime_shopping_rl/scripts/gpu/run_slime_4090_venv.sh
```

Slime 与 Megatron 上游源码、模型权重和 checkpoint 转换工具不包含在这里；启动脚本会安装/获取外部依赖。训练前先看 [`../docs/04-rl-grpo.md`](../docs/04-rl-grpo.md) 的环境、checkpoint 和小规模 rollout 步骤。

## 代码入口

- `shopping_slime/custom_generate.py`：Slime 多轮生成 hook。
- `shopping_slime/action_parser.py`：将生成文本解析为环境动作。
- `shopping_slime/reward_adapter.py`：调用 Mock 环境并计算规则奖励。
- `shopping_slime/rollout_service.py`：本地 HTTP reward 服务。
- `shopping_slime/llm_judge.py`：可选 Judge 奖励微调。
- `shopping_slime/metrics_logger.py` / `metrics_dashboard.py`：记录和查看 rollout 指标。
- `scripts/gpu/run_toolcall_warmup_4090_venv.sh`、`run_full_sft_from_warmup_4090_venv.sh`：两阶段 SFT。
- `scripts/gpu/export_sft_lora_merged_venv.sh`：合并 LoRA adapter。
