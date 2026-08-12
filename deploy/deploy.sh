#!/bin/bash
set -e

PROJECT_DIR="/home/ubuntu/RobertGate"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_DIR="$PROJECT_DIR/backend"
NGINX_WEB_ROOT="/var/www/ruanbo"
NGINX_CONF="/etc/nginx/conf.d/ruanbo.conf"
SERVICE_NAME="robertgate-api"

echo "==> frontend"
cd "$FRONTEND_DIR"
npm install --frozen-lockfile 2>/dev/null || npm install
npm run build
sudo cp -r dist/* "$NGINX_WEB_ROOT/"

echo "==> backend"
cd "$BACKEND_DIR"

# Fix accidental duplicated key prefix in .env (e.g. `DATABASE_URL=DATABASE_URL=...`)
if [ -f .env ] && grep -qE '^([A-Z_][A-Z0-9_]*)=\1=' .env; then
  echo "   fixing duplicated key prefix in .env"
  sed -i -E 's/^([A-Z_][A-Z0-9_]*)=\1=/\1=/' .env
fi

source .venv/bin/activate
pip install -r requirements.txt --no-cache-dir

echo "==> restart $SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl --no-pager status "$SERVICE_NAME" | head -n 10

echo "done. logs: journalctl -u $SERVICE_NAME -f"
