# LinkedIn MCP Server - Optimization Plan

## Overview
Transform the LinkedIn MCP server from a brittle, singleton-based browser scraper into an agent-friendly, structured, and resilient system.

## Current Architecture
- **Type**: Browser-automation scraper (Playwright/patchright)
- **Auth**: Cookie-based (li_at, JSESSIONID, bcookie, bscookie, lidc, li_rm, liap, li_gc, lang, timezone, li_mc)
- **Data extraction**: HTML page navigation → DOM innerText → noise stripping
- **No direct API calls** to LinkedIn REST/GraphQL/Voyager

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
- Updated `README.md`

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