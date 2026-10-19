# 00 · 项目目标、模块与复现路线

## 1. 这个项目解决什么问题

购物 Agent 不只是生成一段推荐文案。它需要理解预算、品类和使用场景，选择合适的工具，读取工具结果，避免编造商品事实，再将推荐与商卡正确对应。项目围绕这条闭环组织后训练实验：制造或整理多轮工具轨迹，以规则和 Judge 发现问题，用 SFT 教会模型稳定调用工具，再通过环境交互和 GRPO 改善多步决策。

项目目标是提供可读、可复现的实验工程，而非提供线上购物服务。`shopping_agent/` 的商品检索使用本地 mock 数据；真实业务接入、线上服务凭据和原始会话采集实现不属于开源运行路径。

## 2. 端到端流程

| 阶段 | 输入 | 主要实现 | 产物 |
|---|---|---|---|
| 任务与轨迹制造 | 场景种子、合成请求或已获授权数据 | `sft_data/`、`shopping_agent/`、`scripts/run_mock_query_batch.py` | 原始 ReAct 轨迹 JSONL |
| 结构和质量门禁 | rollout 轨迹 | `shopping_agent/react/quality_gate.py`、`scripts/check_mock_trajectory_quality.py` | Gate 结果、失败原因 |
| 语义审计与 LLM 评分 | 轨迹和工具证据 | `scripts/audit_mock_trajectory_semantics.py`、`llm_evaluation/evaluate.py` | 五维 Judge 结果、总分和报告 |
| SFT 数据整理 | 通过筛选的轨迹 | `scripts/export_mock_sft.py`、`sft_data/convert_to_chatml_v3.py` | ShareGPT/ChatML JSON |
| LoRA SFT | ChatML 数据和基座模型 | `training/`、`LLaMA-Factory/` | LoRA adapter 或合并 checkpoint |
| Agentic RL | SFT policy、任务、环境和奖励 | `slime_shopping_rl/` + 外部 Slime/Megatron/SGLang | GRPO checkpoint、rollout/reward metrics |

各阶段可以独立使用。想先复现训练时，可直接用仓库整理好的 ChatML；想复现数据闭环，则从 mock rollout 开始。

开箱即用数据的具体文件、样本数和对应启动命令集中在 [06 · 现成数据与代码地图](06-code-and-data-map.md)：包括 1297/142 ChatML、875/100/100 ReAct 切分，以及已转换的 875 条 Slime RL task。

## 3. 重要目录

- `shopping_agent/core/`：上下文、工具注册和 Agent 公共抽象。
- `shopping_agent/agents/`、`shopping_agent/react/`、`shopping_agent/tools/`：购物场景 Agent、ReAct 执行器、Mock 环境和工具。
- `sft_data/`：原始格式样例、整理后的轨迹和训练/验证 JSON，以及旧版与新版转换工具。优先用 `train_chatml_v3.json` / `val_chatml_v3.json` 做 SFT。
- `scripts/`：mock 批跑、质量审计、导出 SFT 样例和敏感信息扫描。
- `llm_evaluation/`：离线规则 Gate 和 LLM-as-a-Judge。
- `trajectory_grader/`：人工查看单条轨迹、Gate 和维度评分的 Streamlit UI。
- `training/` 与 `LLaMA-Factory/`：SFT 配置、数据注册和训练框架 fork。
- `slime_shopping_rl/`：Slime 接口、工具调用 warmup、奖励服务、GRPO 示例和指标仪表板。
- `docs/`：按阶段阅读的使用文档。

## 4. 三种开始方式

### A. 只看格式转换

```bash
python scripts/generate_synthetic_data.py --output data/synthetic.jsonl --count 20
python scripts/convert_to_chatml.py --input data/synthetic.jsonl --output data/train.json
```

### B. 从已有训练集直接做 SFT

按 [03 · LoRA SFT](03-sft-lora.md) 安装 `LLaMA-Factory/` fork，使用 `sft_data/train_chatml_v3.json` 和验证集启动训练。

### C. 复现 rollout → 评估 → SFT 闭环

按 [01 · 数据制造](01-data-pipeline.md) 生成或运行 mock 轨迹，再依次执行 [02 · 质量与 LLM 评估](02-quality-and-llm-evaluation.md) 与 SFT 导出。LLM rollout/Judge 是可选项，需要配置获准使用的 API；纯 Mock 用例可离线运行。

训练完 SFT 后再进入 [04 · Slime GRPO](04-rl-grpo.md)。

## 5. 环境分工

- 数据脚本、Mock 环境、规则 Gate 和样例评估：Python 环境即可，不需要 GPU。
- LLM rollout/Judge：需要兼容的 API endpoint 和环境变量；也可以先用规则 Gate/Mock Judge。
- LoRA SFT：建议 Linux 或 Windows GPU 主机，Python 3.11+、CUDA 兼容 PyTorch 和单独下载的模型。
- Slime GRPO：推荐 Linux GPU 主机或 Slime 官方 Docker，另需 Slime、Megatron-LM、SGLang 与 checkpoint 转换流程。

## 6. 路径约定

下文命令默认当前工作目录是仓库根目录（即包含 `shopping_agent/`、`sft_data/`、`LLaMA-Factory/` 的目录）。Linux/macOS 使用 `/`；PowerShell 使用 `\`。路径含空格时请加引号。输出默认写在 `sft_data/`、`LLaMA-Factory/output/` 或 `slime_shopping_rl/data/`；正式实验应将模型、缓存、日志和 checkpoint 放到容量充足且不提交 Git 的磁盘。

## 7. 阅读顺序

1. [01 · 数据制造与转换](01-data-pipeline.md)
2. [02 · 规则门禁与 LLM 评估](02-quality-and-llm-evaluation.md)
3. [03 · LoRA SFT](03-sft-lora.md)
4. [04 · Slime GRPO](04-rl-grpo.md)
5. [05 · 指标、复现和发布前检查](05-metrics-reproducibility-release.md)
