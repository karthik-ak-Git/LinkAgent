# LinkedIn Cookie & Fingerprint Architecture

## Executive Summary
LinkedIn does **not** use traditional API keys. Auth is entirely **cookie-based** with **client fingerprint validation** via periodic tracking calls. The MCP server is a browser scraper — it drives Chromium via Playwright, injects cookies, and reads rendered HTML.

---

## Cookie Set (from HAR + Code)

| Cookie | Purpose | Lifetime | Source |
|--------|---------|----------|--------|
| `li_at` | Primary session token | ~1 year | Login / cookie import |
| `JSESSIONID` | Server-side session ID | Session | Login |
| `bcookie` | Browser ID (persistent) | 2 years | First visit |
| `bscookie` | Secure browser ID | 2 years | First visit |
| `lidc` | Load balancer routing | 1 day | Each response |
| `li_rm` | Remember me | ~1 year | "Remember me" login |
| `liap` | Login auth token | Session | Login |
| `li_gc` | Guest conversion | Session | Guest→auth transition |
| `lang` | Language preference | Persistent | User setting |
| `timezone` | Timezone offset | Persistent | User setting |
| `li_mc` | Marketing consent | Persistent | User setting |

**Storage locations** (from `session_state.py`):
- `~/.linkedin-mcp/profile/` — Playwright persistent context
- `~/.linkedin-mcp/cookies.json` — Exported cookie jar
- `~/.linkedin-mcp/source-state.json` — Source metadata
- `~/.linkedin-mcp/runtime-profiles/<runtime-id>/` — Per-runtime profiles

---

## Fingerprint Validation (Critical)

### Tracking Endpoints by Auth State

| State | Endpoint | Interval | Cookies Sent |
|-------|----------|----------|--------------|
| Guest | `li/track` | ~2s | **None** |
| Authenticated | `trackingApiService/track` | 7-15s | **Full jar** |
| Authenticated (profile) | + `trackO11yApi/trackO11y`, `trackLixApi/trackLix` | Burst on unload | **Full jar** |

### Required `userRequestHeaderContext` Fields

```json
{
  "theme": 1,
  "interfaceLocale": "en_US",
  "isBrowserPersistentRetryEnabled": true,
  "isFlushOnCloseBrowserTabEnabled": true,
  "clientDeviceType": 1,
  "timeZoneOffsetMinutes": 330
}
```

| Field | Value | Playwright Setting |
|-------|-------|-------------------|
| `theme` | 1=light, 2=dark | `color_scheme: "light"` |
| `interfaceLocale` | e.g., `en_US` | `locale: "en-US"` |
| `clientDeviceType` | 1=desktop, 2=mobile | `user_agent` + `viewport` |
| `timeZoneOffsetMinutes` | e.g., 330 (IST) | `timezone_id: "Asia/Kolkata"` |
| `isBrowserPersistentRetryEnabled` | true | N/A (behavioral) |
| `isFlushOnCloseBrowserTabEnabled` | true | N/A (behavioral) |

**Mismatch = soft ban / checkpoint / auth wall.**

---

## Playwright Context Configuration

```python
context = await browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    viewport={"width": 1920, "height": 1080},
    locale="en-US",
    timezone_id="Asia/Kolkata",
    color_scheme="light",
    # ... other settings
)
await context.add_cookies(cookies)  # Full jar from CookieStore
```

---

## Cookie Acquisition Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Google OAuth   │────▶│  LinkedIn SSO    │────▶│  Cookie Jar     │
│  (browser_import)│     │  (auto-handled)  │     │  (li_at + all)  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                               ┌──────────────────┐
                                               │  Persist to      │
                                               │  ~/.linkedin-mcp/│
                                               │  + runtime-profile│
                                               └────────┬─────────┘
                                                        │
                                                        ▼
                                               ┌──────────────────┐
                                               │  Playwright      │
                                               │  Context +       │
                                               │  Fingerprint     │
                                               └──────────────────┘
```

**Existing code**: `browser_import/orchestrate.py` → `run_browser_import()` → `_cookie_bridge()` → `extract.py` reads Chrome's SQLite `Network/Cookies` DB.

---

## Cookie Replay Strategy

### Health Check (before each session)
```python
async def health_check(context) -> bool:
    response = await context.request.get("https://www.linkedin.com/feed/")
    return response.status == 200 and "feed" in response.url
```

### Auto-Refresh on Expiry
1. Detect `SessionExpired` via rate-limit detection (Phase 1.1)
2. Trigger `browser_import` flow silently
3. Update `CookieStore` and all active browser contexts
4. Retry original request

### Fingerprint Binding
- Store fingerprint hash with cookie jar
- Validate on load: `hash(stored_fingerprint) == hash(current_fingerprint)`
- If mismatch → force re-import

---

## Rate-Limit Tiers (Observed)

| Tier | Limit | Window | Tracking Call Behavior |
|------|-------|--------|------------------------|
| Guest | ~30 req/min | Rolling | `li/track` every 2s, no cookies |
| Authenticated | ~100 req/min | Rolling | `trackingApiService/track` every 7-15s |
| Search | ~30 req/min | Rolling | Same as auth + search-specific events |
| Profile | ~20 req/min | Rolling | + `trackO11yApi`, `trackLixApi` on unload |

---

## Implementation Checklist

- [ ] `CookieStore` class with encryption (Fernet, machine-ID key)
- [ ] Fingerprint hash stored alongside cookies
- [ ] `health_check()` method
- [ ] Auto-refresh on `SessionExpired`
- [ ] Playwright context factory with fingerprint alignment
- [ ] Persistent storage to `~/.linkedin-mcp/`
- [ ] Migration from existing `cookies.json` format

---

## References
- `linkedin_mcp_server/browser_import/extract.py` — Chrome cookie extraction
- `linkedin_mcp_server/browser_import/orchestrate.py` — Import orchestration
- `linkedin_mcp_server/session_state.py` — State persistence paths
- `linkedin_mcp_server/core/browser.py` — BrowserManager, context creation
- HAR files: `har-noauth/`, `linkedlog/`