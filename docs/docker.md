# Docker Deployment

Run LinkAgent MCP in a containerized Chromium environment.

## Quick Start

```bash
# Build and start (full stack: Chromium + MCP server)
docker compose up -d linkagent

# Or just Chromium (expose CDP for external MCP server)
docker compose up -d chromium

# Check if it's running
docker compose ps

# View logs
docker compose logs -f

# Stop
docker compose down
```

## How It Works

The Docker container runs:

1. **Headless Chromium** with CDP on port 9222
2. **LinkAgent MCP server** connecting to that Chromium via CDP

The MCP server communicates over stdio (standard MCP transport). The CDP port is also exposed for external tools.

## Persistent Sessions

Chrome profile data is stored in a Docker volume (`chrome-profile`). This means:

- Login sessions persist across container restarts
- You only need to log in once
- To reset, remove the volume: `docker volume rm linkagent_chrome-profile`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CDP_PORT` | `9222` | Chrome DevTools Protocol port |
| `LINKAGENT_CDP_HOST` | `127.0.0.1` | CDP host address |
| `LINKAGENT_LOG_LEVEL` | `INFO` | Logging level |
| `LINKAGENT_LOG_FILE` | _(none)_ | Log to file |
| `LINKAGENT_SERVER_NAME` | `linkagent` | MCP server name |

Set in `docker-compose.yml` under `environment:`.

## MCP Client Configuration

### Claude Desktop (stdio)

```json
{
  "mcpServers": {
    "linkagent": {
      "command": "docker",
      "args": ["compose", "run", "--rm", "linkagent"],
      "cwd": "D:\\LinkAgent"
    }
  }
}
```

### Claude Desktop (remote CDP)

If you want the MCP server outside Docker but Chromium inside:

```json
{
  "mcpServers": {
    "linkagent": {
      "command": "python",
      "args": ["-m", "linkagent_mcp"],
      "env": {
        "LINKAGENT_CDP_HOST": "127.0.0.1",
        "LINKAGENT_CDP_PORT": "9222"
      }
    }
  }
}
```

Then run only the Chromium part in Docker:

```bash
docker run -d -p 9222:9222 --name chromium \
  -v chrome-profile:/app/chrome-profile \
  chromium/chromium --remote-debugging-address=0.0.0.0 --remote-debugging-port=9222 \
  --no-sandbox --headless=new --user-data-dir=/app/chrome-profile
```

## Networking

- **MCP transport**: stdio (container stdin/stdout)
- **CDP port**: Exposed on `localhost:9223` (configurable in docker-compose.yml)
- **Browser automation**: Headless Chromium inside the container

## Windows Docker Desktop

Docker Desktop on Windows uses a WSL2 VM, which can cause port forwarding issues. If CDP is not accessible from the host:

**Recommended approach:** Use the `linkagent` service (stdio transport):

```json
{
  "mcpServers": {
    "linkagent": {
      "command": "docker",
      "args": ["compose", "run", "--rm", "linkagent"],
      "cwd": "D:\\LinkAgent"
    }
  }
}
```

**Alternative:** Run Chromium in Docker, MCP server on host:

```bash
# Start Chromium in Docker
docker compose up -d chromium

# The CDP port may not be accessible via localhost on Windows Docker Desktop
# If so, find the container IP:
docker inspect linkagent-chromium | grep IPAddress

# Then use that IP in your MCP config:
# LINKAGENT_CDP_HOST=172.18.0.2
```

## Building

```bash
# Build the image
docker compose build

# Rebuild after changes
docker compose build --no-cache
```

## Troubleshooting

### CDP not starting

```bash
docker compose logs linkagent | grep -i "cdp\|chrome\|error"
```

Common causes:
- Chromium binary not found (check `CHROME_BIN` env)
- Port 9222 already in use on host
- Missing system dependencies (handled in Dockerfile)

### Login sessions lost

Ensure the `chrome-profile` volume is mounted:

```bash
docker volume inspect linkagent_chrome-profile
```

### Container exits immediately

```bash
docker compose run --rm linkagent  # Run in foreground to see errors
```

## Advanced: Custom Chromium Flags

Edit `docker/start.sh` to add Chromium flags:

```bash
# Example: enable notifications, set window size
"$CHROME_BIN" \
    --headless=new \
    --remote-debugging-address=0.0.0.0 \
    --remote-debugging-port="$CDP_PORT" \
    --user-data-dir="$CHROME_PROFILE" \
    --no-sandbox \
    --disable-gpu \
    --window-size=1920,1080 \
    --disable-features=TranslateUI \
    &
```

## Security Notes

- CDP is exposed on `0.0.0.0` inside the container. Only expose port 9222 to trusted networks.
- The `--no-sandbox` flag is required in Docker (running as root). For production, consider running as a non-root user.
- Never commit Chrome profiles containing login sessions to version control.
