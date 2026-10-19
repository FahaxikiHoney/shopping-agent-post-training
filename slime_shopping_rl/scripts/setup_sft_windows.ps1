$ErrorActionPreference = "Stop"

conda create -n shopping-sft python=3.11 -y
conda activate shopping-sft

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location (Join-Path $RepoRoot "LLaMA-Factory")
python -m pip install --upgrade pip
pip install -e ".[torch,metrics]"

llamafactory-cli version
