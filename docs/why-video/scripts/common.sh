#!/usr/bin/env bash
# 复现脚本公共部分：定位仓库根目录与 python，供其余脚本 source。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PY="$REPO_ROOT/backend/.venv/bin/python"
PIPELINE="$REPO_ROOT/.claude/skills/why-video/pipeline.py"

if [[ ! -x "$PY" ]]; then
  echo "❌ 找不到 $PY —— 先在 backend/ 下执行: uv venv && uv pip install -r requirements.txt" >&2
  exit 1
fi
