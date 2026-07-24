"""
Search extractor — extracts people and company search results.
"""

from .base import BaseExtractor
from ..types.models import SearchResult


EXTRACT_PEOPLE_SEARCH_JS = """
(() => {
    const url = location.href;
    if (!url.includes('/search/results/people')) return JSON.stringify({error: 'Not a people search page', url});

    const data = {
        url: url,
        query: new URLSearchParams(location.search).get('keywords') || '',
        results: [],
    };

    // Use [role="listitem"] — LinkedIn's CSS modules break class selectors
    const cards = document.querySelectorAll('[role="listitem"]');
    for (const card of cards) {
        const lines = card.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
        const result = {};

        // Find profile link with /in/ URL
        const profileLink = card.querySelector('a[href*="/in/"]');
        if (profileLink) {
            result.url = profileLink.href;
            // Name is typically the first span with aria-hidden="true"
            const nameSpan = profileLink.querySelector('span[aria-hidden="true"]');
            if (nameSpan) result.name = nameSpan.innerText.trim();
        }

        // Headline is usually the line containing job title keywords or second meaningful line
        if (lines.length >= 2 && !result.name) {
            result.name = lines[0];
        }
        // Find headline: line that contains common job title words or is the second line
        for (const line of lines) {
            if (line !== result.name && !line.match(/^\\d/) && line.length > 5 && line.length < 200
                && !line.includes('followers') && !line.includes('connections')
                && !line.match(/^\\d+ [a-z]/)) {
                result.headline = line;
                break;
            }
        }

        // Location: typically ends with country or contains common location patterns
        for (const line of lines) {
            if (line !== result.name && line !== result.headline
                && (line.includes(',') || line.match(/^(Greater|San|New|London|Berlin|Tokyo|India|United)/))) {
                result.location = line;
                break;
            }
        }

        if (result.name) data.results.push(result);
    }

    return JSON.stringify(data);
})()
"""


EXTRACT_COMPANY_SEARCH_JS = """
(() => {
    const url = location.href;
    if (!url.includes('/search/results/companies')) return JSON.stringify({error: 'Not a company search page', url});

    const data = {
        url: url,
        query: new URLSearchParams(location.search).get('keywords') || '',
        results: [],
    };

    // Use [role="listitem"] — CSS module hashes break class selectors
    const cards = document.querySelectorAll('[role="listitem"]');
    for (const card of cards) {
        const lines = card.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
        const result = {};

        // Find company link with /company/ URL
        const companyLink = card.querySelector('a[href*="/company/"]');
        if (companyLink) {
            result.url = companyLink.href;
            const nameSpan = companyLink.querySelector('span[aria-hidden="true"]');
            if (nameSpan) result.name = nameSpan.innerText.trim();
        }

        if (!result.name && lines.length > 0) result.name = lines[0];

        // Industry/description is usually the second line
        for (const line of lines) {
            if (line !== result.name && line.length > 3 && line.length < 200
                && !line.match(/^\\d/) && !line.includes('followers')) {
                result.headline = line;
                break;
            }
        }

        // Location
        for (const line of lines) {
            if (line !== result.name && line !== result.headline
                && (line.includes(',') || line.match(/^(Greater|San|New|London|Berlin|Tokyo|India|United)/))) {
                result.location = line;
                break;
            }
        }

        if (result.name) data.results.push(result);
    }

    return JSON.stringify(data);
})()
"""


class SearchExtractor(BaseExtractor):
    """Extracts people and company search results."""

    async def extract(self, keyword: str = "", search_type: str = "people", **kwargs) -> dict:
        url = await self._get_url()

        if search_type == "company":
            return await self._extract_company_search(url, keyword)
        else:
            return await self._extract_people_search(url, keyword)

    async def _extract_people_search(self, current_url: str, keyword: str) -> dict:
        """Extract people search results."""
        if keyword and f"keywords={keyword}" not in current_url:
            target = f"https://www.linkedin.com/search/results/people/?keywords={keyword}"
            await self.client.navigate(target)
            await self._wait_for_element('[role="listitem"]', timeout_ms=8000)

        raw = await self._eval(EXTRACT_PEOPLE_SEARCH_JS)
        if not raw:
            return {"error": "Empty response from CDP"}

        try:
            data = __import__("json").loads(raw)
        except Exception as e:
            return {"error": f"Failed to parse response: {e}"}

        if "error" in data:
            return data

        results = []
        for r in data.get("results", []):
            results.append(SearchResult(
                name=r.get("name", ""),
                headline=r.get("headline", ""),
                location=r.get("location", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                result_type="person",
            ).__dict__)

        return {
            "url": data.get("url", current_url),
            "query": data.get("query", keyword),
            "search_type": "people",
            "result_count": len(results),
            "results": results,
        }

    async def _extract_company_search(self, current_url: str, keyword: str) -> dict:
        """Extract company search results."""
        if keyword and f"keywords={keyword}" not in current_url:
            target = f"https://www.linkedin.com/search/results/companies/?keywords={keyword}"
            await self.client.navigate(target)
            await self._wait_for_element('[role="listitem"]', timeout_ms=8000)

        raw = await self._eval(EXTRACT_COMPANY_SEARCH_JS)
        if not raw:
            return {"error": "Empty response from CDP"}

        try:
            data = __import__("json").loads(raw)
        except Exception as e:
            return {"error": f"Failed to parse response: {e}"}

        if "error" in data:
            return data

        results = []
        for r in data.get("results", []):
            results.append(SearchResult(
                name=r.get("name", ""),
                headline=r.get("headline", ""),
                location=r.get("location", ""),
                url=r.get("url", ""),
                result_type="company",
            ).__dict__)

        return {
            "url": data.get("url", current_url),
            "query": data.get("query", keyword),
            "search_type": "company",
            "result_count": len(results),
            "results": results,
        }
