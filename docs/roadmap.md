# Roadmap

What we've built, what's next, and what we want to overcome.

## What We've Built (v0.1.0)

- Universal CDP-based extraction framework
- Plugin system with auto-discovery
- 5 LinkedIn extractors (feed, profile, company, jobs, search)
- 5 browser control tools (navigate, screenshot, execute_js, list_tabs, scroll)
- Cross-platform browser detection (Windows, macOS, Linux)
- Environment-based configuration
- Structured logging
- MCP server with stdio transport

## What's Next (v0.2.0)

### Priority 1: Robustness

- **Auto-reconnection** — Reconnect to browser if CDP connection drops
- **Health checks** — Periodic tab liveness verification
- **Error recovery** — Retry failed extractions with backoff
- **Session validation** — Check if browser is logged in before extraction

### Priority 2: Write Operations (v0.3.0)

Add safe, controlled write operations with human-in-the-loop approval:

**LinkedIn Actions:**
- **Send connection requests** — with personalized notes
- **Send messages** — InMail and direct messages
- **Apply to jobs** — Easy Apply and external redirects
- **Post content** — text, articles, images
- **Comment on posts** — engagement actions
- **Follow/unfollow** — people and companies
- **React to content** — like, celebrate, insightful

**Safety Mechanisms:**
- **Approval flow** — every write requires explicit user confirmation
- **Rate limiting** — configurable cooldown between actions (default: 60s)
- **Dry-run mode** — preview what would happen without executing
- **Audit log** — full history of all write operations with timestamps
- **Rollback** — undo last N actions where possible (unfollow, unreact)

**Architecture:**
```
MCP Client → server.py → registry.py → actions/executor.py
                                          │
                                    ┌─────┴─────┐
                                    │  approve?  │
                                    └─────┬─────┘
                                          │ yes
                                          ▼
                                    actions/linkedin.py
                                          │
                                    CDP click/type
                                          │
                                          ▼
                                    Audit Log + Result
```

### Priority 3: More Data

- **Pagination** — Auto-scroll and extract multiple pages
- **Expanded sections** — Click "Show more" and "See more" automatically
- **Media extraction** — Capture images, videos, document links
- **Notifications** — Extract notification data
- **Messaging** — Read messages (not send)

### Priority 3: More Sites

- **Twitter/X** — Feed, profiles, search
- **GitHub** — Repositories, profiles, issues
- **Reddit** — Posts, comments, subreddits
- **Instagram** — Profiles, posts, stories
- **Facebook** — Pages, groups, posts
- **YouTube** — Videos, channels, comments

### Priority 4: Better Output

- **Data storage** — SQLite/PostgreSQL integration
- **Export formats** — CSV, Excel, PDF
- **Real-time streaming** — WebSocket for live data
- **Caching** — Avoid re-extracting unchanged data
- **Deduplication** — Track seen items across extractions

## What We Want to Overcome

### Problem: Fragile Selectors

**Current:** LinkedIn changes DOM structure regularly. Selectors break.

**Goal:** Self-healing selectors that adapt to changes.

**Ideas:**
- Fallback selector chains (try multiple strategies)
- Machine learning-based element detection
- Automatic selector updates via CI/CD
- Community-maintained selector registry

---

### Problem: No Write Operations (Addressed in v0.3.0)

**Current:** Can only read data, not interact.

**Goal:** Safe, controlled write operations with approval flow.

**Plan:**
- `actions/` module with executor and LinkedIn action handlers
- Every write goes through approval flow (user must confirm)
- Rate limiting with configurable cooldown (default 60s)
- Dry-run mode for previewing actions
- Audit log recording all write operations
- Rollback support for reversible actions (unfollow, unreact, withdraw application)

**Implementation Phases:**
1. Executor with approval gate and rate limiter
2. LinkedIn connection requests and messages
3. Job application actions (Easy Apply)
4. Content actions (post, comment, react)
5. Audit log and rollback system

---

### Problem: Single Browser

**Current:** One browser, one profile, one session.

**Goal:** Multiple browsers, profiles, and sessions.

**Ideas:**
- Browser pool management
- Profile switching (personal, company, client)
- Remote browser support (Docker, cloud)
- Session isolation between profiles

---

### Problem: No Scheduling

**Current:** Manual extraction only.

**Goal:** Automated extraction on schedule.

**Ideas:**
- Cron-like scheduling (extract feed every hour)
- Event-driven extraction (new post detected)
- Alert system (keyword mentioned in feed)
- Background daemon mode

---

### Problem: No Analytics

**Current:** Raw JSON output only.

**Goal:** Insights and analytics from extracted data.

**Ideas:**
- Trend analysis (topic popularity over time)
- Network analysis (who connects with whom)
- Content analysis (sentiment, topics, keywords)
- Competitive intelligence (company activity tracking)

---

### Problem: Deployment Complexity

**Current:** Requires local browser with CDP.

**Goal:** Easy deployment anywhere.

**Ideas:**
- Docker image with browser included
- Cloud deployment (AWS, GCP, Azure)
- Headless browser support
- Remote browser connection (SSH tunnel)
- Browser-as-a-service integration

---

### Problem: No Testing Framework

**Current:** Manual testing only.

**Goal:** Automated tests for extractors.

**Ideas:**
- Snapshot testing (compare extracted data over time)
- DOM replay testing (record and replay page loads)
- Mock CDP server for unit tests
- Integration test framework
- Selector health monitoring

---

### Problem: Limited MCP Integration

**Current:** Basic tool listing and calling.

**Goal:** Full MCP feature utilization.

**Ideas:**
- Resource endpoints (extraction results as MCP resources)
- Prompt templates (common extraction workflows)
- Sampling support (let MCP client guide extraction)
- Roots support (restrict extraction to allowed domains)
- Logging integration (MCP logging protocol)

---

## Long-Term Vision

### Phase 1: LinkedIn Mastery (Current)
Complete LinkedIn coverage with all extractors working reliably.

### Phase 2: Multi-Site Expansion
Add support for 5+ major platforms with consistent API.

### Phase 3: Intelligence Layer
Add analytics, insights, and automation on top of raw extraction.

### Phase 4: Platform
Turn LinkAgent into a platform for browser-based data extraction with:
- Visual extractor builder
- Marketplace for community extractors
- Cloud hosting option
- Enterprise features (teams, permissions, audit)

### Phase 5: Agent Integration
Deep integration with AI agents for:
- Autonomous research workflows
- Market monitoring and alerts
- Competitive intelligence
- Content curation and summarization
