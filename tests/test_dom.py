"""Deep DOM inspection to find correct selectors."""
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

    # Check search page DOM structure
    await client.navigate("https://www.linkedin.com/search/results/people/?keywords=software+engineer")
    await asyncio.sleep(5)

    js = """
    (() => {
        // Find all elements with "result" in class
        const resultClasses = new Set();
        document.querySelectorAll('*').forEach(el => {
            el.classList.forEach(c => {
                if (c.includes('result') || c.includes('entity') || c.includes('search'))
                    resultClasses.add(c);
            });
        });

        // Find list items
        const listItems = document.querySelectorAll('li');
        const liInfo = [...listItems].slice(0, 5).map(li => ({
            classes: [...li.classList],
            childCount: li.children.length,
            textSnippet: li.innerText.substring(0, 100)
        }));

        // Find any card-like elements
        const cards = document.querySelectorAll('[data-view-name], [data-view-action], [data-container-id]');
        const cardInfo = [...cards].slice(0, 5).map(c => ({
            tag: c.tagName,
            classes: [...c.classList].slice(0, 5),
            dataAttrs: Object.keys(c.dataset).slice(0, 5),
            text: c.innerText.substring(0, 80)
        }));

        return JSON.stringify({
            resultClasses: [...resultClasses].slice(0, 30),
            listItemCount: listItems.length,
            liInfo,
            cardCount: cards.length,
            cardInfo
        });
    })()
    """
    raw = await client.evaluate(js)
    data = json.loads(raw)
    print("Result-related classes:", data["resultClasses"])
    print(f"\nList items: {data['listItemCount']}")
    for i, li in enumerate(data["liInfo"], 1):
        print(f"  LI {i}: classes={li['classes'][:3]}, text={li['textSnippet'][:80]}")
    print(f"\nCard-like elements: {data['cardCount']}")
    for i, card in enumerate(data["cardInfo"], 1):
        print(f"  Card {i}: tag={card['tag']}, classes={card['classes']}, data={card['dataAttrs']}")
        print(f"    text: {card['text'][:80]}")

    # Now check profile page
    await client.navigate("https://www.linkedin.com/in/satyanadella/")
    await asyncio.sleep(5)

    js2 = """
    (() => {
        // Find profile-specific elements
        const bodyText = document.body.innerText;
        const nameMatch = bodyText.match(/Satya Nadella/);

        // Look for section headings
        const headings = [...document.querySelectorAll('h2, h3')].map(h => ({
            tag: h.tagName,
            text: h.innerText.trim().substring(0, 60),
            classes: [...h.classList].slice(0, 3)
        })).slice(0, 15);

        // Look for about/experience sections
        const sections = [...document.querySelectorAll('section')].map(s => ({
            label: s.getAttribute('aria-label'),
            id: s.id,
            classes: [...s.classList].slice(0, 3)
        })).filter(s => s.label || s.id);

        // Find text containing key profile terms
        const aboutEl = [...document.querySelectorAll('*')].find(el =>
            el.innerText && el.innerText.includes('Chairman and CEO') && el.children.length < 5
        );

        return JSON.stringify({
            nameFound: bool(nameMatch),
            headings,
            sections,
            aboutText: aboutEl?.innerText?.substring(0, 200) || 'NOT FOUND'
        });
    })()
    """
    raw2 = await client.evaluate(js2)
    data2 = json.loads(raw2)
    print("\n\n=== PROFILE DEEP INSPECTION ===")
    print(f"Name found in body: {data2['nameFound']}")
    print(f"\nHeadings:")
    for h in data2["headings"]:
        print(f"  {h['tag']}: {h['text'][:50]} | classes={h['classes']}")
    print(f"\nSections:")
    for s in data2["sections"]:
        print(f"  id={s['id']}, label={s['label']}, classes={s['classes']}")
    print(f"\nAbout text: {data2['aboutText'][:200]}")


if __name__ == "__main__":
    asyncio.run(main())
