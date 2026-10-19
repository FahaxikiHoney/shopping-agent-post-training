# 04 · Slime rollout 与 GRPO

SFT 之后可用 Agent 环境做 on-policy rollout，并用组相对优势（GRPO）优化工具选择、环境交互和最终回答。仓库提供 Slime adapter、任务转换、规则奖励服务和启动示例；Slime、Megatron-LM、SGLang、CUDA、模型 checkpoint 与权重转换工具均是外部依赖。

## 1. RL 数据格式

已经准备好的 RL 输入集中在 `sft_data/ready_to_run/rl/joybuy_slime_tasks.jsonl`（875 条）。`slime_joybuy_rl/joybuy_slime/task_data.py` 可从 `sft_data/ready_to_run/react_sft/train_joybuy_react.json` 重新生成它。每行包含：

- `prompt`: 对话 prompt 列表；
- `label`: 可选参考标签；
- `metadata`: query、site、scenario 和 task id，供 rollout 环境初始化。

转换器会读取 `conversations` 格式。若输入是 `messages` 格式，先转换成 LLaMA-Factory 的 conversations 形式，或扩展转换器后再运行。

```bash
python slime_joybuy_rl/joybuy_slime/task_data.py \
  --input sft_data/ready_to_run/react_sft/train_joybuy_react.json \
  --output sft_data/ready_to_run/rl/joybuy_slime_tasks.jsonl
```

这两个输入/输出文件都随仓库提供；默认 RL 启动脚本会直接读取已生成的 task 文件，不需要先执行转换。

## 2. 本地 reward smoke test

启动基于规则奖励的本地 HTTP 服务：

```bash
python -m slime_joybuy_rl.joybuy_slime.rollout_service --port 8791
```

可选 Judge 奖励需要 OpenAI-compatible endpoint。通过环境变量配置 `JUDGE_API_KEY`、`JUDGE_API_BASE`、`JUDGE_MODEL`，不要把真实密钥写在 `.env` 或示例配置中。Judge 只在规则奖励基础上作有限调整，缺失商卡等硬失败仍会失败。

## 3. 环境安装

Slime 训练推荐 Linux GPU 主机或 Slime 官方容器；不要在普通 Windows 环境照搬 Linux/Megatron 启动脚本。项目脚本 `run_slime_4090_venv.sh` 会从上游获取 Slime 与 Megatron-LM，因此需要网络、足够磁盘和匹配的 CUDA 软件栈。首次运行先查看脚本顶部变量和 `slime_joybuy_rl/ENVIRONMENT.md`，重点确认：

- `THIRD_PARTY_DIR`、Slime/Megatron checkout 路径；
- `HF_CHECKPOINT`、`MEGATRON_REF`、`MEGATRON_SAVE`；
- Python、PyTorch、CUDA、SGLang 版本；
- 训练任务 JSONL 路径和 rollout GPU 数量。

```bash
VENV_DIR=/data/venvs/shopping-rl \
THIRD_PARTY_DIR=/data/third_party \
HF_CHECKPOINT=/models/merged-sft \
MEGATRON_REF=/models/megatron-ref \
MEGATRON_SAVE=/data/checkpoints/shopping-grpo \
TRAIN_DATA=sft_data/ready_to_run/rl/joybuy_slime_tasks.jsonl \
RUN_TRAIN=1 \
bash slime_joybuy_rl/scripts/gpu/run_slime_4090_venv.sh
```

设置 `RUN_TRAIN=1` 才会开始 GRPO；去掉该变量会只准备环境并运行适配 smoke check。该脚本可能 clone/upstream install 大型依赖，首次执行前检查存储和网络要求。

## 4. GRPO 配置

示例为 `slime_joybuy_rl/configs/joybuy_qwen3_0_6b_grpo.example.sh`，包括 HF checkpoint、reference checkpoint、训练数据、rollout 函数、`--advantage-estimator grpo` 和每个 prompt 的采样数。实际 batch、上下文长度、GPU 数量和 checkpoint 结构必须按你的 Slime 版本及硬件调整。先使用小任务数和少量 rollout 验证解析、环境重置、奖励和保存恢复。

Rollout 通过 `joybuy_slime/custom_generate.py` 调用环境。`action_parser.py` 负责将模型生成解析为工具动作；`reward_adapter.py` 对轨迹做确定性质量评分；可选 Judge、HTTP reward service 和 metrics logger 提供附加评估。

## 5. 训练顺序建议

1. 先跑单元级 adapter/environment smoke check。
2. 用固定 seed tasks 验证 prompt、工具调用解析、tool observation 和终止动作。
3. 检查 reward 是否能区分完成任务、虚构商品和错误商卡。
4. 从 SFT adapter 或其合并/转换 checkpoint 初始化，不要未经检查从随机/不兼容 checkpoint 开始。
5. 小规模 GRPO 验证 rollout 数、组内采样、保存和恢复，再扩大训练。

Slime/Megatron 上游 API 变化较快；将本仓库 adapter 与使用的上游 commit 一起记录。示例脚本不承诺对任意上游版本直接兼容。
