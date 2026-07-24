"""
Browser discovery and CDP connection management.

Supports any Chromium-based browser: Chrome, Edge, Opera, Brave, Vivaldi.
Cross-platform: Windows, macOS, Linux.

The BrowserManager handles:
- Discovering installed browsers on the system
- Launching browsers with CDP enabled
- Finding tabs by domain for site-specific extraction
- Managing the CDP WebSocket connection lifecycle
"""

import json
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional

from ..logging import get_logger

logger = get_logger("cdp.browser")


@dataclass(frozen=True)
class Tab:
    """Represents a browser tab with CDP access."""

    id: str
    title: str
    url: str
    ws_url: str
    type: str = "page"


@dataclass(frozen=True)
class Browser:
    """Represents a discovered Chromium browser installation."""

    name: str
    executable: str
    port: int


def _get_browser_paths() -> list[Browser]:
    """
    Get platform-specific Chromium browser paths.

    Returns:
        List of Browser instances with discovered executable paths.
    """
    system = platform.system()
    paths = []

    if system == "Windows":
        paths = [
            Browser("Chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe", 9222),
            Browser("Chrome", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", 9222),
            Browser("Chrome", os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"), 9222),
            Browser("Edge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", 9222),
            Browser("Edge", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", 9222),
            Browser("Opera GX", os.path.expanduser(r"~\AppData\Local\Programs\Opera GX\opera.exe"), 9222),
            Browser("Opera", os.path.expanduser(r"~\AppData\Local\Programs\Opera\opera.exe"), 9222),
            Browser("Brave", r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe", 9222),
            Browser("Brave", os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"), 9222),
            Browser("Vivaldi", os.path.expanduser(r"~\AppData\Local\Vivaldi\Application\vivaldi.exe"), 9222),
        ]
    elif system == "Darwin":
        home = os.path.expanduser("~")
        paths = [
            Browser("Chrome", f"{home}/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", 9222),
            Browser("Chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", 9222),
            Browser("Edge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", 9222),
            Browser("Opera", f"{home}/Applications/Opera.app/Contents/MacOS/Opera", 9222),
            Browser("Opera", "/Applications/Opera.app/Contents/MacOS/Opera", 9222),
            Browser("Brave", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser", 9222),
            Browser("Vivaldi", "/Applications/Vivaldi.app/Contents/MacOS/Vivaldi", 9222),
        ]
    elif system == "Linux":
        paths = [
            Browser("Chrome", "/usr/bin/google-chrome", 9222),
            Browser("Chrome", "/usr/bin/google-chrome-stable", 9222),
            Browser("Chrome", "/snap/bin/chromium", 9222),
            Browser("Edge", "/usr/bin/microsoft-edge", 9222),
            Browser("Opera", "/usr/bin/opera", 9222),
            Browser("Brave", "/usr/bin/brave-browser", 9222),
            Browser("Vivaldi", "/usr/bin/vivaldi", 9222),
        ]

    return paths


class BrowserManager:
    """
    Manages CDP connections to Chromium browsers.

    Discovers installed browsers, finds tabs by domain, and provides
    the CDP WebSocket URLs needed for remote JavaScript evaluation.

    Usage:
        manager = BrowserManager(cdp_port=9222)
        if manager.is_cdp_available():
            tab = manager.find_tab("linkedin.com")
            if tab:
                client = CDPClient(tab.ws_url)
    """

    def __init__(self, cdp_host: str = "127.0.0.1", cdp_port: int = 9222):
        """
        Initialize the browser manager.

        Args:
            cdp_host: Host address for CDP connections.
            cdp_port: Port number for Chrome DevTools Protocol.
        """
        self.cdp_host = cdp_host
        self.cdp_port = cdp_port
        self._base_url = f"http://{cdp_host}:{cdp_port}"
        self._browser_paths = _get_browser_paths()

    def is_cdp_available(self) -> bool:
        """
        Check if CDP is available on the configured host:port.

        Returns:
            True if a CDP-compatible browser is listening.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                if s.connect_ex((self.cdp_host, self.cdp_port)) != 0:
                    return False
            resp = urllib.request.urlopen(f"{self._base_url}/json/version", timeout=5)
            data = json.loads(resp.read())
            return "Browser" in data
        except Exception:
            return False

    def get_version(self) -> Optional[dict]:
        """
        Get browser version info from CDP.

        Returns:
            Dict with Browser, webSocketDebuggerUrl, etc., or None.
        """
        try:
            resp = urllib.request.urlopen(f"{self._base_url}/json/version", timeout=5)
            return json.loads(resp.read())
        except Exception:
            return None

    def get_tabs(self) -> list[Tab]:
        """
        Get all open browser tabs.

        Returns:
            List of Tab objects for each open page.
        """
        try:
            resp = urllib.request.urlopen(f"{self._base_url}/json", timeout=5)
            data = json.loads(resp.read())
            return [
                Tab(
                    id=t["id"],
                    title=t.get("title", ""),
                    url=t.get("url", ""),
                    ws_url=t.get("webSocketDebuggerUrl", ""),
                )
                for t in data
                if t.get("type") == "page"
            ]
        except Exception:
            return []

    def get_any_tab(self) -> Optional[Tab]:
        """Get any available browser tab."""
        tabs = self.get_tabs()
        return tabs[0] if tabs else None

    def find_tab(self, domain: str) -> Optional[Tab]:
        """
        Find a tab whose URL contains the given domain string.

        This is the primary method for site-specific extraction —
        it locates the browser tab that has the target site open.

        Args:
            domain: Domain to search for (e.g. "linkedin.com", "twitter.com").

        Returns:
            Matching Tab, or None if no tab has that domain open.

        Examples:
            find_tab("linkedin.com")
            find_tab("github.com")
            find_tab("docs.python.org")
        """
        for tab in self.get_tabs():
            if domain in tab.url:
                logger.debug("Found tab for %s: %s", domain, tab.url)
                return tab
        logger.debug("No tab found for domain: %s", domain)
        return None

    def launch(
        self,
        url: str = "about:blank",
        use_temp_profile: bool = True,
    ) -> Optional[subprocess.Popen]:
        """
        Launch a Chromium browser with CDP enabled.

        Args:
            url: Initial URL to open.
            use_temp_profile: If True, use a temporary user data directory.

        Returns:
            Popen handle for the browser process, or None if no browser found.
        """
        browser = self._find_installed_browser()
        if not browser:
            logger.warning("No Chromium browser found on this system")
            return None

        cmd = [
            browser.executable,
            f"--remote-debugging-port={self.cdp_port}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            url,
        ]

        if use_temp_profile:
            import tempfile
            tmp_dir = os.path.join(
                tempfile.gettempdir(),
                f"linkagent_{browser.name.lower().replace(' ', '_')}",
            )
            os.makedirs(tmp_dir, exist_ok=True)
            cmd.append(f"--user-data-dir={tmp_dir}")

        logger.info("Launching %s with CDP on port %d", browser.name, self.cdp_port)
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def wait_for_cdp(self, timeout: int = 20) -> bool:
        """
        Block until CDP becomes available or timeout.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            True if CDP became available, False on timeout.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_cdp_available():
                time.sleep(0.5)
                return True
            time.sleep(0.5)
        return False

    def _find_installed_browser(self) -> Optional[Browser]:
        """Find the first installed Chromium browser."""
        seen = set()
        for browser in self._browser_paths:
            if browser.name in seen:
                continue
            if os.path.isfile(browser.executable):
                seen.add(browser.name)
                return browser
        return None

    def list_installed_browsers(self) -> list[Browser]:
        """
        List all installed Chromium browsers found on the system.

        Returns:
            List of Browser objects with name and path.
        """
        result = []
        seen = set()
        for browser in self._browser_paths:
            if browser.name not in seen and os.path.isfile(browser.executable):
                seen.add(browser.name)
                result.append(browser)
        return result
