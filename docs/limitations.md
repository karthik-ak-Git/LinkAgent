# Limitations

Known issues, constraints, and things that don't work yet.

## Current Limitations

### 1. Read-Only Operations

The system only extracts data. It cannot:
- Post content to LinkedIn
- Send messages or connection requests
- Comment on posts
- Like or react to content
- Follow/unfollow users

**Why:** Write operations risk account restriction. LinkedIn actively monitors automated actions.

**Future:** Write operations could be added as opt-in features with rate limiting and human-in-the-loop approval.

---

### 2. Browser Must Be Running

The browser with CDP enabled must be open and logged in before using the server.

**Why:** CDP connects to an already-running browser. It cannot create sessions or handle login flows.

**Future:** Session persistence, auto-login via cookies, headless mode for server deployments.

---

### 3. Single Browser Connection

Currently connects to one browser instance on `127.0.0.1:9222`.

**Why:** Simplifies configuration. Multi-browser support adds complexity.

**Future:** Support multiple browser profiles, remote browsers, Docker containers.

---

### 4. No Pagination

Extractors return only what's visible on the current page. Feed shows ~5-10 posts, search shows first page of results.

**Why:** Pagination requires scrolling and waiting for dynamic content to load, which is slow and unpredictable.

**Future:** Auto-scroll and pagination support with configurable depth limits.

---

### 5. Fragile DOM Selectors

LinkedIn changes their DOM structure regularly. Selectors that work today may break tomorrow.

**Why:** LinkedIn uses CSS modules with hash-based class names that change every deployment.

**Mitigation:** We use aria-labels, role attributes, and semantic HTML (H1, H2, button) which are more stable. Body text line parsing is used as a fallback.

**Future:** Self-healing selectors, machine learning-based element detection, automatic selector updates.

---

### 6. No Authentication Handling

The system assumes the browser is already logged in. It cannot:
- Handle login flows
- Manage session cookies
- Refresh expired sessions
- Handle two-factor authentication

**Why:** Authentication is best handled by the user in the browser.

**Future:** Cookie import/export, session persistence, automatic session refresh.

---

### 7. No Rate Limiting

The system has no built-in rate limiting for extraction calls.

**Why:** CDP is local and fast. Rate limiting is more relevant for API-based approaches.

**Future:** Configurable rate limits, request queuing, cooldown periods.

---

### 8. No Data Storage

Extracted data is returned as JSON but not stored anywhere.

**Why:** Storage is application-specific. The MCP server focuses on extraction.

**Future:** Optional SQLite/PostgreSQL storage, export to CSV/JSON files, integration with databases.

---

### 9. No Error Recovery

If a CDP connection drops, the system doesn't automatically reconnect.

**Why:** Current implementation is simple request-response.

**Future:** Automatic reconnection, connection pooling, health checks.

---

### 10. Single Tab per Request

Each extraction call works with one browser tab. No parallel extraction across multiple tabs.

**Why:** Simplifies the implementation. Parallel extraction adds complexity.

**Future:** Multi-tab extraction, concurrent requests, tab pooling.

---

## Platform Limitations

### Windows

- Browser paths are hardcoded for common install locations
- Opera GX path may need manual configuration
- Some Linux-specific features not available

### macOS

- Browser paths assume standard install locations
- App bundle paths may vary

### Linux

- Browser paths assume system-wide installation
- Snap/Flatpak paths not included

---

## LinkedIn-Specific Limitations

### Feed

- Only shows ~5-10 posts per extraction
- Sponsored posts may be included
- "See more" expanded text not captured
- Embedded media (images, videos) not extracted

### Profile

- Private profiles return limited data
- "Show more" sections not expanded
- Activity tab not accessible
- Recommendations not extracted

### Company

- Employee list not reliably extractable
- Jobs tab requires separate extraction
- Posts limited to recent 3-5

### Jobs

- Search results limited to first page
- Salary information not always available
- "Easy Apply" form not supported
- Application submission not supported

### Search

- Results limited to first page
- Filters not supported
- Boolean search not supported
