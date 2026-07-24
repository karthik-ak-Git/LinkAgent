# Selector Strategy

How we pick DOM elements that survive LinkedIn's frequent updates.

## The Problem

LinkedIn uses CSS modules with hash-based class names:

```html
<div class="_71b6f1ad _90c0d3e5">
  <span class="_8d6_e2f1">John Smith</span>
</div>
```

These hashes change every deployment. A selector like `._71b6f1ad` breaks weekly.

## Our Approach: Layered Selection

We use three layers of selectors, from most to least stable:

### Layer 1: Semantic & Accessibility (Primary)

These are required by web standards and accessibility guidelines. They rarely change.

```javascript
// Semantic HTML
document.querySelector('h1')           // Page title
document.querySelector('h2')           // Section headings
document.querySelector('nav')          // Navigation
document.querySelector('main')         // Main content

// ARIA attributes
document.querySelector('button[aria-label*="Comment"]')
document.querySelector('[role="article"]')
document.querySelector('[role="listitem"]')
document.querySelector('section[aria-label="Primary content"]')
```

**Why stable:** LinkedIn must maintain these for screen readers and SEO. Removing them would break accessibility compliance.

### Layer 2: Structural Patterns (Secondary)

Patterns that describe DOM structure without relying on specific classes.

```javascript
// Find elements by their relationship to other elements
const commentBtn = document.querySelector('button[aria-label*="Comment"]');
let container = commentBtn.parentElement;
for (let i = 0; i < 15; i++) {
    container = container.parentElement;
    if (container.innerText.length > 200) break;
}

// Find elements by tag + content pattern
const h2s = [...document.querySelectorAll('h2')];
const aboutH2 = h2s.find(h => h.innerText.trim().startsWith('About'));
```

**Why stable:** Structural relationships (parent-child, sibling order) change less frequently than class names.

### Layer 3: Body Text Parsing (Fallback)

When DOM selectors fail, we parse the visible text directly.

```javascript
const body = document.body.innerText;
const lines = body.split('\n').map(l => l.trim()).filter(Boolean);

// Parse by content patterns
for (const line of lines) {
    if (line.match(/^\d+[hmd]$/)) {
        post.time = line;  // "2h", "3d", "1w"
    }
    if (line.includes('•') && line.includes('3rd')) {
        post.author = line.split('•')[0].trim();
    }
}
```

**Why stable:** The visible text is what users see. LinkedIn can't change it without changing the user experience.

## Examples by Feature

### Feed Posts

```javascript
// Post boundary detection (stable)
const commentBtns = primarySection.querySelectorAll('button[aria-label*="Comment"]');

// Author detection (body text parsing)
const lines = text.split('\n');
for (const line of lines) {
    if (line.includes('•') && line.includes('3rd')) {
        post.author = line.split('•')[0].trim();
        break;
    }
}

// Metrics detection (pattern matching)
for (const line of lines) {
    if (line.match(/^\d+[kKmM]?$/) && parseInt(line.replace(/[kKmM]/, '')) < 100000) {
        nums.push(line);
    }
}
```

### Profile Pages

```javascript
// Name extraction (H2, not H1)
const h2s = [...document.querySelectorAll('h2')];
const nameH2 = h2s.find(h => {
    const text = h.innerText.trim();
    return text && text.length > 1 && text.length < 60
        && !text.includes('notifications')
        && !text.includes('Ad Options');
});

// Section extraction (H2-based)
const aboutH2 = h2s.find(h => h.innerText.trim().startsWith('About'));
const section = aboutH2.closest('section') || aboutH2.parentElement;
```

### Job Cards

```javascript
// Job card detection (class-based, but stable)
const cards = document.querySelectorAll('.job-card-container');

// Metadata parsing (body text)
for (const line of lines) {
    if (line.match(/\(On-site\)|\(Remote\)|\(Hybrid\)/)) {
        result.location = line;
    }
    if (line.match(/\d+\s*(hour|day|week|month)s?\s*ago/i)) {
        result.posted = line;
    }
}
```

### Search Results

```javascript
// Result container (role-based)
const cards = document.querySelectorAll('[role="listitem"]');

// Profile link detection
const profileLink = card.querySelector('a[href*="/in/"]');
const nameSpan = profileLink.querySelector('span[aria-hidden="true"]');
```

## Selector Stability Ranking

| Rank | Type | Example | Change Frequency |
|------|------|---------|------------------|
| 1 | Aria labels | `button[aria-label*="Like"]` | Rarely |
| 2 | Roles | `[role="article"]` | Rarely |
| 3 | Semantic HTML | `h1`, `h2`, `section` | Never |
| 4 | Data attributes | `[data-testid="..."]` | Sometimes |
| 5 | Tag + position | `div > span:first-child` | Sometimes |
| 6 | CSS modules | `._71b6f1ad` | Weekly |
| 7 | XPath | `//div[3]/span[2]` | Often |

## Testing Selectors

To verify a selector still works:

1. Open browser with CDP enabled
2. Navigate to the target page
3. Open DevTools Console
4. Run your selector:
   ```javascript
   document.querySelector('your-selector-here')
   ```
5. If it returns elements, the selector works
6. Bookmark the test — run it periodically

## When Selectors Break

If an extractor stops working:

1. Check the page manually — did the DOM change?
2. Try alternative selectors from the stability ranking
3. Add fallback selectors (try multiple strategies)
4. Update the extractor with the new selector
5. Test against real LinkedIn pages

## Future: Self-Healing Selectors

We want to build a system that:
1. Monitors selector health over time
2. Detects when selectors break
3. Automatically tries alternative selectors
4. Updates extractors without manual intervention
5. Shares selector updates across users
