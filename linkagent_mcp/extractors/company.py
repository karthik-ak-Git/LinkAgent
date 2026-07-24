"""
Company page extractor — extracts LinkedIn company page data.
"""

from .base import BaseExtractor
from ..types.models import Company


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
        employees: [],
        posts: [],
    };

    // Company name
    const h1 = document.querySelector('h1');
    if (h1) data.name = h1.innerText.trim();

    // Headline/tagline
    const headlineEl = document.querySelector('.org-top-card-summary__headline');
    if (headlineEl) data.headline = headlineEl.innerText.trim();

    // About section
    const aboutSection = document.querySelector('#about');
    if (aboutSection) {
        let container = aboutSection.closest('section') || aboutSection.parentElement;
        if (container) {
            const aboutText = container.querySelector('.inline-show-more-text, .org-about-module__description');
            if (aboutText) data.about = aboutText.innerText.trim();
        }
    }

    // Company details (industry, size, etc.)
    const detailItems = document.querySelectorAll('.org-about-module__org-details dd, .org-about-module__org-information');
    const labels = ['industry', 'size', 'headquarters', 'founded', 'website'];
    let detailIdx = 0;
    for (const item of detailItems) {
        const text = item.innerText.trim();
        if (text && detailIdx < labels.length) {
            data[labels[detailIdx]] = text;
            detailIdx++;
        }
    }

    // Try alternative selectors for details
    if (!data.industry) {
        const industryEl = document.querySelector('[data-test="about-company__industry"]');
        if (industryEl) data.industry = industryEl.innerText.replace('Industry', '').trim();
    }
    if (!data.size) {
        const sizeEl = document.querySelector('[data-test="about-company__size"]');
        if (sizeEl) data.size = sizeEl.innerText.replace('Company size', '').trim();
    }

    // Website
    if (!data.website) {
        const websiteLink = document.querySelector('a[href*="http"][data-test="about-company__website"]');
        if (websiteLink) data.website = websiteLink.href;
    }

    // Recent posts
    const postSection = document.querySelector('.org-page-details__feed');
    if (postSection) {
        const postItems = postSection.querySelectorAll('.org-update__card');
        for (const item of postItems) {
            const text = item.querySelector('.org-update__text');
            const date = item.querySelector('.org-update__date');
            if (text) {
                data.posts.push({
                    text: text.innerText.trim().substring(0, 500),
                    date: date ? date.innerText.trim() : '',
                });
            }
        }
    }

    // Employees (top list on page)
    const empSection = document.querySelector('.org-people profiles-list');
    if (empSection) {
        const empItems = empSection.querySelectorAll('li');
        for (const item of empItems) {
            const name = item.querySelector('.actor-name');
            const title = item.querySelector('.artdeco-entity-lockup__subtitle');
            if (name) {
                data.employees.push({
                    name: name.innerText.trim(),
                    title: title ? title.innerText.trim() : '',
                });
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
            employees=data.get("employees", []),
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
            "employee_count": len(company.employees),
            "employees": company.employees,
            "post_count": len(company.posts),
            "posts": company.posts,
        }
