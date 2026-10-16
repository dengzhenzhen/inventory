#!/usr/bin/env bash
# 一键启动开发环境：后端 (FastAPI:8000) + 前端 (Vite:5173)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> 启动后端"
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  uv venv .venv
  uv pip install --python .venv/bin/python -r requirements.txt
fi
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$ROOT/backend/uvicorn.log" 2>&1 &
echo "    后端已启动: http://localhost:8000  (API 文档: /docs)"

echo "==> 启动前端"
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install --no-audit --no-fund
fi
echo "    前端即将启动: http://localhost:5173"
npm run dev
