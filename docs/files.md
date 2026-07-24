# File Reference

Every file in `linkagent_mcp/` and what it does.

## Root

| File | Purpose |
|------|---------|
| `__init__.py` | Package definition. Exports version and docstring. |
| `__main__.py` | Entry point for `python -m linkagent_mcp`. Calls `server.main()`. |
| `server.py` | MCP protocol handler. Registers tools, routes calls, runs stdio transport. |
| `config.py` | Environment-based configuration. Reads `LINKAGENT_*` env vars and `.env`. |
| `logging.py` | Logging setup. Configures structured output to stderr and optional file. |
| `pyproject.toml` | Package metadata, dependencies, entry points. |
| `requirements.txt` | Minimal dependencies: `mcp>=1.0.0`, `websockets>=12.0`. |

## `cdp/` — Browser Communication

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports: `CDPClient`, `BrowserManager`, `Tab`, `Browser`. |
| `browser.py` | Finds running Chromium browsers, discovers CDP tabs, provides `find_tab(domain)`. Cross-platform (Windows, macOS, Linux). |
| `client.py` | WebSocket client for CDP commands. Methods: `evaluate()`, `navigate()`, `screenshot()`, `scroll()`, `get_url()`, `get_title()`, `send()`. |

### How `browser.py` works

1. Tries to connect to `http://{host}:{port}/json/version`
2. If successful, browser is already running with CDP
3. If not, tries to launch browser with `--remote-debugging-port`
4. Lists all tabs via `/json` endpoint
5. `find_tab(domain)` matches tab URLs to the requested domain
6. Returns `Tab` dataclass with `id`, `url`, `title`, `ws_url`

### How `client.py` works

1. Connects to tab's `ws_url` via WebSocket
2. Sends JSON messages: `{"id": N, "method": "Runtime.evaluate", "params": {...}}`
3. Receives responses matched by ID
4. Auto-increments message IDs
5. 50MB max message size (for large pages)

## `core/` — Extraction Framework

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports: `BaseExtractor`, `Registry`, `ExtractionResult`. |
| `base.py` | Abstract base class. Provides `_eval()`, `_navigate()`, `_wait_for_element()`, `_scroll()`, `_screenshot()`. Subclass this for new sites. |
| `registry.py` | Maps tool names to extractor classes. Generates MCP tool definitions. Handles auto-discovery. |
| `models.py` | Data classes: `ExtractionResult`, `Post`, `Profile`, `Company`, `Job`, `SearchResult`. |

### How `registry.py` works

1. `registry.register(name, extractor_class, domain, ...)` stores an entry
2. `registry.get_entry(name)` returns the entry (or None)
3. `registry.list_tools()` generates MCP `Tool` definitions from entries
4. `registry.extract(name, client, **kwargs)` instantiates the extractor and calls `extract()`
5. `registry.get_domains()` returns unique domains for tab matching

### How `base.py` works

BaseExtractor provides these helpers to subclasses:

- `_eval(js)` — Execute JavaScript, return result
- `_navigate(url)` — Navigate to URL
- `_wait_for_element(selector, timeout_ms)` — Poll until element exists
- `_scroll(pixels)` — Scroll the page
- `_screenshot()` — Capture page screenshot
- `_get_url()` — Get current URL
- `_get_title()` — Get current title

## `sites/` — Site-Specific Extractors

| File | Purpose |
|------|---------|
| `__init__.py` | `auto_discover(registry)` — scans `sites/` for modules with `register()`. |
| `linkedin/__init__.py` | `register(registry)` — registers all 5 LinkedIn extractors. |
| `linkedin/extractors/__init__.py` | Re-exports all extractor classes. |
| `linkedin/extractors/feed.py` | FeedExtractor — parses feed posts. |
| `linkedin/extractors/profile.py` | ProfileExtractor — parses person profiles. |
| `linkedin/extractors/company.py` | CompanyExtractor — parses company pages. |
| `linkedin/extractors/jobs.py` | JobExtractor — parses job search and details. |
| `linkedin/extractors/search.py` | SearchExtractor — parses people/company search. |

### How auto-discovery works

1. `auto_discover()` iterates `sites/` directory
2. For each subdirectory with `__init__.py`, imports it
3. Checks if module has a `register()` function
4. Calls `register(registry)` to register all extractors
5. Logs warnings for failed imports (non-fatal)

## `tests/` — Test Files

| File | Purpose |
|------|---------|
| `test_live.py` | Live test — runs all 5 extractors against real LinkedIn. |
| `test_dom.py` | DOM inspection — dumps raw HTML structure for analysis. |
| `test_dom2.py` | Extended DOM inspection. |
| `test_inspect.py` | Quick inspection utilities. |
