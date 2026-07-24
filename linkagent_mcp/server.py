"""
LinkAgent MCP Server — entry point.

Universal extraction server that connects to any Chromium browser via CDP.
Site extractors are discovered and registered automatically.

Architecture:
    server.py        → MCP protocol, tool routing
    cdp/browser.py   → Browser discovery and tab management
    cdp/client.py    → CDP WebSocket communication
    core/base.py     → BaseExtractor ABC for all site modules
    core/registry.py → Tool registry, dynamic dispatch
    sites/           → Site-specific extractors (linkedin, twitter, etc.)

Configuration:
    Set environment variables or create a .env file:
        LINKAGENT_CDP_PORT=9222
        LINKAGENT_LOG_LEVEL=INFO

Usage:
    python -m linkagent_mcp
    # or
    linkagent-mcp  (if installed via pip)
"""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .config import get_config
from .cdp.browser import BrowserManager
from .cdp.client import CDPClient
from .core.registry import registry
from .logging import setup_logging
from .sites import auto_discover

logger = logging.getLogger("linkagent.server")

# ──────────────────────────────────────────────────────────────
# Browser control tool definitions
# ──────────────────────────────────────────────────────────────

BROWSER_TOOLS = [
    Tool(
        name="navigate",
        description="Navigate to any URL in the browser.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"},
            },
            "required": ["url"],
        },
    ),
    Tool(
        name="take_screenshot",
        description="Take a screenshot of the current page.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="execute_js",
        description="Execute arbitrary JavaScript in the current page via CDP.",
        inputSchema={
            "type": "object",
            "properties": {
                "script": {"type": "string", "description": "JavaScript to execute"},
            },
            "required": ["script"],
        },
    ),
    Tool(
        name="list_tabs",
        description="List all open browser tabs.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="scroll_page",
        description="Scroll the current page up or down.",
        inputSchema={
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down"], "default": "down"},
                "pixels": {"type": "integer", "description": "Pixels to scroll", "default": 800},
            },
        },
    ),
]


# ──────────────────────────────────────────────────────────────
# Server initialization
# ──────────────────────────────────────────────────────────────

def _create_server() -> Server:
    """Create and configure the MCP server with all registered tools."""
    config = get_config()
    setup_logging(level=config.log_level, log_file=config.log_file)
    config.ensure_dirs()

    logger.info("Initializing %s server", config.server_name)
    logger.info("CDP target: %s:%d", config.cdp_host, config.cdp_port)

    # Discover and register all site extractors
    auto_discover(registry)
    registered = registry.list_tools()
    logger.info("Registered %d extraction tools", len(registered))
    for tool in registered:
        logger.debug("  - %s", tool["name"])

    return Server(config.server_name)


# ──────────────────────────────────────────────────────────────
# CDP client helpers
# ──────────────────────────────────────────────────────────────

_server = _create_server()
_browser = BrowserManager(
    cdp_host=get_config().cdp_host,
    cdp_port=get_config().cdp_port,
)


def _get_client_for_url(url: str = "") -> CDPClient | None:
    """
    Get a CDPClient for a tab matching the URL's domain.

    Falls back to any available tab if no domain-specific match is found.
    Returns None if no browser tab is available.
    """
    tab = None
    if url:
        for domain in registry.get_domains():
            if domain in url:
                tab = _browser.find_tab(domain)
                break
    if not tab:
        tab = _browser.get_any_tab()
    if not tab or not tab.ws_url:
        return None
    return CDPClient(tab.ws_url)


def _get_client_for_tab(tab=None) -> CDPClient | None:
    """Create a CDPClient for a given tab, or any available tab."""
    if tab is None:
        tab = _browser.get_any_tab()
    if not tab or not tab.ws_url:
        return None
    return CDPClient(tab.ws_url)


# ──────────────────────────────────────────────────────────────
# MCP tool listing
# ──────────────────────────────────────────────────────────────

@_server.list_tools()
async def list_tools() -> list[Tool]:
    """Return all available MCP tools (extraction + browser control)."""
    tools = []

    # Auto-generated tools from registered site extractors
    for t in registry.list_tools():
        tools.append(Tool(
            name=t["name"],
            description=t["description"],
            inputSchema=t["inputSchema"],
        ))

    # Built-in browser control tools
    tools.extend(BROWSER_TOOLS)

    return tools


# ──────────────────────────────────────────────────────────────
# MCP tool dispatch
# ──────────────────────────────────────────────────────────────

@_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Route a tool call to the appropriate handler.

    Registry-based extraction tools are dispatched dynamically.
    Browser control tools are handled inline.
    """
    try:
        # ── Registry-based extraction tools ──
        entry = registry.get_entry(name)
        if entry:
            client = _get_client_for_url(entry.navigate_url)
            if not client:
                return [TextContent(
                    type="text",
                    text="No browser tab found. Open a browser with CDP enabled and navigate to the target site.",
                )]
            result = await registry.extract(name, client, **arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        # ── Built-in browser control tools ──
        if name == "navigate":
            return await _handle_navigate(arguments)
        elif name == "take_screenshot":
            return await _handle_screenshot()
        elif name == "execute_js":
            return await _handle_execute_js(arguments)
        elif name == "list_tabs":
            return await _handle_list_tabs()
        elif name == "scroll_page":
            return await _handle_scroll(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.exception("Tool call failed: %s", name)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ──────────────────────────────────────────────────────────────
# Browser control handlers
# ──────────────────────────────────────────────────────────────

async def _handle_navigate(args: dict) -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    url = args["url"]
    await client.navigate(url)
    logger.info("Navigated to %s", url)
    return [TextContent(type="text", text=f"Navigated to {url}")]


async def _handle_screenshot() -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    data = await client.screenshot()
    if not data:
        return [TextContent(type="text", text="Screenshot failed")]
    import base64
    path = get_config().screenshot_dir / "screenshot.png"
    with open(path, "wb") as f:
        f.write(base64.b64decode(data))
    logger.info("Screenshot saved to %s", path)
    return [TextContent(type="text", text=f"Screenshot saved to {path}")]


async def _handle_execute_js(args: dict) -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    result = await client.evaluate(args["script"])
    return [TextContent(type="text", text=str(result)[:5000] if result else "No result")]


async def _handle_list_tabs() -> list[TextContent]:
    tabs = _browser.get_tabs()
    result = [{"id": t.id, "title": t.title, "url": t.url} for t in tabs]
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_scroll(args: dict) -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    direction = args.get("direction", "down")
    pixels = args.get("pixels", 800)
    sign = pixels if direction == "down" else -pixels
    await client.scroll(sign)
    return [TextContent(type="text", text=f"Scrolled {direction} {pixels}px")]


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

async def main():
    """Start the MCP server over stdio transport."""
    logger.info("Starting LinkAgent MCP server")
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(read_stream, write_stream, _server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
