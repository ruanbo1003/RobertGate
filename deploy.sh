#!/bin/bash
set -e

# ============================================
# RobertGate 前端构建 & Nginx 部署脚本
# ============================================

# 配置项（按需修改）
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

sudo cp -r dist/* "$NGINX_WEB_ROOT/"

echo "==> 测试 Nginx 配置"
sudo nginx -t

echo "==> 重载 Nginx"
sudo nginx -s reload

echo "==> 部署完成！"
echo "    前端：http://your-server-ip"
echo "    后端：http://your-server-ip/api/v1/health"
