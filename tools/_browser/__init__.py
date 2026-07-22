"""Private infrastructure: browser lifecycle and management.

Bridges to linkedin-mcp-server's BrowserManager singleton.
Will be refactored into standalone modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def get_browser(headless: bool | None = None):
    """Get or create the singleton browser instance."""
    from linkedin_mcp_server.drivers.browser import get_or_create_browser
    return get_or_create_browser(headless=headless)


async def close_browser() -> None:
    """Close the browser and clean up resources."""
    from linkedin_mcp_server.drivers.browser import close_browser as _close
    await _close()


def get_profile_dir() -> Path:
    """Get the resolved profile directory."""
    from linkedin_mcp_server.drivers.browser import get_profile_dir as _get
    return _get()
