"""Inspect jobs page body text and job card structure."""
import asyncio, json
from websockets.asyncio.client import connect

async def get_ws_url():
    import urllib.request
    data = json.loads(urllib.request.urlopen("http://localhost:9222/json").read())
    for t in data:
        if t.get("type") == "page": return t["webSocketDebuggerUrl"]
    return data[0]["webSocketDebuggerUrl"]

async def evaluate(ws, js, msg_id=1):
    await ws.send(json.dumps({"id": msg_id, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True}}))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get("id") == msg_id:
            return resp.get("result", {}).get("result", {}).get("value")

async def main():
    ws_url = await get_ws_url()
    async with connect(ws_url, max_size=2**24) as ws:
        mid = [0]
        def nm():
            mid[0] += 1; return mid[0]
        await ws.send(json.dumps({"id": nm(), "method": "Page.enable"}))

        # Jobs page should already be loaded from previous test
        js = """
        (() => {
            const url = location.href;

            // Get full body text
            const body = document.body.innerText;

            // Find all elements with "job" in class name
            const jobEls = document.querySelectorAll('[class*="job"]');
            const jobClasses = new Set();
            for (const el of jobEls) {
                for (const cls of el.classList) {
                    if (cls.includes('job')) jobClasses.add(cls);
                }
            }

            // Find elements with "card" in class name
            const cardEls = document.querySelectorAll('[class*="card"]');
            const cardClasses = new Set();
            for (const el of cardEls) {
                for (const cls of el.classList) {
                    if (cls.includes('card')) cardClasses.add(cls);
                }
            }

            // Get job card containers - look for UL with job-related classes
            const jobULs = document.querySelectorAll('ul[class*="job"], ul[class*="card"]');
            const jobLists = [];
            for (const ul of jobULs) {
                const lis = ul.querySelectorAll('li');
                if (lis.length > 0) {
                    jobLists.push({
                        class: ul.className.substring(0, 100),
                        li_count: lis.length,
                        first_li_text: lis[0].innerText.substring(0, 200),
                    });
                }
            }

            // Try to find job cards by class patterns
            const baseCards = document.querySelectorAll('li[class*="job-card"], div[class*="job-card"]');
            const results = [];
            for (const card of [...baseCards].slice(0, 3)) {
                results.push({
                    tag: card.tagName,
                    class: card.className.substring(0, 100),
                    text: card.innerText.substring(0, 300),
                });
            }

            return JSON.stringify({
                url,
                body_text: body.substring(0, 2000),
                job_classes: [...jobClasses].slice(0, 20),
                card_classes: [...cardClasses].slice(0, 20),
                job_lists: jobLists,
                job_cards_found: baseCards.length,
                card_results: results,
            });
        })()
        """
        result = json.loads(await evaluate(ws, js, nm()))
        print(f"URL: {result.get('url')}")
        print(f"\nBody text:\n{result.get('body_text', '')[:1500]}")
        print(f"\nJob classes: {result.get('job_classes', [])}")
        print(f"\nCard classes: {result.get('card_classes', [])}")
        print(f"\nJob lists: {result.get('job_lists', [])}")
        print(f"\nJob cards found: {result.get('job_cards_found', 0)}")
        for i, c in enumerate(result.get('card_results', [])):
            print(f"\n  Card {i+1}: {c['tag']} | {c['class'][:60]}")
            print(f"  Text: {c['text'][:200]}")

asyncio.run(main())
