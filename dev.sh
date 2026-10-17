#!/usr/bin/env bash
# 一键启动开发环境：后端 (FastAPI:8000) + 前端 (Vite:5173)
# 按 Ctrl+C（或关闭终端）会同时停止前后端。
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT/backend/.uvicorn.pid"
BACKEND_PID=""

# 停止指定 PID 的后端进程：先 TERM 优雅退出，超时再 KILL 兜底
stop_backend() {
  local pid="$1"
  [ -n "$pid" ] || return 0
  kill -0 "$pid" 2>/dev/null || return 0
  kill -TERM "$pid" 2>/dev/null || true
  i=0
  while [ "$i" -lt 15 ]; do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 0.2
    i=$((i + 1))
  done
  kill -KILL "$pid" 2>/dev/null || true
}

cleanup() {
  trap - INT TERM HUP EXIT
  if [ -n "$BACKEND_PID" ]; then
    echo ""
    echo "==> 停止后端 (PID $BACKEND_PID)"
    stop_backend "$BACKEND_PID"
  fi
  rm -f "$PID_FILE"
}
trap cleanup INT TERM HUP EXIT

# 清理上一次运行可能遗留的后端进程（旧版本用 nohup 启动，可能没被回收）
if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "==> 清理上次遗留的后端进程 (PID $OLD_PID)"
    stop_backend "$OLD_PID"
  fi
  rm -f "$PID_FILE"
fi

echo "==> 启动后端"
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  uv venv .venv
  uv pip install --python .venv/bin/python -r requirements.txt
fi
# 作为当前脚本的子进程启动（不再用 nohup 脱离），确保 Ctrl+C 能回收
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$ROOT/backend/uvicorn.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_FILE"
echo "    后端已启动: http://localhost:8000  (API 文档: /docs, PID $BACKEND_PID)"

# 后端若因端口占用等原因立刻退出，提前报错，避免误以为已启动
sleep 1
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "    后端启动失败，请查看 backend/uvicorn.log"
  exit 1
fi

echo "==> 启动前端"
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install --no-audit --no-fund
fi
echo "    前端即将启动: http://localhost:5173  (按 Ctrl+C 停止全部服务)"
npm run dev
