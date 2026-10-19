# Shopping Agent LLM 轨迹评估

这个目录提供规则 Gate 和五维 LLM-as-a-Judge 批量评估。已有数据、输入 schema、命令示例和如何衔接 rollout 导出见 [`../docs/02-quality-and-llm-evaluation.md`](../docs/02-quality-and-llm-evaluation.md) 与 [`../docs/06-code-and-data-map.md`](../docs/06-code-and-data-map.md)。

## 文件

- `evaluate.py`：主评估程序，包含 Judge 提示词、规则 Gate、五维评分和批量执行逻辑。
- `__init__.py`：Python 包标识。
- `sft_data/evaluate_v2.py`：旧路径兼容入口，实际调用本目录的 `evaluate.py`。

## 评估维度

- D1：需求理解
- D2：事实与价格准确性
- D3：推荐相关性与选择质量
- D4：回复完整性
- D5：推荐理由价值

评估前还会检查商卡编号和回复文本质量。

## 使用方法

```bash
python3 llm_evaluation/evaluate.py \
  --input sft_data/mock_购物助手_思考链_清洗后_100条_v14_20260818.jsonl \
  --model GLM-5.2 \
  -c 3 \
  --judge-retries 3 \
  --retry-delay 5 \
  --output sft_data/mock_queries100_llm_eval.jsonl
```

只运行规则 Gate，不调用 LLM：

```bash
python3 llm_evaluation/evaluate.py \
  --input sft_data/mock_购物助手_思考链_清洗后_100条_v14_20260818.jsonl \
  --gate-only \
  --output sft_data/mock_queries100_gate_eval.jsonl
```

旧命令仍然可用：

```bash
python3 sft_data/evaluate_v2.py --help
```

## 输入格式

输入必须是清洗后的轨迹 JSONL，每条包含：

- `trajectory_id`
- `user_query`
- `tools`
- `messages`
- `metadata`
- `evaluation`
- `quality_tag`

## 输出格式

每条评估结果包含规则 Gate、五维 Judge 结果和最终 `score`。Judge 请求失败时，`score` 为 `-1.0`，应重试而不是计入平均质量分。

评估器会把 `final_price`、`original_price`、`sales`、`keyword` 和可用规格完整提供给 Judge，不再为无币种的价格数字硬编码美元符号。
