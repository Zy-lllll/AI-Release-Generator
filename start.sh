#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
  ./.venv/bin/python -m pip install -q --upgrade pip
fi
./.venv/bin/python -m pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "已生成 .env，请填入 GITHUB_TOKEN 与 AI_API_KEY 后重新运行。"
  exit 0
fi

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "电脑访问: http://127.0.0.1:8000"
[ -n "$IP" ] && echo "手机访问: http://$IP:8000"
exec ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
