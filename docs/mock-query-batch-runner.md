# Mock Query 批量轨迹 Runner

入口：`scripts/run_mock_query_batch.py`。当前发布版的可直接运行 query 集为 `sft_data/queries_600_sample100_seed20260817.jsonl`（100 条）。原始 600/2000 条线上 query 集未随发布版提供。

## 抽样预览

下面命令固定抽 10 条并只显示选择结果，不调用模型：

```bash
python scripts/run_mock_query_batch.py \
  --input sft_data/queries_600_sample100_seed20260817.jsonl \
  --output sft_data/generated/mock_rollouts.jsonl \
  --sample-size 10 --seed 20261019 --dry-run
```

## 执行轨迹生成

需要配置 OpenAI-compatible LLM：

```bash
export LLM_API_URL="https://your-approved-endpoint/v1/chat/completions"
export LLM_API_KEY="<your-key>"

python scripts/run_mock_query_batch.py \
  --input sft_data/queries_600_sample100_seed20260817.jsonl \
  --output sft_data/generated/mock_rollouts.jsonl \
  --sample-output sft_data/generated/selected_queries.jsonl \
  --quality-output sft_data/generated/mock_rollouts_quality.json \
  --sample-size 10 --seed 20261019 --model your-model --retries 3
```

runner 串行运行并支持重试。输出主 JSONL 每行包含 `sample`、`trajectory`、`elapsed_seconds`、`attempts` 和 `error`；结束时写质量汇总和逐条 Gate 结果。Gate 失败会返回非零退出码，但已完成结果仍保存在文件中。

## 断点续跑和定点重跑

```bash
python scripts/run_mock_query_batch.py \
  --input sft_data/queries_600_sample100_seed20260817.jsonl \
  --output sft_data/generated/mock_rollouts.jsonl \
  --sample-size 10 --seed 20261019 --resume
```

使用 `--resume` 跳过已经 `done` 的 sample；失败或缺失样本会重试。指定 `--sample-id` 可定点选择样本，配合 `--resume --rerun` 强制重跑。正式大批量运行前先用 `--dry-run` 并设置少量 `--sample-size`。

完整数据制造、Gate、导出 SFT 和 LLM Judge 路线见 [06 · 代码与数据地图](06-code-and-data-map.md)。
