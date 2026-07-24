"""
Base class for all LinkedIn page extractors.
"""

from abc import ABC, abstractmethod
from typing import Any

from ..cdp.client import CDPClient


class BaseExtractor(ABC):
    """
    Base class for LinkedIn page extractors.

    Each extractor:
    - Takes a CDPClient connected to a tab
    - Executes JavaScript to extract structured data
    - Returns a typed dataclass result
    """

    def __init__(self, client: CDPClient):
        self.client = client

    @abstractmethod
    async def extract(self, **kwargs) -> dict:
        """
        Extract data from the current page.
        Returns a dictionary with extracted data.
        """
        pass

    async def _eval(self, js: str) -> Any:
        """Shortcut to evaluate JavaScript via CDP."""
        return await self.client.evaluate(js)

    async def _get_url(self) -> str:
        """Get current page URL."""
        return await self.client.get_url()

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
