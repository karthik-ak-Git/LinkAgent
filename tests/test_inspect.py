"""Inspect LinkedIn DOM to fix selectors."""
import sys
sys.path.insert(0, r"D:\LinkAgent")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import json
from linkagent_mcp.cdp.browser import BrowserManager
from linkagent_mcp.cdp.client import CDPClient


async def inspect_profile(client):
    print("\n=== PROFILE PAGE INSPECTION ===")
    await client.navigate("https://www.linkedin.com/in/satyanadella/")
    await asyncio.sleep(4)
    url = await client.get_url()
    print(f"URL: {url}")

    js = """
    (() => {
        const h1 = document.querySelector('h1');
        const title = document.title;
        const allH1 = [...document.querySelectorAll('h1')].map(e => e.innerText.trim()).filter(Boolean);
        const sections = [...document.querySelectorAll('section')].map(s => s.getAttribute('aria-label')).filter(Boolean);
        const bodySnippet = document.body.innerText.substring(0, 500);
        return JSON.stringify({title, h1: h1?.innerText, allH1, sections, bodySnippet});
    })()
    """
    raw = await client.evaluate(js)
    data = json.loads(raw)
    print(f"Title: {data['title']}")
    print(f"H1: {data.get('h1', 'NONE')}")
    print(f"All H1s: {data['allH1']}")
    print(f"Sections: {data['sections']}")
    print(f"Body snippet: {data['bodySnippet'][:400]}")


async def inspect_company(client):
    print("\n=== COMPANY PAGE INSPECTION ===")
    await client.navigate("https://www.linkedin.com/company/microsoft/")
    await asyncio.sleep(4)
    url = await client.get_url()
    print(f"URL: {url}")

    js = """
    (() => {
        const h1 = document.querySelector('h1');
        const title = document.title;
        const allH1 = [...document.querySelectorAll('h1')].map(e => e.innerText.trim()).filter(Boolean);
        const sections = [...document.querySelectorAll('section')].map(s => s.getAttribute('aria-label')).filter(Boolean);
        const bodySnippet = document.body.innerText.substring(0, 500);
        return JSON.stringify({title, h1: h1?.innerText, allH1, sections, bodySnippet});
    })()
    """
    raw = await client.evaluate(js)
    data = json.loads(raw)
    print(f"Title: {data['title']}")
    print(f"H1: {data.get('h1', 'NONE')}")
    print(f"All H1s: {data['allH1']}")
    print(f"Sections: {data['sections']}")
    print(f"Body snippet: {data['bodySnippet'][:400]}")


async def inspect_jobs(client):
    print("\n=== JOBS PAGE INSPECTION ===")
    await client.navigate("https://www.linkedin.com/jobs/search/?keywords=python+developer")
    await asyncio.sleep(4)
    url = await client.get_url()
    print(f"URL: {url}")

    js = """
    (() => {
        const title = document.title;
        const sections = [...document.querySelectorAll('section')].map(s => s.getAttribute('aria-label')).filter(Boolean);
        const bodySnippet = document.body.innerText.substring(0, 800);
        const jobCards = document.querySelectorAll('[class*="job-card"], [class*="jobs-search"]');
        return JSON.stringify({title, sections, bodySnippet, jobCardCount: jobCards.length});
    })()
    """
    raw = await client.evaluate(js)
    data = json.loads(raw)
    print(f"Title: {data['title']}")
    print(f"Sections: {data['sections']}")
    print(f"Job cards found: {data['jobCardCount']}")
    print(f"Body snippet: {data['bodySnippet'][:600]}")


async def inspect_search(client):
    print("\n=== SEARCH PAGE INSPECTION ===")
    await client.navigate("https://www.linkedin.com/search/results/people/?keywords=software+engineer")
    await asyncio.sleep(4)
    url = await client.get_url()
    print(f"URL: {url}")

    js = """
    (() => {
        const title = document.title;
        const sections = [...document.querySelectorAll('section')].map(s => s.getAttribute('aria-label')).filter(Boolean);
        const bodySnippet = document.body.innerText.substring(0, 800);
        const resultCards = document.querySelectorAll('[class*="entity-result"], [class*="reusable-search"]');
        return JSON.stringify({title, sections, bodySnippet, resultCardCount: resultCards.length});
    })()
    """
    raw = await client.evaluate(js)
    data = json.loads(raw)
    print(f"Title: {data['title']}")
    print(f"Sections: {data['sections']}")
    print(f"Result cards found: {data['resultCardCount']}")
    print(f"Body snippet: {data['bodySnippet'][:600]}")


async def main():
    bm = BrowserManager(cdp_port=9222)
    tab = bm.find_tab("linkedin.com")
    if not tab:
        print("ERROR: No LinkedIn tab found")
        return
    print(f"Connected to: {tab.title}")
    client = CDPClient(tab.ws_url)

    await inspect_profile(client)
    await inspect_company(client)
    await inspect_jobs(client)
    await inspect_search(client)


if __name__ == "__main__":
    asyncio.run(main())
