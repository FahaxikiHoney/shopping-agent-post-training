# SFT 数据、轨迹和评估产物

本目录保留项目已整理的多轮购物 Agent 轨迹、SFT 文件、Mock rollout、Gate/Judge 结果、转换和生成脚本。不要把目录中所有 JSONL 当成同一种 schema；先按 [数据与代码地图](../docs/06-code-and-data-map.md) 选择对应文件。

## 直接可用的 SFT 数据

- `train_chatml_v3.json`：1297 条 ShareGPT `messages` 训练数据（发布清理版）。
- `val_chatml_v3.json`：142 条验证数据（发布清理版）。
- `ready_to_run/chatml/dataset_info.json`：当前主 ChatML SFT 配置从 `dataset_dir` 读取的注册文件；根目录 `dataset_info.json` 为兼容副本。
- `train_llamafactory.json`：另一个转换版本；使用前检查对应 registry 与列格式。

另一套 875/100/100 ReAct 数据在 `../LLaMA-Factory/llamafactory/`，配套项目配置和注册。875 条训练 split 也转换成 `../slime_joybuy_rl/data/joybuy_slime_tasks.jsonl`。

## 常用脚本

- `gen_react_data.py`：按项目场景生成完整 ReAct 轨迹，输出 `trajectories_react.jsonl`，需配置 LLM API。
- `llm_gen_oxygen.py --mock`：使用本地 Mock 场景生成轨迹，不需外部 API。
- `convert_to_chatml_v3.py`：将历史轨迹 schema 固定路径转成 train/validation ChatML。
- `convert_trajectory.py`、`convert_to_chatml.py`、`convert_to_chatml_v2.py`：不同历史格式的转换工具，参数和输入格式各异。
- `evaluate.py` / `evaluate_v2.py`：兼容入口；主要五维评估器现在位于 `../llm_evaluation/evaluate.py`。

完整命令、数据字段、质量 Gate 和评估步骤见 `../docs/01-data-pipeline.md`、`../docs/02-quality-and-llm-evaluation.md` 和 `../docs/06-code-and-data-map.md`。

## 数据边界

原始线上轨迹采集/回放总目录没有随发布版提供。其余整理数据也应在公开分发前确认来源和再分发许可。LLM 生成器从 `LLM_API_URL`、`LLM_API_KEY` 环境变量读取服务地址与凭据。
