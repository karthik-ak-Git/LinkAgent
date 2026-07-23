# LinkedIn MCP Server - Optimization Plan

## Overview
Transform the LinkedIn MCP server from a brittle, singleton-based browser scraper into an agent-friendly, structured, and resilient system.

## Current Architecture
- **Type**: Browser-automation scraper (Playwright/patchright)
- **Auth**: Cookie-based (li_at, JSESSIONID, bcookie, bscookie, lidc, li_rm, liap, li_gc, lang, timezone, li_mc)
- **Data extraction**: HTML page navigation → DOM innerText → noise stripping
- **No direct API calls** to LinkedIn REST/GraphQL/Voyager

## Architectural Rationale (Why Not the Official LinkedIn API?)

| Aspect | Official REST API | Browser Scraper |
|--------|------------------|-----------------|
| **Access** | LinkedIn-approved developers only — not available to most | Any LinkedIn session works |
| **Profile fields** | ~10 basic fields (id, name, photo, headline) | **11 sections** — experience, education, skills, certifications, projects, posts, etc. |
| **Lookup** | By Person ID only (per-app unique, can't share) | By username: `linkedin.com/in/{username}` |
| **Data storage** | Forbidden for non-authenticated members | No restriction |
| **Opt-out** | Members can hide via "Off-LinkedIn Visibility" | Can't be hidden |

The official REST API (`v2/me`, `v2/people/(id:{id})`) is a non-starter for this project — it returns 10× less data, can't look up by username, requires LinkedIn approval (rarely granted), and forbids storing data about other members. **Scraping is the only viable approach.**

---

## Phase 1: Foundation & Bug Fixes (Additive Only)

| ID | Task | Target |
|----|------|--------|
| 1.1 | Rate-limit detection — Playwright definitive inspection | `detection/rate_limit.py` |
| 1.2 | Auth cookie architecture doc | `AUTH_COOKIE_ARCHITECTURE.md` |
| 1.3 | Fix `get_company_posts` silent rate-limit drop | `tools/company.py:133-142` |
| 1.4 | Route unknown exceptions through diagnostics | `error_handler.py:184-186` |
| 1.5 | Complete `_tool_name_for_context` mapping | `error_diagnostics.py:384-408` |
| 1.6 | Fix `_inside_running_event_loop` dead code | `error_diagnostics.py:92-96` |
| 1.7 | Slug reconstruction from full URLs | `utils/slug.py` |
| 1.8 | Input validation for slug tools | `tools/person.py`, `tools/company.py` |

---

## Phase 2: New Core Modules (Additive)

| ID | Module | Purpose |
|----|--------|---------|
| 2.1 | `errors/` (6 files) | Typed exceptions + `RecoveryHint` with `RecoveryAction` enum |
| 2.2 | `container.py` | Explicit DI container replacing singletons |
| 2.3 | `tools/registry.py` | `ToolRegistry` + `ToolMeta` for declarative registration |
| 2.4 | `middleware/per_tool_semaphore.py` | Per-tool concurrency (search=3, profile=2, company=2, feed=2, auth=1) |
| 2.5 | `middleware/error_classifier.py` | Wrap tool calls → classify exception → attach recovery hint |
| 2.6 | `services/rate_limit_accountant.py` | Token buckets per tier, 429→backoff, persist to disk |
| 2.7 | `services/cookie_store.py` | Encrypted cookie jar + fingerprint binding + health check |
| 2.8 | `services/browser_pool.py` | Playwright context pool with cookie injection + fingerprint spoofing |

---

## Phase 3: Wiring (New Entry Point)
- Create `server_v2.py` with container, registry, middlewares, services
- Register all 15 tools via `ToolRegistry`
- Run parallel to legacy `server.py` on different port

---

## Phase 4: Cookie Replay Hardening
- `CookieStore.health_check()` — lightweight `/feed/` fetch before session
- Fingerprint alignment (UA, viewport, locale, timezone, color_scheme)
- Auto-refresh on `SessionExpired` via `browser_import` flow
- Harden Google OAuth → LinkedIn cookie bridge

---

## Phase 5: Extraction Resilience
- Replace `_RATE_LIMITED_MSG` sentinel with `RateLimited` exception
- Exponential backoff + jitter in `extract_page()`
- Structured returns: `{data, section_errors, rate_limit_info, auth_status}`
- Pre-parse overlay detection (auth wall, checkpoint, captcha)

---

## Phase 6: Observability & Agent-Friendly Output
- JSON-line structured logging
- MCP responses include `meta: {recovery_hint, rate_limit_remaining, cookies_healthy}`
- `/health` endpoint

---

## Phase 7: Migration & Cutover
- Parallel run validation
- Integration tests
- Deprecate singletons and global lock
- Rename `server_v2.py` → `server.py`

---

## Phase 8: Documentation
- `OPTIMIZATION_PLAN.md` (this file)
- `AUTH_COOKIE_ARCHITECTURE.md`
- `AGENT_INTEGRATION_GUIDE.md`
- Updated `README.md` (reference `linkedin_mcp_server` internals here, not in tool code)

---

## Phase 9: Standalone Module Extraction (tools/ Separation)

The new `tools/` package must eventually operate without importing from `linkedin_mcp_server`. Currently it bridges via thin wrappers (`tools/_auth/`, `tools/_browser/`, `tools/_scraping/`). This phase extracts each bridge into a fully standalone module.

### Architecture

```
tools/
├── _auth/__init__.py         → Bridge to linkedin_mcp_server.auth (Phase 9.1-9.4)
├── _browser/__init__.py      → Bridge to linkedin_mcp_server.drivers.browser (Phase 9.5-9.7)
├── _scraping/__init__.py     → Bridge to linkedin_mcp_server.scraping (Phase 9.8)
├── _scraping/fields.py       → ALREADY standalone — section configs and parsers
└── person/profile.py         → ALREADY matches official auth flow
```

### Extraction Plan

| ID | Task | Current State | Target |
|----|------|---------------|--------|
| 9.1 | `_auth/get_authenticated_extractor()` | Bridge — calls `get_ready_extractor()` flow from `linkedin_mcp_server.dependencies` | **Keep as bridge** — the official flow is stable; wrapping it is correct |
| 9.2 | `CookieStore` | Only in `linkedin_mcp_server` plan (Phase 2.7) | Extract to `tools/_auth/store.py` — encrypts `cookies.json` with Fernet + machine-ID key |
| 9.3 | `FingerprintEngine` | Implicit in `synthesize_user_agent()` + `SourceState` | Extract to `tools/_auth/fingerprint.py` — capture UA, viewport, locale, timezone; hash + validate on load |
| 9.4 | `SessionHealth` | Implicit in `ensure_authenticated()` → `validate_session()` | Extract to `tools/_auth/health.py` — `/feed/` health check, `SessionExpired` detection |
| 9.5 | `BrowserPool` | `_browser` global singleton in `drivers/browser.py` | Extract to `tools/_browser/pool.py` — multi-context pool with cookie injection |
| 9.6 | `CookieInjector` | `browser.import_cookies()` + `_BRIDGE_COOKIE_PRESETS` in `core/browser.py` | Extract to `tools/_browser/injector.py` — cookie preset selection, domain normalization, async injection |
| 9.7 | `ProfileManager` | `session_state.py` — `SourceState`, `RuntimeState`, paths | Extract to `tools/_browser/profiles.py` — state persistence, path resolution, generation tracking |
| 9.8 | `LinkedInExtractor` | `scraping/extractor.py` (1350+ lines) | Extract to `tools/_scraping/extractor.py` — strip server-specific deps (logging, diagnostics), keep extraction logic |
| 9.9 | `tools/errors/` | `tools/_errors/exceptions.py` already exists | Verify alignment with `core/exceptions.py` hierarchy |

### File Layout After Phase 9

```
tools/
├── _auth/
│   ├── __init__.py         ← get_authenticated_extractor() bridge (kept thin)
│   ├── store.py            ← CookieStore (encrypted jar + fingerprint binding)
│   ├── fingerprint.py      ← FingerprintEngine (capture, hash, validate)
│   └── health.py           ← SessionHealth (/feed/ check, expiry detection)
├── _browser/
│   ├── __init__.py         ← get_browser(), close_browser() bridge (kept thin)
│   ├── pool.py             ← BrowserPool (multi-context lifecycle)
│   ├── injector.py         ← CookieInjector (presets, domain norm, injection)
│   └── profiles.py         ← ProfileManager (SourceState, RuntimeState, paths)
├── _scraping/
│   ├── __init__.py         ← re-exports
│   ├── fields.py           ← standalone (already done)
│   └── extractor.py        ← LinkedInExtractor (extraction logic only)
├── _errors/
│   ├── __init__.py         ← re-exports
│   └── exceptions.py       ← Typed exception hierarchy
├── base_tool.py            ← BaseTool ABC (standalone)
├── tool_registry.py        ← ToolRegistry (standalone)
├── person/                 ← tool implementations
├── company/
├── job/
├── messaging/
└── feed/
```

### Migration Path
1. Extract `CookieStore` first (no runtime deps, just file I/O + crypto)
2. Extract `BrowserPool` + `CookieInjector` + `ProfileManager` (need `patchright`)
3. Extract `LinkedInExtractor` (biggest file, needs careful de-coupling)
4. Replace bridge imports with direct standalone imports
5. Delete bridges once all consumers are migrated

---

## Success Criteria
- [ ] Every MCP tool response includes `meta.recovery_hint` on failure
- [ ] Rate-limit detection returns definitive cause (not heuristic)
- [ ] Cookie replay survives 24h+ without re-login
- [ ] Per-tool concurrency prevents starvation
- [ ] Structured logging enables debugging without code changes
- [ ] `server_v2.py` passes all integration tests alongside legacy

---

## Open Decisions
1. Rate-limit detection context: fresh incognito vs reuse existing
2. Cookie encryption: Fernet (machine-ID key) vs plaintext
3. Google OAuth bridge: harden existing vs rewrite
4. Parallel run ports: 8000/8001 + feature flag vs header routing