# Shopping Agent Post-Training

[English](README_EN.md)

一个面向研究复现的购物 Agent 后训练项目，覆盖从任务/轨迹数据构造、质量门禁、LLM-as-a-Judge 评估，到 LoRA SFT、工具调用 warmup、Slime GRPO rollout 和训练指标分析的完整链路。项目展示的是一套可检查、可替换、可在 mock 环境复现的方法；仓库中的 mock 商品目录不连接真实电商服务。

这是项目的**第一版公开发布准备稿（v0.1.0）**。数据构造、评估、SFT 和 RL 的链路已整理成可阅读和复现的工程；后续会持续修正文档、改进脚本并补充实验说明。欢迎提问、报告问题和提交改进建议。

> **作者联系**：欢迎通过[小红书](https://xhslink.cn/o/5IN1FW83UoN)联系作者，也欢迎在 GitHub 提交 Issue。

> **发布说明**：仓库保留已整理的训练样例、mock 回归样例和评估产物，便于理解数据结构与流程。原始线上轨迹采集/回放目录不在发布版中。请在再分发或继续加入数据前核实数据授权；代码、模型、数据集可能分别适用不同许可。

## 项目目标

1. 将购物任务表达成带工具调用的多轮 Agent 轨迹，并支持 Mock 环境下可重复运行。
2. 用确定性 Gate 拦截结构错误、无效工具调用和商卡引用问题，再用五维 Judge 评价需求理解、事实准确、推荐质量、完整性和推荐价值。
3. 将通过筛选的轨迹转成 ShareGPT/ChatML，使用 LLaMA-Factory 完成 LoRA SFT，并提供工具调用 warmup 与整轨迹 SFT 的实验脚本。
4. 将 SFT policy 接入 Slime 的多轮 rollout 和 GRPO 奖励流程，记录 reward、Gate 和 rollout 指标。

## 流程总览

```text
任务种子 / 合成或授权数据
        │
        ├── Mock Agent 批量 rollout ──> 原始轨迹 JSONL
        │                                  │
        │                                  ├── 规则 Gate / 语义审计
        │                                  └── LLM Judge 五维评估
        │                                                │
        └── 现成清洗轨迹 ────────────────────────────────┤
                                                         ▼
                                           筛选、转换、导出 ChatML
                                                         │
                                                         ▼
                                               LLaMA-Factory LoRA SFT
                                                         │
                                           可选工具调用 warmup / 合并
                                                         │
                                                         ▼
                                       Slime + Megatron + SGLang rollout
                                                         │
                                                         ▼
                                                GRPO 奖励与指标复盘
```

## 目录导航

| 路径 | 用途 |
|---|---|
| `joybuy_agent/` | Agent、工具注册、ReAct 执行和确定性 Mock 商品环境 |
| `sft_data/` | 轨迹/SFT 样例、数据生成与格式转换、回归和评估结果 |
| `scripts/` | Mock rollout、语义审计、质量检查、SFT 导出和发布前扫描 |
| `llm_evaluation/` | 批量 LLM Judge 与规则 Gate |
| `trajectory_grader/` | 可视化的单条轨迹审阅和评分工具 |
| `training/` | LoRA 配置、数据集注册和训练说明 |
| `LLaMA-Factory/` | 项目使用的 LLaMA-Factory fork（保留其 Apache-2.0 LICENSE） |
| `slime_joybuy_rl/` | Slime rollout adapter、奖励服务、任务转换、GRPO 启动示例与指标面板 |
| `docs/` | 按阶段编排的完整指南、数据协议、评估方法和复现实验说明 |

## 建议阅读顺序

从 [项目流程与复现路线](docs/00-project-overview.md) 开始，然后按顺序阅读 [数据制造](docs/01-data-pipeline.md)、[质量门禁与 LLM 评估](docs/02-quality-and-llm-evaluation.md)、[LoRA SFT](docs/03-sft-lora.md)、[Slime GRPO](docs/04-rl-grpo.md)、[指标与发布](docs/05-metrics-reproducibility-release.md)。要查“哪份数据配哪个脚本、如何直接启动”，看 [现成数据和代码使用地图](docs/06-code-and-data-map.md)；第一次发布到 GitHub 可参考 [首次发布步骤](docs/07-github-first-release.md)。

首次使用建议先跑本地 mock 命令和 Gate，再设置模型 API 执行 rollout/Judge；SFT 与 RL 需要 NVIDIA GPU、模型权重及各自训练依赖。不要把 API 凭据、个人信息或训练 checkpoint 提交到仓库。

## 快速开始：本地数据格式示例

在仓库根目录 `opensource/` 执行。无需 GPU 或 LLM API 即可生成合成请求并检查格式：

```bash
python scripts/generate_synthetic_data.py --output data/synthetic.jsonl --count 20 --seed 7
python scripts/convert_to_chatml.py --input data/synthetic.jsonl --output data/train.json
python scripts/scan_sensitive.py
```

这条 quick start 只演示数据 schema 与转换，不代表完整 Agent 轨迹质量实验。完整 mock rollout 与评估路径见 `docs/01` 和 `docs/02`。

## 仓库中已准备好的数据

- `sft_data/train_chatml_v3.json` / `val_chatml_v3.json`：发布清理后 1297 条训练、142 条验证，供 `training/lora_sft.yaml` 直接使用。
- `LLaMA-Factory/llamafactory/` 下的 train/eval/test JSON：875/100/100 条，配套 fork 内的 ReAct LoRA 配置。
- `slime_joybuy_rl/data/joybuy_slime_tasks.jsonl`：从 875 条训练数据预转换好的 RL task JSONL。

数据清单、其他轨迹和评估样例见 [代码与数据地图](docs/06-code-and-data-map.md)。

完整集中版数据包现已放在 [`sft_data/ready_to_run/`](sft_data/ready_to_run/README.md)，包含 ChatML v3、875/100/100 ReAct SFT 切分、已转换的 875 条 RL tasks、query 样例和可评估轨迹。文件为便于开箱使用的副本；原有路径仍然保留。

从仓库根目录可以通过统一入口执行各模块：

```bash
python scripts/run_module.py --help
python scripts/run_module.py mock-data
python scripts/run_module.py gate
python scripts/run_module.py judge --count 10 --model your-judge-model
python scripts/run_module.py rollout --sample-size 10 --model your-agent-model --overwrite
python scripts/run_module.py export-sft  # rollout 完成后执行
python scripts/run_module.py sft --model-path /path/to/Qwen3-0.6B
python scripts/run_module.py rl --hf-checkpoint /path/to/sft-hf --megatron-ref /path/to/megatron-ref
```

Judge 和 rollout 需要 `LLM_API_URL`、`LLM_API_KEY`；SFT/RL 需要 GPU 训练环境和相应模型 checkpoint。各命令的输入、输出、环境要求见 [现成数据和代码地图](docs/06-code-and-data-map.md) 及数据包说明。

## 直接启动 LoRA SFT

先准备本地基座模型并安装 fork，然后从仓库根目录运行 1297/142 条发布清理版配置：

```bash
cd LLaMA-Factory
python -m pip install -e ".[torch,metrics]"
cd ..
llamafactory-cli train training/lora_sft.yaml
```

该配置读取已有 ChatML v3 数据。另有 875/100/100 ReAct 训练配置和脚本，详见 `docs/06-code-and-data-map.md`。基座模型权重需自行下载；Windows 用户请看 [SFT 指南](docs/03-sft-lora.md)，Slime GRPO 推荐 Linux GPU 环境。

## RL 数据与训练

875 条 RL task 已在 `slime_joybuy_rl/data/joybuy_slime_tasks.jsonl`，不需要先手动转换。训练还需要 SFT checkpoint、Megatron reference checkpoint 和 Slime/Megatron/SGLang/CUDA 环境；准备好这些外部资源后设置 `HF_CHECKPOINT`、`MEGATRON_REF`、`MEGATRON_SAVE` 并用 `RUN_TRAIN=1` 启动 `slime_joybuy_rl/scripts/gpu/run_slime_4090_venv.sh`。完整命令见 [GRPO 指南](docs/04-rl-grpo.md)。

## 环境变量

调用 OpenAI-compatible Judge 或数据生成模型时，通过环境变量提供地址和密钥，不要将凭据写入代码或提交到 Git：

```bash
# Bash
export LLM_API_URL="https://your-approved-endpoint/v1/chat/completions"
export LLM_API_KEY="<your-key>"
```

PowerShell:

```powershell
$env:LLM_API_URL = "https://your-approved-endpoint/v1/chat/completions"
$env:LLM_API_KEY = "<your-key>"
```

## 重要边界

- 仓库里的 SFT 和 mock 样例用于说明本项目的数据形态，不意味着所有源数据都可无条件再分发；发布方应维护数据来源和授权记录。
- `sft_data/training-data/data/` 原始线上采集/回放文件没有随发布版提供。需要复现实验时，使用仓库内的 mock/整理数据，或自行提供获准公开的数据。
- GRPO 需要外部 Slime、Megatron-LM、SGLang、CUDA 和可用 checkpoint；本仓库提供适配层和脚本，不打包这些上游依赖或模型权重。
- 根目录 MIT License 适用于本项目代码；`LLaMA-Factory/` 自带的 Apache-2.0 许可继续适用于该 fork。第三方模型、依赖和数据需分别遵循其许可。

## 提问、反馈与联系作者

- **欢迎提问题**：GitHub 仓库创建后，可以在 Issues 中提问、报告 bug 或建议改进。提问前可先看 `docs/` 和 [贡献指南](CONTRIBUTING.md)。请在公开内容中移除密钥、真实地址、订单号、个人信息和内部日志。
- **项目迭代**：这是第一版，仍有不少可以优化的地方；如果你发现复现步骤不清楚、数据格式有问题，或有更好的评估/SFT/RL方案，欢迎提出。
- **小红书**：[联系作者](https://xhslink.cn/o/5IN1FW83UoN)。公开讨论和问题反馈也欢迎提交到 GitHub Issues。

## 引用与致谢

如果本项目对你的工作有帮助，请参照 [CITATION.md](CITATION.md) 引用本项目版本。使用 LLaMA-Factory、GRPO 或 Qwen 系列时，也请按 [参考文献与致谢](REFERENCES.md) 引用对应上游项目或论文。

## 开源文件

- [贡献指南](CONTRIBUTING.md)：提问、报告问题和提交 PR 的方式。
- [行为准则](CODE_OF_CONDUCT.md)：社区交流约定。
- [安全问题说明](SECURITY.md)：漏洞的私下报告方式。
- [数据集说明](DATASET_CARD.md)：数据内容、用途、限制与发布注意事项。
- [第三方软件与许可说明](THIRD_PARTY_NOTICES.md)：代码、数据、依赖和模型权重的许可边界。
- [版本引用信息](CITATION.cff)：GitHub 可识别的 Citation File Format。
- [版本更新记录](CHANGELOG.md)：首个公开版本包含的内容和后续更新。


