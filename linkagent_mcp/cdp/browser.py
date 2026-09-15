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
    incognito: bool = False
    hidden: bool = False


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

    # ── Browser-level WebSocket (for target/window management) ──

    def get_browser_ws_url(self) -> Optional[str]:
        """Get the browser-level WebSocket URL from /json/version.

        This URL is needed for browser-level CDP commands like
        Target.createTarget, Target.getTargets, Browser.createWindow, etc.

        Returns:
            The WebSocket URL string, or None if CDP is unavailable.
        """
        try:
            resp = urllib.request.urlopen(f"{self._base_url}/json/version", timeout=5)
            data = json.loads(resp.read())
            ws_url = data.get("webSocketDebuggerUrl")
            if ws_url:
                logger.debug("Browser WS URL: %s", ws_url)
            return ws_url
        except Exception as e:
            logger.debug("Failed to get browser WS URL: %s", e)
            return None

    def _make_page_ws_url(self, target_id: str) -> str:
        """Construct a page-level WebSocket URL for the given target ID."""
        return f"ws://{self.cdp_host}:{self.cdp_port}/devtools/page/{target_id}"

    # ── Hidden tab tracking (instance-level, not class shared) ──
    def __init__(self, cdp_host: str = "127.0.0.1", cdp_port: int = 9222):
        self.cdp_host = cdp_host
        self.cdp_port = cdp_port
        self._base_url = f"http://{cdp_host}:{cdp_port}"
        self._browser_paths = _get_browser_paths()
        self._hidden_tabs: dict[str, Tab] = {}
        self._session_ownership: dict[str, str] = {}  # target_id -> "user" | "agent"

    # Keep old __init__ compat via override - already defined above

    # ── Target/window management ──

    async def create_hidden_tab(self, url: str = "about:blank") -> Optional[Tab]:
        """Create a new hidden (background) tab for extraction work.

        The tab is created in the background — it won't steal focus or
        appear visibly to the user. Uses the same browser context/session
        as existing tabs (same cookies, auth state).

        Args:
            url: Initial URL to load in the new tab.

        Returns:
            Tab object for the new hidden tab, or None on failure.
        """
        browser_ws = self.get_browser_ws_url()
        if not browser_ws:
            logger.warning("Cannot create hidden tab: browser WS URL unavailable")
            return None

        from .client import CDPClient
        client = CDPClient(browser_ws)
        await client.connect()
        try:
            result = await client.create_target(url=url, background=True)
            target_id = result.get("result", {}).get("targetId")
            if not target_id:
                logger.error("create_target returned no targetId")
                return None

            ws_url = self._make_page_ws_url(target_id)
            tab = Tab(
                id=target_id,
                title="",
                url=url,
                ws_url=ws_url,
                type="page",
                incognito=False,
                hidden=True,
            )
            self._hidden_tabs[target_id] = tab
            logger.info("Created hidden tab %s for %s", target_id[:8], url)
            return tab
        finally:
            await client.disconnect()

    async def create_incognito_tab(self, url: str = "about:blank") -> Optional[Tab]:
        """Create a new incognito window with a tab.

        The new window has its own browser context — cookies, storage,
        and auth state are completely separate from the main browser session.

        Args:
            url: Initial URL to load.

        Returns:
            Tab object for the incognito tab, or None on failure.
        """
        browser_ws = self.get_browser_ws_url()
        if not browser_ws:
            logger.warning("Cannot create incognito tab: browser WS URL unavailable")
            return None

        from .client import CDPClient
        client = CDPClient(browser_ws)
        await client.connect()
        try:
            window_result = await client.create_window(url=url, incognito=True)
            window_id = window_result.get("result", {}).get("windowId")
            if not window_id:
                logger.error("create_window returned no windowId")
                return None

            targets = await client.get_targets()
            target_id = None
            for t in targets:
                if t.get("type") == "page" and (
                    t.get("url", "") == url or (url == "about:blank" and t.get("url", "") == "about:blank")
                ):
                    target_id = t["targetId"]
                    break
            if not target_id:
                logger.error("Could not find target for new incognito window")
                return None

            ws_url = self._make_page_ws_url(target_id)
            tab = Tab(
                id=target_id,
                title="",
                url=url,
                ws_url=ws_url,
                type="page",
                incognito=True,
                hidden=False,
            )
            logger.info("Created incognito tab %s for %s", target_id[:8], url)
            return tab
        finally:
            await client.disconnect()

    async def close_tab(self, target_id: str) -> bool:
        """Close a tab (or any target) by its target ID.

        Args:
            target_id: The target ID to close.

        Returns:
            True if closed successfully, False otherwise.
        """
        if target_id in self._hidden_tabs:
            del self._hidden_tabs[target_id]

        browser_ws = self.get_browser_ws_url()
        if not browser_ws:
            return False

        from .client import CDPClient
        client = CDPClient(browser_ws)
        try:
            await client.connect()
            await client.close_target(target_id)
            logger.info("Closed tab %s", target_id[:8])
            return True
        except Exception as e:
            logger.warning("Failed to close tab %s: %s", target_id[:8], e)
            return False
        finally:
            await client.disconnect()

    def get_hidden_tabs(self) -> list[Tab]:
        """Get all hidden tabs that were created by LinkAgent.

        Returns:
            List of Tab objects for currently tracked hidden tabs.
        """
        return list(self._hidden_tabs.values())

    async def get_tabs_extended(self) -> list[Tab]:
        """Get all available tabs with enhanced info (incognito, hidden).

        Combines tabs from the standard /json endpoint (visible, non-incognito)
        with any hidden tabs created by LinkAgent. Also attempts to detect
        incognito tabs via the browser-level Target.getTargets.

        Returns:
            List of Tab objects with incognito and hidden flags populated.
        """
        visible_tabs = self.get_tabs()

        tabs = list(visible_tabs)

        hidden_tabs = self.get_hidden_tabs()
        for t in hidden_tabs:
            if not any(t.id == vt.id for vt in tabs):
                tabs.append(t)

        browser_ws = self.get_browser_ws_url()
        if browser_ws:
            try:
                from .client import CDPClient
                client = CDPClient(browser_ws)
                await client.connect()
                try:
                    all_targets = await client.get_targets()
                    incognito_target_ids: set[str] = set()
                    contexts_seen: set[str] = set()
                    default_context_id = None
                    for t in all_targets:
                        ctx = t.get("browserContextId")
                        if ctx:
                            if default_context_id is None:
                                default_context_id = ctx
                            elif ctx != default_context_id:
                                incognito_target_ids.add(t["targetId"])

                    for tab in tabs:
                        if tab.id in incognito_target_ids:
                            object.__setattr__(tab, "incognito", True)
                finally:
                    await client.disconnect()
            except Exception as e:
                logger.debug("Failed to enhance tab info: %s", e)

        return tabs

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
