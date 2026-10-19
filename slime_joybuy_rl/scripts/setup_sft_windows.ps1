$ErrorActionPreference = "Stop"

conda create -n joybuy-sft python=3.11 -y
conda activate joybuy-sft

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location (Join-Path $RepoRoot "LLaMA-Factory")
python -m pip install --upgrade pip
pip install -e ".[torch,metrics]"

llamafactory-cli version
