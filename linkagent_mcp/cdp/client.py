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

    async def click(self, selector: str) -> bool:
        """
        Click an element matching a CSS selector.

        Uses CDP Input.dispatchMouseEvent on the element's bounding box center,
        which triggers native click events (not just JS click()).

        Args:
            selector: CSS selector for the element to click.

        Returns:
            True if element was found and clicked, False otherwise.
        """
        js = f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (!el) return null;
            const rect = el.getBoundingClientRect();
            return {{ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2,
                     width: rect.width, height: rect.height }};
        }})()
        """
        result = await self.evaluate(js)
        if not result:
            return False

        x, y = result["x"], result["y"]
        # Move mouse, press, release — simulates a real click
        await self.send("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": x, "y": y,
        })
        await self.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x, "y": y,
            "button": "left", "clickCount": 1,
        })
        await self.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x, "y": y,
            "button": "left", "clickCount": 1,
        })
        return True

    async def click_coordinates(self, x: float, y: float) -> None:
        """
        Click at absolute page coordinates.

        Args:
            x: X coordinate.
            y: Y coordinate.
        """
        await self.send("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": x, "y": y,
        })
        await self.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x, "y": y,
            "button": "left", "clickCount": 1,
        })
        await self.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x, "y": y,
            "button": "left", "clickCount": 1,
        })

    async def type_text(self, selector: str, text: str, delay_ms: int = 50) -> bool:
        """
        Focus an element and type text character by character.

        Uses CDP Input.dispatchKeyEvent for realistic keyboard input that
        triggers native input events (onkeydown, oninput, onchange).

        Args:
            selector: CSS selector for the input/textarea element.
            text: Text to type.
            delay_ms: Delay between keystrokes in milliseconds (0 for instant).

        Returns:
            True if element was found and typed into, False otherwise.
        """
        # Focus the element first
        focused = await self.evaluate(f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (!el) return false;
            el.focus();
            return true;
        }})()
        """)
        if not focused:
            return False

        for char in text:
            await self.send("Input.dispatchKeyEvent", {
                "type": "keyDown", "text": char,
            })
            await self.send("Input.dispatchKeyEvent", {
                "type": "keyUp", "text": char,
            })
            if delay_ms > 0:
                import asyncio
                await asyncio.sleep(delay_ms / 1000)
        return True

    async def clear_and_type(self, selector: str, text: str, delay_ms: int = 50) -> bool:
        """
        Clear an input field and type new text.

        Selects all existing text, deletes it, then types the new text.

        Args:
            selector: CSS selector for the input/textarea element.
            text: Text to type after clearing.
            delay_ms: Delay between keystrokes in milliseconds.

        Returns:
            True if successful, False otherwise.
        """
        focused = await self.evaluate(f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (!el) return false;
            el.focus();
            el.select();
            return true;
        }})()
        """)
        if not focused:
            return False

        # Delete selected text
        await self.send("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": "Backspace", "code": "Backspace",
            "windowsVirtualKeyCode": 8, "nativeVirtualKeyCode": 8,
        })
        await self.send("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "Backspace", "code": "Backspace",
            "windowsVirtualKeyCode": 8, "nativeVirtualKeyCode": 8,
        })

        for char in text:
            await self.send("Input.dispatchKeyEvent", {
                "type": "keyDown", "text": char,
            })
            await self.send("Input.dispatchKeyEvent", {
                "type": "keyUp", "text": char,
            })
            if delay_ms > 0:
                import asyncio
                await asyncio.sleep(delay_ms / 1000)
        return True

    async def send_keys(self, keys: list[str]) -> None:
        """
        Send raw keyboard key presses (e.g. ["Enter"], ["Tab"], ["Escape"]).

        Uses CDP Input.dispatchKeyEvent with proper key/code values.

        Args:
            keys: List of key names to press in sequence.
                  Supported: Enter, Tab, Escape, Backspace, ArrowDown, ArrowUp,
                  ArrowLeft, ArrowRight, Home, End, Delete, Space, etc.
        """
        key_map = {
            "Enter": {"key": "Enter", "code": "Enter",
                      "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13},
            "Tab": {"key": "Tab", "code": "Tab",
                    "windowsVirtualKeyCode": 9, "nativeVirtualKeyCode": 9},
            "Escape": {"key": "Escape", "code": "Escape",
                       "windowsVirtualKeyCode": 27, "nativeVirtualKeyCode": 27},
            "Backspace": {"key": "Backspace", "code": "Backspace",
                          "windowsVirtualKeyCode": 8, "nativeVirtualKeyCode": 8},
            "Delete": {"key": "Delete", "code": "Delete",
                       "windowsVirtualKeyCode": 46, "nativeVirtualKeyCode": 46},
            "ArrowDown": {"key": "ArrowDown", "code": "ArrowDown",
                          "windowsVirtualKeyCode": 40, "nativeVirtualKeyCode": 40},
            "ArrowUp": {"key": "ArrowUp", "code": "ArrowUp",
                        "windowsVirtualKeyCode": 38, "nativeVirtualKeyCode": 38},
            "ArrowLeft": {"key": "ArrowLeft", "code": "ArrowLeft",
                          "windowsVirtualKeyCode": 37, "nativeVirtualKeyCode": 37},
            "ArrowRight": {"key": "ArrowRight", "code": "ArrowRight",
                           "windowsVirtualKeyCode": 39, "nativeVirtualKeyCode": 39},
            "Home": {"key": "Home", "code": "Home",
                     "windowsVirtualKeyCode": 36, "nativeVirtualKeyCode": 36},
            "End": {"key": "End", "code": "End",
                    "windowsVirtualKeyCode": 35, "nativeVirtualKeyCode": 35},
            "Space": {"key": " ", "code": "Space",
                      "windowsVirtualKeyCode": 32, "nativeVirtualKeyCode": 32},
        }
        for key_name in keys:
            info = key_map.get(key_name, {"key": key_name, "code": key_name})
            await self.send("Input.dispatchKeyEvent", {"type": "keyDown", **info})
            await self.send("Input.dispatchKeyEvent", {"type": "keyUp", **info})

    async def get_text(self, selector: str) -> Optional[str]:
        """
        Get the visible text content of an element.

        Args:
            selector: CSS selector for the element.

        Returns:
            Text content string, or None if element not found.
        """
        return await self.evaluate(f"""
        (() => {{
            const el = document.querySelector('{selector}');
            return el ? el.innerText || el.textContent : null;
        }})()
        """)

    async def get_value(self, selector: str) -> Optional[str]:
        """
        Get the value property of an input/textarea element.

        Args:
            selector: CSS selector for the input element.

        Returns:
            Current value string, or None if element not found.
        """
        return await self.evaluate(f"""
        (() => {{
            const el = document.querySelector('{selector}');
            return el ? el.value : null;
        }})()
        """)

    async def wait_for_element(self, selector: str, timeout_ms: int = 5000) -> bool:
        """
        Wait until an element matching the CSS selector appears in the DOM.

        Args:
            selector: CSS selector to wait for.
            timeout_ms: Maximum wait time in milliseconds.

        Returns:
            True if element appeared, False on timeout.
        """
        js = f"""
        new Promise((resolve) => {{
            if (document.querySelector('{selector}')) {{ resolve(true); return; }}
            const obs = new MutationObserver(() => {{
                if (document.querySelector('{selector}')) {{
                    obs.disconnect();
                    resolve(true);
                }}
            }});
            obs.observe(document.body, {{ childList: true, subtree: true }});
            setTimeout(() => {{ obs.disconnect(); resolve(false); }}, {timeout_ms});
        }})
        """
        return await self.evaluate(js)

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
