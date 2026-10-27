#!/usr/bin/env bash
# 合成（免费，本地 ffmpeg）：对齐 → 拼接 → 烧字幕 → final.mp4
# 用法: 04-assemble.sh <项目目录>
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

[[ $# -ge 1 ]] || { echo "用法: $0 <项目目录>" >&2; exit 2; }

cd "$REPO_ROOT"
exec "$PY" "$PIPELINE" assemble "$1"
