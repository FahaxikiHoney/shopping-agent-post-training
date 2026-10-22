# Ready-to-run data bundle

This directory groups the project's prepared inputs in one place. Files are release-cleaned copies of the canonical datasets elsewhere in the repository. Rows containing unrecoverable Unicode replacement characters were removed, and order/tracking identifiers and retailer deep links were redacted. Existing training configurations point to these cleaned copies.

| Directory | Contents | Intended use |
|---|---|---|
| `chatml/` | ChatML v3 train (1,297), validation (142), dataset registry | Main LLaMA-Factory LoRA run (`training/lora_sft.yaml`) |
| `react_sft/` | ReAct train (875), eval (100), test (100) ShareGPT records | Tool-use LoRA fine-tuning |
| `rl/` | Ready Slime tasks (875), seed tasks, format sample | Slime rollout/GRPO |
| `query/` | 100 anonymized sample queries | Generate new mock-agent trajectories |
| `trajectory/` | 58 cleaned trajectories and 97 scored trajectories | Gate and LLM-as-a-Judge evaluation |

## Start the included ReAct LoRA SFT

The `react_sft/` directory is already registered for the bundled LLaMA-Factory fork. From the repository root, install the fork in your Python 3.11+ CUDA environment and launch training:

```bash
cd LLaMA-Factory
python -m pip install -e ".[torch,metrics]"
cd ..
llamafactory-cli train LLaMA-Factory/llamafactory/lora_qwen3_0.6b.yaml
```

This trains on 875 examples and evaluates on 100. The default base model is `Qwen/Qwen3-0.6B`; edit `model_name_or_path` in the config to use a local model. For automatic venv setup and launch, run `python scripts/run_module.py sft --model-path /absolute/path/to/Qwen3-0.6B` from the repository root (Linux, WSL, or Git Bash).

For the separate 1,297-example ChatML dataset in `chatml/`, run `llamafactory-cli train training/lora_sft.yaml` from the repository root. Its default base model is `Qwen/Qwen2.5-0.5B-Instruct`.

Run all entry points from the repository root using `python scripts/run_module.py --help`. Quick examples:

```bash
python scripts/run_module.py mock-data
python scripts/run_module.py gate
python scripts/run_module.py judge --model your-judge-model --count 10
python scripts/run_module.py rollout --sample-size 10 --model your-agent-model --overwrite
python scripts/run_module.py export-sft  # after rollout has created JSONL + quality report
python scripts/run_module.py sft --model-path /path/to/Qwen3-0.6B
python scripts/run_module.py rl --hf-checkpoint /path/to/sft-hf --megatron-ref /path/to/megatron-ref
```

`rollout` and `judge` need `LLM_API_URL` and `LLM_API_KEY`. SFT needs a compatible local model, CUDA/PyTorch, and the first run installs the fork in a virtual environment. RL additionally requires Linux/WSL, Slime/Megatron/SGLang/CUDA support, an SFT HF checkpoint, and a converted Megatron reference checkpoint. Outputs go to the ignored `sft_data/generated/` directory by default.

Data schemas and pipeline details are described in [the data guide](../../docs/01-data-pipeline.md), [the module map](../../docs/06-code-and-data-map.md), and [the project root README](../../README.md).
