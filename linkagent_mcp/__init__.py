"""
LinkAgent MCP — Universal browser extraction via CDP.

A plugin-based MCP server that extracts structured data from any website
using Chrome DevTools Protocol. Site extractors are auto-discovered and
registered at startup.

Architecture:
    server.py           → MCP protocol, tool routing, stdio transport
    config.py           → Environment-based configuration
    logging.py          → Structured logging setup
    cdp/browser.py      → Browser discovery (cross-platform)
    cdp/client.py       → WebSocket CDP commands
    core/base.py        → BaseExtractor ABC for site modules
    core/registry.py    → Tool registry, dynamic dispatch
    sites/              → Site-specific extractors (linkedin, etc.)

Adding a new site:
    1. Create sites/mysite/__init__.py
    2. Implement extractors subclassing core.BaseExtractor
    3. Define register(registry) function
    4. Restart the server — it's auto-discovered
"""

__version__ = "0.1.0"
