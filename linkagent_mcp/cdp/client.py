"""
CDP WebSocket client for communicating with Chromium browser tabs.

Sends CDP commands over WebSocket to evaluate JavaScript, navigate,
capture screenshots, and scroll pages.

Protocol:
    Each command is a JSON message with a unique ID and method name.
    Responses are matched by ID and returned as dicts.

Connection:
    Uses a persistent WebSocket connection. Call connect() before sending
    commands, and disconnect() when done. The client also supports
    context manager usage (async with).
"""

import json
from typing import Any, Optional

import websockets
from websockets.protocol import State

from ..logging import get_logger

logger = get_logger("cdp.client")


class CDPClient:
    """
    WebSocket client for Chrome DevTools Protocol.

    Connects to a browser tab's WebSocket endpoint and sends CDP commands
    for page interaction (JS evaluation, navigation, screenshots).

    Usage:
        client = CDPClient("ws://127.0.0.1:9222/devtools/page/ABC123")
        await client.connect()
        result = await client.evaluate("document.title")
        await client.navigate("https://example.com")
        await client.disconnect()

    Or as a context manager:
        async with CDPClient(ws_url) as client:
            result = await client.evaluate("document.title")
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
        self._ws: Optional[websockets.WebSocketClientProtocol] = None

    @property
    def _is_open(self) -> bool:
        return self._ws is not None and self._ws.state == State.OPEN

    async def connect(self) -> None:
        """Open a persistent WebSocket connection to the tab."""
        if self._is_open:
            return
        self._ws = await websockets.connect(
            self.ws_url,
            max_size=50 * 1024 * 1024,  # 50MB for large pages
            close_timeout=5,
        )
        logger.debug("Connected to %s", self.ws_url)

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._is_open:
            await self._ws.close()
            logger.debug("Disconnected from %s", self.ws_url)
        self._ws = None

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
        Send a raw CDP command over the persistent connection.

        Args:
            method: CDP method name (e.g. "Runtime.evaluate").
            params: Optional parameters dict.

        Returns:
            CDP response dict.

        Raises:
            RuntimeError: If not connected (call connect() first).
        """
        if not self._is_open:
            raise RuntimeError("Not connected. Call connect() first.")

        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params

        await self._ws.send(json.dumps(msg))

        # Read until we get our response (skip CDP events)
        while True:
            raw = await self._ws.recv()
            resp = json.loads(raw)
            if resp.get("id") == self._msg_id:
                return resp

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()
