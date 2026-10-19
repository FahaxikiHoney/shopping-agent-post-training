# 06 · 现成数据、脚本地图与直接运行

本文是“我要用哪份数据、跑哪个脚本”的操作索引。默认所有命令都从仓库根目录运行。完整背景见 [00 · 项目概览](00-project-overview.md)，数据字段和自行造轨迹见 [01 · 数据制造](01-data-pipeline.md)，评估原理见 [02 · 质量和 Judge](02-quality-and-llm-evaluation.md)。

## 1. 已随仓库准备好的数据

可直接使用的数据副本集中在 [`sft_data/ready_to_run/`](../sft_data/ready_to_run/README.md)。主配置仍引用原路径；数据包是集中下载/浏览用的开箱目录。

| 路径 | 当前规模 | 格式/用途 | 直接配套 |
|---|---:|---|---|
| `sft_data/train_chatml_v3.json` | 1297 | ShareGPT `messages`，主 LoRA SFT 训练集 | `training/lora_sft.yaml` |
| `sft_data/val_chatml_v3.json` | 142 | 对应验证集 | `training/lora_sft.yaml` |
| `LLaMA-Factory/llamafactory/train_joybuy_react.json` | 875 | ShareGPT `conversations`，含工具回合 | fork 项目配置 `lora_qwen3_0.6b.yaml` |
| `LLaMA-Factory/llamafactory/eval_joybuy_react.json` | 100 | eval split | 同上 |
| `LLaMA-Factory/llamafactory/test_joybuy_react.json` | 100 | 独立 test split | 用于训练后评估 |
| `slime_joybuy_rl/data/joybuy_slime_tasks.jsonl` | 875 | 已由上面 875 条训练数据转换的 Slime `prompt/label/metadata` JSONL | `run_slime_4090_venv.sh` 默认输入 |
| `slime_joybuy_rl/data/seed_tasks.jsonl` | 3 | 小型环境 smoke task | Mock 环境/adapter 联调 |
| `slime_joybuy_rl/data/joybuy_slime_tasks.sample.jsonl` | 5 | Slime task 格式示例 | 学习字段结构 |
| `sft_data/购物助手_思考链_清洗后.jsonl` | 58 | 已整理的多轮轨迹评估样例 | `llm_evaluation/evaluate.py` |
| `sft_data/购物助手_思考链_带评分_97条.jsonl` | 97 | 含已有评估字段的轨迹样例 | 评估分析/参考 |
| `sft_data/queries_600_sample100_seed20260817.jsonl` | 100 | 批量轨迹 runner 的现成 query 输入 | `scripts/run_mock_query_batch.py` |

仓库同时包含更多 mock rollout、Gate 报告、Judge 输出、语义审计报告和历史转换版本。它们用于对照实验和排查失败；新实验应写入新输出目录，不要覆盖这些基线文件。原始线上采集/回放总目录未包含。

## 1.1 每个模块的一键入口

在仓库根目录执行 `python scripts/run_module.py --help` 查看入口。统一启动器将产物写到 `sft_data/generated/`：

| 模块 | 命令 | 说明 |
|---|---|---|
| Mock 轨迹数据生成 | `python scripts/run_module.py mock-data` | 本地 mock，无 API；可传 `--count`、`--scenario`、`--output` |
| LLM 批量轨迹 | `python scripts/run_module.py rollout --sample-size 10 --model MODEL --overwrite` | 默认使用数据包中的 100 条 query；需 `LLM_API_URL`、`LLM_API_KEY` |
| 确定性 Gate | `python scripts/run_module.py gate` | 默认检查数据包中的清洗轨迹；可传输入/输出路径 |
| 五维 LLM Judge | `python scripts/run_module.py judge --count 10 --model MODEL` | 默认评测清洗轨迹；需 LLM API；`--gate-only` 仅运行规则 |
| rollout 导出 SFT | `python scripts/run_module.py export-sft` | 读取默认 rollout 和 quality report，导出过滤后的 SFT JSONL |
| ReAct LoRA SFT | `python scripts/run_module.py sft --model-path /path/to/model` | 自动复用现有 venv 安装脚本并启动 875 条 ReAct 训练 |
| Slime GRPO | `python scripts/run_module.py rl --hf-checkpoint /path/to/sft --megatron-ref /path/to/ref` | 使用数据包 875 RL tasks；需 Linux/WSL、CUDA、Slime/Megatron/SGLang 和 checkpoint |

`export-sft` 必须在批量 rollout 生成 JSONL 与对应 quality report 后执行；它不接收数据包里的扁平轨迹文件。比如：

```bash
python scripts/run_module.py rollout --sample-size 10 --model your-agent-model --overwrite
python scripts/run_module.py export-sft
```

SFT/RL 首次启动会安装依赖并占用较多磁盘/网络；RL 命令会设置 `RUN_TRAIN=1` 真正进入训练。基于 1297/142 ChatML 的训练仍使用 `llamafactory-cli train training/lora_sft.yaml`，详见下一节。

## 2. 直接跑 1297/142 条 LoRA SFT

从仓库根目录安装本地 LLaMA-Factory fork，再训练：

```bash
cd LLaMA-Factory
python -m pip install -e ".[torch,metrics]"
cd ..
llamafactory-cli train training/lora_sft.yaml
```

此配置读取 `sft_data/ready_to_run/chatml/dataset_info.json`，训练 `train_chatml_v3.json`，评估 `val_chatml_v3.json`。训练前仅需准备可用的本地/Hub 基座模型，并按 GPU 调整 `training/lora_sft.yaml` 中模型路径、精度和 batch。模型权重未打包在仓库中。

## 3. 直接跑 875 条项目 ReAct SFT

该方案使用 LLaMA-Factory fork 内的项目配置、数据注册和 875/100/100 train/eval/test 切分。准备好本地 Qwen3-0.6B（或兼容模型）和 CUDA 环境后：

```bash
MODEL_PATH=/models/Qwen3-0.6B \
RUN_TRAIN=1 \
bash slime_joybuy_rl/scripts/gpu/run_sft_4090_venv.sh
```

PowerShell/Git Bash 的路径写法按当前 shell 改。脚本会创建/复用 venv、安装 fork、生成临时 YAML 并启动训练；第一次运行会下载依赖和 PyTorch wheel。也可手动从 `LLaMA-Factory/llamafactory/` 使用 `lora_qwen3_0.6b.yaml`。原有 `train.sh`/`train.bat` 已改成调用统一启动入口。

## 4. 直接跑已有轨迹的 Gate 与 LLM 评估

### 4.1 规则 Gate（离线，不需要模型）

```bash
python scripts/check_mock_trajectory_quality.py \
  sft_data/mock_queries10_sft_20260818.jsonl \
  --output sft_data/generated/mock_queries10_gate.json
```

输入是 ReAct trajectory JSONL，输出 JSON 报告含通过率、失败项和逐样本结果。CLI 也支持多个输入或 glob。

### 4.2 五维 LLM Judge

`llm_evaluation/evaluate.py` 用规则门禁加 D1–D5 Judge 评估清洗后的 SFT trajectory schema。先设置获准使用的兼容 API：

```bash
export LLM_API_URL="https://your-approved-endpoint/v1/chat/completions"
export LLM_API_KEY="<your-key>"
```

运行：

```bash
python llm_evaluation/evaluate.py \
  --input sft_data/购物助手_思考链_清洗后.jsonl \
  --model your-judge-model -c 3 \
  --output sft_data/generated/judge_results.jsonl
```

只执行规则、不调用 LLM：

```bash
python llm_evaluation/evaluate.py \
  --input sft_data/购物助手_思考链_清洗后.jsonl \
  --gate-only \
  --output sft_data/generated/gate_results.jsonl
```

Judge 文件会逐行写入；若中断，先确认脚本的覆盖行为再重跑到新的输出路径。更完整的输入要求、维度含义和人工校准方法见 [02 文档](02-quality-and-llm-evaluation.md)。

### 4.3 独立语义审计

批跑输出是 `{sample, trajectory, attempts, ...}` 包装格式时，用专门的语义审计脚本，不要直接传给只接受扁平 SFT schema 的 Judge：

```bash
python scripts/audit_mock_trajectory_semantics.py \
  --input sft_data/generated/mock_rollouts.jsonl \
  --output sft_data/generated/trajectory_semantics.json \
  --model your-judge-model --resume
```

## 5. 自己制造新轨迹并评估

### 路线 A：本地 Mock 商品环境生成（无需 LLM API）

```bash
python sft_data/llm_gen_oxygen.py --mock -n 20 --scenario all \
  --output sft_data/generated/mock_sft.jsonl
```

输出追加到指定 JSONL；若文件已存在会继续追加。此生成器使用内置场景/Mock 商品返回，不是线上商品数据。

### 路线 B：批量 query → LLM ReAct rollout → Gate

先用仓库里的 100 条 query 跑一小批：

```bash
export LLM_API_URL="https://your-approved-endpoint/v1/chat/completions"
export LLM_API_KEY="<your-key>"
python scripts/run_mock_query_batch.py \
  --input sft_data/queries_600_sample100_seed20260817.jsonl \
  --output sft_data/generated/mock_rollouts.jsonl \
  --sample-size 10 --seed 20261019 --overwrite
```

若使用自己的任务，`--input` JSONL 每行需有 `query`，并推荐 `sample_id`、`site_code`、`scenario_type`。跑完整输入时将 `--sample-size` 设为 0 或不限制（具体以 `--help` 为准）。runner 会同时产生 `mock_rollouts_quality.json`；失败时先看 execution error/Gate issue，再决定是否修数据、prompt 或工具。

### 路线 C：将 rollout 导出为可评估 SFT 轨迹

```bash
python scripts/export_mock_sft.py \
  --input sft_data/generated/mock_rollouts.jsonl \
  --quality-report sft_data/generated/mock_rollouts_quality.json \
  --output sft_data/generated/filtered_trajectories.jsonl

python llm_evaluation/evaluate.py \
  --input sft_data/generated/filtered_trajectories.jsonl \
  --model your-judge-model \
  --output sft_data/generated/filtered_judge.jsonl
```

也可以先运行 `scripts/audit_mock_trajectory_semantics.py` 独立判断整条 rollout 的任务完成和证据一致性。字段转换、失败过滤和质量标签见 [01 文档](01-data-pipeline.md)。

## 6. 命令与脚本索引

| 要做什么 | 入口 | 输入 | 输出/备注 |
|---|---|---|---|
| 生成简化合成 query | `scripts/generate_synthetic_data.py` | count/seed | `data/synthetic.jsonl`；用于 schema 演示 |
| 生成完整 mock ReAct 轨迹 | `sft_data/llm_gen_oxygen.py --mock` | 内置主题与 mock 商品 | `sft_data/generated/mock_sft.jsonl`（需指定 `--output`） |
| 从 query 文件批量跑模型 | `scripts/run_mock_query_batch.py` | query JSONL + LLM API | rollout JSONL + `_quality.json` |
| 固定场景能力 smoke | `scripts/run_mock_capability_smoke.py` | 脚本内固定场景 + LLM API | 多语言/多场景 rollout 报告 |
| 确定性质量 Gate | `scripts/check_mock_trajectory_quality.py` | trajectory JSONL | JSON 逐条 Gate 报告 |
| Judge 轨迹语义 | `scripts/audit_mock_trajectory_semantics.py` | batch wrapper JSONL + LLM API | JSON 语义审计 |
| Judge 商品召回相关性 | `scripts/audit_mock_recall_semantics.py` | 带召回结果的 rollout + LLM API | JSON 召回审计 |
| Judge 五维回复质量 | `llm_evaluation/evaluate.py` | 扁平 SFT trajectory JSONL | JSONL Gate + D1–D5 |
| 导出合格 rollout | `scripts/export_mock_sft.py` | batch JSONL + quality JSON | 扁平 SFT schema JSONL |
| 单条人工审阅 | `streamlit run trajectory_grader/app.py` | 手动加载样例 | 浏览器 UI |
| 转 Slime task | `slime_joybuy_rl/joybuy_slime/task_data.py` | fork ShareGPT JSON | `prompt/label/metadata` JSONL |
| 本地 RL reward API | `python -m slime_joybuy_rl.joybuy_slime.rollout_service` | task + completion | rule reward response |
| GRPO 训练启动 | `slime_joybuy_rl/scripts/gpu/run_slime_4090_venv.sh` | 现成 875 tasks + 外部 checkpoint | 先 setup/smoke；`RUN_TRAIN=1` 才训练 |
| RL 指标面板 | `slime_joybuy_rl/scripts/gpu/run_metrics_dashboard_venv.sh` | metrics JSONL | 本地 dashboard |

各 CLI 参数随 `--help` 检查；新运行输出建议放到 `sft_data/generated/`，该目录已被 `.gitignore` 排除。
