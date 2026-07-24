# LinkAgent MCP

Universal browser extraction server using Chrome DevTools Protocol. Extract structured data from any website through an extensible plugin system.

## How It Works

LinkAgent connects to a running Chromium browser via CDP (Chrome DevTools Protocol) — the same protocol Chrome DevTools uses internally. This means:

- **No browser automation** — reads directly from the live DOM
- **Indistinguishable from normal browsing** — no injected scripts, no headless flags
- **Works on any site** — CDP sees exactly what you see
- **Cross-browser** — Chrome, Edge, Opera, Brave, Vivaldi (anything Chromium-based)

## Architecture

```
linkagent_mcp/
├── server.py              # MCP protocol, tool routing
├── config.py              # Environment-based configuration
├── logging.py             # Structured logging setup
├── cdp/
│   ├── browser.py         # Browser discovery (cross-platform)
│   └── client.py          # WebSocket CDP commands
├── core/
│   ├── base.py            # BaseExtractor ABC
│   ├── registry.py        # Tool registry, dynamic dispatch
│   └── models.py          # Data models
└── sites/
    └── linkedin/          # LinkedIn extractors
        ├── extractors/
        │   ├── feed.py
        │   ├── profile.py
        │   ├── company.py
        │   ├── jobs.py
        │   └── search.py
        └── __init__.py    # register() function
```

See [docs/architecture.md](docs/architecture.md) for detailed design.

## Quick Start

### 1. Start your browser with CDP

```bash
# Windows (Chrome)
chrome.exe --remote-debugging-port=9222

# Windows (Edge)
msedge.exe --remote-debugging-port=9222

# Windows (Opera)
"C:\Users\YourName\AppData\Local\Programs\Opera\opera.exe" --remote-debugging-port=9222

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

Log in to LinkedIn (or any target site) in this browser window.

### 2. Install and run

```bash
cd linkagent_mcp
pip install -e .
python -m linkagent_mcp
```

### 3. Use from any MCP client

The server exposes these tools:

| Tool | Description |
|------|-------------|
| `linkedin_feed` | Extract posts from the LinkedIn feed |
| `linkedin_profile` | Extract a person's profile |
| `linkedin_company` | Extract a company page |
| `linkedin_jobs` | Search jobs or extract job details |
| `linkedin_search` | Search for people or companies |
| `navigate` | Navigate to any URL |
| `take_screenshot` | Capture a page screenshot |
| `execute_js` | Run arbitrary JavaScript |
| `list_tabs` | List open browser tabs |
| `scroll_page` | Scroll the current page |

See [docs/tasks.md](docs/tasks.md) for detailed tool documentation.

## Docker

Run in a containerized Chromium — no local browser needed.

```bash
# Build and run
docker compose up -d

# Check logs
docker compose logs -f

# Stop
docker compose down
```

The container runs headless Chromium with CDP exposed on port 9222. Login sessions persist in a Docker volume (`chrome-profile`).

**Docker + Claude Desktop:**

```json
{
  "mcpServers": {
    "linkagent": {
      "command": "docker",
      "args": ["compose", "run", "--rm", "linkagent"]
    }
  }
}
```

**Docker + external CDP access:**

The CDP port is exposed on `localhost:9222`. Other tools can connect directly:

```python
import websockets, json
async with websockets.connect("ws://localhost:9222") as ws:
    await ws.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
    print(await ws.recv())
```

See [docs/docker.md](docs/docker.md) for advanced Docker configuration.

## Configuration

Set via environment variables or a `.env` file:

```bash
LINKAGENT_CDP_PORT=9222        # CDP debugging port
LINKAGENT_CDP_HOST=127.0.0.1   # CDP host
LINKAGENT_LOG_LEVEL=INFO       # DEBUG, INFO, WARNING, ERROR
LINKAGENT_LOG_FILE=linkagent.log  # Optional file logging
```

See `.env.example` for all options.

## Adding a New Site

See [docs/adding-sites.md](docs/adding-sites.md) for a step-by-step guide.

```
sites/
└── twitter/
    ├── __init__.py      # register(registry) function
    └── extractors/
        ├── __init__.py
        └── feed.py      # Your extractor
```

**1. Create the extractor:**

```python
# sites/twitter/extractors/feed.py
from linkagent_mcp.core.base import BaseExtractor

class TwitterFeedExtractor(BaseExtractor):
    """Extract tweets from Twitter/X feed."""

    async def extract(self, **kwargs) -> dict:
        raw = await self._eval("""
            (() => {
                const tweets = [];
                // ... your extraction logic ...
                return JSON.stringify({ tweets });
            })()
        """)
        return json.loads(raw)
```

**2. Register it:**

```python
# sites/twitter/__init__.py
from linkagent_mcp.core.registry import Registry
from .extractors.feed import TwitterFeedExtractor

def register(registry: Registry):
    registry.register(
        name="twitter_feed",
        extractor_class=TwitterFeedExtractor,
        domain="twitter.com",
        description="Extract tweets from the feed",
        input_schema={"type": "object", "properties": {}},
        navigate_url="https://x.com/home",
        url_patterns=["/home", "/search"],
    )
```

**3. Restart the server** — it's auto-discovered.

## MCP Client Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "linkagent": {
      "command": "python",
      "args": ["-m", "linkagent_mcp"],
      "cwd": "D:\\LinkAgent"
    }
  }
}
```

### Cursor / Windsurf

Add to your MCP settings:

```json
{
  "linkagent": {
    "command": "python",
    "args": ["-m", "linkagent_mcp"],
    "cwd": "D:\\LinkAgent"
  }
}
```

## Development

```bash
# Install dev dependencies
pip install -e .

# Run with debug logging
LINKAGENT_LOG_LEVEL=DEBUG python -m linkagent_mcp

# Run tests
python tests/test_live.py
```

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for the full roadmap.

### Current (v0.1.0)

- Universal CDP-based extraction framework
- Plugin system with auto-discovery
- 5 LinkedIn extractors (feed, profile, company, jobs, search)
- 5 browser control tools
- Cross-platform browser detection
- Environment-based configuration
- Structured logging

### Next (v0.2.0)

- **Robustness** — Auto-reconnection, health checks, error recovery
- **More data** — Pagination, expanded sections, media extraction
- **More sites** — Twitter/X, GitHub, Reddit, Instagram
- **Better output** — Data storage, export formats, caching

### Future Goals

- **Self-healing selectors** — Automatically adapt to DOM changes
- **Write operations** — Safe, controlled posting and messaging with human approval
- **Multi-browser** — Multiple profiles, remote browsers, Docker support
- **Scheduling** — Cron-like extraction, event-driven alerts
- **Analytics** — Trend analysis, network analysis, competitive intelligence
- **Platform** — Visual extractor builder, marketplace, cloud hosting

### What We Want to Overcome

| Problem | Current State | Goal |
|---------|---------------|------|
| Fragile selectors | Manual updates when LinkedIn changes | Self-healing, automatic adaptation |
| Read-only | Cannot post, message, or interact | Controlled writes with approval |
| Single browser | One profile, one session | Multiple browsers and profiles |
| No scheduling | Manual extraction only | Cron jobs, event-driven alerts |
| No storage | JSON output only | SQLite/PostgreSQL, CSV export |
| No testing | Manual testing only | Snapshot tests, selector monitoring |
| Deployment | Requires local browser | Docker, cloud, headless mode |

See [docs/limitations.md](docs/limitations.md) for known issues.

## Documentation

- [Architecture](docs/architecture.md) — System design and data flow
- [File Reference](docs/files.md) — What every file does
- [Tasks](docs/tasks.md) — Tool documentation and return values
- [Limitations](docs/limitations.md) — Known issues and constraints
- [Adding Sites](docs/adding-sites.md) — Step-by-step guide
- [Selector Strategy](docs/selectors.md) — How we pick stable DOM elements
- [Roadmap](docs/roadmap.md) — Future plans and goals

## License

MIT — see [LICENSE](LICENSE).
