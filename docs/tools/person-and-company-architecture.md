# Person & Company Tools — Architecture Overview

## 1. Tool Inventory

### Person Tools (5 tools)

| Tool | Tier | Old File | New File |
|------|------|----------|----------|
| `get_person_profile` | Scraping | `tools/person.py` (lines 31-102) | `tools/person/profile.py` |
| `search_people` | Search | `tools/person.py` (lines 104-185) | `tools/person/search.py` |
| `connect_with_person` | Actions | `tools/person.py` (lines 187-254) | `tools/person/connect.py` |
| `get_sidebar_profiles` | Scraping | `tools/person.py` (lines 256-307) | `tools/person/sidebar.py` |
| `get_my_profile` | Scraping | `tools/person.py` (lines 309-368) | `tools/person/my_profile.py` |

### Company Tools (4 tools)

| Tool | Tier | Old File | New File |
|------|------|----------|----------|
| `get_company_profile` | Scraping | `tools/company.py` (lines 30-96) | `tools/company/profile.py` |
| `get_company_posts` | Scraping | `tools/company.py` (lines 98-162) | `tools/company/posts.py` |
| `search_companies` | Search | `tools/company.py` (lines 164-209) | `tools/company/search.py` |
| `get_company_employees` | Scraping | `tools/company.py` (lines 211-278) | `tools/company/employees.py` |

## 2. How Each Tool Works

All tools share a common flow:

```
Tool called → get authenticated extractor → navigate LinkedIn page(s) → extract innerText → return structured dict
```

### 2.1 The Full Call Chain (Old Architecture)

```
MCP Client
  → @mcp.tool() decorator (person.py / company.py)
    → get_ready_extractor(ctx, tool_name)         [dependencies.py]
      → ensure_tool_ready_or_raise()                [bootstrap.py — env check, profile dir, cookies]
      → get_or_create_browser()                     [drivers/browser.py — Playwright launch]
      → ensure_authenticated()                      [drivers/browser.py — cookie injection + auth gate]
      → return LinkedInExtractor(browser.page)      [scraping/extractor.py — wraps the Playwright page]
    → extractor.{scrape_person/search_people/...}() [scraping/extractor.py — actual LinkedIn scraping]
      → extract_page(url, section_name)             [scraping/extractor.py — navigate, scroll, innerText]
        → self._page.goto(url)
        → scroll to bottom / click "Show more"
        → page.innerText("*") → strip noise (sidebar, footer)
        → return ExtractedSection(text, references, error)
      → assemble result dict {url, sections, references, section_errors}
    → on AuthenticationError → close_browser() + trigger re-login
    → on any Exception → raise_tool_error() → ToolError with diagnostics
```

### 2.2 Section System (fields.py)

Each section maps to a distinct LinkedIn URL:

```python
PERSON_SECTIONS = {
    "main_profile":   ("/", False),                    # Always included
    "experience":     ("/details/experience/", False),
    "education":      ("/details/education/", False),
    "interests":      ("/details/interests/", False),
    "honors":         ("/details/honors/", False),
    "languages":      ("/details/languages/", False),
    "certifications": ("/details/certifications/", False),
    "skills":         ("/details/skills/", False),
    "projects":       ("/details/projects/", False),
    "contact_info":   ("/overlay/contact-info/", True),  # Overlay dialog
    "posts":          ("/recent-activity/all/", False),
}
```

`is_overlay=True` means LinkedIn opens a dialog overlay instead of navigating to a new page — the scraper handles these differently (waits for overlay element).

### 2.3 Tool-Specific Behavior

**`get_person_profile`**: Navigates to `/in/{username}/`, extracts main profile, then iterates requested sections by appending each URL suffix to the base profile URL. Each section is a separate `extract_page()` call. Supports `max_scrolls` for "Show more" pagination.

**`get_my_profile`**: Goes to `/in/me/`, waits for LinkedIn's redirect resolution to the real username (e.g. `/in/johndoe/`), then scrapes same as `get_person_profile` but without needing a username argument.

**`search_people`**: Builds a LinkedIn search URL with optional filters (location, network degree F/S/O, current company URN). Navigates to it and extracts the search results page.

**`connect_with_person`**: Navigates to the person's profile, detects their connection state via locale-independent heuristics (URL patterns for invite anchors, ARIA attribute presence), then either clicks "Connect" or accepts an incoming request. Returns a status string.

**`get_sidebar_profiles`**: Navigates to a profile page, extracts sidebar recommendation sections ("More profiles", "People you may know", etc.), follows "Show all" links to get full lists.

**`get_company_profile`**: Navigates to `/company/{slug}/about/`, then iterates requested sections (posts, jobs). Extracts company URN from "See all employees" link when present.

**`get_company_posts`**: Direct `extract_page` call to `/company/{slug}/posts/`. Note: this is the only Person/Company tool that does NOT use `scrape_company` — it calls `extract_page` directly in the tool layer and assembles its own result dict (with explicit section_errors handling).

**`search_companies`**: Builds LinkedIn search URL for companies, navigates, extracts results.

**`get_company_employees`**: Navigates to `/company/{slug}/people/`, extracts employee list with demographics (location, education, function breakdown).

### 2.4 Error Handling Flow

```
Any exception in tool body
  → AuthenticationError → handle_auth_error() [dependencies.py]
      → close_browser()
      → invalidate_auth_and_trigger_relogin()  # Starts interactive login, raises
  → ToolError (from search_people filter validation)
      → Re-raised directly (bypasses raise_tool_error)
  → All other exceptions → raise_tool_error() [error_handler.py]
      → Maps known types (RateLimitError, ProfileNotFoundError, etc.) to user-friendly ToolError strings
      → Attaches diagnostics from error_diagnostics.py
      → Unknown exceptions re-raised for FastMCP's mask_error_details
```

## 3. Return Format

All scraping tools return:

```python
{
    "url": "https://www.linkedin.com/in/username/",         # The scraped URL
    "sections": {
        "main_profile": "raw innerText with no structure",   # Section name → raw text
        "experience": "...",
    },
    # Optional:
    "references": {                                          # discoverable links
        "about": [{"kind": "company_urn", "value": "1234"}],
        "employees": [{"kind": "profile", "url": "/in/..."}],
    },
    "section_errors": {
        "posts": {"error_type": "RateLimitError", ...}
    },
    "unknown_sections": ["bogus_section"],                   # Invalid section names passed in
}
```

The LLM is expected to parse the raw `innerText` in each section — there is **no structured schema** on the output. This is by design: LinkedIn's HTML varies constantly, and innerText is the most resilient extraction strategy.

## 4. Old vs New Architecture

### Old Architecture (`linkedin-mcp-server/linkedin_mcp_server/tools/person.py` and `company.py`)

- **Registration**: `def register_person_tools(mcp: FastMCP) → None` — imperative registration via `@mcp.tool()` decorator
- **Auth/Deps**: `get_ready_extractor(ctx, tool_name=tool_name)` — FastMCP `Context`-aware DI, handles auth errors with progress reporting
- **Progress**: `MCPContextProgressCallback(ctx)` — wraps FastMCP context for `report_progress()`
- **Filter Validation**: `search_people` catches `FilterValidationError` and re-raises as `ToolError` to avoid `mask_error_details` swallowing the message
- **Rate-limit sentinel**: `get_company_posts` checks `_RATE_LIMITED_MSG` string constant from `extractor.py`

### New Architecture (`tools/person/*.py` and `tools/company/*.py`)

- **Registration**: `class GetPersonProfile(BaseTool):` — declarative class with metadata fields, auto-discovered by `ToolRegistry.walk_packages()`
- **Auth/Deps**: `get_authenticated_extractor()` — simplified, no `Context`, no progress reporting, no auth-error re-login flow
- **Progress**: **None** — no progress callbacks at all
- **Error handling**: **None** — no `raise_tool_error()`, no diagnostics. Any exception is caught by `_instrument_execute` wrapper in `base_tool.py` and returns `ToolResult(success=False, error=f"{type(exc).__name__}: {exc}")`
- **Tier/Stability metadata**: Each tool declares `tier`, `stability`, `best_for`, `not_good_for`, `input_schema` as class attributes

### Key Gaps in New Architecture

| Feature | Old Arch | New Arch |
|---------|----------|----------|
| Context/progress reporting | `MCPContextProgressCallback(ctx)` | ❌ Missing |
| Auth-error re-login trigger | `handle_auth_error()` | ❌ Missing |
| Filter validation bypass | `raise ToolError(str(e))` | ❌ Missing |
| Rate-limit sentinel check | `_RATE_LIMITED_MSG` | ❌ Missing |
| Diagnostics on error | `build_issue_diagnostics()` | ❌ Missing |
| `unknown_sections` parsing | Present on all scrapers | ✅ Present |
| Input validation | Pydantic `Field(ge=1, le=50)` | ❌ Missing |
| Section-errors in result | Present on `get_company_posts` | ✅ Present |

## 5. Dependencies (File Graph)

```
Tool calls (person.py / company.py)
  → dependencies.py
    → bootstrap.py          (env check, profile dir, cookie validation)
    → drivers/browser.py    (BrowserManager, Playwright lifecycle)
    → scraping/extractor.py (LinkedInExtractor — 3936 lines)
      → scraping/fields.py  (section definitions)
      → scraping/connection.py (ActionSignals for connection detection)
      → scraping/link_metadata.py (Reference building)
    → core/exceptions.py    (AuthenticationError, RateLimitError, etc.)
    → exceptions.py         (LinkedInMCPError hierarchy)
    → error_handler.py      (raise_tool_error → ToolError)
    → error_diagnostics.py  (build_issue_diagnostics)
    → callbacks.py          (MCPContextProgressCallback)
    → config/schema.py      (DEFAULT_TOOL_TIMEOUT_SECONDS, BrowserConfig)
```

## 6. Scraping Strategy (extractor.py internals)

The `LinkedInExtractor` wraps a single Playwright `Page` object. All extraction uses:

1. **Navigation**: `page.goto(url)` → wait for `document.readyState === 'complete'`
2. **Lazy loading**: Scroll to bottom for infinite-scroll sections (posts, search results)
3. **Show more**: Click "Show more" buttons for detail sections (experience, certifications)
4. **InnerText**: `page.evaluate("document.body.innerText")` → strip known noise (sidebar, footer, nav)
5. **Section separation**: Each section is a separate page navigation — never combined

Detection is intentionally **locale-independent**:
- Connection state: URL patterns (`/preload/custom-invite/`), attribute presence (`aria-label` exists), never text values
- Rate limits: Sentinels in innerText, HTTP status, URL redirect patterns
- Auth barriers: Known overlay elements, URL changes to `/checkpoint/`
