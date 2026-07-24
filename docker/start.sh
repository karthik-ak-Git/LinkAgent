#!/bin/bash
set -e

CHROME_BIN="${CHROME_BIN:-/usr/bin/chromium}"
CHROME_PROFILE="${CHROME_PROFILE:-/app/chrome-profile}"
CDP_PORT="${CDP_PORT:-9222}"

echo "=== LinkAgent MCP Server ==="
echo "Chrome: $CHROME_BIN"
echo "Profile: $CHROME_PROFILE"
echo "CDP Port: $CDP_PORT"

# Create profile directory if it doesn't exist
mkdir -p "$CHROME_PROFILE"

# Remove stale profile locks from previous runs
rm -f "$CHROME_PROFILE/SingletonLock" 2>/dev/null || true
rm -f "$CHROME_PROFILE/SingletonSocket" 2>/dev/null || true
rm -f "$CHROME_PROFILE/SingletonCookie" 2>/dev/null || true

# Launch Chromium with CDP enabled
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

# Wait for CDP to become available (no curl in slim image, use python)
echo "[2/2] Waiting for CDP on port $CDP_PORT..."
for i in $(seq 1 30); do
    if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$CDP_PORT/json/version', timeout=2)" 2>/dev/null; then
        echo "CDP ready!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: CDP did not start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Start the MCP server (stdio transport)
echo "Starting MCP server..."
cd /app
exec python -m linkagent_mcp
