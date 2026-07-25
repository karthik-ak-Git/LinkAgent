#!/bin/bash
set -e

CHROME_BIN="${CHROME_BIN:-/usr/bin/chromium}"
CHROME_PROFILE="${CHROME_PROFILE:-/app/chrome-profile}"
CDP_PORT="${CDP_PORT:-9222}"

echo "=== LinkAgent MCP Server ==="
echo "Chrome: $CHROME_BIN"
echo "Profile: $CHROME_PROFILE"
echo "CDP Port: $CDP_PORT"

mkdir -p "$CHROME_PROFILE"

rm -f "$CHROME_PROFILE/SingletonLock" 2>/dev/null || true
rm -f "$CHROME_PROFILE/SingletonSocket" 2>/dev/null || true
rm -f "$CHROME_PROFILE/SingletonCookie" 2>/dev/null || true

echo "[1/2] Starting Chromium with CDP on port $CDP_PORT..."
"$CHROME_BIN" \
    --headless=new \
    --remote-debugging-address=0.0.0.0 \
    --remote-debugging-port="$CDP_PORT" \
    --user-data-dir="$CHROME_PROFILE" \
    --no-sandbox \
    --disable-gpu \
    --disable-dev-shm-usage \
    --disable-background-networking \
    --no-first-run \
    --disable-features=TranslateUI \
    --lang=en-US \
    &
CHROME_PID=$!

echo "Waiting for CDP on port $CDP_PORT..."
CDP_READY=0
for i in $(seq 1 60); do
    if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$CDP_PORT/json/version', timeout=2)" 2>/dev/null; then
        echo "CDP ready!"
        CDP_READY=1
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "WARNING: CDP not ready after 60s, MCP server will start anyway"
        kill "$CHROME_PID" 2>/dev/null || true
        break
    fi
    sleep 1
done

echo "[2/2] Starting MCP server..."
cd /app
exec python -m linkagent_mcp
