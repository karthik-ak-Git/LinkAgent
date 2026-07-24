#!/usr/bin/env python3
"""
LinkAgent MCP Server

Exposes browser automation tools to AI agents via MCP protocol.
Connects directly to Opera via Chrome DevTools Protocol (CDP).
"""

import json
import asyncio
import urllib.request
from typing import Any, Dict, List
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

CDP_BASE = "http://localhost:9222"

server = Server("linkagent")


def get_cdp_tabs():
    """Get list of CDP targets from Opera."""
    return json.loads(urllib.request.urlopen(f"{CDP_BASE}/json").read())


def get_page_ws(page_id: str) -> str:
    """Get WebSocket URL for a page."""
    tabs = get_cdp_tabs()
    for t in tabs:
        if t["id"] == page_id:
            return t.get("webSocketDebuggerUrl", "")
    return ""


def find_linkedin_tab():
    """Find the LinkedIn feed tab."""
    tabs = get_cdp_tabs()
    for t in tabs:
        if t["type"] == "page" and "linkedin.com/feed" in t.get("url", ""):
            return t
    return None


async def cdp_eval(ws_url: str, expression: str) -> Any:
    """Evaluate JavaScript via CDP WebSocket."""
    import websockets
    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        msg = json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": expression, "returnByValue": True}
        })
        await ws.send(msg)
        resp = json.loads(await ws.recv())
        return resp.get("result", {}).get("result", {}).get("value")


EXTRACT_FEED_JS = """
(() => {
    const posts = [];
    const primarySection = document.querySelector('section[aria-label="Primary content"]');
    if (!primarySection) return JSON.stringify({error: 'No primary section', url: location.href});

    const commentBtns = primarySection.querySelectorAll('button[aria-label*="Comment"]');

    for (const btn of commentBtns) {
        let container = btn.parentElement;
        for (let i = 0; i < 15; i++) {
            if (container.parentElement) container = container.parentElement;
            const text = container.innerText || '';
            if (text.length > 200) break;
        }

        const text = container.innerText || '';
        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

        const post = {};
        for (const line of lines) {
            if (line === 'Feed post' || line === 'From your activity' || line.startsWith('Promoted')) continue;
            if (line.includes('•') && (line.includes('3rd') || line.includes('2nd') || line.includes('1st'))) {
                post.author = line.split('•')[0].trim();
                break;
            }
            if (line.length > 2 && line.length < 100 && !line.includes('Follow') && !line.includes('Sort by')) {
                post.author = line;
                break;
            }
        }

        let foundAuthor = false;
        for (const line of lines) {
            if (line === post.author) { foundAuthor = true; continue; }
            if (foundAuthor && !post.headline) {
                if (line.length > 10 && line.length < 200 && !line.match(/^\\d+[hmd]/) && line !== 'Follow') {
                    post.headline = line;
                }
            }
            if (!post.time && line.match(/^[\\d]+[hmd]$/)) post.time = line;
        }

        let postTextLines = [];
        for (const line of lines) {
            if (line.length > 50 && !line.includes('Follow') && !line.includes('Feed post') && !line.includes('Sort by') && !line.includes('Recommended')) {
                postTextLines.push(line);
            }
        }
        if (postTextLines.length > 0) post.text = postTextLines.join(' ').substring(0, 2000);

        const nums = [];
        for (const line of lines) {
            if (line.match(/^\\d+[kKmM]?$/) && parseInt(line.replace(/[kKmM]/, '')) < 100000) nums.push(line);
        }
        if (nums.length >= 3) { post.likes = nums[0]; post.comments = nums[1]; post.reposts = nums[2]; }

        const links = container.querySelectorAll('a[href]');
        for (const link of links) {
            const href = link.href;
            if (href && (href.includes('/pulse/') || href.includes('/posts/') || href.includes('/in/') || href.includes('github.com'))) {
                post.link = href;
                break;
            }
        }

        const skipAuthors = ['Start a post', 'Sort by', 'Feed post', 'Recommended for you', 'Show more'];
        if (post.author && !skipAuthors.includes(post.author) && !posts.find(p => p.author === post.author)) posts.push(post);
    }

    return JSON.stringify({url: location.href, title: document.title, postCount: posts.length, posts});
})()
"""


@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="linkedin_feed",
            description="Extract posts from the LinkedIn feed currently open in Opera. Returns authors, headlines, post text, links, and engagement metrics.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="linkedin_navigate",
            description="Navigate to a LinkedIn URL in Opera",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "LinkedIn URL to navigate to"}
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="take_screenshot",
            description="Take a screenshot of the current page in Opera",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="execute_js",
            description="Execute JavaScript in the current page via CDP",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "JavaScript to execute"}
                },
                "required": ["script"]
            }
        ),
        Tool(
            name="list_tabs",
            description="List all open tabs in Opera",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="scroll_page",
            description="Scroll the current page up or down",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down"], "default": "down"},
                    "pixels": {"type": "integer", "description": "Pixels to scroll", "default": 800}
                }
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        if name == "linkedin_feed":
            tab = find_linkedin_tab()
            if not tab:
                return [TextContent(type="text", text="No LinkedIn tab found. Open linkedin.com/feed in Opera.")]
            result = await cdp_eval(tab["webSocketDebuggerUrl"], EXTRACT_FEED_JS)
            data = json.loads(result)
            return [TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]

        elif name == "linkedin_navigate":
            tab = find_linkedin_tab()
            if not tab:
                tabs = [t for t in get_cdp_tabs() if t["type"] == "page"]
                tab = tabs[0] if tabs else None
            if not tab:
                return [TextContent(type="text", text="No browser tabs found")]
            import websockets
            async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=10*1024*1024) as ws:
                await ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": arguments["url"]}}))
                resp = json.loads(await ws.recv())
            return [TextContent(type="text", text=f"Navigated to {arguments['url']}")]

        elif name == "take_screenshot":
            tab = find_linkedin_tab() or next((t for t in get_cdp_tabs() if t["type"] == "page"), None)
            if not tab:
                return [TextContent(type="text", text="No tab found")]
            import websockets
            async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=50*1024*1024) as ws:
                await ws.send(json.dumps({"id": 1, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
                resp = json.loads(await ws.recv())
                data = resp.get("result", {}).get("data", "")
            if data:
                import base64, os
                path = os.path.join(os.path.dirname(__file__), "screenshot.png")
                with open(path, "wb") as f:
                    f.write(base64.b64decode(data))
                return [TextContent(type="text", text=f"Screenshot saved to {path}")]
            return [TextContent(type="text", text="Screenshot failed")]

        elif name == "execute_js":
            tab = find_linkedin_tab() or next((t for t in get_cdp_tabs() if t["type"] == "page"), None)
            if not tab:
                return [TextContent(type="text", text="No tab found")]
            result = await cdp_eval(tab["webSocketDebuggerUrl"], arguments["script"])
            return [TextContent(type="text", text=str(result)[:5000] if result else "No result")]

        elif name == "list_tabs":
            tabs = get_cdp_tabs()
            result = [{"id": t["id"], "title": t.get("title", ""), "url": t.get("url", ""), "type": t["type"]} for t in tabs if t["type"] == "page"]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "scroll_page":
            tab = find_linkedin_tab() or next((t for t in get_cdp_tabs() if t["type"] == "page"), None)
            if not tab:
                return [TextContent(type="text", text="No tab found")]
            direction = arguments.get("direction", "down")
            pixels = arguments.get("pixels", 800)
            sign = pixels if direction == "down" else -pixels
            await cdp_eval(tab["webSocketDebuggerUrl"], f"window.scrollBy(0, {sign})")
            return [TextContent(type="text", text=f"Scrolled {direction} {pixels}px")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
