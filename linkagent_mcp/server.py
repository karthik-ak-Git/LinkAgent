"""
LinkAgent MCP Server

Exposes LinkedIn data extraction tools to AI agents via MCP protocol.
Uses Chrome DevTools Protocol (CDP) to connect to any Chromium browser.
"""

import json
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .cdp.browser import BrowserManager
from .cdp.client import CDPClient
from .extractors import (
    FeedExtractor,
    ProfileExtractor,
    CompanyExtractor,
    JobExtractor,
    SearchExtractor,
)

server = Server("linkagent")
browser = BrowserManager(cdp_port=9222)


def _get_client_for_tab(tab=None) -> CDPClient | None:
    """Create a CDPClient for a given tab or the current LinkedIn tab."""
    if tab is None:
        tab = browser.find_linkedin_tab()
    if not tab or not tab.ws_url:
        return None
    return CDPClient(tab.ws_url)


@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="linkedin_feed",
            description="Extract posts from the LinkedIn feed. Returns authors, headlines, post text, links, and engagement metrics.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="linkedin_profile",
            description="Extract a LinkedIn person profile. Provide username or navigate to profile first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "LinkedIn username (from URL /in/username)",
                    },
                },
            },
        ),
        Tool(
            name="linkedin_company",
            description="Extract a LinkedIn company page. Provide company name or navigate first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "LinkedIn company name (from URL /company/name)",
                    },
                },
            },
        ),
        Tool(
            name="linkedin_jobs",
            description="Search jobs or extract job details. Provide keyword for search, or job_id for detail.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Job search keyword",
                    },
                    "job_id": {
                        "type": "string",
                        "description": "LinkedIn job ID (from URL /jobs/view/{id})",
                    },
                },
            },
        ),
        Tool(
            name="linkedin_search",
            description="Search for people or companies on LinkedIn.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Search keyword",
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["people", "company"],
                        "default": "people",
                        "description": "Type of search: people or company",
                    },
                },
            },
        ),
        Tool(
            name="linkedin_navigate",
            description="Navigate to a LinkedIn URL in the browser.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "LinkedIn URL to navigate to"},
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


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        # --- LinkedIn extraction tools ---
        if name == "linkedin_feed":
            tab = browser.find_linkedin_tab()
            client = _get_client_for_tab(tab)
            if not client:
                return [TextContent(type="text", text="No LinkedIn tab found. Open linkedin.com/feed in your browser.")]
            result = await FeedExtractor(client).extract()
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "linkedin_profile":
            tab = browser.find_linkedin_tab()
            client = _get_client_for_tab(tab)
            if not client:
                return [TextContent(type="text", text="No LinkedIn tab found. Open LinkedIn in your browser.")]
            result = await ProfileExtractor(client).extract(username=arguments.get("username", ""))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "linkedin_company":
            tab = browser.find_linkedin_tab()
            client = _get_client_for_tab(tab)
            if not client:
                return [TextContent(type="text", text="No LinkedIn tab found. Open LinkedIn in your browser.")]
            result = await CompanyExtractor(client).extract(company_name=arguments.get("company_name", ""))
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "linkedin_jobs":
            tab = browser.find_linkedin_tab()
            client = _get_client_for_tab(tab)
            if not client:
                return [TextContent(type="text", text="No LinkedIn tab found. Open LinkedIn in your browser.")]
            result = await JobExtractor(client).extract(
                keyword=arguments.get("keyword", ""),
                job_id=arguments.get("job_id", ""),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "linkedin_search":
            tab = browser.find_linkedin_tab()
            client = _get_client_for_tab(tab)
            if not client:
                return [TextContent(type="text", text="No LinkedIn tab found. Open LinkedIn in your browser.")]
            result = await SearchExtractor(client).extract(
                keyword=arguments.get("keyword", ""),
                search_type=arguments.get("search_type", "people"),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        # --- Browser control tools ---
        elif name == "linkedin_navigate":
            tab = browser.find_linkedin_tab() or (browser.get_tabs()[0] if browser.get_tabs() else None)
            if not tab:
                return [TextContent(type="text", text="No browser tabs found")]
            client = CDPClient(tab.ws_url)
            await client.navigate(arguments["url"])
            return [TextContent(type="text", text=f"Navigated to {arguments['url']}")]

        elif name == "take_screenshot":
            tabs = browser.get_tabs()
            tab = browser.find_linkedin_tab() or (tabs[0] if tabs else None)
            if not tab:
                return [TextContent(type="text", text="No tab found")]
            client = CDPClient(tab.ws_url)
            data = await client.screenshot()
            if data:
                import base64, os
                path = os.path.join(os.path.dirname(__file__), "screenshot.png")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(data))
                return [TextContent(type="text", text=f"Screenshot saved to {path}")]
            return [TextContent(type="text", text="Screenshot failed")]

        elif name == "execute_js":
            tabs = browser.get_tabs()
            tab = browser.find_linkedin_tab() or (tabs[0] if tabs else None)
            if not tab:
                return [TextContent(type="text", text="No tab found")]
            client = CDPClient(tab.ws_url)
            result = await client.evaluate(arguments["script"])
            return [TextContent(type="text", text=str(result)[:5000] if result else "No result")]

        elif name == "list_tabs":
            tabs = browser.get_tabs()
            result = [{"id": t.id, "title": t.title, "url": t.url} for t in tabs]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "scroll_page":
            tabs = browser.get_tabs()
            tab = browser.find_linkedin_tab() or (tabs[0] if tabs else None)
            if not tab:
                return [TextContent(type="text", text="No tab found")]
            client = CDPClient(tab.ws_url)
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
