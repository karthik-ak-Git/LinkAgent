"""
Universal base extractor — works with any website via CDP.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from ..cdp.client import CDPClient


class BaseExtractor(ABC):
    """
    Base class for all site extractors.

    Each extractor:
    - Takes a CDPClient connected to a browser tab
    - Knows which domain/URL pattern it handles
    - Executes JavaScript to extract structured data
    - Returns a dict result

    To create a new site extractor:
    1. Subclass BaseExtractor
    2. Set `domain` and `url_patterns`
    3. Implement `extract(**kwargs)`
    4. Register it via `registry.register()`
    """

    # Override in subclass
    domain: str = ""
    url_patterns: list[str] = []

    def __init__(self, client: CDPClient):
        self.client = client

    @abstractmethod
    async def extract(self, **kwargs) -> dict:
        """Extract data from the current page. Returns a dict."""
        pass

    def matches_url(self, url: str) -> bool:
        """Check if this extractor handles the given URL."""
        return any(pattern in url for pattern in self.url_patterns)

    async def _eval(self, js: str) -> Any:
        """Evaluate JavaScript via CDP."""
        return await self.client.evaluate(js)

    async def _get_url(self) -> str:
        """Get current page URL."""
        return await self.client.get_url()

    async def _get_title(self) -> str:
        """Get current page title."""
        return await self.client.get_title()

    async def _navigate(self, url: str) -> dict:
        """Navigate to a URL."""
        return await self.client.navigate(url)

    async def _wait_for_element(self, selector: str, timeout_ms: int = 5000) -> bool:
        """Wait for an element to appear in the DOM."""
        js = f"""
        new Promise((resolve) => {{
            const check = () => {{
                if (document.querySelector('{selector}')) resolve(true);
                else if (Date.now() - start > {timeout_ms}) resolve(false);
                else requestAnimationFrame(check);
            }};
            const start = Date.now();
            check();
        }})
        """
        return await self._eval(js)

    async def _click(self, selector: str) -> bool:
        """Click an element by CSS selector. Returns True on success."""
        return await self.client.click(selector)

    async def _type(self, selector: str, text: str, delay_ms: int = 50) -> bool:
        """Type text into an element. Returns True on success."""
        return await self.client.type_text(selector, text, delay_ms)

    async def _clear_and_type(self, selector: str, text: str, delay_ms: int = 50) -> bool:
        """Clear an input and type new text. Returns True on success."""
        return await self.client.clear_and_type(selector, text, delay_ms)

    async def _send_keys(self, keys: list[str]) -> None:
        """Send keyboard keys (e.g. ['Enter'], ['Tab'])."""
        await self.client.send_keys(keys)

    async def _get_text(self, selector: str) -> Optional[str]:
        """Get visible text of an element."""
        return await self.client.get_text(selector)

    async def _get_value(self, selector: str) -> Optional[str]:
        """Get value of an input element."""
        return await self.client.get_value(selector)

    async def _scroll(self, pixels: int = 800) -> None:
        """Scroll the page."""
        await self.client.scroll(pixels)

    async def _screenshot(self) -> Optional[str]:
        """Capture screenshot. Returns base64 data."""
        return await self.client.screenshot()
