# 05 · 指标、实验复现与开源发布

## 1. 评估指标

至少分别记录以下结果，避免只用一个平均分掩盖失败类型：

- 规则 Gate 通过率、各失败原因计数；
- D1–D5 各维度通过率/得分和总体分布；
- 工具调用成功率、无效动作率、平均调用步数；
- 有效商品引用率、无召回幻觉率、预算/硬约束违反率；
- RL reward 均值与分布、完成率、截断/超时率、每组采样有效率；
- 按场景、语言/站点、难度切片的指标。

评估产物应保留输入版本和样本 ID（公开时为匿名 ID），但不要把个人标识写入 dashboard label。Judge 结果与规则 Gate 结果要分开存档。

## 2. 训练与 rollout 日志

LoRA 训练输出默认写到 YAML 中的 `output_dir`。Slime 指标由 `slime_shopping_rl/shopping_slime/metrics_logger.py` 写入 JSONL；仪表板入口是 `metrics_dashboard.py`，启动脚本为：

```bash
bash slime_shopping_rl/scripts/gpu/run_metrics_dashboard_venv.sh
```

默认端口为本机 dashboard 端口，具体以启动日志/脚本变量为准。只在受控网络中暴露 dashboard；日志可能包含 prompt、模型输出或任务内容，应按训练数据同等级别管理。

## 3. 可复现实验记录

每个实验至少保存：

1. 代码 commit 和 LLaMA-Factory/Slime/Megatron 上游版本。
2. 基座模型标识与 revision、LoRA adapter 或 checkpoint 标识。
3. 训练/验证数据清单、过滤规则、样本数量和 SHA-256。
4. YAML/启动参数、随机种子、硬件、CUDA/PyTorch 和 Python 版本。
5. rollout/Judge 模型与提示词版本、温度、并发、重试和评估日期。
6. Gate、五维 Judge、训练曲线、RL reward 和失败样例摘要。

数据路径、API 密钥和机器用户名不要写进可公开日志。对样本内容做访问控制，输出脱敏的实验摘要。

## 4. 发布前扫描

从仓库根目录运行：

```bash
python scripts/scan_sensitive.py
```

这是启发式检查，不能取代人工审查。默认扫描项目自有代码、数据和文档，包含本项目的 LLaMA-Factory 配置/数据，但排除完整第三方 fork；传入路径可覆盖默认范围。扫描检查密钥、邮箱、手机号、订单/物流编号、零售深链和本机路径。逐项人工检查新增数据与日志中的姓名、家庭/收货地址、内部域名、私有仓库链接、未公开商品字段、用户 prompt 和模型输出。还需检查 Git 历史：即使当前文件已脱敏，历史提交仍可能保留原凭据或原始文件；首次公开应检查提交历史或使用干净的发布分支。上游 fork 应按其自身许可、来源和更新记录单独检查。

## 5. 许可与数据治理

- 项目根 `LICENSE` 是 MIT；`LLaMA-Factory/LICENSE` 是 Apache-2.0，fork 的来源与修改情况应在正式发布前核对。
- 每个数据文件应有来源、许可/授权、处理方式和更新时间说明；没有明确再分发权限的数据不应纳入公开版本。
- 基座模型、Judge 模型、Slime、Megatron-LM、SGLang 及 Python 依赖各自有许可和使用条款。项目 README 不能替代这些条款。
- 对线上轨迹，即便删除显式个人字段，独特 query、时间戳、商品/订单组合也可能重新识别用户；需要风险评估和授权，而不只是正则脱敏。

## 6. 发布检查清单

- [ ] README 的模块、路径、数据入口和命令与实际文件一致。
- [ ] 训练、验证和评估文件都能解析，训练配置引用的文件确实存在。
- [ ] 样本 ID 已匿名化；确认没有地址、联系信息、订单号或内部地址。
- [ ] 未提交 `.env`、checkpoint、API key、个人日志和模型权重。
- [ ] 清理 Git 历史中的敏感文件/凭据，并对发布 commit 再跑扫描。
- [ ] 写明每个数据集和第三方代码的许可、来源及必要 attribution。
- [ ] 根目录包含 README、数据卡、贡献/安全说明、第三方声明和 Citation File Format；维护者公开署名/主页已填写。
- [ ] SFT 和 GRPO 指南区分本仓库提供内容与外部依赖。

## 7. 故障排查入口

- 数据列/ShareGPT 格式错误：检查 `training/dataset_info.json`、输入 JSON schema 和对应转换器。
- Gate 通过但 Judge 低分：打开轨迹详情，核对用户限制、工具 observation 和商卡引用，不要只看总分。
- 模型不调用工具：检查训练数据中 assistant tool-call 轮是否保留；考虑先跑 tool-call warmup。
- RL reward 一直为零：逐步检查 action parser、环境重置 metadata、tool observation 和终止状态；先跑 seed task，不要直接扩训练。
- CUDA/依赖冲突：对照 LLaMA-Factory 与 Slime 各自环境文档，优先拆分 SFT/RL 环境。
