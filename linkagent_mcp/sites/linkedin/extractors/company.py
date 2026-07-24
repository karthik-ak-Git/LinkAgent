"""
Company page extractor — extracts LinkedIn company page data.
"""

from ....core.base import BaseExtractor
from ....core.models import Company


EXTRACT_COMPANY_JS = """
(() => {
    const url = location.href;
    if (!url.includes('/company/')) return JSON.stringify({error: 'Not a company page', url});

    const data = {
        url: url,
        name: '',
        headline: '',
        about: '',
        website: '',
        industry: '',
        size: '',
        headquarters: '',
        founded: '',
        employees_count: '',
        followers: '',
        posts: [],
    };

    // Company name — H1 works for company pages
    const h1 = document.querySelector('h1');
    if (h1) data.name = h1.innerText.trim();

    // Parse body text for structured info
    const bodyText = document.body.innerText;

    // Followers
    const followerMatch = bodyText.match(/(\\d[\\d,.]*[MK]?\\s*followers)/i);
    if (followerMatch) data.followers = followerMatch[1];

    // Employees
    const employeeMatch = bodyText.match(/(\\d[\\d,.]*[MK+]*\\s*employees)/i);
    if (employeeMatch) data.employees_count = employeeMatch[1];

    // Industry — look for text after "Industry" label
    const industryMatch = bodyText.match(/Industry\\s*\\n([^\\n]+)/i);
    if (industryMatch) data.industry = industryMatch[1].trim();

    // Company size
    const sizeMatch = bodyText.match(/Company size\\s*\\n([^\\n]+)/i);
    if (sizeMatch) data.size = sizeMatch[1].trim();

    // Headquarters
    const hqMatch = bodyText.match(/Headquarters?\\s*\\n([^\\n]+)/i);
    if (hqMatch) data.headquarters = hqMatch[1].trim();

    // Founded
    const foundedMatch = bodyText.match(/Founded\\s*\\n([^\\n]+)/i);
    if (foundedMatch) data.founded = foundedMatch[1].trim();

    // Website — look for external link in the page
    const websiteLinks = document.querySelectorAll('a[href^="http"]');
    for (const link of websiteLinks) {
        const href = link.href;
        if (href && !href.includes('linkedin.com') && !href.includes('google')
            && !href.includes('javascript') && link.innerText.trim().length > 0) {
            data.website = href;
            break;
        }
    }

    // About section — find H2 "Overview" and grab content
    const h2s = [...document.querySelectorAll('h2')];
    const overviewH2 = h2s.find(h => h.innerText.trim().startsWith('Overview'));
    if (overviewH2) {
        const section = overviewH2.closest('section') || overviewH2.parentElement;
        if (section) {
            const sectionText = section.innerText;
            const start = sectionText.indexOf('Overview');
            if (start >= 0) {
                data.about = sectionText.substring(start + 8, start + 2000).trim();
                // Clean up: remove next section heading
                const nextSection = data.about.search(/\\n(Posts|Jobs|Life|People|Home)/);
                if (nextSection > 0) data.about = data.about.substring(0, nextSection).trim();
            }
        }
    }

    // Posts section
    const postsH2 = h2s.find(h => h.innerText.trim().startsWith('Posts'));
    if (postsH2) {
        const section = postsH2.closest('section') || postsH2.parentElement;
        if (section) {
            const postItems = section.querySelectorAll('[role="article"], li');
            for (const item of [...postItems].slice(0, 5)) {
                const text = item.innerText.trim();
                if (text.length > 10 && text.length < 1000) {
                    data.posts.push({text: text.substring(0, 500)});
                }
            }
        }
    }

    return JSON.stringify(data);
})()
"""


class CompanyExtractor(BaseExtractor):
    """Extracts company data from a LinkedIn /company/ page."""

    async def extract(self, company_name: str = "", **kwargs) -> dict:
        url = await self._get_url()

        # Navigate if needed
        if company_name and f"/company/{company_name}" not in url:
            target = f"https://www.linkedin.com/company/{company_name}"
            await self.client.navigate(target)
            await self._wait_for_element("h1", timeout_ms=8000)

        if "/company/" not in url:
            return {"error": f"Not a company page. Current URL: {url}"}

        raw = await self._eval(EXTRACT_COMPANY_JS)
        if not raw:
            return {"error": "Empty response from CDP"}

        try:
            data = __import__("json").loads(raw)
        except Exception as e:
            return {"error": f"Failed to parse response: {e}"}

        if "error" in data:
            return data

        company = Company(
            name=data.get("name", ""),
            headline=data.get("headline", ""),
            about=data.get("about", ""),
            website=data.get("website", ""),
            industry=data.get("industry", ""),
            size=data.get("size", ""),
            headquarters=data.get("headquarters", ""),
            founded=data.get("founded", ""),
            company_url=data.get("url", url),
            employees=[],  # Employee list not reliably extractable
            posts=data.get("posts", []),
        )

        return {
            "url": company.company_url,
            "name": company.name,
            "headline": company.headline,
            "about": company.about,
            "website": company.website,
            "industry": company.industry,
            "size": company.size,
            "headquarters": company.headquarters,
            "founded": company.founded,
            "followers": data.get("followers", ""),
            "employees_count": data.get("employees_count", ""),
            "post_count": len(company.posts),
            "posts": company.posts,
        }
