"""Test all extractors against live LinkedIn."""
import asyncio
import json
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from linkagent_mcp.cdp.browser import BrowserManager
from linkagent_mcp.cdp.client import CDPClient
from linkagent_mcp.sites.linkedin.extractors import (
    FeedExtractor, ProfileExtractor, CompanyExtractor,
    JobExtractor, SearchExtractor,
)

async def test_feed(client):
    print("\n" + "="*60)
    print("TEST 1: FEED EXTRACTOR")
    print("="*60)
    await client.navigate("https://www.linkedin.com/feed/")
    await asyncio.sleep(3)
    extractor = FeedExtractor(client)
    result = await extractor.extract()
    print(f"URL: {result.get('url', 'N/A')}")
    print(f"Post count: {result.get('post_count', 0)}")
    for i, post in enumerate(result.get('posts', [])[:3], 1):
        print(f"\n--- Post {i} ---")
        print(f"  Author: {post.get('author', 'N/A')}")
        print(f"  Headline: {post.get('headline', 'N/A')[:80]}")
        print(f"  Text: {post.get('text', 'N/A')[:100]}...")
        print(f"  Time: {post.get('time', 'N/A')}")
        print(f"  Likes: {post.get('likes', 'N/A')} | Comments: {post.get('comments', 'N/A')}")
    return result

async def test_profile(client):
    print("\n" + "="*60)
    print("TEST 2: PROFILE EXTRACTOR (navigate to a profile)")
    print("="*60)
    # Navigate to a LinkedIn profile first
    await client.navigate("https://www.linkedin.com/in/satyanadella/")
    await asyncio.sleep(3)
    extractor = ProfileExtractor(client)
    result = await extractor.extract()
    print(f"Name: {result.get('name', 'N/A')}")
    print(f"Headline: {result.get('headline', 'N/A')[:80]}")
    print(f"Location: {result.get('location', 'N/A')}")
    print(f"About: {result.get('about', 'N/A')[:120]}...")
    print(f"Experience count: {len(result.get('experience', []))}")
    print(f"Education count: {len(result.get('education', []))}")
    print(f"Skills count: {len(result.get('skills', []))}")
    return result

async def test_company(client):
    print("\n" + "="*60)
    print("TEST 3: COMPANY EXTRACTOR (navigate to a company)")
    print("="*60)
    await client.navigate("https://www.linkedin.com/company/microsoft/")
    await asyncio.sleep(3)
    extractor = CompanyExtractor(client)
    result = await extractor.extract()
    print(f"Name: {result.get('name', 'N/A')}")
    print(f"Headline: {result.get('headline', 'N/A')[:80]}")
    print(f"Industry: {result.get('industry', 'N/A')}")
    print(f"Size: {result.get('size', 'N/A')}")
    print(f"About: {result.get('about', 'N/A')[:120]}...")
    print(f"Posts: {result.get('post_count', 0)}")
    return result

async def test_jobs(client):
    print("\n" + "="*60)
    print("TEST 4: JOBS EXTRACTOR (search for jobs)")
    print("="*60)
    await client.navigate("https://www.linkedin.com/jobs/search/?keywords=python+developer")
    await asyncio.sleep(4)
    extractor = JobExtractor(client)
    result = await extractor.extract()
    print(f"Query: {result.get('query', 'N/A')}")
    print(f"Result count: {result.get('result_count', 0)}")
    for i, job in enumerate(result.get('results', [])[:3], 1):
        print(f"\n--- Job {i} ---")
        print(f"  Title: {job.get('title', 'N/A')}")
        print(f"  Company: {job.get('company', 'N/A')}")
        print(f"  Location: {job.get('location', 'N/A')}")
        print(f"  Posted: {job.get('posted', 'N/A')}")
    return result

async def test_search(client):
    print("\n" + "="*60)
    print("TEST 5: SEARCH EXTRACTOR (search for people)")
    print("="*60)
    await client.navigate("https://www.linkedin.com/search/results/people/?keywords=software+engineer")
    await asyncio.sleep(3)
    extractor = SearchExtractor(client)
    result = await extractor.extract()
    print(f"Query: {result.get('query', 'N/A')}")
    print(f"Search type: {result.get('search_type', 'N/A')}")
    print(f"Result count: {result.get('result_count', 0)}")
    for i, r in enumerate(result.get('results', [])[:3], 1):
        print(f"\n--- Result {i} ---")
        print(f"  Name: {r.get('name', 'N/A')}")
        print(f"  Headline: {r.get('headline', 'N/A')[:80]}")
        print(f"  Location: {r.get('location', 'N/A')}")
    return result

async def main():
    bm = BrowserManager(cdp_port=9222)
    tab = bm.find_tab("linkedin.com")
    if not tab:
        print("ERROR: No LinkedIn tab found. Open linkedin.com/feed in your browser.")
        return

    print(f"Connected to: {tab.title}")
    print(f"URL: {tab.url}")

    client = CDPClient(tab.ws_url)

    # Run all tests
    results = {}
    results['feed'] = await test_feed(client)
    results['profile'] = await test_profile(client)
    results['company'] = await test_company(client)
    results['jobs'] = await test_jobs(client)
    results['search'] = await test_search(client)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, res in results.items():
        status = "OK" if not res.get("error") else f"ERROR: {res['error']}"
        print(f"  {name.upper():12} {status}")

if __name__ == "__main__":
    asyncio.run(main())
