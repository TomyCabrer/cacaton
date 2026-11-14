#!/usr/bin/env bash
# Copi Drill: two seats on two laptops.
#   ./drill.sh            tower here, pilot on the same Wi-Fi (the pilot types to Copi)
#   ./drill.sh --tunnel   also opens an https link through cloudflared: works on any network,
#                         and the pilot's browser will open its microphone for Copi
#   add --reload          while the code is still changing: the server reloads itself when a file in app/
#                         changes, and the pilot's link and key stay the same (a running drill starts over)
# The join link carries a key. Anyone without it gets a 403.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8000}"
rm -f .drill_tunnel
CF=""
AG=""
cleanup() { [ -n "$CF" ] && kill "$CF" 2>/dev/null; [ -n "$AG" ] && kill "$AG" 2>/dev/null; rm -f .drill_tunnel; }
trap cleanup EXIT INT TERM
TUNNEL=0
RELOAD=()
for arg in "$@"; do
  case "$arg" in
    --tunnel) TUNNEL=1 ;;
    --reload) RELOAD=(--reload --reload-dir app) ;;
  esac
done
# One join key for the whole run, so that a reload does not change the pilot's link.
export MEMORIA_KEY="${MEMORIA_KEY:-$(openssl rand -hex 4)}"
if [ "$TUNNEL" = 1 ]; then
  command -v cloudflared >/dev/null || { echo "cloudflared not found. Install it: brew install cloudflared"; exit 1; }
  cloudflared tunnel --url "http://localhost:$PORT" --no-autoupdate > .drill_tunnel.log 2>&1 &
  CF=$!
  URL=""
  for _ in $(seq 1 60); do
    URL=$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' .drill_tunnel.log | head -1 || true)
    [ -n "$URL" ] && break
    sleep 0.5
  done
  if [ -n "$URL" ]; then
    echo "$URL" > .drill_tunnel
    echo "  https tunnel is up. Give it ten seconds before the pilot opens the link: a new address needs that long to resolve."
  else
    echo "The tunnel did not come up. See .drill_tunnel.log"
  fi
fi
# Copi's voice (LiveKit): listens on the pilot-tower radio and talks to the tower on its own line.
if grep -q '^LIVEKIT_URL=.' .env 2>/dev/null && command -v uv >/dev/null; then
  ( cd voice && uv sync -q && uv run agent.py download-files >/dev/null 2>&1 ) || true
  ( cd voice && COPI_SERVER="http://127.0.0.1:$PORT" exec uv run agent.py start ) > .copi_voice.log 2>&1 &
  AG=$!
  echo "  Copi's voice is starting (log: .copi_voice.log)"
else
  echo "  No LIVEKIT_URL in .env (or no uv): no radio, Copi writes but does not speak."
fi
echo
echo "  Control tower (this laptop):  http://localhost:$PORT/drill/control"
echo "  Pilot (the other laptop):     the link is shown at the top of the tower's screen"
echo
MEMORIA_LAN=1 PORT="$PORT" ./run.sh --host 0.0.0.0 ${RELOAD[@]+"${RELOAD[@]}"}
