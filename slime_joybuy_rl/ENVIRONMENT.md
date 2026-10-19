# Joybuy SFT and Slime RL Environments

Recommendation: use the venv scripts first. Keep SFT and Slime RL in two venvs
by default; use the single-venv script only on a Linux GPU machine when you
want to test whether everything can coexist.

One environment can work only on a Linux GPU machine if Slime, SGLang,
Megatron-LM, LLaMA-Factory, and CUDA wheels all agree on the same Python and
PyTorch versions. In practice this is fragile. For this project, keep SFT and
RL separate:

- `.venv-joybuy-sft`: Windows Git Bash or Linux, LLaMA-Factory, Python 3.11.
- `.venv-joybuy-slime`: Linux, Slime + Megatron-LM + SGLang.
- `.venv-joybuy-posttrain`: optional single Linux venv.

## Why Two Environments

LLaMA-Factory in this repo declares `requires-python >=3.11`.

Slime is an RL framework around Megatron training and SGLang rollout. The
official docs strongly recommend Docker because Slime may carry temporary
patches for SGLang/Megatron. The conda route needs a separate Megatron checkout
on `PYTHONPATH` and a matching SGLang install.

Windows is fine for your current SFT flow. Slime RL should be done on Linux or
inside the Slime Docker image.

## Environment A: SFT

Use this for LLaMA-Factory SFT and LoRA merge. The convenient path is:

```bash
bash slime_joybuy_rl/scripts/gpu/run_sft_4090_venv.sh
```

The script creates `.venv-joybuy-sft` and writes an install marker under
`.venv-joybuy-sft/.install_markers/`. Set `FORCE_INSTALL=1` to reinstall deps.
This repo's LLaMA-Factory requires Python 3.11+, so use `PYTHON_BIN=python3.11`
or newer when the system default is Python 3.10.
The checked-in SFT YAML contains Windows paths. The venv script generates a
Linux YAML under `.cache/generated/` and replaces:

- `model_name_or_path` with `MODEL_PATH`
- `dataset_dir` with `LLaMA-Factory/data`
- `output_dir` with `LLaMA-Factory/output/joybuy_qwen3_0.6b_lora`

Example:

```bash
MODEL_PATH=/root/autodl-tmp/Qwen3-0.6B \
bash slime_joybuy_rl/scripts/gpu/run_sft_4090_venv.sh
```

If the root disk is small, put the venv and pip cache on a data disk:

```bash
MODEL_PATH=/root/autodl-tmp/Qwen3-0.6B \
VENV_DIR=/root/autodl-tmp/.venv-joybuy-sft \
PIP_CACHE_DIR=/root/autodl-tmp/pip-cache \
FORCE_INSTALL=1 \
bash slime_joybuy_rl/scripts/gpu/run_sft_4090_venv.sh
```

If disk is very tight, add `PIP_NO_CACHE_DIR=1` to avoid keeping wheel cache.

Manual equivalent:

```powershell
python -m venv $env:PROJECT_ROOT/.venv-joybuy-sft
$env:PROJECT_ROOT/.venv-joybuy-sft\Scripts\activate

cd $env:PROJECT_ROOT/LLaMA-Factory
python -m pip install --upgrade pip setuptools wheel
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install --upgrade pip
pip install -e ".[torch,metrics]"

llamafactory-cli version
```

Then run your existing SFT script:

```bash
cd $PROJECT_ROOT/LLaMA-Factory/llamafactory
bash train.sh
```

Expected SFT output:

```text
$PROJECT_ROOT/LLaMA-Factory/output/joybuy_qwen3_0.6b_lora
$PROJECT_ROOT/LLaMA-Factory/output/joybuy_qwen3_0.6b_merged
```

After SFT, run a separate inference test:

```bash
MODEL_PATH=/root/autodl-tmp/Qwen3-0.6B \
ADAPTER_PATH=/workspace/project/LLaMA-Factory/output/joybuy_qwen3_0.6b_lora \
LIMIT=10 \
bash slime_joybuy_rl/scripts/gpu/run_sft_test_4090_venv.sh
```

For a quick first check, run only one sample and shorter decoding:

```bash
MODEL_PATH=/root/autodl-tmp/Qwen3-0.6B \
ADAPTER_PATH=/workspace/project/LLaMA-Factory/output/joybuy_qwen3_0.6b_lora \
LIMIT=1 \
MAX_NEW_TOKENS=256 \
bash slime_joybuy_rl/scripts/gpu/run_sft_test_4090_venv.sh
```

If the model skips tools and directly emits product cards, enable strict
tool-first testing:

```bash
MODEL_PATH=/root/autodl-tmp/Qwen3-0.6B \
ADAPTER_PATH=/workspace/project/LLaMA-Factory/output/joybuy_qwen3_0.6b_lora \
LIMIT=1 \
MAX_NEW_TOKENS=256 \
STRICT_TOOL_FIRST=1 \
bash slime_joybuy_rl/scripts/gpu/run_sft_test_4090_venv.sh
```

If it still skips tools, run tool-call warmup SFT:

```bash
MODEL_PATH=/root/autodl-tmp/Qwen3-0.6B \
EPOCHS=8 \
LR=1.0e-4 \
bash slime_joybuy_rl/scripts/gpu/run_toolcall_warmup_4090_venv.sh
```

Then test:

```bash
MODEL_PATH=/root/autodl-tmp/Qwen3-0.6B \
ADAPTER_PATH=/workspace/project/LLaMA-Factory/output/joybuy_qwen3_0.6b_toolcall_warmup \
LIMIT=1 \
MAX_NEW_TOKENS=256 \
STRICT_TOOL_FIRST=1 \
bash slime_joybuy_rl/scripts/gpu/run_sft_test_4090_venv.sh
```

Outputs:

```text
slime_joybuy_rl/output/sft_test_outputs.jsonl
slime_joybuy_rl/output/sft_test_outputs.md
```

## Environment B: Slime RL

Preferred route:

```bash
docker pull slimerl/slime:latest
docker run --rm --gpus all --ipc=host --shm-size=16g \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  -v $PROJECT_ROOT:/workspace/project \
  -v /path/to/models:/models \
  -it slimerl/slime:latest /bin/bash
```

Venv route on a Linux 4090 machine:

```bash
bash slime_joybuy_rl/scripts/gpu/run_slime_4090_venv.sh
```

This creates `.venv-joybuy-slime`, clones Slime and Megatron-LM into
`third_party/`, installs SGLang, converts a small Joybuy task file if needed,
and runs local adapter tests. It does not launch training unless `RUN_TRAIN=1`.
It also uses an install marker; set `FORCE_INSTALL=1` to reinstall deps and
`UPDATE_THIRD_PARTY=1` to pull existing Slime/Megatron checkouts.

Inside the container:

```bash
cd /root/slime
git pull
pip install -e . --no-deps

cd /workspace/project
export PYTHONPATH="$PWD/slime_joybuy_rl:$PWD:$PYTHONPATH"

python slime_joybuy_rl/joybuy_slime/task_data.py \
  --input LLaMA-Factory/llamafactory/train_joybuy_react.json \
  --output slime_joybuy_rl/data/joybuy_slime_tasks.jsonl \
  --limit 200
```

Then edit and run:

```bash
HF_CHECKPOINT=/models/joybuy_qwen3_0.6b_merged \
MEGATRON_REF=/models/megatron/joybuy_qwen3_0.6b_ref \
MEGATRON_SAVE=/models/megatron/joybuy_qwen3_0.6b_grpo \
bash slime_joybuy_rl/configs/joybuy_qwen3_0_6b_grpo.example.sh
```

## Optional Single Linux Environment

Try this only if you want one Linux venv for both SFT and RL:

```bash
bash slime_joybuy_rl/scripts/gpu/run_all_4090_venv.sh
```

If dependency resolution downgrades `transformers`, `trl`, `torch`, or
`pydantic` in a way that breaks either side, stop and split the environments.

## Minimum Validation

Run these before Slime RL:

```bash
python -m unittest tests.test_slime_joybuy_adapter tests.test_react_environment -v
python slime_joybuy_rl/joybuy_slime/task_data.py \
  --input LLaMA-Factory/llamafactory/train_joybuy_react.json \
  --output slime_joybuy_rl/data/joybuy_slime_tasks.sample.jsonl \
  --limit 5
```

