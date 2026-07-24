# Adding a New Site

Step-by-step guide to add extractors for a new website.

## Overview

1. Create a directory under `sites/`
2. Implement extractors subclassing `BaseExtractor`
3. Define a `register()` function
4. Restart the server — auto-discovery handles the rest

## Step 1: Create the Directory Structure

```
linkagent_mcp/
└── sites/
    └── twitter/
        ├── __init__.py
        └── extractors/
            ├── __init__.py
            └── feed.py
```

## Step 2: Create the Extractor

```python
# sites/twitter/extractors/feed.py
import json
from linkagent_mcp.core.base import BaseExtractor


EXTRACT_FEED_JS = """
(() => {
    const tweets = [];
    // Your extraction logic here
    // Use document.querySelector with stable selectors
    // Return JSON.stringify({tweets})
})()
"""


class TwitterFeedExtractor(BaseExtractor):
    """Extract tweets from the Twitter/X home feed."""

    async def extract(self, **kwargs) -> dict:
        # Verify we're on the right page
        url = await self._get_url()
        if "x.com/home" not in url and "twitter.com/home" not in url:
            return {"error": f"Not on home page. Current URL: {url}"}

        # Execute extraction JavaScript
        raw = await self._eval(EXTRACT_FEED_JS)
        if not raw:
            return {"error": "Empty response from CDP"}

        # Parse and return
        try:
            data = json.loads(raw)
        except Exception as e:
            return {"error": f"Failed to parse: {e}"}

        return {
            "url": url,
            "tweet_count": len(data.get("tweets", [])),
            "tweets": data.get("tweets", []),
        }
```

## Step 3: Create the Package Init

```python
# sites/twitter/extractors/__init__.py
from .feed import TwitterFeedExtractor

__all__ = ["TwitterFeedExtractor"]
```

## Step 4: Create the Site Module

```python
# sites/twitter/__init__.py
from linkagent_mcp.core.registry import Registry
from .extractors import TwitterFeedExtractor


def register(registry: Registry):
    """Register all Twitter/X extractors."""
    registry.register(
        name="twitter_feed",
        extractor_class=TwitterFeedExtractor,
        domain="x.com",
        description="Extract tweets from the Twitter/X home feed",
        input_schema={"type": "object", "properties": {}},
        navigate_url="https://x.com/home",
        url_patterns=["/home", "/search"],
    )
```

## Step 5: Restart the Server

```bash
python -m linkagent_mcp
```

The server will auto-discover the new module and register the tools.

## Best Practices

### Selectors

Use stable selectors that survive website updates:

```python
# Good — semantic, stable
document.querySelector('h1')
document.querySelector('button[aria-label*="Post"]')
document.querySelector('[role="article"]')

# Bad — fragile, changes often
document.querySelector('.feed-item_v2_abc123')
document.querySelector('div[class*="css-"]')
```

### Body Text Parsing

When DOM selectors aren't reliable, parse body text:

```python
EXTRACT_JS = """
(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n').map(l => l.trim()).filter(Boolean);

    // Parse by position
    const result = {};
    for (let i = 0; i < lines.length; i++) {
        if (lines[i] === 'Label:') {
            result.value = lines[i + 1];
        }
    }
    return JSON.stringify(result);
})()
"""
```

### Error Handling

Always check for errors:

```python
async def extract(self, **kwargs) -> dict:
    url = await self._get_url()
    if "target-site.com" not in url:
        return {"error": f"Not on target page. Current URL: {url}"}

    raw = await self._eval(JS_CODE)
    if not raw:
        return {"error": "Empty response from CDP"}

    try:
        data = json.loads(raw)
    except Exception as e:
        return {"error": f"Failed to parse: {e}"}

    if "error" in data:
        return data

    return data
```

### Navigation

Auto-navigate to the right page:

```python
async def extract(self, keyword: str = "", **kwargs) -> dict:
    url = await self._get_url()

    if keyword and f"keywords={keyword}" not in url:
        target = f"https://example.com/search?q={keyword}"
        await self.client.navigate(target)
        await self._wait_for_element('[data-results]', timeout_ms=8000)

    # Now extract...
```

## Testing

Create a test file:

```python
# tests/test_twitter.py
import asyncio
from linkagent_mcp.core.registry import registry
from linkagent_mcp.cdp import CDPClient
from linkagent_mcp.sites import auto_discover

async def test_twitter_feed():
    auto_discover(registry)
    client = CDPClient("ws://127.0.0.1:9222/devtools/page/YOUR_TAB_ID")
    result = await registry.extract("twitter_feed", client)
    print(result)

asyncio.run(test_twitter_feed())
```

## Selector Strategy Guide

| Selector Type | Example | Stability |
|--------------|---------|-----------|
| Aria labels | `button[aria-label*="Like"]` | High |
| Role attributes | `[role="article"]` | High |
| Semantic HTML | `h1`, `h2`, `nav`, `main` | High |
| Data attributes | `[data-testid="tweet"]` | Medium |
| Tag + position | `div > span:first-child` | Medium |
| CSS classes | `.css-abc123` | Low |
| XPath | `//div[3]/span[2]` | Low |

**Rule of thumb:** If it's required for accessibility or testing, it's probably stable.
