"""
CDP (Chrome DevTools Protocol) client and browser management.

Provides low-level access to Chromium browser tabs for JavaScript
evaluation, navigation, and screenshot capture.
"""

from .client import CDPClient
from .browser import BrowserManager, Tab, Browser

__all__ = ["CDPClient", "BrowserManager", "Tab", "Browser"]
