# Architecture Overview

## The Problem

LinkedIn (and most modern web apps) use:
- **CSS module hashes** — class names like `_71b6f1ad` that change weekly
- **Bot detection** — Cloudflare, fingerprinting, behavior analysis
- **Anti-automation** — Browser automation tools (Playwright, Puppeteer) are detected and blocked

Traditional scraping breaks constantly. Browser automation gets blocked immediately.

## The Solution: CDP

Chrome DevTools Protocol (CDP) is the same protocol Chrome DevTools uses to inspect pages. It connects directly to the browser's rendering engine — no injection, no automation flags, no detectable difference from normal browsing.

```
┌─────────────────────────────────────────────────────┐
│                   MCP Client                        │
│            (Claude, Cursor, etc.)                   │
└──────────────────────┬──────────────────────────────┘
                       │ stdio (JSON-RPC)
                       ▼
┌─────────────────────────────────────────────────────┐
│                 server.py                           │
│         MCP protocol, tool routing                  │
└──────────┬──────────────────────┬───────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐  ┌──────────────────────────────┐
│  core/registry.py│  │    cdp/browser.py            │
│  Tool dispatch   │  │    Tab discovery             │
└────────┬─────────┘  └──────────────┬───────────────┘
         │                           │
         ▼                           ▼
┌──────────────────┐  ┌──────────────────────────────┐
│  sites/linkedin/ │  │    cdp/client.py             │
│  Extractors      │  │    WebSocket CDP commands    │
└──────────────────┘  └──────────────────────────────┘
                              │
                              │ WebSocket
                              ▼
                     ┌──────────────────┐
                     │  Chromium Browser │
                     │  (user logged in) │
                     └──────────────────┘
```

## Data Flow

1. **MCP Client** calls a tool (e.g., `linkedin_feed`)
2. **Server** looks up the tool in the registry
3. **Registry** returns the extractor class and config
4. **Extractor** receives a `CDPClient` connected to the right tab
5. **CDPClient** sends JavaScript to the browser via WebSocket
6. **Browser** executes the JS in the live page context
7. **Result** flows back: browser → CDPClient → extractor → registry → server → MCP client

## Key Design Decisions

### Why not browser automation?

Patchright/Playwright/Puppeteer all modify the browser environment. LinkedIn's Cloudflare protection detects these modifications and blocks the session. CDP connects to an already-running browser — nothing to detect.

### Why a plugin system?

Each website has different DOM structure. A monolithic extractor would be unmaintainable. The plugin system lets you:
- Add new sites without touching core code
- Test extractors independently
- Share extractors across projects

### Why aria-labels over CSS classes?

LinkedIn uses CSS modules that generate hash-based class names (`_71b6f1ad`). These change every deployment. Aria-labels, role attributes, and semantic HTML (H1, H2, button) are stable because they're required for accessibility.

### Why innerText line parsing?

Many LinkedIn elements don't have unique selectors. The most reliable approach is:
1. Get the full text of a container
2. Split by newlines
3. Parse lines by position and content patterns

This is fragile to layout changes but much more resilient than CSS selectors.

---

## Write Operations Architecture (v0.3.0)

### Data Flow

```
┌─────────────────────────────────────────────────────┐
│                   MCP Client                        │
│            (Claude, Cursor, etc.)                   │
└──────────────────────┬──────────────────────────────┘
                       │ stdio (JSON-RPC)
                       ▼
┌─────────────────────────────────────────────────────┐
│                 server.py                           │
│         MCP protocol, tool routing                  │
└──────────┬──────────────────────┬───────────────────┘
           │                      │
           ▼                      ▼
┌──────────────────┐  ┌──────────────────────────────┐
│  core/registry.py│  │    actions/executor.py       │
│  Tool dispatch   │  │    Approval + rate limiting  │
└────────┬─────────┘  └──────────────┬───────────────┘
         │                           │
         ▼                           ▼
┌──────────────────┐  ┌──────────────────────────────┐
│  sites/linkedin/ │  │    actions/linkedin.py       │
│  Extractors      │  │    Write action handlers     │
└──────────────────┘  └──────────────┬───────────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │   Audit Log          │
                          │   (linkagent_audit)  │
                          └──────────────────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │    CDPClient          │
                          │    click/type/navigate│
                          └──────────┬───────────┘
                                     │ WebSocket
                                     ▼
                          ┌──────────────────────┐
                          │  Chromium Browser     │
                          │  (user logged in)     │
                          └──────────────────────┘
```

### New Modules

```
linkagent_mcp/
├── actions/
│   ├── __init__.py
│   ├── executor.py          # Approval flow, rate limiting, dry-run
│   └── linkedin/
│       ├── __init__.py
│       ├── connect.py       # Send connection requests
│       ├── message.py       # Send direct messages
│       ├── apply.py         # Job applications
│       ├── post.py          # Create posts
│       ├── comment.py       # Comment on posts
│       ├── react.py         # Like/celebrate/insightful
│       └── follow.py        # Follow/unfollow
├── core/
│   ├── audit.py             # Audit log writer
│   └── approval.py          # User approval interface
```

### Approval Flow

```python
# Conceptual flow in actions/executor.py
async def execute_write(action: WriteAction) -> ActionResult:
    # 1. Validate action parameters
    validate_action(action)

    # 2. Check rate limits
    if rate_limiter.is_cooldown_active(action.type):
        return ActionResult(cooldown_remaining=rate_limiter.time_remaining())

    # 3. Dry-run check
    if config.dry_run:
        return ActionResult(preview=True, would_do=action.description)

    # 4. Request user approval (MCP prompt)
    approval = await request_approval(action)
    if not approval:
        return ActionResult(rejected=True)

    # 5. Execute via CDP
    result = await perform_action(action)

    # 6. Log to audit trail
    audit_log.record(action, result)

    # 7. Update rate limiter
    rate_limiter.record(action.type)

    return result
```

### Safety Layers

| Layer | Purpose | Config |
|-------|---------|--------|
| Approval | User confirms every write | Always on for writes |
| Rate Limit | Cooldown between actions | `LINKAGENT_WRITE_COOLDOWN` |
| Dry-run | Preview without execute | `LINKAGENT_DRY_RUN` |
| Audit | Full operation history | `linkagent_audit.log` |
| Rollback | Undo reversible actions | 24h window |
| Random Delay | Mimic human behavior | 0.5-2s between steps |
