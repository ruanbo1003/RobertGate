#!/bin/bash
set -e

PROJECT_DIR="/home/ubuntu/RobertGate"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_DIR="$PROJECT_DIR/backend"
NGINX_WEB_ROOT="/var/www/ruanbo"
NGINX_CONF="/etc/nginx/conf.d/ruanbo.conf"

echo "==> frontend"
cd "$FRONTEND_DIR"
npm install --frozen-lockfile 2>/dev/null || npm install
npm run build
sudo cp -r dist/* /var/www/ruanbo/

echo "==> backend"
cd "$BACKEND_DIR"
source .venv/bin/activate
# stop existing uvicorn process if any
pkill -f "uvicorn app.main:app" || true
pip install -r requirements.txt --no-cache-dir
uvicorn app.main:app --host 0.0.0.0 --port 8000
