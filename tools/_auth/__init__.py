"""Private infrastructure: authentication, cookie store, session health.

Bridges to linkedin-mcp-server's auth and session management.
Will be refactored into standalone modules.
"""

from __future__ import annotations

from typing import Any


async def get_authenticated_extractor():
    """Get a ready LinkedInExtractor with validated auth session."""
    from linkedin_mcp_server.dependencies import get_ready_extractor
    from tools._browser import get_browser

    browser = await get_browser()

    from linkedin_mcp_server.scraping import LinkedInExtractor

    if not hasattr(browser, "_extractor") or browser._extractor is None:
        browser._extractor = LinkedInExtractor(browser)
    return browser._extractor


async def ensure_authenticated() -> None:
    """Confirm the shared browser completed startup authentication."""
    from linkedin_mcp_server.drivers.browser import ensure_authenticated as _ensure
    await _ensure()


def validate_session() -> bool:
    """Check whether startup authentication has already succeeded."""
    from linkedin_mcp_server.drivers.browser import validate_session as _validate
    return _validate()
