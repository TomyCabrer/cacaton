#!/usr/bin/env bash
# Start Copi. Usage: ./run.sh            (http://localhost:8000)
#                       PORT=8765 ./run.sh --reload --reload-dir app
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/uvicorn ]; then
  if command -v uv >/dev/null; then
    uv venv -q .venv && uv pip install -q --python .venv/bin/python -r requirements.txt
  else
    python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
  fi
fi
# SSE streams never close on their own: cap graceful shutdown so reloads and Ctrl+C don't hang.
exec .venv/bin/uvicorn app.main:app --port "${PORT:-8000}" --timeout-graceful-shutdown 1 "$@"
