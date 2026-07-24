"""
CDP WebSocket client for communicating with Chromium browsers.
"""

import json
from typing import Any, Optional

import websockets


class CDPClient:
    """Manages WebSocket connection to a CDP-enabled browser tab."""

    def __init__(self, ws_url: str, timeout: int = 30):
        self.ws_url = ws_url
        self.timeout = timeout
        self._msg_id = 0

    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript expression and return the result."""
        resp = await self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
        })
        result = resp.get("result", {}).get("result", {})
        if result.get("type") == "undefined":
            return None
        return result.get("value")

    async def navigate(self, url: str) -> dict:
        """Navigate to a URL. Returns navigation response."""
        return await self.send("Page.navigate", {"url": url})

    async def screenshot(self, format: str = "png") -> Optional[str]:
        """Capture screenshot. Returns base64-encoded image data."""
        resp = await self.send("Page.captureScreenshot", {"format": format})
        return resp.get("result", {}).get("data")

    async def scroll(self, pixels: int = 800) -> None:
        """Scroll the page by the given number of pixels (negative = up)."""
        await self.evaluate(f"window.scrollBy(0, {pixels})")

    async def get_url(self) -> str:
        """Get the current page URL."""
        return await self.evaluate("location.href") or ""

    async def get_title(self) -> str:
        """Get the current page title."""
        return await self.evaluate("document.title") or ""

    async def send(self, method: str, params: Optional[dict] = None) -> dict:
        """Send a CDP command and return the response."""
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params

        async with websockets.connect(
            self.ws_url,
            max_size=50 * 1024 * 1024,
            close_timeout=5,
        ) as ws:
            await ws.send(json.dumps(msg))
            return json.loads(await ws.recv())

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass
