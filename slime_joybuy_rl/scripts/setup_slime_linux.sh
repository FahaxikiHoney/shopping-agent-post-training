#!/usr/bin/env bash
set -euo pipefail

# Prefer the official Slime Docker image. Use this conda setup only when Docker
# is not available on the Linux training machine.

conda create -n joybuy-slime python=3.10 -y
conda activate joybuy-slime

python -m pip install --upgrade pip
conda install pytorch pytorch-cuda=12.1 -c pytorch -c nvidia -y

git clone https://github.com/THUDM/slime.git "${SLIME_HOME:-/opt/slime}"
cd "${SLIME_HOME:-/opt/slime}"
pip install -e .

git clone https://github.com/NVIDIA/Megatron-LM.git "${MEGATRON_HOME:-/opt/Megatron-LM}"
pip install "sglang[all]"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "Add this before running Joybuy RL:"
echo "export PYTHONPATH=${MEGATRON_HOME:-/opt/Megatron-LM}:${REPO_ROOT}/slime_joybuy_rl:${REPO_ROOT}:\$PYTHONPATH"
