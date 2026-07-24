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

    const cards = document.querySelectorAll('.reusable-search__result-container, li.reusable-search-simple-insight');
    for (const card of cards) {
        const nameEl = card.querySelector('.entity-result__title-text a, span.entity-result__title-text');
        const headlineEl = card.querySelector('.entity-result__primary-subtitle, .artdeco-entity-lockup__subtitle');
        const locationEl = card.querySelector('.entity-result__secondary-subtitle, .artdeco-entity-lockup__caption');
        const snippetEl = card.querySelector('.entity-result__summary');

        const result = {};
        if (nameEl) {
            result.name = nameEl.innerText.trim();
            const link = nameEl.closest('a') || nameEl.querySelector('a');
            if (link) result.url = link.href;
        }
        if (headlineEl) result.headline = headlineEl.innerText.trim();
        if (locationEl) result.location = locationEl.innerText.trim();
        if (snippetEl) result.snippet = snippetEl.innerText.trim();

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

    const cards = document.querySelectorAll('.reusable-search__result-container, li.reusable-search-simple-insight');
    for (const card of cards) {
        const nameEl = card.querySelector('.entity-result__title-text a, span.entity-result__title-text');
        const headlineEl = card.querySelector('.entity-result__primary-subtitle, .artdeco-entity-lockup__subtitle');
        const locationEl = card.querySelector('.entity-result__secondary-subtitle, .artdeco-entity-lockup__caption');

        const result = {};
        if (nameEl) {
            result.name = nameEl.innerText.trim();
            const link = nameEl.closest('a') || nameEl.querySelector('a');
            if (link) result.url = link.href;
        }
        if (headlineEl) result.headline = headlineEl.innerText.trim();
        if (locationEl) result.location = locationEl.innerText.trim();

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
            await self._wait_for_element(".entity-result__title-text", timeout_ms=8000)

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
            await self._wait_for_element(".entity-result__title-text", timeout_ms=8000)

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
