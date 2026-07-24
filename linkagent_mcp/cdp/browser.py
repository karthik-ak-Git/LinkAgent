"""
Browser discovery and management for CDP connections.

Works with any Chromium browser (Chrome, Edge, Opera, Brave, Vivaldi).
No site-specific logic — use find_tab(domain) for any website.
"""

import json
import os
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass
class Tab:
    """Represents a browser tab."""
    id: str
    title: str
    url: str
    ws_url: str
    type: str = "page"


@dataclass
class Browser:
    """Represents a discovered browser."""
    name: str
    executable: str
    port: int


# Chromium browser paths (Windows)
BROWSER_PATHS = [
    Browser(name="Chrome", executable=r"C:\Program Files\Google\Chrome\Application\chrome.exe", port=9222),
    Browser(name="Chrome", executable=r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", port=9222),
    Browser(name="Chrome", executable=os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"), port=9222),
    Browser(name="Edge", executable=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", port=9222),
    Browser(name="Edge", executable=r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", port=9222),
    Browser(name="Opera GX", executable=os.path.expanduser(r"~\AppData\Local\Programs\Opera GX\opera.exe"), port=9222),
    Browser(name="Opera", executable=os.path.expanduser(r"~\AppData\Local\Programs\Opera\opera.exe"), port=9222),
    Browser(name="Brave", executable=r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe", port=9222),
    Browser(name="Brave", executable=os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"), port=9222),
    Browser(name="Vivaldi", executable=os.path.expanduser(r"~\AppData\Local\Vivaldi\Application\vivaldi.exe"), port=9222),
]


class BrowserManager:
    """Manages CDP connections to Chromium browsers."""

    def __init__(self, cdp_port: int = 9222):
        self.cdp_port = cdp_port
        self._base_url = f"http://127.0.0.1:{cdp_port}"

    def is_cdp_available(self) -> bool:
        """Check if CDP is available on the configured port."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                if s.connect_ex(("127.0.0.1", self.cdp_port)) != 0:
                    return False
            resp = urllib.request.urlopen(f"{self._base_url}/json/version", timeout=5)
            data = json.loads(resp.read())
            return "Browser" in data
        except Exception:
            return False

    def get_version(self) -> Optional[dict]:
        """Get browser version info from CDP."""
        try:
            resp = urllib.request.urlopen(f"{self._base_url}/json/version", timeout=5)
            return json.loads(resp.read())
        except Exception:
            return None

    def get_tabs(self) -> list[Tab]:
        """Get all open tabs from CDP."""
        try:
            resp = urllib.request.urlopen(f"{self._base_url}/json", timeout=5)
            data = json.loads(resp.read())
            tabs = []
            for t in data:
                if t.get("type") == "page":
                    tabs.append(Tab(
                        id=t["id"],
                        title=t.get("title", ""),
                        url=t.get("url", ""),
                        ws_url=t.get("webSocketDebuggerUrl", ""),
                    ))
            return tabs
        except Exception:
            return []

    def get_any_tab(self) -> Optional[Tab]:
        """Get any available browser tab."""
        tabs = self.get_tabs()
        return tabs[0] if tabs else None

    def find_tab(self, domain: str) -> Optional[Tab]:
        """
        Find a tab whose URL contains the given domain string.

        Examples:
            find_tab("linkedin.com")
            find_tab("twitter.com")
            find_tab("github.com")
        """
        for tab in self.get_tabs():
            if domain in tab.url:
                return tab
        return None

    def launch(self, url: str = "about:blank", use_temp_profile: bool = True) -> Optional[subprocess.Popen]:
        """
        Launch a Chromium browser with CDP enabled.
        Returns Popen handle or None if no browser found.
        """
        browser = self._find_installed_browser()
        if not browser:
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
            tmp_dir = os.path.join(tempfile.gettempdir(), f"linkagent_{browser.name.lower().replace(' ', '_')}")
            os.makedirs(tmp_dir, exist_ok=True)
            cmd.append(f"--user-data-dir={tmp_dir}")

        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def wait_for_cdp(self, timeout: int = 20) -> bool:
        """Wait until CDP becomes available."""
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
        for browser in BROWSER_PATHS:
            if browser.name in seen:
                continue
            if os.path.isfile(browser.executable):
                seen.add(browser.name)
                return browser
        return None

    def list_installed_browsers(self) -> list[Browser]:
        """List all installed Chromium browsers."""
        result = []
        seen = set()
        for browser in BROWSER_PATHS:
            if browser.name not in seen and os.path.isfile(browser.executable):
                seen.add(browser.name)
                result.append(browser)
        return result
