#!/usr/bin/env bash
# 建项目目录（免费）：把样例分镜（2 镜）复制成一个可生成的项目。
# 用法: 02-new-project.sh [项目名]   默认 demo-复现样例
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

NAME="${1:-demo-复现样例}"
PROJECT="$REPO_ROOT/output/why-videos/$(date +%Y%m%d)-$NAME"

mkdir -p "$PROJECT/clips"
cp "$(dirname "${BASH_SOURCE[0]}")/sample-storyboard.json" "$PROJECT/storyboard.json"

echo "✅ 项目已创建: $PROJECT"
echo "   下一步: docs/why-video/scripts/03-generate.sh \"$PROJECT\""
