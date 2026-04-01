#!/bin/bash
set -e

PROJECT_DIR="/root/RobertGate"
FRONTEND_DIR="$PROJECT_DIR/frontend"
NGINX_WEB_ROOT="/var/www/ruanbo"
NGINX_CONF="/etc/nginx/conf.d/ruanbo.conf"

echo "==> 进入前端目录"
cd "$FRONTEND_DIR"

echo "==> 安装依赖"
npm install --frozen-lockfile 2>/dev/null || npm install

echo "==> 构建前端"
npm run build

sudo cp -r dist/* /var/www/ruanbo/
