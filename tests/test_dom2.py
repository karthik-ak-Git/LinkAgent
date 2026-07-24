"""Find working selectors using ARIA, roles, and semantic HTML."""
import sys
sys.path.insert(0, r"D:\LinkAgent")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import json
from linkagent_mcp.cdp.browser import BrowserManager
from linkagent_mcp.cdp.client import CDPClient


async def main():
    bm = BrowserManager(cdp_port=9222)
    tab = bm.find_tab("linkedin.com")
    client = CDPClient(tab.ws_url)

    # ── SEARCH PAGE ──
    print("=" * 60)
    print("SEARCH PAGE: people search")
    print("=" * 60)
    await client.navigate("https://www.linkedin.com/search/results/people/?keywords=software+engineer")
    await asyncio.sleep(5)

    js = """
    (() => {
        // Use ARIA and role-based selectors
        const results = [];

        // Method 1: Look for list items with profile links
        const profileLinks = document.querySelectorAll('a[href*="/in/"]');
        for (const link of profileLinks) {
            const name = link.querySelector('span[aria-hidden="true"]');
            if (name) {
                const li = link.closest('li') || link.closest('[role="listitem"]') || link.parentElement?.parentElement;
                const headline = li?.querySelector('[class*="entity-result__primary-subtitle"], [aria-label*="headline"]');
                const location = li?.querySelector('[class*="entity-result__secondary-subtitle"]');
                results.push({
                    name: name.innerText.trim(),
                    url: link.href,
                    headline: headline?.innerText?.trim() || '',
                    location: location?.innerText?.trim() || '',
                    parentTag: li?.tagName,
                    parentClasses: li ? [...li.classList].slice(0, 3) : [],
                });
            }
        }

        // Method 2: ARIA roles
        const roleList = document.querySelectorAll('[role="list"], [role="listitem"]');
        const ariaItems = [...roleList].slice(0, 5).map(el => ({
            role: el.getAttribute('role'),
            tag: el.tagName,
            text: el.innerText.substring(0, 100)
        }));

        // Method 3: All section labels
        const sections = [...document.querySelectorAll('section')].map(s => ({
            label: s.getAttribute('aria-label'),
            id: s.id
        })).filter(s => s.label);

        return JSON.stringify({profileLinks: results.slice(0, 5), ariaItems, sections});
    })()
    """
    raw = await client.evaluate(js)
    data = json.loads(raw)
    print(f"Profile links found: {len(data['profileLinks'])}")
    for i, r in enumerate(data["profileLinks"], 1):
        print(f"  {i}. {r['name']} | {r['url'][:60]}")
        print(f"     headline: {r['headline'][:60]}")
        print(f"     parent: {r['parentTag']} classes={r['parentClasses']}")
    print(f"ARIA items: {data['ariaItems']}")
    print(f"Sections: {data['sections']}")

    # ── PROFILE PAGE ──
    print("\n" + "=" * 60)
    print("PROFILE PAGE: Satya Nadella")
    print("=" * 60)
    await client.navigate("https://www.linkedin.com/in/satyanadella/")
    await asyncio.sleep(5)

    js2 = """
    (() => {
        const result = {};

        // Find profile sections by heading text
        const allElements = document.body.innerText;
        result.bodyLength = allElements.length;

        // Look for h2 headings (About, Experience, Education, etc.)
        const h2s = [...document.querySelectorAll('h2')].map(h => h.innerText.trim());
        result.h2s = h2s;

        // Look for section IDs
        const sectionIds = [...document.querySelectorAll('section[id]')].map(s => s.id);
        result.sectionIds = sectionIds;

        // Try to find the name
        const spans = [...document.querySelectorAll('span')].filter(s =>
            s.innerText.trim() === 'Satya Nadella' && s.children.length === 0
        );
        result.nameSpans = spans.length;

        // Find "About" section
        const aboutHeading = [...document.querySelectorAll('h2')].find(h => h.innerText.includes('About'));
        if (aboutHeading) {
            const section = aboutHeading.closest('section');
            if (section) {
                const text = section.innerText.substring(0, 300);
                result.aboutSection = text;
            }
        }

        // Find "Experience" section
        const expHeading = [...document.querySelectorAll('h2')].find(h => h.innerText.includes('Experience'));
        if (expHeading) {
            const section = expHeading.closest('section');
            if (section) {
                result.experienceSection = section.innerText.substring(0, 300);
            }
        }

        return JSON.stringify(result);
    })()
    """
    raw2 = await client.evaluate(js2)
    data2 = json.loads(raw2)
    print(f"Body length: {data2['bodyLength']}")
    print(f"H2 headings: {data2['h2s']}")
    print(f"Section IDs: {data2['sectionIds']}")
    print(f"Name spans found: {data2['nameSpans']}")
    if data2.get("aboutSection"):
        print(f"About section: {data2['aboutSection'][:200]}")
    if data2.get("experienceSection"):
        print(f"Experience section: {data2['experienceSection'][:200]}")

    # ── COMPANY PAGE ──
    print("\n" + "=" * 60)
    print("COMPANY PAGE: Microsoft")
    print("=" * 60)
    await client.navigate("https://www.linkedin.com/company/microsoft/")
    await asyncio.sleep(5)

    js3 = """
    (() => {
        const result = {};
        result.title = document.title;
        const h1 = document.querySelector('h1');
        result.h1 = h1?.innerText?.trim();

        // H2 headings
        result.h2s = [...document.querySelectorAll('h2')].map(h => h.innerText.trim());

        // Section IDs
        result.sectionIds = [...document.querySelectorAll('section[id]')].map(s => s.id);

        // Body text with company info
        const bodyText = document.body.innerText;
        const followerMatch = bodyText.match(/[\d.]+[MK]?\s*followers/i);
        const employeeMatch = bodyText.match(/[\d.]+[MK+]?\s*employees/i);
        result.followers = followerMatch?.[0] || '';
        result.employees = employeeMatch?.[0] || '';

        // About text
        const aboutHeading = [...document.querySelectorAll('h2')].find(h => h.innerText.includes('About'));
        if (aboutHeading) {
            const section = aboutHeading.closest('section');
            if (section) result.aboutText = section.innerText.substring(0, 300);
        }

        return JSON.stringify(result);
    })()
    """
    raw3 = await client.evaluate(js3)
    data3 = json.loads(raw3)
    print(f"Title: {data3['title']}")
    print(f"H1: {data3.get('h1')}")
    print(f"H2s: {data3['h2s']}")
    print(f"Section IDs: {data3['sectionIds']}")
    print(f"Followers: {data3.get('followers')}")
    print(f"Employees: {data3.get('employees')}")
    if data3.get("aboutText"):
        print(f"About: {data3['aboutText'][:200]}")


if __name__ == "__main__":
    asyncio.run(main())
