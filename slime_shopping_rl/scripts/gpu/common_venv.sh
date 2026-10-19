#!/usr/bin/env bash

log() {
  printf "\033[0;32m[INFO]\033[0m %s\n" "$*"
}

warn() {
  printf "\033[1;33m[WARN]\033[0m %s\n" "$*"
}

die() {
  printf "\033[0;31m[ERR]\033[0m %s\n" "$*" >&2
  exit 1
}

repo_root_from_gpu_script() {
  cd "$(dirname "${BASH_SOURCE[1]}")/../../.." && pwd
}

create_and_activate_venv() {
  local venv_dir="$1"
  local python_bin="$2"
  if [[ ! -d "${venv_dir}" ]]; then
    log "Creating venv: ${venv_dir}"
    "${python_bin}" -m venv "${venv_dir}"
  fi

  if [[ -f "${venv_dir}/Scripts/activate" ]]; then
    # Windows Git Bash
    # shellcheck disable=SC1090
    source "${venv_dir}/Scripts/activate"
  elif [[ -f "${venv_dir}/bin/activate" ]]; then
    # Linux
    # shellcheck disable=SC1090
    source "${venv_dir}/bin/activate"
  else
    die "Cannot find venv activation script under ${venv_dir}"
  fi

  log "Python: $(python --version 2>&1)"
  log "Python path: $(command -v python)"
}

install_once() {
  local marker="$1"
  shift
  if [[ "${FORCE_INSTALL:-0}" == "1" || ! -f "${marker}" ]]; then
    "$@"
    mkdir -p "$(dirname "${marker}")"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "${marker}"
  else
    log "Dependencies already installed: ${marker}"
  fi
}

install_cuda_torch() {
  local index_url="$1"
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install torch torchvision torchaudio --index-url "${index_url}"
}

show_gpu() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader || true
  else
    warn "nvidia-smi not found"
  fi
}

require_python_at_least() {
  local major="$1"
  local minor="$2"
  python - "$major" "$minor" <<'PY'
import sys

required = (int(sys.argv[1]), int(sys.argv[2]))
current = sys.version_info[:2]
if current < required:
    raise SystemExit(
        f"Python {required[0]}.{required[1]}+ is required, "
        f"but current Python is {sys.version.split()[0]}"
    )
PY
}

clone_or_update() {
  local repo="$1"
  local dir="$2"
  if [[ ! -d "${dir}/.git" ]]; then
    log "Cloning ${repo} -> ${dir}"
    git clone "${repo}" "${dir}"
  elif [[ "${UPDATE_THIRD_PARTY:-0}" == "1" ]]; then
    log "Updating ${dir}"
    git -C "${dir}" pull --ff-only
  else
    log "Using existing checkout: ${dir}"
  fi
}

load_optional_env_file() {
  local env_file="$1"
  if [[ -f "${env_file}" ]]; then
    log "Loading env file: ${env_file}"
    set -a
    # shellcheck disable=SC1090
    source "${env_file}"
    set +a
  fi
}
