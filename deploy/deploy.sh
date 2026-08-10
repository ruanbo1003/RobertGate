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
sleep 1
pip install -r requirements.txt --no-cache-dir

LOG_DIR="$BACKEND_DIR/logs"
mkdir -p "$LOG_DIR"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  >> "$LOG_DIR/uvicorn.log" 2>&1 &

echo "backend started, pid=$!, log=$LOG_DIR/uvicorn.log"

# 简单健康探测：等待端口可用（最多 15 秒）
for i in $(seq 1 15); do
  if curl -sf http://127.0.0.1:8000/api/health > /dev/null 2>&1 \
     || curl -sf http://127.0.0.1:8000/ > /dev/null 2>&1; then
    echo "backend is up"
    exit 0
  fi
  sleep 1
done
echo "warning: backend not responding yet, check $LOG_DIR/uvicorn.log"
