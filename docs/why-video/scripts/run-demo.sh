#!/usr/bin/env bash
# 一键全流程复现（2 镜小样本，视频生成花费约 ¥2，生成环节有交互确认）。
# 验证 → 建项目 → 生成 → 合成 → 打印成片路径。
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT="$REPO_ROOT/output/why-videos/$(date +%Y%m%d)-demo-复现样例"

"$SCRIPTS/01-verify.sh"
"$SCRIPTS/02-new-project.sh" "demo-复现样例"
"$SCRIPTS/03-generate.sh" "$PROJECT"
"$SCRIPTS/04-assemble.sh" "$PROJECT"

echo ""
echo "🎬 复现完成，成片: $PROJECT/final.mp4"
