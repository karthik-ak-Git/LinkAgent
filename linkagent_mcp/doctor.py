from __future__ import annotations

from typing import Any


def browser_doctor(browser_manager, requested_browser: str | None = None) -> dict[str, Any]:
    """Read-only browser health report.

    This follows Agent Reach's doctor pattern: inspect the real runtime, do not
    start a browser, and never claim that credentials/cookies were inspected.
    """
    installed = [
        {"name": item.name, "executable": item.executable, "port": item.port}
        for item in browser_manager.list_installed_browsers()
    ]
    version = browser_manager.get_version() or {}
    cdp_available = bool(version)
    detected = str(version.get("Browser") or "")
    requested = (requested_browser or "").strip().lower() or None
    selected = None
    if requested:
        selected = next((item for item in installed if item["name"].casefold() == requested), None)
    elif cdp_available:
        selected = next((item for item in installed if item["name"].casefold() in detected.casefold()), None)

    issues: list[str] = []
    if requested and not selected:
        issues.append(f"Requested browser is not installed: {requested}")
    if not cdp_available:
        issues.append("No CDP endpoint is available on the configured host/port")
    if cdp_available and not detected:
        issues.append("CDP responded without a browser identity")

    return {
        "selected_browser": selected["name"].casefold() if selected else requested,
        "detected_browser": detected or None,
        "requested_browser": requested,
        "installed_browsers": installed,
        "cdp_available": cdp_available,
        "browser_profile_mode": "existing_regular" if cdp_available else "unavailable",
        "credentials": "not_inspected",
        "background_tabs_supported": cdp_available,
        "incognito_requires_explicit_user_request": True,
        "issues": issues,
        "next_action": (
            "Use the selected browser with Start-LinkAgent.ps1 -Browser <name>; "
            "create_hidden_tab reuses the regular session."
            if issues
            else "Ready: use create_hidden_tab for background work in the attached regular session."
        ),
    }
