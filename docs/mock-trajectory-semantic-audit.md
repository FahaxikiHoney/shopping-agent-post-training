# Shopping Mock 完整轨迹语义审计

入口：`scripts/audit_mock_trajectory_semantics.py`

该审计器使用独立模型检查完整最终回复，而不仅检查工具格式。判定范围包括：

- 推荐商品是否与 Query 和硬约束相关
- 最终回复事实是否来自工具字段
- 空召回和 bundle 缺项是否诚实说明
- 动态促销、最新款、外部价格等信息是否有免责声明
- 回复主体语言是否遵循 Query；短而歧义的 Query 可使用站点语言
- 商品标题、币种和销量标签可保持站点契约语言

## 执行

```bash
python scripts/audit_mock_trajectory_semantics.py \
  --input sft_data/generated/mock_rollouts.jsonl \
  --output sft_data/generated/trajectory_semantics.json \
  --model your-judge-model \
  --batch-size 4 \
  --retries 3 \
  --retry-delay 5
```

## 断点续跑

```bash
python scripts/audit_mock_trajectory_semantics.py \
  --input sft_data/generated/mock_rollouts.jsonl \
  --output sft_data/generated/trajectory_semantics.json \
  --model your-judge-model \
  --batch-size 4 \
  --retries 3 \
  --retry-delay 5 \
  --resume
```

每批完成后立即写入 checkpoint。429、502、503、504、网络错误、`socket.timeout`、普通超时和无效 JSON 均支持重试。

## Verdict

- `pass`：回复相关、事实有依据、语言正确、缺货表达完整。
- `warn`：回复安全，但受无库存、Query 歧义、主观条件或动态数据不可用限制。
- `fail`：无关商品、硬约束违反、工具外事实、错误语言、隐藏 bundle 缺项或无免责声明的动态结论。

审计器只在出现 `fail` 时返回非零退出码。合理的安全空召回不会被判为 fail。
