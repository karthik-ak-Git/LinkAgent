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
