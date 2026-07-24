"""
LinkedIn Jobs Extractor.

Extracts job search results and individual job details including title,
company, location, description, employment type, and seniority level.

Selector strategy:
    - Job cards: .job-card-container DIVs (NOT [role="listitem"])
    - Job detail: H1 for title, body text parsing for metadata
    - Description: Text between "About the job" and next section
    - Tags: Easy Apply, Promoted detection
"""

from ....core.base import BaseExtractor
from ....core.models import Job


EXTRACT_JOB_SEARCH_JS = """
(() => {
    const url = location.href;
    if (!url.includes('/jobs/')) return JSON.stringify({error: 'Not a jobs page', url});

    const data = {
        url: url,
        query: new URLSearchParams(location.search).get('keywords') || '',
        results: [],
    };

    // Job cards use class "job-card-container" (DIVs, not LIs or role=listitem)
    const cards = document.querySelectorAll('.job-card-container');
    for (const card of cards) {
        const lines = card.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
        const result = {};

        // Find job detail link
        const link = card.querySelector('a[href*="/jobs/view/"]');
        if (link) result.url = link.href;

        // Title is typically the first meaningful line
        if (lines.length >= 1) result.title = lines[0];

        // Company is typically the second line
        if (lines.length >= 2) result.company = lines[1];

        // Location: line containing city/country patterns or "(On-site)" / "(Remote)"
        for (const line of lines) {
            if (line.match(/\\(On-site\\)|\\(Remote\\)|\\(Hybrid\\)|India|USA|London|Berlin|Remote/i)
                && line !== result.title && line !== result.company) {
                result.location = line;
                break;
            }
        }

        // Posted time: line containing "ago", "hour", "day", "week", "month"
        for (const line of lines) {
            if (line.match(/\\d+\\s*(hour|day|week|month|minute)s?\\s*ago/i)
                || line.match(/Just posted|Today|Yesterday/i)) {
                result.posted = line;
                break;
            }
        }

        // Salary: line containing currency symbols or "/yr" / "/hr"
        for (const line of lines) {
            if (line.match(/[₹$€£]|\\/yr|\\/hr|LPA|Lakh/i) && line !== result.title) {
                result.salary = line;
                break;
            }
        }

        // Tags (Easy Apply, Promoted, etc.)
        const tags = [];
        for (const line of lines) {
            if (line.match(/^Easy Apply$|^Promoted$|^Actively reviewing/i)) {
                tags.push(line);
            }
        }
        if (tags.length > 0) result.tags = tags;

        if (result.title) data.results.push(result);
    }

    // Get total result count from page text
    const bodyText = document.body.innerText;
    const countMatch = bodyText.match(/([\\d,]+\\+?)\\s*results?/i);
    if (countMatch) data.total_results = countMatch[1];

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

    // Title — H1 works for job detail pages
    const h1 = document.querySelector('h1');
    if (h1) data.title = h1.innerText.trim();

    // Parse body text for structured info
    const body = document.body.innerText;
    const lines = body.split('\\n').map(l => l.trim()).filter(Boolean);

    // Company — line after the title
    const titleIdx = lines.indexOf(data.title);
    if (titleIdx >= 0 && titleIdx + 1 < lines.length) {
        data.company = lines[titleIdx + 1];
    }

    // Location — line containing location patterns
    for (const line of lines) {
        if (line.match(/\\(On-site\\)|\\(Remote\\)|\\(Hybrid\\)|India|USA|London|Berlin/i)
            && line !== data.title && line !== data.company) {
            data.location = line;
            break;
        }
    }

    // Posted — line with "ago" or "posted"
    for (const line of lines) {
        if (line.match(/\\d+\\s*(hour|day|week|month)s?\\s*ago/i)
            || line.match(/Just posted|Today|Posted/i)) {
            data.posted = line;
            break;
        }
    }

    // Applicants
    for (const line of lines) {
        if (line.match(/\\d+\\s*applicant/i)) {
            data.applicants = line;
            break;
        }
    }

    // Easy Apply
    data.easy_apply = body.includes('Easy Apply') || !!document.querySelector('button[aria-label*="Easy Apply"]');

    // Employment type & seniority
    for (const line of lines) {
        if (line.match(/^Full-time|^Part-time|^Contract|^Internship|^Temporary/i)) {
            data.employment_type = line;
        }
        if (line.match(/^Entry|^Mid|^Senior|^Director|^Executive|^Associate/i)) {
            data.seniority_level = line;
        }
    }

    // Description — everything between "About the job" / "Description" and the next section
    const descStart = body.search(/About the job|Description|Job Description/i);
    if (descStart >= 0) {
        let descText = body.substring(descStart, descStart + 5000);
        // Cut off at next major section
        const cutPoints = descText.search(/\\n(Benefits|Perks|Company|Similar|Report|Save|Apply now|Show more)/i);
        if (cutPoints > 50) descText = descText.substring(0, cutPoints);
        data.description = descText.trim();
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
            await self._wait_for_element(".job-card-container", timeout_ms=8000)

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
