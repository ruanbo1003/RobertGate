#!/usr/bin/env bash
# 第 0 步：能力验证（免费）。检查 API key、ffmpeg-full、可用模型清单。
# 加 --full 会额外做一句试音 + 一段测试视频（花钱）。
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

cd "$REPO_ROOT"
exec "$PY" "$PIPELINE" verify "$@"
