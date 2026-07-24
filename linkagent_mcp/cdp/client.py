"""
CDP WebSocket client for communicating with Chromium browser tabs.

Sends CDP commands over WebSocket to evaluate JavaScript, navigate,
capture screenshots, and scroll pages.

Protocol:
    Each command is a JSON message with a unique ID and method name.
    Responses are matched by ID and returned as dicts.
"""

import json
from typing import Any, Optional

import websockets

from ..logging import get_logger

logger = get_logger("cdp.client")


class CDPClient:
    """
    WebSocket client for Chrome DevTools Protocol.

    Connects to a browser tab's WebSocket endpoint and sends CDP commands
    for page interaction (JS evaluation, navigation, screenshots).

    Usage:
        client = CDPClient("ws://127.0.0.1:9222/devtools/page/ABC123")
        result = await client.evaluate("document.title")
        await client.navigate("https://example.com")
    """

    def __init__(self, ws_url: str, timeout: int = 30):
        """
        Initialize the CDP client.

        Args:
            ws_url: WebSocket URL for the target tab (from CDP /json endpoint).
            timeout: Command timeout in seconds.
        """
        self.ws_url = ws_url
        self.timeout = timeout
        self._msg_id = 0

    async def evaluate(self, expression: str) -> Any:
        """
        Evaluate a JavaScript expression in the page context.

        Args:
            expression: JavaScript code to evaluate. Can be a statement or expression.
                       Use IIFE syntax (() => {...})() for multi-line logic.

        Returns:
            The evaluated result, or None if undefined.
        """
        resp = await self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
        })
        result = resp.get("result", {}).get("result", {})
        if result.get("type") == "undefined":
            return None
        return result.get("value")

    async def navigate(self, url: str) -> dict:
        """
        Navigate the tab to a URL.

        Args:
            url: Target URL.

        Returns:
            CDP navigation response dict.
        """
        logger.debug("Navigating to %s", url)
        return await self.send("Page.navigate", {"url": url})

    async def screenshot(self, format: str = "png") -> Optional[str]:
        """
        Capture a screenshot of the current page.

        Args:
            format: Image format ("png" or "jpeg").

        Returns:
            Base64-encoded image data, or None on failure.
        """
        resp = await self.send("Page.captureScreenshot", {"format": format})
        return resp.get("result", {}).get("data")

    async def scroll(self, pixels: int = 800) -> None:
        """
        Scroll the page by the given number of pixels.

        Args:
            pixels: Number of pixels to scroll (negative = up).
        """
        await self.evaluate(f"window.scrollBy(0, {pixels})")

    async def get_url(self) -> str:
        """Get the current page URL."""
        return await self.evaluate("location.href") or ""

    async def get_title(self) -> str:
        """Get the current page title."""
        return await self.evaluate("document.title") or ""

    async def send(self, method: str, params: Optional[dict] = None) -> dict:
        """
        Send a raw CDP command.

        Args:
            method: CDP method name (e.g. "Runtime.evaluate").
            params: Optional parameters dict.

        Returns:
            CDP response dict.
        """
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params

        async with websockets.connect(
            self.ws_url,
            max_size=50 * 1024 * 1024,  # 50MB for large pages
            close_timeout=5,
        ) as ws:
            await ws.send(json.dumps(msg))
            return json.loads(await ws.recv())

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass
