# Shopping Agent Post-Training

[简体中文](README.md)

An end-to-end research codebase for shopping-agent post-training: trajectory construction, deterministic quality gates, LLM-as-a-Judge evaluation, LLaMA-Factory LoRA SFT, and Slime GRPO examples. The included product tools use local mock fixtures and do not access a live retailer service.

This is the first public release candidate (`v0.1.0`). The project will continue to improve. Questions, bug reports, documentation fixes, and ideas are welcome through GitHub Issues after the repository is published.

## Workflow

```text
task/query data → agent trajectories → quality gate and LLM judge
→ filtered ShareGPT/ChatML → LoRA SFT → optional Slime GRPO
```

The complete prepared dataset bundle is in [`sft_data/ready_to_run/`](sft_data/ready_to_run/README.md): 1,297/142 cleaned ChatML train/validation records, 875/100/100 ReAct train/eval/test records, 875 converted RL tasks, a 100-query sample, and trajectory evaluation examples. Rows containing unrecoverable text-encoding replacement characters were excluded from release datasets.

## Quick start

Run from the repository root. Python 3.10+ is recommended for data/evaluation utilities.

```bash
python scripts/run_module.py --help
python scripts/run_module.py mock-data
python scripts/run_module.py gate
```

To generate model-based trajectories or run the LLM judge, set `LLM_API_URL` and `LLM_API_KEY` in your environment, then run:

```bash
python scripts/run_module.py rollout --sample-size 10 --model YOUR_AGENT_MODEL --overwrite
python scripts/run_module.py judge --count 10 --model YOUR_JUDGE_MODEL
```

SFT requires a compatible model checkpoint and CUDA/PyTorch environment. RL additionally requires Linux/WSL and compatible Slime, Megatron-LM, SGLang, CUDA, and converted checkpoints. See the [module/data map](docs/06-code-and-data-map.md) and [step-by-step docs](docs/00-project-overview.md). Most detailed guides are currently in Chinese.

## Repository map

- `joybuy_agent/`: ReAct agents, tools, local mock catalog, and quality gate.
- `sft_data/`: prepared datasets, trajectory utilities, and local evaluation examples.
- `scripts/`: trajectory generation, quality checks, audits, exports, and unified module launcher.
- `llm_evaluation/`: rule gates and five-dimension LLM judge.
- `LLaMA-Factory/`: included fork and project fine-tuning configuration.
- `slime_joybuy_rl/`: Slime adapter, reward logic, task conversion, and GPU launch examples.
- `docs/`: workflow, data schemas, evaluation, SFT, RL, and release instructions.

## License and data

The root [MIT License](LICENSE) applies to original project code. The included LLaMA-Factory fork has its own [Apache-2.0 license](LLaMA-Factory/LICENSE). Dataset files, model checkpoints, third-party code, generated outputs, product names, and marks may be governed by separate terms; see [`DATASET_CARD.md`](DATASET_CARD.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). No model weights are bundled.

## Citation and contributions

See [`CITATION.md`](CITATION.md) and [`REFERENCES.md`](REFERENCES.md) to cite this release and upstream methods. Contributions are welcome; read [`CONTRIBUTING.md`](CONTRIBUTING.md) first. For a first-time GitHub release checklist, see [`docs/07-github-first-release.md`](docs/07-github-first-release.md).

See [`CHANGELOG.md`](CHANGELOG.md) for the first release contents and future updates.

## Author contact

Contact the author through [Xiaohongshu](https://xhslink.cn/o/5IN1FW83UoN). Questions and bug reports are also welcome through GitHub Issues.


