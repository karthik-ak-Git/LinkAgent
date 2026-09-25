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
from .research.engine import ResearchEngine
from .research.reasoning import initialize as initialize_reasoning
from .jobs.manager import JobManager

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
    Tool(
        name="click",
        description="Click an element on the page by CSS selector. Triggers native mouse events (mousedown, mouseup, click).",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the element to click"},
            },
            "required": ["selector"],
        },
    ),
    Tool(
        name="type_text",
        description="Type text into an input field or textarea by CSS selector. Focuses the element and types character by character.",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the input element"},
                "text": {"type": "string", "description": "Text to type"},
                "clear": {"type": "boolean", "description": "Clear existing text before typing", "default": False},
                "delay_ms": {"type": "integer", "description": "Delay between keystrokes in ms", "default": 50},
            },
            "required": ["selector", "text"],
        },
    ),
    Tool(
        name="send_keys",
        description="Send keyboard key presses (e.g. Enter, Tab, Escape). Useful for submitting forms, navigating, or closing modals.",
        inputSchema={
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of key names to press (e.g. ['Enter'], ['Tab', 'Enter'])",
                },
            },
            "required": ["keys"],
        },
    ),
    Tool(
        name="get_text",
        description="Get the visible text content of an element by CSS selector.",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the element"},
            },
            "required": ["selector"],
        },
    ),
    Tool(
        name="get_value",
        description="Get the current value of an input/textarea element.",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the input element"},
            },
            "required": ["selector"],
        },
    ),
    Tool(
        name="wait_for_element",
        description="Wait until an element appears on the page (by CSS selector). Useful after navigation or clicking.",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector to wait for"},
                "timeout_ms": {"type": "integer", "description": "Max wait time in ms", "default": 5000},
            },
            "required": ["selector"],
        },
    ),
    Tool(
        name="create_hidden_tab",
        description="Create a new hidden background tab for extraction work. The tab loads in the background without disturbing the user's visible browsing. Uses the same browser session (cookies, auth).",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to load in the new tab (default: about:blank)", "default": "about:blank"},
            },
        },
    ),
    Tool(
        name="create_incognito_tab",
        description="Create a new incognito/private window with a tab. The tab has a separate browser context — cookies, storage, and auth are completely isolated from the main session.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to load in the incognito tab (default: about:blank)", "default": "about:blank"},
            },
        },
    ),
    Tool(
        name="close_tab",
        description="Close a browser tab by its target ID. Useful for cleaning up hidden or incognito tabs created by LinkAgent.",
        inputSchema={
            "type": "object",
            "properties": {
                "target_id": {"type": "string", "description": "Target ID of the tab to close"},
            },
            "required": ["target_id"],
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
_engine = ResearchEngine(browser_manager=_browser, max_queries=get_config().max_queries, coverage_threshold=get_config().coverage_threshold, workers=get_config().max_workers)
_job_manager = JobManager(_engine)

RESEARCH_TOOLS = [
    Tool(
        name="agent_init",
        description="Initialize a concise, evidence-first execution envelope with a small token budget, background support, and the existing regular browser profile. This is a compact checklist, not private chain-of-thought.",
        inputSchema={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Optional task label; do not replace the exact request in research_create"},
                "execution_mode": {"type": "string", "enum": ["interactive", "background"], "default": "background"},
                "token_budget": {"type": "integer", "minimum": 256, "maximum": 8000, "default": 1200},
                "browser_mode": {"type": "string", "enum": ["existing", "hidden_tab"], "default": "existing"},
            },
        },
    ),
    Tool(
        name="research_create",
        description="Create an evidence-first research job. The exact request is immutable; requirements, primary sources, and scope are preserved before any search.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Exact user request; do not silently paraphrase"},
                "requirements": {"type": "array", "items": {"type": "object", "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "type": {"type": "string"},
                    "required": {"type": "boolean", "default": True},
                }}},
                "primary_sources": {"type": "array", "items": {"type": "string"}},
                "scope": {"type": "array", "items": {"type": "string"}},
                "max_queries": {"type": "integer", "minimum": 1, "maximum": 500, "default": 500},
                "background": {"type": "boolean", "default": True},
            },
            "required": ["query"],
        },
    ),
    Tool(name="research_context", description="Return the immutable request IR, checksum, requirements, and next evidence action.", inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}),
    Tool(name="research_plan", description="Build or return a request-preserving query plan. A plan is not evidence.", inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}, "max_queries": {"type": "integer", "minimum": 1, "maximum": 500}, "rebuild": {"type": "boolean", "default": False}}, "required": ["job_id"]}),
    Tool(name="research_ingest", description="Ingest a retrieved source with exact URL, excerpt, provenance, and verification state. Never infer a source was inspected without ingesting it.", inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}, "url": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}, "excerpt": {"type": "string"}, "source_type": {"type": "string", "enum": ["primary", "secondary", "tertiary"]}, "primary": {"type": "boolean", "default": False}, "verified": {"type": "boolean", "default": False}, "claim": {"type": "string"}, "requirement_ids": {"type": "array", "items": {"type": "string"}}, "locator": {"type": "string"}, "published_at": {"type": "string"}, "freshness": {"type": "number", "minimum": 0, "maximum": 1}}, "required": ["job_id", "url"]}),
    Tool(name="research_claim", description="Record a material claim and bind it to ingested evidence IDs. Unsupported claims remain unverified.", inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}, "claim": {"type": "string"}, "requirement_ids": {"type": "array", "items": {"type": "string"}}, "evidence_ids": {"type": "array", "items": {"type": "string"}}, "status": {"type": "string", "enum": ["supported", "partially_supported", "unverified", "ambiguous", "insufficient_data"]}}, "required": ["job_id", "claim"]}),
    Tool(
        name="research_correct",
        description="Record an explicit user correction, retire active hypotheses, preserve the original request, and rebuild the gap plan.",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "correction": {"type": "string"},
                "requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "type": {"type": "string"},
                            "required": {"type": "boolean", "default": True},
                        },
                    },
                },
            },
            "required": ["job_id", "correction"],
        },
    ),
    Tool(name="research_audit", description="Run independent request-fidelity, evidence, freshness, contradiction, primary-source, and coverage gates.", inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}, "final": {"type": "boolean", "default": False}}, "required": ["job_id"]}),
    Tool(name="research_synthesize", description="Compile only supported claims and expose uncovered requirements, unknowns, and contradictions.", inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}),
    Tool(name="research_export", description="Export the complete auditable research state as JSON.", inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}),
    Tool(name="research_status", description="Get research job status, request checksum, and coverage summary.", inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}),
    Tool(name="research_cancel", description="Cancel a research job without deleting its audit trail.", inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}),
    Tool(name="browser_status", description="Browser discovery + session ownership status", inputSchema={"type": "object", "properties": {}}),
]


def _get_client_for_url(url: str = "") -> CDPClient | None:
    """
    Get a connected CDPClient for a tab matching the URL's domain.

    Priority order:
    1. Hidden background tab (created by LinkAgent) matching the domain
    2. Any hidden background tab
    3. Existing visible tab matching the domain
    4. Any existing visible tab

    Returns None if no browser tab is available.
    """
    hidden_tabs = _browser.get_hidden_tabs()

    if url:
        for domain in registry.get_domains():
            if domain in url:
                for t in hidden_tabs:
                    if domain in t.url or t.url in ("about:blank", ""):
                        return CDPClient(t.ws_url)
                tab = _browser.find_tab(domain)
                if tab:
                    return CDPClient(tab.ws_url)

    if hidden_tabs:
        return CDPClient(hidden_tabs[0].ws_url)

    tab = _browser.get_any_tab()
    if not tab or not tab.ws_url:
        return None
    return CDPClient(tab.ws_url)


def _get_client_for_tab(tab=None) -> CDPClient | None:
    """Create a connected CDPClient for a given tab, or the best available tab."""
    if tab is None:
        hidden = _browser.get_hidden_tabs()
        if hidden:
            tab = hidden[0]
        else:
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
    tools.extend(RESEARCH_TOOLS)
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
                hidden_tab = await _browser.create_hidden_tab(entry.navigate_url or "about:blank")
                if not hidden_tab:
                    return [TextContent(
                        type="text",
                        text="No browser tab found and could not create a hidden one. Make sure a browser with CDP enabled is running (e.g., Chrome with --remote-debugging-port=9222).",
                    )]
                logger.info("Auto-created hidden tab for extraction: %s", name)
                client = CDPClient(hidden_tab.ws_url)
            await client.connect()
            try:
                result = await registry.extract(name, client, **arguments)
            finally:
                await client.disconnect()
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
        elif name == "click":
            return await _handle_click(arguments)
        elif name == "type_text":
            return await _handle_type(arguments)
        elif name == "send_keys":
            return await _handle_send_keys(arguments)
        elif name == "get_text":
            return await _handle_get_text(arguments)
        elif name == "get_value":
            return await _handle_get_value(arguments)
        elif name == "wait_for_element":
            return await _handle_wait(arguments)
        elif name == "create_hidden_tab":
            return await _handle_create_hidden_tab(arguments)
        elif name == "create_incognito_tab":
            return await _handle_create_incognito_tab(arguments)
        elif name == "close_tab":
            return await _handle_close_tab(arguments)
        elif name == "agent_init":
            return [TextContent(type="text", text=json.dumps(initialize_reasoning(
                task=arguments.get("task", ""),
                execution_mode=arguments.get("execution_mode", "background"),
                token_budget=arguments.get("token_budget", 1200),
                browser_mode=arguments.get("browser_mode", "existing"),
            ), indent=2, ensure_ascii=False))]
        elif name == "research_create":
            st = _job_manager.create(
                arguments["query"],
                max_queries=arguments.get("max_queries", 500),
                background=arguments.get("background", True),
                requirements=arguments.get("requirements"),
                primary_sources=arguments.get("primary_sources"),
                scope=arguments.get("scope"),
            )
            return [TextContent(type="text", text=json.dumps({
                "job_id": st.task_id,
                "status": st.status,
                "context": _engine.context(st.task_id),
            }, indent=2, ensure_ascii=False))]
        elif name == "research_context":
            return [TextContent(type="text", text=json.dumps(_engine.context(arguments["job_id"]), indent=2, ensure_ascii=False))]
        elif name == "research_plan":
            return [TextContent(type="text", text=json.dumps({
                "job_id": arguments["job_id"],
                "request_checksum": _engine.get(arguments["job_id"]).request.checksum,
                "plan": _engine.build_plan(arguments["job_id"], arguments.get("max_queries"), arguments.get("rebuild", False)),
            }, indent=2, ensure_ascii=False))]
        elif name == "research_ingest":
            return [TextContent(type="text", text=json.dumps(_engine.ingest_source(
                arguments["job_id"],
                url=arguments["url"],
                title=arguments.get("title", ""),
                content=arguments.get("content", ""),
                excerpt=arguments.get("excerpt", ""),
                source_type=arguments.get("source_type", "secondary"),
                primary=arguments.get("primary", False),
                verified=arguments.get("verified", False),
                claim=arguments.get("claim", ""),
                requirement_ids=arguments.get("requirement_ids"),
                locator=arguments.get("locator", ""),
                published_at=arguments.get("published_at"),
                freshness=arguments.get("freshness"),
            ), indent=2, ensure_ascii=False))]
        elif name == "research_claim":
            return [TextContent(type="text", text=json.dumps(_engine.add_claim(
                arguments["job_id"],
                arguments["claim"],
                requirement_ids=arguments.get("requirement_ids"),
                evidence_ids=arguments.get("evidence_ids"),
                status=arguments.get("status", "unverified"),
            ), indent=2, ensure_ascii=False))]
        elif name == "research_correct":
            return [TextContent(type="text", text=json.dumps(_engine.apply_correction(
                arguments["job_id"],
                arguments["correction"],
                requirements=arguments.get("requirements"),
            ), indent=2, ensure_ascii=False))]
        elif name == "research_audit":
            return [TextContent(type="text", text=json.dumps(_engine.audit(
                arguments["job_id"], final=arguments.get("final", False)
            ), indent=2, ensure_ascii=False))]
        elif name == "research_synthesize":
            return [TextContent(type="text", text=json.dumps(_engine.synthesize(arguments["job_id"]), indent=2, ensure_ascii=False))]
        elif name == "research_export":
            return [TextContent(type="text", text=json.dumps(_engine.export(arguments["job_id"]), indent=2, ensure_ascii=False))]
        elif name == "research_status":
            st = _job_manager.status(arguments["job_id"])
            return [TextContent(type="text", text=json.dumps(st.progress() if st else {"error": "not found"}, indent=2, ensure_ascii=False))]
        elif name == "research_cancel":
            st = _job_manager.cancel(arguments["job_id"])
            return [TextContent(type="text", text=json.dumps({"job_id": arguments["job_id"], "status": st.status if st else "not found"}, indent=2, ensure_ascii=False))]
        elif name == "browser_status":
            return [TextContent(type="text", text=json.dumps({"cdp_available": _browser.is_cdp_available(), "tabs": len(_browser.get_tabs()), "hidden": len(_browser.get_hidden_tabs()), "mode": get_config().browser_mode}, indent=2))]
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
    await client.connect()
    try:
        url = args["url"]
        await client.navigate(url)
        logger.info("Navigated to %s", url)
        return [TextContent(type="text", text=f"Navigated to {url}")]
    finally:
        await client.disconnect()


async def _handle_screenshot() -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    await client.connect()
    try:
        data = await client.screenshot()
        if not data:
            return [TextContent(type="text", text="Screenshot failed")]
        import base64
        path = get_config().screenshot_dir / "screenshot.png"
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        logger.info("Screenshot saved to %s", path)
        return [TextContent(type="text", text=f"Screenshot saved to {path}")]
    finally:
        await client.disconnect()


async def _handle_execute_js(args: dict) -> list[TextContent]:
    # §29 security: restrict to allowlisted read-only patterns unless privileged
    import os
    if os.getenv("LINKAGENT_ALLOW_JS","0") != "1":
        return [TextContent(type="text", text="execute_js disabled for security. Set LINKAGENT_ALLOW_JS=1 to enable.")]
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    await client.connect()
    try:
        result = await client.evaluate(args["script"])
        return [TextContent(type="text", text=str(result)[:5000] if result else "No result")]
    finally:
        await client.disconnect()


async def _handle_list_tabs() -> list[TextContent]:
    tabs = await _browser.get_tabs_extended()
    result = [
        {
            "id": t.id,
            "title": t.title,
            "url": t.url,
            "incognito": t.incognito,
            "hidden": t.hidden,
            "type": t.type,
        }
        for t in tabs
    ]
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_scroll(args: dict) -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    await client.connect()
    try:
        direction = args.get("direction", "down")
        pixels = args.get("pixels", 800)
        sign = pixels if direction == "down" else -pixels
        await client.scroll(sign)
        return [TextContent(type="text", text=f"Scrolled {direction} {pixels}px")]
    finally:
        await client.disconnect()


async def _handle_click(args: dict) -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    await client.connect()
    try:
        selector = args["selector"]
        clicked = await client.click(selector)
        if clicked:
            return [TextContent(type="text", text=f"Clicked: {selector}")]
        else:
            return [TextContent(type="text", text=f"Element not found: {selector}")]
    finally:
        await client.disconnect()


async def _handle_type(args: dict) -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    await client.connect()
    try:
        selector = args["selector"]
        text = args["text"]
        clear = args.get("clear", False)
        delay_ms = args.get("delay_ms", 50)
        if clear:
            ok = await client.clear_and_type(selector, text, delay_ms)
        else:
            ok = await client.type_text(selector, text, delay_ms)
        if ok:
            return [TextContent(type="text", text=f"Typed into: {selector}")]
        else:
            return [TextContent(type="text", text=f"Element not found: {selector}")]
    finally:
        await client.disconnect()


async def _handle_send_keys(args: dict) -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    await client.connect()
    try:
        keys = args["keys"]
        await client.send_keys(keys)
        return [TextContent(type="text", text=f"Sent keys: {', '.join(keys)}")]
    finally:
        await client.disconnect()


async def _handle_get_text(args: dict) -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    await client.connect()
    try:
        selector = args["selector"]
        text = await client.get_text(selector)
        if text is not None:
            return [TextContent(type="text", text=text[:5000])]
        else:
            return [TextContent(type="text", text=f"Element not found: {selector}")]
    finally:
        await client.disconnect()


async def _handle_get_value(args: dict) -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    await client.connect()
    try:
        selector = args["selector"]
        value = await client.get_value(selector)
        if value is not None:
            return [TextContent(type="text", text=value)]
        else:
            return [TextContent(type="text", text=f"Element not found: {selector}")]
    finally:
        await client.disconnect()


async def _handle_wait(args: dict) -> list[TextContent]:
    client = _get_client_for_tab()
    if not client:
        return [TextContent(type="text", text="No browser tab found")]
    await client.connect()
    try:
        selector = args["selector"]
        timeout_ms = args.get("timeout_ms", 5000)
        found = await client.wait_for_element(selector, timeout_ms)
        if found:
            return [TextContent(type="text", text=f"Element appeared: {selector}")]
        else:
            return [TextContent(type="text", text=f"Timeout waiting for: {selector}")]
    finally:
        await client.disconnect()


async def _handle_create_hidden_tab(args: dict) -> list[TextContent]:
    """Create a new hidden background tab for extraction work."""
    url = args.get("url", "about:blank")
    tab = await _browser.create_hidden_tab(url)
    if not tab:
        return [TextContent(type="text", text="Failed to create hidden tab. Is a browser with CDP running?")]
    return [TextContent(type="text", text=json.dumps({
        "target_id": tab.id,
        "ws_url": tab.ws_url,
        "url": tab.url,
        "status": "created_hidden_background",
    }, indent=2))]


async def _handle_create_incognito_tab(args: dict) -> list[TextContent]:
    """Create an incognito window only when explicitly enabled."""
    if not get_config().allow_incognito:
        return [TextContent(type="text", text="Incognito tabs are disabled. LinkAgent is configured to use the existing regular browser profile.")]
    url = args.get("url", "about:blank")
    tab = await _browser.create_incognito_tab(url)
    if not tab:
        return [TextContent(type="text", text="Failed to create incognito tab. Is a browser with CDP running?")]
    return [TextContent(type="text", text=json.dumps({
        "target_id": tab.id,
        "ws_url": tab.ws_url,
        "url": tab.url,
        "status": "created_incognito",
    }, indent=2))]


async def _handle_close_tab(args: dict) -> list[TextContent]:
    """Close a browser tab by target ID."""
    target_id = args["target_id"]
    ok = await _browser.close_tab(target_id)
    if ok:
        return [TextContent(type="text", text=f"Closed tab: {target_id}")]
    return [TextContent(type="text", text=f"Failed to close tab: {target_id}")]


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
