# Tasks & Capabilities

What the system can do right now, and what each tool returns.

## Extraction Tools

### `linkedin_feed`

**What it does:** Extracts posts from the LinkedIn feed page.

**Requirements:** Browser must be on `linkedin.com/feed/`

**Returns:** URL, title, post count, and array of posts with author, headline, text, time, link, likes, comments, reposts.

**How it works:**
1. Finds `section[aria-label="Primary content"]`
2. Locates comment buttons as post boundaries
3. Traverses up to find the post container
4. Parses body text line-by-line for author, headline, metrics
5. Deduplicates by author name

---

### `linkedin_profile`

**What it does:** Extracts a person's LinkedIn profile.

**Input:** Optional `username` (from `/in/username` URL)

**Returns:** URL, name, headline, location, about, connections, experience array, education array, skills array.

**How it works:**
1. Navigates to profile if username provided
2. Extracts name from H2 (LinkedIn uses H2, not H1)
3. Parses body text lines for headline and location
4. Finds sections by H2 headings (About, Experience, Education, Skills)
5. Extracts list items within each section

---

### `linkedin_company`

**What it does:** Extracts a LinkedIn company page.

**Input:** Optional `company_name` (from `/company/name` URL)

**Returns:** URL, name, about, website, industry, size, headquarters, founded, followers, employees count, recent posts.

**How it works:**
1. Navigates to company page if name provided
2. Extracts name from H1
3. Parses body text for followers and employees (regex)
4. Finds Overview section via H2
5. Extracts external website links

---

### `linkedin_jobs`

**What it does:** Search jobs or extract job details.

**Input:** `keyword` for search, or `job_id` for detail page.

**Returns (search):** URL, query, result count, array of jobs with title, company, location, posted, URL.

**Returns (detail):** URL, title, company, location, description, posted, applicants, employment type, seniority level, easy apply flag.

**How it works:**
1. Uses `.job-card-container` DIVs for search results
2. Parses body text lines for metadata
3. Job detail: H1 for title, regex for structured fields
4. Description: text between "About the job" and next section

---

### `linkedin_search`

**What it does:** Search for people or companies on LinkedIn.

**Input:** `keyword`, optional `search_type` (people/company).

**Returns:** URL, query, search type, result count, array with name, headline, location, URL.

**How it works:**
1. Uses `[role="listitem"]` divs
2. Finds `a[href*="/in/"]` for people, `a[href*="/company/"]` for companies
3. Extracts name from `span[aria-hidden="true"]`
4. Parses remaining lines for headline and location

## Browser Control Tools

| Tool | Description |
|------|-------------|
| `navigate` | Go to any URL |
| `take_screenshot` | Capture page as PNG |
| `execute_js` | Run arbitrary JavaScript |
| `list_tabs` | List all open browser tabs |
| `scroll_page` | Scroll up/down by pixels |

## Write Operations (v0.3.0)

### Planned Write Tools

| Tool | Action | Input | Risk |
|------|--------|-------|------|
| `linkedin_connect` | Send connection request | `username`, `note` (optional) | Medium |
| `linkedin_message` | Send direct message | `username`, `message` | Medium |
| `linkedin_apply` | Apply to job | `job_id`, `resume` (optional) | High |
| `linkedin_post` | Create a post | `content`, `visibility` | Medium |
| `linkedin_comment` | Comment on post | `post_url`, `comment` | Low |
| `linkedin_react` | Like/celebrate/insightful | `post_url`, `reaction_type` | Low |
| `linkedin_follow` | Follow person/company | `profile_url` | Low |
| `linkedin_unfollow` | Unfollow person/company | `profile_url` | Low |
| `linkedin_withdraw` | Withdraw job application | `application_id` | Medium |

### Safety Features

- **Approval Required** — every write operation requires explicit user confirmation
- **Rate Limiting** — configurable cooldown between actions (default: 60s)
- **Dry-Run Mode** — preview actions without executing (`LINKAGENT_DRY_RUN=true`)
- **Audit Log** — full history of all write operations (`linkagent_audit.log`)
- **Rollback** — undo reversible actions within 24 hours

## Read vs Write Operations

**Fully supported (read):**
- Extract feed posts
- Extract profiles
- Extract company pages
- Extract job listings
- Search people/companies

**Not yet supported (write):**
- Posting content (planned v0.3.0)
- Sending messages (planned v0.3.0)
- Sending connection requests (planned v0.3.0)
- Commenting (planned v0.3.0)
- Reacting to content (planned v0.3.0)
- Following/unfollowing (planned v0.3.0)
- Job applications (planned v0.3.0)

Write operations are intentionally excluded in v0.1.0 due to risk of account restriction. They will be added in v0.3.0 with safety mechanisms including approval flow, rate limiting, and audit logging.
