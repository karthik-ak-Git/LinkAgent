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

    async def _scroll(self, pixels: int = 800) -> None:
        """Scroll the page."""
        await self.client.scroll(pixels)

    async def _screenshot(self) -> Optional[str]:
        """Capture screenshot. Returns base64 data."""
        return await self.client.screenshot()
