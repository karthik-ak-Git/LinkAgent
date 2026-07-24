"""
Profile page extractor — extracts person profile data.
"""

from .base import BaseExtractor
from ..types.models import Profile


EXTRACT_PROFILE_JS = """
(() => {
    const url = location.href;
    if (!url.includes('/in/')) return JSON.stringify({error: 'Not a profile page', url});

    const data = {
        url: url,
        name: '',
        headline: '',
        location: '',
        about: '',
        connections: '',
        experience: [],
        education: [],
        skills: [],
    };

    // Name — top heading
    const h1 = document.querySelector('h1');
    if (h1) data.name = h1.innerText.trim();

    // Headline — text directly below name
    const headlineEl = document.querySelector('.text-body-medium.break-words');
    if (headlineEl) data.headline = headlineEl.innerText.trim();

    // Location — near the headline
    const spans = document.querySelectorAll('.text-body-small.inline.t-black--light.break-words');
    for (const span of spans) {
        const text = span.innerText.trim();
        if (text && !text.includes(' connections') && text.length < 100) {
            data.location = text;
            break;
        }
    }

    // Connections
    const connLinks = document.querySelectorAll('a[href*="connections"]');
    for (const link of connLinks) {
        const text = link.innerText.trim();
        if (text.includes('connection')) {
            data.connections = text;
            break;
        }
    }

    // About section
    const aboutSection = document.querySelector('#about');
    if (aboutSection) {
        let container = aboutSection.closest('section') || aboutSection.parentElement;
        if (container) {
            const aboutText = container.querySelector('.inline-show-more-text, .display-flex.align-items-center.t-14.t-normal');
            if (aboutText) data.about = aboutText.innerText.trim();
        }
    }

    // Experience section
    const expSection = document.querySelector('#experience');
    if (expSection) {
        let container = expSection.closest('section') || expSection.parentElement;
        if (container) {
            const items = container.querySelectorAll('li.artdeco-list__item');
            for (const item of items) {
                const title = item.querySelector('.display-flex.align-items-center.t-14.t-normal');
                const company = item.querySelector('.t-14.t-normal.t-black');
                const dateRange = item.querySelector('.t-14.t-normal.t-black--light');
                if (title) {
                    data.experience.push({
                        title: title.innerText.trim(),
                        company: company ? company.innerText.trim() : '',
                        dateRange: dateRange ? dateRange.innerText.trim() : '',
                    });
                }
            }
        }
    }

    // Education section
    const eduSection = document.querySelector('#education');
    if (eduSection) {
        let container = eduSection.closest('section') || eduSection.parentElement;
        if (container) {
            const items = container.querySelectorAll('li.artdeco-list__item');
            for (const item of items) {
                const school = item.querySelector('.display-flex.align-items-center.t-14.t-normal');
                const degree = item.querySelector('.t-14.t-normal.t-black');
                if (school) {
                    data.education.push({
                        school: school.innerText.trim(),
                        degree: degree ? degree.innerText.trim() : '',
                    });
                }
            }
        }
    }

    // Skills
    const skillsSection = document.querySelector('#skills');
    if (skillsSection) {
        let container = skillsSection.closest('section') || skillsSection.parentElement;
        if (container) {
            const skillItems = container.querySelectorAll('.display-flex.align-items-center.t-14.t-normal span[aria-hidden="true"]');
            for (const skill of skillItems) {
                const text = skill.innerText.trim();
                if (text && text.length > 1) data.skills.push(text);
            }
        }
    }

    return JSON.stringify(data);
})()
"""


class ProfileExtractor(BaseExtractor):
    """Extracts person profile data from a LinkedIn /in/ page."""

    async def extract(self, username: str = "", **kwargs) -> dict:
        url = await self._get_url()

        # Navigate if needed
        if username and f"/in/{username}" not in url:
            target = f"https://www.linkedin.com/in/{username}"
            await self.client.navigate(target)
            await self._wait_for_element("h1", timeout_ms=8000)

        if "/in/" not in url:
            return {"error": f"Not a profile page. Current URL: {url}"}

        raw = await self._eval(EXTRACT_PROFILE_JS)
        if not raw:
            return {"error": "Empty response from CDP"}

        try:
            data = __import__("json").loads(raw)
        except Exception as e:
            return {"error": f"Failed to parse response: {e}"}

        if "error" in data:
            return data

        profile = Profile(
            name=data.get("name", ""),
            headline=data.get("headline", ""),
            location=data.get("location", ""),
            about=data.get("about", ""),
            connections=data.get("connections", ""),
            profile_url=data.get("url", url),
            experience=data.get("experience", []),
            education=data.get("education", []),
            skills=data.get("skills", []),
        )

        return {
            "url": profile.profile_url,
            "name": profile.name,
            "headline": profile.headline,
            "location": profile.location,
            "about": profile.about,
            "connections": profile.connections,
            "experience": profile.experience,
            "education": profile.education,
            "skills": profile.skills,
        }
