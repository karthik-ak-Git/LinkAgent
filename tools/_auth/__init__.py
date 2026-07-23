"""Private infrastructure: authentication, cookie store, session health.

Bridges to linkedin-mcp-server's auth and session management.
Will be refactored into standalone modules (see OPTIMIZATION_PLAN.md Phase 9).

Official auth flow (mirrors dependencies.get_ready_extractor):
  1. ensure_tool_ready_or_raise  — bootstrap gate (browser setup + auth check)
  2. get_or_create_browser       — singleton browser manager
  3. ensure_authenticated        — quick /feed/ validation
  4. LinkedInExtractor(browser.page) — extractor with Playwright Page
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from linkedin_mcp_server.scraping import LinkedInExtractor


async def get_authenticated_extractor(
    ctx: Context | None = None,
    *,
    tool_name: str = "unknown",
) -> LinkedInExtractor:  # type: ignore[name-defined]
    """Get a ready LinkedInExtractor with validated auth session.

    Args:
        ctx: FastMCP context (optional — used for progress reporting).
        tool_name: Name of the calling tool for diagnostics.

    Returns:
        LinkedInExtractor bound to an authenticated Playwright page.

    Raises:
        AuthenticationError: Session expired, triggers re-login flow.
        BrowserSetupInProgressError: Browser still installing.
        Various bootstrap errors per bootstrap.ensure_tool_ready_or_raise.
    """
    from linkedin_mcp_server.bootstrap import ensure_tool_ready_or_raise
    from linkedin_mcp_server.drivers.browser import (
        ensure_authenticated,
        get_or_create_browser,
    )
    from linkedin_mcp_server.scraping import LinkedInExtractor

    await ensure_tool_ready_or_raise(tool_name, ctx)
    browser = await get_or_create_browser()
    await ensure_authenticated()
    return LinkedInExtractor(browser.page)


async def ensure_authenticated_session() -> None:
    """Confirm the shared browser completed startup authentication."""
    from linkedin_mcp_server.drivers.browser import ensure_authenticated as _ensure

    await _ensure()


def validate_session_available() -> bool:
    """Check whether startup authentication has already succeeded."""
    from linkedin_mcp_server.drivers.browser import validate_session as _validate

    return _validate()
