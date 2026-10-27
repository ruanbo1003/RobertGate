#!/usr/bin/env bash
# 第二幕生成（花钱）：逐分镜 TTS + 视频生成，断点续跑（中断后重跑同一命令即可）。
# 用法: 03-generate.sh <项目目录> [--redo 1,2]
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

[[ $# -ge 1 ]] || { echo "用法: $0 <项目目录> [--redo 1,2]" >&2; exit 2; }
PROJECT="$1"; shift

cd "$REPO_ROOT"
# 不带 --yes：脚本内会展示成本预估并要求输入 y 确认
exec "$PY" "$PIPELINE" generate "$PROJECT" "$@"
