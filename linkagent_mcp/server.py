"""
LinkAgent MCP Server

Universal extraction server. Uses CDP to connect to any Chromium browser.
Site extractors are registered dynamically via the registry.

To add a new site:
1. Create a module under sites/ (e.g. sites/twitter/)
2. Implement extractors subclassing core.BaseExtractor
3. Call registry.register() or expose a register(registry) function
4. The server auto-discovers and exposes new tools
"""

import json
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .cdp.browser import BrowserManager
from .cdp.client import CDPClient
from .core.registry import registry
from .sites import auto_discover

# ── Bootstrap ──

server = Server("linkagent")
browser = BrowserManager(cdp_port=9222)

# Register all site extractors
auto_discover(registry)


def _get_client_for_url(url: str = "") -> CDPClient | None:
    """Get a CDPClient for a tab matching the URL, or any available tab."""
    tab = None
    if url:
        # Try to find a tab that matches the URL's domain
        for domain in registry.get_domains():
            if domain in url:
                tab = browser.find_tab(domain)
                break
    if not tab:
        tab = browser.find_tab("linkedin.com") or browser.get_any_tab()
    if not tab or not tab.ws_url:
        return None
    return CDPClient(tab.ws_url)


def _get_client_for_tab(tab=None) -> CDPClient | None:
    """Create a CDPClient for a given tab or any available tab."""
    if tab is None:
        tab = browser.get_any_tab()
    if not tab or not tab.ws_url:
        return None
    return CDPClient(tab.ws_url)


# ── Dynamic tool listing ──

@server.list_tools()
async def list_tools() -> List[Tool]:
    tools = []

    # Auto-generated tools from registered extractors
    for t in registry.list_tools():
        tools.append(Tool(
            name=t["name"],
            description=t["description"],
            inputSchema=t["inputSchema"],
        ))

    # Built-in browser control tools
    tools.extend([
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
    ])

    return tools


# ── Tool dispatch ──

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        # ── Registry-based extraction tools ──
        entry = registry.get_entry(name)
        if entry:
            client = _get_client_for_url(entry.navigate_url)
            if not client:
                return [TextContent(type="text", text="No browser tab found. Open a browser with CDP enabled on port 9222.")]
            result = await registry.extract(name, client, **arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        # ── Built-in browser tools ──
        if name == "navigate":
            client = _get_client_for_tab()
            if not client:
                return [TextContent(type="text", text="No browser tab found")]
            await client.navigate(arguments["url"])
            return [TextContent(type="text", text=f"Navigated to {arguments['url']}")]

        elif name == "take_screenshot":
            client = _get_client_for_tab()
            if not client:
                return [TextContent(type="text", text="No tab found")]
            data = await client.screenshot()
            if data:
                import base64, os
                path = os.path.join(os.path.dirname(__file__), "screenshot.png")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(data))
                return [TextContent(type="text", text=f"Screenshot saved to {path}")]
            return [TextContent(type="text", text="Screenshot failed")]

        elif name == "execute_js":
            client = _get_client_for_tab()
            if not client:
                return [TextContent(type="text", text="No tab found")]
            result = await client.evaluate(arguments["script"])
            return [TextContent(type="text", text=str(result)[:5000] if result else "No result")]

        elif name == "list_tabs":
            tabs = browser.get_tabs()
            result = [{"id": t.id, "title": t.title, "url": t.url} for t in tabs]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "scroll_page":
            client = _get_client_for_tab()
            if not client:
                return [TextContent(type="text", text="No tab found")]
            direction = arguments.get("direction", "down")
            pixels = arguments.get("pixels", 800)
            sign = pixels if direction == "down" else -pixels
            await client.scroll(sign)
            return [TextContent(type="text", text=f"Scrolled {direction} {pixels}px")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
