"""
Job extractor — extracts job search results and job details.
"""

from .base import BaseExtractor
from ..types.models import Job


EXTRACT_JOB_SEARCH_JS = """
(() => {
    const url = location.href;
    if (!url.includes('/jobs/')) return JSON.stringify({error: 'Not a jobs page', url});

    const data = {
        url: url,
        query: new URLSearchParams(location.search).get('keywords') || '',
        results: [],
    };

    const cards = document.querySelectorAll('.jobs-search-results__list-item, li.jobs-search-results__result-card');
    for (const card of cards) {
        const titleEl = card.querySelector('.job-card-list__title--link, a.job-card-container__link');
        const companyEl = card.querySelector('.artdeco-entity-lockup__subtitle, .job-card-container__primary-description');
        const locationEl = card.querySelector('.artdeco-entity-lockup__caption, .job-card-container__metadata-item');
        const dateEl = card.querySelector('.job-card-container__listed-time, .t-date');
        const linkEl = card.querySelector('a[href*="/jobs/view/"]');

        const job = {};
        if (titleEl) job.title = titleEl.innerText.trim();
        if (companyEl) job.company = companyEl.innerText.trim();
        if (locationEl) job.location = locationEl.innerText.trim();
        if (dateEl) job.posted = dateEl.innerText.trim();
        if (linkEl) job.url = linkEl.href;

        if (job.title) data.results.push(job);
    }

    return JSON.stringify(data);
})()
"""


EXTRACT_JOB_DETAIL_JS = """
(() => {
    const url = location.href;
    if (!url.includes('/jobs/view/')) return JSON.stringify({error: 'Not a job detail page', url});

    const data = {
        url: url,
        title: '',
        company: '',
        location: '',
        description: '',
        posted: '',
        applicants: '',
        employment_type: '',
        seniority_level: '',
        easy_apply: false,
    };

    // Title
    const h1 = document.querySelector('h1');
    if (h1) data.title = h1.innerText.trim();

    // Company
    const companyEl = document.querySelector('.jobs-unified-top-card__company-name a, .jobs-unified-top-card__company-name');
    if (companyEl) data.company = companyEl.innerText.trim();

    // Location
    const locationEl = document.querySelector('.jobs-unified-top-card__bullet, .jobs-unified-top-card__primary-description span');
    if (locationEl) data.location = locationEl.innerText.trim();

    // Posted date and applicants
    const postedEl = document.querySelector('.jobs-unified-top-card__listed-time, .t-black--light.t-normal');
    if (postedEl) {
        const text = postedEl.innerText.trim();
        if (text.includes('ago')) data.posted = text;
        if (text.includes('applicant')) data.applicants = text;
    }

    // Easy Apply button
    const easyApplyBtn = document.querySelector('button.jobs-apply-button, button[aria-label*="Easy Apply"]');
    if (easyApplyBtn) data.easy_apply = true;

    // Description
    const descContainer = document.querySelector('.jobs-description, .jobs-box__html-content');
    if (descContainer) {
        data.description = descContainer.innerText.trim().substring(0, 5000);
    }

    // Job details (employment type, seniority level, etc.)
    const detailItems = document.querySelectorAll('.jobs-unified-top-card__job-insight span');
    for (const item of detailItems) {
        const text = item.innerText.trim();
        if (text.includes('Full-time') || text.includes('Part-time') || text.includes('Contract')) {
            data.employment_type = text;
        }
        if (text.includes('Entry') || text.includes('Mid') || text.includes('Senior') || text.includes('Director') || text.includes('Executive')) {
            data.seniority_level = text;
        }
    }

    return JSON.stringify(data);
})()
"""


class JobExtractor(BaseExtractor):
    """Extracts job search results and job details."""

    async def extract(self, keyword: str = "", job_id: str = "", **kwargs) -> dict:
        url = await self._get_url()

        # Job detail page
        if job_id or "/jobs/view/" in url:
            return await self._extract_detail(url, job_id)

        # Job search page
        if keyword or "/jobs/search" in url:
            return await self._extract_search(url, keyword)

        return {"error": f"Not a jobs page. Current URL: {url}"}

    async def _extract_search(self, current_url: str, keyword: str) -> dict:
        """Extract job search results."""
        if keyword and f"keywords={keyword}" not in current_url:
            target = f"https://www.linkedin.com/jobs/search/?keywords={keyword}"
            await self.client.navigate(target)
            await self._wait_for_element(".jobs-search-results__list-item", timeout_ms=8000)

        raw = await self._eval(EXTRACT_JOB_SEARCH_JS)
        if not raw:
            return {"error": "Empty response from CDP"}

        try:
            data = __import__("json").loads(raw)
        except Exception as e:
            return {"error": f"Failed to parse response: {e}"}

        if "error" in data:
            return data

        jobs = []
        for j in data.get("results", []):
            jobs.append(Job(
                title=j.get("title", ""),
                company=j.get("company", ""),
                location=j.get("location", ""),
                posted=j.get("posted", ""),
                job_url=j.get("url", ""),
            ).__dict__)

        return {
            "url": data.get("url", current_url),
            "query": data.get("query", keyword),
            "result_count": len(jobs),
            "results": jobs,
        }

    async def _extract_detail(self, current_url: str, job_id: str) -> dict:
        """Extract a single job detail."""
        if job_id and job_id not in current_url:
            target = f"https://www.linkedin.com/jobs/view/{job_id}"
            await self.client.navigate(target)
            await self._wait_for_element("h1", timeout_ms=8000)

        raw = await self._eval(EXTRACT_JOB_DETAIL_JS)
        if not raw:
            return {"error": "Empty response from CDP"}

        try:
            data = __import__("json").loads(raw)
        except Exception as e:
            return {"error": f"Failed to parse response: {e}"}

        if "error" in data:
            return data

        job = Job(
            title=data.get("title", ""),
            company=data.get("company", ""),
            location=data.get("location", ""),
            description=data.get("description", ""),
            posted=data.get("posted", ""),
            applicants=data.get("applicants", ""),
            employment_type=data.get("employment_type", ""),
            seniority_level=data.get("seniority_level", ""),
            job_url=data.get("url", current_url),
            easy_apply=data.get("easy_apply", False),
        )

        return {
            "url": job.job_url,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "posted": job.posted,
            "applicants": job.applicants,
            "employment_type": job.employment_type,
            "seniority_level": job.seniority_level,
            "easy_apply": job.easy_apply,
        }
