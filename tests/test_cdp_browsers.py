"""
CDP Browser Compatibility Test Suite
Tests Chrome DevTools Protocol connectivity across all Chromium-based browsers.
Firefox and Safari are excluded — they do not support CDP.

Supported: Chrome, Edge, Opera, Opera GX, Brave, Vivaldi
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# ─── Browser Definitions ────────────────────────────────────────────

@dataclass
class BrowserCandidate:
    name: str
    executable: list[str]
    cdp_port: int = 9222
    user_data_dir: Optional[str] = None  # None = use default profile

BROWSERS = [
    BrowserCandidate(
        name="Chrome",
        executable=[
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv("USERNAME", "")),
        ],
    ),
    BrowserCandidate(
        name="Edge",
        executable=[
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
    ),
    BrowserCandidate(
        name="Opera GX",
        executable=[
            r"C:\Users\{}\AppData\Local\Programs\Opera GX\opera.exe".format(os.getenv("USERNAME", "")),
        ],
    ),
    BrowserCandidate(
        name="Opera",
        executable=[
            r"C:\Users\{}\AppData\Local\Programs\Opera\opera.exe".format(os.getenv("USERNAME", "")),
            r"C:\Program Files\Opera\opera.exe",
        ],
    ),
    BrowserCandidate(
        name="Brave",
        executable=[
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Users\{}\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe".format(os.getenv("USERNAME", "")),
        ],
    ),
    BrowserCandidate(
        name="Vivaldi",
        executable=[
            r"C:\Users\{}\AppData\Local\Vivaldi\Application\vivaldi.exe".format(os.getenv("USERNAME", "")),
            r"C:\Program Files\Vivaldi\Application\vivaldi.exe",
        ],
    ),
]


# ─── Helpers ────────────────────────────────────────────────────────

def find_executable(candidate: BrowserCandidate) -> Optional[str]:
    """Return first existing executable path, or None."""
    for path in candidate.executable:
        if os.path.isfile(path):
            return path
    return None


def is_port_open(port: int) -> bool:
    """Check if a TCP port is listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def cdp_http_fetch(port: int, path: str) -> Optional[dict]:
    """Fetch a CDP HTTP endpoint. Returns parsed JSON or None."""
    try:
        url = f"http://127.0.0.1:{port}{path}"
        resp = urllib.request.urlopen(url, timeout=5)
        return json.loads(resp.read())
    except Exception:
        return None


def get_cdp_tabs(port: int = 9222) -> list[dict]:
    """Get list of open tabs via CDP /json endpoint."""
    data = cdp_http_fetch(port, "/json")
    return data if isinstance(data, list) else []


def get_cdp_version(port: int = 9222) -> Optional[dict]:
    """Get browser version info via CDP /json/version."""
    return cdp_http_fetch(port, "/json/version")


def kill_browser_on_port(port: int):
    """Kill any process listening on the given port (Windows)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                pid = line.strip().split()[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid],
                               capture_output=True, timeout=5)
    except Exception:
        pass


# ─── Launch ─────────────────────────────────────────────────────────

def launch_browser(candidate: BrowserCandidate, port: int = 9222,
                   url: str = "about:blank") -> Optional[subprocess.Popen]:
    """
    Launch a Chromium browser with CDP enabled.
    Returns Popen handle or None if executable not found.
    """
    exe = find_executable(candidate)
    if not exe:
        return None

    # Use a temp profile to avoid locking the user's real profile
    if candidate.user_data_dir is None:
        tmp_dir = Path(os.getenv("TEMP", "/tmp")) / f"cdp_test_{candidate.name.lower().replace(' ', '_')}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        user_data_dir = str(tmp_dir)
    else:
        user_data_dir = candidate.user_data_dir

    cmd = [
        exe,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-popup-blocking",
        url,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc


def wait_for_cdp(port: int, timeout: int = 20) -> bool:
    """Wait until CDP is reachable on the given port."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open(port):
            # Give it a moment to fully initialize
            time.sleep(1)
            tabs = get_cdp_tabs(port)
            if tabs is not None:
                return True
        time.sleep(0.5)
    return False


# ─── Test Scenarios ─────────────────────────────────────────────────

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.details = ""
        self.error = ""

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        s = f"[{status}] {self.name}"
        if self.details:
            s += f" — {self.details}"
        if self.error:
            s += f" (error: {self.error})"
        return s


def test_discovery() -> list[tuple[BrowserCandidate, str]]:
    """Test 1: Discover which browsers are installed."""
    results = []
    for candidate in BROWSERS:
        exe = find_executable(candidate)
        if exe:
            results.append((candidate, exe))
    return results


def test_cdp_port_binding(candidate: BrowserCandidate, exe: str,
                          port: int = 9222) -> TestResult:
    """Test 2: Browser launches with CDP port open."""
    result = TestResult(f"{candidate.name}: CDP port binding")

    # Kill anything on the port first
    kill_browser_on_port(port)
    time.sleep(1)

    proc = launch_browser(candidate, port)
    if proc is None:
        result.error = "Failed to launch"
        return result

    try:
        ok = wait_for_cdp(port, timeout=20)
        if ok:
            result.passed = True
            result.details = f"Port {port} listening, PID {proc.pid}"
        else:
            result.error = "Port never opened within timeout"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        kill_browser_on_port(port)

    return result


def test_cdp_version(candidate: BrowserCandidate, exe: str,
                     port: int = 9222) -> TestResult:
    """Test 3: CDP /json/version returns valid browser info."""
    result = TestResult(f"{candidate.name}: CDP version info")

    kill_browser_on_port(port)
    time.sleep(1)

    proc = launch_browser(candidate, port)
    if proc is None:
        result.error = "Failed to launch"
        return result

    try:
        if not wait_for_cdp(port):
            result.error = "CDP never became available"
            return result

        version = get_cdp_version(port)
        if version and "Browser" in version:
            result.passed = True
            result.details = version["Browser"]
        else:
            result.error = f"Unexpected version response: {version}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        kill_browser_on_port(port)

    return result


def test_cdp_list_tabs(candidate: BrowserCandidate, exe: str,
                       port: int = 9222) -> TestResult:
    """Test 4: CDP /json returns list of open tabs."""
    result = TestResult(f"{candidate.name}: CDP tab listing")

    kill_browser_on_port(port)
    time.sleep(1)

    proc = launch_browser(candidate, port, url="about:blank")
    if proc is None:
        result.error = "Failed to launch"
        return result

    try:
        if not wait_for_cdp(port):
            result.error = "CDP never became available"
            return result

        tabs = get_cdp_tabs(port)
        page_tabs = [t for t in tabs if t.get("type") == "page"]
        if page_tabs:
            result.passed = True
            result.details = f"{len(page_tabs)} tab(s): {page_tabs[0].get('title', 'untitled')}"
        else:
            result.error = f"No page tabs found in {len(tabs)} targets"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        kill_browser_on_port(port)

    return result


def test_cdp_websocket(candidate: BrowserCandidate, exe: str,
                       port: int = 9222) -> TestResult:
    """Test 5: Can connect via WebSocket and evaluate JS."""
    result = TestResult(f"{candidate.name}: CDP WebSocket + JS eval")

    kill_browser_on_port(port)
    time.sleep(1)

    proc = launch_browser(candidate, port)
    if proc is None:
        result.error = "Failed to launch"
        return result

    try:
        if not wait_for_cdp(port):
            result.error = "CDP never became available"
            return result

        tabs = get_cdp_tabs(port)
        page_tabs = [t for t in tabs if t.get("type") == "page"]
        if not page_tabs:
            result.error = "No page tabs"
            return result

        ws_url = page_tabs[0].get("webSocketDebuggerUrl", "")
        if not ws_url:
            result.error = "No WebSocket URL"
            return result

        import websockets
        import asyncio

        async def eval_js():
            async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
                msg = json.dumps({
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": "navigator.userAgent",
                        "returnByValue": True,
                    },
                })
                await ws.send(msg)
                resp = json.loads(await ws.recv())
                return resp.get("result", {}).get("result", {}).get("value", "")

        ua = asyncio.run(eval_js())
        if ua:
            result.passed = True
            result.details = f"UA: {ua[:80]}"
        else:
            result.error = "Empty user agent response"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        kill_browser_on_port(port)

    return result


def test_cdp_navigate(candidate: BrowserCandidate, exe: str,
                      port: int = 9222) -> TestResult:
    """Test 6: Can navigate to a URL via CDP."""
    result = TestResult(f"{candidate.name}: CDP navigation")

    kill_browser_on_port(port)
    time.sleep(1)

    proc = launch_browser(candidate, port)
    if proc is None:
        result.error = "Failed to launch"
        return result

    try:
        if not wait_for_cdp(port):
            result.error = "CDP never became available"
            return result

        tabs = get_cdp_tabs(port)
        page_tabs = [t for t in tabs if t.get("type") == "page"]
        if not page_tabs:
            result.error = "No page tabs"
            return result

        ws_url = page_tabs[0].get("webSocketDebuggerUrl", "")
        if not ws_url:
            result.error = "No WebSocket URL"
            return result

        import websockets
        import asyncio

        async def navigate():
            async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
                # Navigate
                await ws.send(json.dumps({
                    "id": 1,
                    "method": "Page.navigate",
                    "params": {"url": "https://www.example.com"},
                }))
                resp = json.loads(await ws.recv())
                # Wait for load
                time.sleep(3)
                # Get current URL
                await ws.send(json.dumps({
                    "id": 2,
                    "method": "Runtime.evaluate",
                    "params": {"expression": "location.href", "returnByValue": True},
                }))
                resp2 = json.loads(await ws.recv())
                return resp2.get("result", {}).get("result", {}).get("value", "")

        url = asyncio.run(navigate())
        if url and "example.com" in url:
            result.passed = True
            result.details = f"Navigated to {url}"
        else:
            result.error = f"Navigation failed, current URL: {url}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        kill_browser_on_port(port)

    return result


# ─── Non-Chromium (negative tests) ─────────────────────────────────

def test_firefox_no_cdp() -> TestResult:
    """Test: Firefox does NOT support CDP (expected failure)."""
    result = TestResult("Firefox: CDP unsupported (expected)")

    firefox_paths = [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ]
    exe = None
    for p in firefox_paths:
        if os.path.isfile(p):
            exe = p
            break

    if not exe:
        result.details = "Firefox not installed — skip"
        result.passed = True  # Not a failure, just not applicable
        return result

    # Try to launch Firefox with CDP flag (it will ignore it)
    proc = subprocess.Popen(
        [exe, "--remote-debugging-port=9222", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(5)
        if is_port_open(9222):
            result.error = "Port 9222 opened — unexpected! Firefox should not support CDP"
        else:
            result.passed = True
            result.details = "Port 9222 not opened — CDP correctly unsupported"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    return result


def test_safari_no_cdp() -> TestResult:
    """Test: Safari does NOT support CDP (expected failure)."""
    result = TestResult("Safari: CDP unsupported (expected)")
    # Safari is macOS-only, so on Windows this is always N/A
    if sys.platform != "darwin":
        result.passed = True
        result.details = "Safari not available on Windows — N/A"
    return result


# ─── Runner ─────────────────────────────────────────────────────────

def run_all_tests(port: int = 9222) -> list[TestResult]:
    """Run the full test suite."""
    all_results: list[TestResult] = []

    # 1. Discovery
    installed = test_discovery()
    print(f"\n{'='*60}")
    print(f"  CDP Browser Compatibility Test Suite")
    print(f"{'='*60}")
    print(f"\n  Discovered {len(installed)} Chromium browser(s):")
    for cand, exe in installed:
        print(f"    - {cand.name}: {exe}")

    if not installed:
        print("  No Chromium browsers found. Tests cannot proceed.")
        return all_results

    # 2. Run tests per browser
    for cand, exe in installed:
        print(f"\n{'─'*60}")
        print(f"  Testing: {cand.name}")
        print(f"{'─'*60}")

        tests = [
            test_cdp_port_binding,
            test_cdp_version,
            test_cdp_list_tabs,
            test_cdp_websocket,
            test_cdp_navigate,
        ]

        for test_fn in tests:
            print(f"  Running: {test_fn.__doc__.strip()} ...", end=" ", flush=True)
            result = test_fn(cand, exe, port)
            all_results.append(result)
            print(result)

    # 3. Negative tests
    print(f"\n{'─'*60}")
    print(f"  Negative tests (non-Chromium)")
    print(f"{'─'*60}")

    neg_tests = [test_firefox_no_cdp, test_safari_no_cdp]
    for test_fn in neg_tests:
        print(f"  Running: {test_fn.__doc__.strip()} ...", end=" ", flush=True)
        result = test_fn()
        all_results.append(result)
        print(result)

    # 4. Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed)
    print(f"  Passed: {passed}/{len(all_results)}")
    print(f"  Failed: {failed}/{len(all_results)}")
    if failed:
        print(f"\n  Failed tests:")
        for r in all_results:
            if not r.passed:
                print(f"    {r}")
    print(f"{'='*60}\n")

    return all_results


if __name__ == "__main__":
    run_all_tests()
