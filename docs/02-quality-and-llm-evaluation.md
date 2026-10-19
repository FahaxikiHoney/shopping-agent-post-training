# 02 · 规则门禁、语义审计与 LLM Judge

质量评估分两层：先用确定性规则快速拦截结构和硬约束，再用 Judge 对推荐质量做语义判断。LLM 评分不能取代工具证据，也不能把规则失败“平均”掉。

## 1. 质量门禁

`joybuy_agent/react/quality_gate.py` 在轨迹执行时检查工具调用与回复约束；`scripts/check_mock_trajectory_quality.py`、`scripts/audit_mock_trajectory_semantics.py` 和 `scripts/audit_mock_recall_semantics.py` 面向离线 JSONL 做质量或语义审计。先查看参数：

```bash
python scripts/check_mock_trajectory_quality.py --help
python scripts/audit_mock_trajectory_semantics.py --help
python scripts/audit_mock_recall_semantics.py --help
```

门禁重点包括：工具调用 schema 是否有效、轨迹状态是否完成、工具 observation 是否可关联、无召回时是否虚构商品、回复中的 `[product:N]` 是否能映射到候选商品、预算/筛选条件是否违反。将 Gate 失败样本单独隔离，修复生成器或环境后重新跑；不要直接把失败轨迹混进正例 SFT。

## 2. LLM Judge 维度

主评估程序为 `llm_evaluation/evaluate.py`。它保留规则 Gate，并对五个维度给出判定和原因：

| 维度 | 评估重点 |
|---|---|
| D1 需求理解 | 是否识别品类、预算、场景、限制条件和用户意图 |
| D2 事实准确 | 价格、规格、销量、库存等是否有工具结果作为依据 |
| D3 推荐质量 | 候选是否相关，筛选和替代是否合理 |
| D4 完整性 | 是否完成任务、正确引用商卡、必要时说明无结果 |
| D5 推荐价值 | 理由是否具体、有比较依据并帮助用户决策 |

## 3. 只运行 Gate

无需 LLM API。对已整理轨迹运行：

```bash
python llm_evaluation/evaluate.py `
  --input sft_data/trajectories_react_sample.jsonl `
  --gate-only `
  --output sft_data/eval/gate_sample.jsonl
```

Linux/macOS 将续行符换成反斜杠 `\`。路径可替换为你的 rollout 文件。

## 4. 运行 LLM Judge

配置兼容的 endpoint 和密钥：

```powershell
$env:LLM_API_URL = "https://your-approved-endpoint/v1/chat/completions"
$env:LLM_API_KEY = "<your-key>"
```

然后运行：

```bash
python llm_evaluation/evaluate.py \
  --input sft_data/trajectories_react_sample.jsonl \
  --model your-judge-model -c 3 \
  --judge-retries 3 --retry-delay 5 \
  --output sft_data/eval/judge_sample.jsonl
```

评估器读取工具候选和最终回答，为 Judge 提供事实对照。Judge 调用失败或输出不可解析会标记失败分数，失败记录应重试或剔除，不能混入正常平均分。运行耗时和 API 花费随样本量、模型和并发变化。

## 5. 人工复核 UI

`trajectory_grader/` 提供 Streamlit 单条轨迹查看器和 mock judge：

```bash
python -m pip install -r trajectory_grader/requirements.txt
streamlit run trajectory_grader/app.py
```

人工复核特别适合检查 Judge 分歧、低分样本、Gate 边界案例和工具结果无法支撑的“看似合理”回答。具体 UI 导入配置见 `trajectory_grader/config.py`。

## 6. 评估结果如何用于训练

推荐流程：

1. Gate 硬失败先排除。
2. 检查 Judge 是否真的基于工具 observation，而非只看最终文案。
3. 将高置信度正例用于 SFT；将典型失败用于修复数据、环境或工具描述。
4. 保存评估输入版本、模型名、提示词版本、并发和输出文件名，保证分数可追溯。

Judge 是带噪声的测量，不应直接把高分当作事实真值。每次更换 Judge 模型或提示词后，抽样人工校准一批样本。
