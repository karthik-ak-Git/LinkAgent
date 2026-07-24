"""
LinkedIn Profile Extractor.

Extracts person profile data including name, headline, location, about,
connections, experience, education, and skills.

Selector strategy:
    - Name: H2 (not H1 — LinkedIn uses H2 for profile names)
    - Headline/location: Body text line parsing after name
    - Sections: H2-based extraction (About, Experience, Education, Skills)
    - Experience items: <li> elements within section
"""

from ....core.base import BaseExtractor
from ....core.models import Profile


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

    // Name — use H2 (LinkedIn profile pages use H2 for the name, not H1)
    const h2s = [...document.querySelectorAll('h2')];
    const nameH2 = h2s.find(h => {
        const text = h.innerText.trim();
        return text && text.length > 1 && text.length < 60
            && !text.includes('notifications') && !text.includes('Ad Options')
            && !text.includes("Don't");
    });
    if (nameH2) data.name = nameH2.innerText.trim();

    // Headline — text below name, look for job title pattern
    const allText = document.body.innerText;
    const lines = allText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
    const nameIdx = lines.findIndex(l => l === data.name);
    if (nameIdx >= 0) {
        // Next non-empty line after name is usually the headline
        for (let i = nameIdx + 1; i < Math.min(nameIdx + 5, lines.length); i++) {
            const line = lines[i];
            if (line.length > 5 && line.length < 200 && line !== data.name
                && !line.includes('More') && !line.includes('Message') && !line.includes('Follow')
                && !line.includes('verification') && !line.includes('connections')) {
                data.headline = line;
                break;
            }
        }
        // Location — often after headline, contains city/country patterns
        for (let i = nameIdx + 1; i < Math.min(nameIdx + 8, lines.length); i++) {
            const line = lines[i];
            if ((line.includes(',') || line.includes('Area') || line.includes('India')
                || line.includes('United') || line.includes('Germany') || line.includes('Remote'))
                && line.length < 100 && !line.includes('followers') && !line.includes('connections')) {
                data.location = line;
                break;
            }
        }
    }

    // Connections
    const connMatch = allText.match(/(\\d+[\\d,.]*\\s*connections?)/i);
    if (connMatch) data.connections = connMatch[1];

    // About section — find by H2 "About" and grab the section content
    const aboutH2 = h2s.find(h => h.innerText.trim().startsWith('About'));
    if (aboutH2) {
        const section = aboutH2.closest('section') || aboutH2.parentElement;
        if (section) {
            // Get all text in this section, skip the heading itself
            const sectionText = section.innerText;
            const aboutStart = sectionText.indexOf('About');
            if (aboutStart >= 0) {
                data.about = sectionText.substring(aboutStart + 5, aboutStart + 2000).trim();
                // Clean up: remove next section heading if present
                const nextSection = data.about.search(/\\n(Experience|Education|Skills|Projects|Recommendations)/);
                if (nextSection > 0) data.about = data.about.substring(0, nextSection).trim();
            }
        }
    }

    // Experience section
    const expH2 = h2s.find(h => h.innerText.trim().startsWith('Experience'));
    if (expH2) {
        const section = expH2.closest('section') || expH2.parentElement;
        if (section) {
            const items = section.querySelectorAll('li');
            for (const item of items) {
                const text = item.innerText.trim();
                if (text.length > 5 && text.length < 500) {
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                    if (lines.length >= 1) {
                        data.experience.push({
                            title: lines[0] || '',
                            company: lines[1] || '',
                            dateRange: lines.find(l => l.match(/\\d{4}|Present|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec/)) || '',
                        });
                    }
                }
            }
        }
    }

    // Education section
    const eduH2 = h2s.find(h => h.innerText.trim().startsWith('Education'));
    if (eduH2) {
        const section = eduH2.closest('section') || eduH2.parentElement;
        if (section) {
            const items = section.querySelectorAll('li');
            for (const item of items) {
                const text = item.innerText.trim();
                if (text.length > 5 && text.length < 300) {
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                    if (lines.length >= 1) {
                        data.education.push({
                            school: lines[0] || '',
                            degree: lines[1] || '',
                        });
                    }
                }
            }
        }
    }

    // Skills section
    const skillsH2 = h2s.find(h => h.innerText.trim().startsWith('Skills'));
    if (skillsH2) {
        const section = skillsH2.closest('section') || skillsH2.parentElement;
        if (section) {
            const items = section.querySelectorAll('li');
            for (const item of items) {
                const text = item.innerText.trim();
                if (text.length > 1 && text.length < 100) {
                    // First line of each skill item is usually the skill name
                    const skillName = text.split('\\n')[0].trim();
                    if (skillName) data.skills.push(skillName);
                }
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
            await self._wait_for_element("h2", timeout_ms=8000)

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
