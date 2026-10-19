# 01 · 数据制造、轨迹和 ChatML 转换

本文说明任务如何变成 Agent 轨迹，再进入训练集。默认从仓库根目录执行命令。

## 1. 两类数据入口

### 仓库内整理样例

`sft_data/trajectories_react.jsonl`、`sft_data/trajectories_cleaned.jsonl` 等是不同阶段的轨迹样例；`sft_data/train_chatml_v3.json` 与 `val_chatml_v3.json` 已经是可供 LLaMA-Factory 使用的训练/验证集。复现 SFT 时可以直接使用它们。

### 新建或自有任务

从 `scripts/generate_synthetic_data.py` 生成通用合成请求，或准备自己的授权任务 JSONL。生成脚本输出的字段为 `id`、`scenario`、`query`、`rationale` 和 `response`，它是轻量格式转换演示输入，不等同于完整的工具调用轨迹。

```bash
python scripts/generate_synthetic_data.py --output data/synthetic.jsonl --count 100 --seed 7
python scripts/convert_to_chatml.py --input data/synthetic.jsonl --output data/synthetic_chatml.json
```

## 2. Mock Agent 批量 rollout

完整 ReAct mock 环境位于 `shopping_agent/react/`，包含工具解析、商品检索、环境状态与轨迹质量 Gate。批量运行器 `scripts/run_mock_query_batch.py` 可调用配置好的 LLM 生成多步轨迹，并支持抽样、续跑和质量报告。其历史默认输入 `sft_data/training-data/data/trajectory_inputs/queries_600.jsonl` 是未随发布版提供的原始集合；仓库另带经过抽样整理的 `sft_data/queries_600_sample100_seed20260817.jsonl`，可以直接作为演示输入，也可显式指定你有权使用的自有 query JSONL：

```bash
python scripts/run_mock_query_batch.py `
  --input data/my_authorized_queries.jsonl `
  --output sft_data/generated/mock_rollouts.jsonl `
  --sample-size 100 --seed 20260817 --overwrite
```

Linux/macOS:

```bash
python scripts/run_mock_query_batch.py \
  --input data/my_authorized_queries.jsonl \
  --output sft_data/generated/mock_rollouts.jsonl \
  --sample-size 100 --seed 20260817 --overwrite
```

输入每行至少应包含 `query`；建议提供唯一 `sample_id`、`site_code` 和 `scenario_type`。查看 CLI 全部选项：

```bash
python scripts/run_mock_query_batch.py --help
```

先用 `--dry-run` 检查样本抽样，不调用模型。若需要 LLM，请在进程环境中设置 `LLM_API_URL`、`LLM_API_KEY`，然后指定受支持的 `--model`。密钥不要写进数据文件、脚本或 YAML。

## 3. 轨迹结构

完整轨迹是 JSONL（一行一条 JSON object），一般包括：

- `trajectory_id` / 样本 ID：标识样本；公开前应使用新生成的匿名 ID。
- `user_query`：任务文本。
- `messages`：system/user/assistant/tool 多轮记录；assistant 工具调用保留结构化 `tool_calls`，tool 结果应与调用 ID 对应。
- `tools`：本条轨迹可调用的工具 schema。
- `final_response` 或最后一条 assistant 消息：最终回答，商品引用用 `[product:N]` 对应工具返回商卡。
- `metadata`、`status`：场景、调用数、运行状态等实验字段。
- `evaluation`：规则 Gate 和 Judge 结果（若已运行）。

工具调用轨迹必须保存工具调用和 observation 的顺序；只保留最终回答会丢失 Agentic SFT 的主要监督信号。

## 4. 由 mock rollout 导出 SFT

`scripts/export_mock_sft.py` 可将批跑轨迹和质量报告筛选、规范化后导出为训练样例。先检查 CLI 参数：

```bash
python scripts/export_mock_sft.py --help
```

示例：

```bash
python scripts/export_mock_sft.py \
  --input sft_data/generated/mock_rollouts.jsonl \
  --quality-report sft_data/generated/mock_rollouts_quality.json \
  --output sft_data/generated/filtered_sft.jsonl
```

参数实际名称是 `--quality-report`（可重复指定），不是 `--quality`。不要覆盖原始 rollout。导出器会校验工具调用与 tool message 的对应关系，并写入质量标签/评估字段。最终供 LLaMA-Factory 使用的 ShareGPT 文件需有 `messages` 数组。

仓库还保留 `sft_data/convert_to_chatml_v3.py`，它是针对项目历史轨迹 schema 的固定路径转换脚本，默认从同目录的 `trajectories_r1_compressed.jsonl` 读取并写出 `train_chatml_v3.json` / `val_chatml_v3.json`。复用时先检查脚本中的输入轨迹是否为你要处理的数据；该脚本按项目 schema 工作，不是任意 JSONL 的通用转换器。

## 5. 格式快速检查

转换后用 Python 检查 JSON 和 message 角色：

```bash
python -c "import json; p='sft_data/train_chatml_v3.json'; d=json.load(open(p,encoding='utf-8')); print('rows',len(d),'first roles',[m['role'] for m in d[0]['messages']])"
```

LLaMA-Factory 从 `dataset_dir` 读取 `dataset_info.json`。当前发布配置的活动注册文件是 `sft_data/ready_to_run/chatml/dataset_info.json`；`sft_data/dataset_info.json` 和 `training/dataset_info.json` 是兼容/文档副本。更改文件名时，确保活动注册文件仍能定位到数据文件。

## 6. 数据治理

发布或引入数据前，清除姓名、电话、邮箱、完整地址、订单/账户/会话 ID、私有 URL、访问 token 和内部商品/用户字段。保留随机化后的样本 ID 以支持去重与审计。对于来源于线上会话的文本，即使删除 ID，也要确认再分发授权；匿名化不能替代授权审查。原始线上轨迹采集和回放数据目录未包含在本开源版中。
