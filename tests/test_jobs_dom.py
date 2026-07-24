"""Deep DOM inspection of jobs page to find working selectors."""
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

async def navigate(ws, url, msg_id=1):
    await ws.send(json.dumps({"id": msg_id, "method": "Page.navigate", "params": {"url": url}}))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get("id") == msg_id: return

async def main():
    ws_url = await get_ws_url()
    async with connect(ws_url, max_size=2**24) as ws:
        mid = [0]
        def nm():
            mid[0] += 1; return mid[0]
        await ws.send(json.dumps({"id": nm(), "method": "Page.enable"}))

        # Navigate to jobs page
        await navigate(ws, "https://www.linkedin.com/jobs/search/?keywords=python+developer", nm())
        await asyncio.sleep(4)

        # Deep DOM inspection
        js = """
        (() => {
            const url = location.href;
            const body = document.body.innerText;

            // Check various possible containers
            const checks = {
                url: url,
                body_len: body.length,
                hasRoleList: !!document.querySelector('[role="list"]'),
                hasRoleListItem: !!document.querySelector('[role="listitem"]'),
                hasRoleArticle: !!document.querySelector('[role="article"]'),
                hasBaseCards: document.querySelectorAll('base-card').length,
                hasJobCards: document.querySelectorAll('[class*="job"]').length,
                hasSearchResults: document.querySelectorAll('ul.search-results__result-list li').length,
                hasOrgGroups: document.querySelectorAll('.jobs-search-results__list li').length,
                hasArtDecoCards: document.querySelectorAll('div.artdeco-card').length,
                hasLiItems: document.querySelectorAll('li').length,
            };

            // Get all UL and OL elements
            const lists = document.querySelectorAll('ul, ol');
            checks.list_count = lists.length;
            checks.list_info = [];
            for (const list of [...lists].slice(0, 10)) {
                checks.list_info.push({
                    tag: list.tagName,
                    li_count: list.querySelectorAll('li').length,
                    class: list.className.substring(0, 80),
                    role: list.getAttribute('role'),
                    aria_label: list.getAttribute('aria-label'),
                });
            }

            // Get top-level divs with many children
            const topDivs = document.querySelectorAll('div');
            checks.top_divs = [];
            for (const div of [...topDivs].slice(0, 50)) {
                if (div.children.length >= 3 && div.children.length <= 30) {
                    checks.top_divs.push({
                        tag: div.tagName,
                        child_count: div.children.length,
                        class: div.className.substring(0, 80),
                        id: div.id,
                        role: div.getAttribute('role'),
                        aria_label: (div.getAttribute('aria-label') || '').substring(0, 60),
                    });
                }
            }

            // Check for job card patterns in body text
            const jobPatterns = body.match(/\\d+\\s*(?:new\\s+)?(?:jobs?|results?)/gi);
            checks.job_patterns = jobPatterns ? jobPatterns.slice(0, 5) : [];

            // Look for specific LinkedIn job search elements
            checks.hasH1 = !!document.querySelector('h1');
            checks.h1_text = document.querySelector('h1')?.innerText || '';

            // Check all h2s
            checks.h2s = [...document.querySelectorAll('h2')].map(h => h.innerText.trim()).slice(0, 5);

            // Check all h3s
            checks.h3s = [...document.querySelectorAll('h3')].map(h => h.innerText.trim()).slice(0, 10);

            return JSON.stringify(checks);
        })()
        """
        result = json.loads(await evaluate(ws, js, nm()))
        for k, v in result.items():
            if k in ('list_info', 'top_divs'):
                print(f"\n{k}:")
                for item in v:
                    print(f"  {item}")
            else:
                print(f"{k}: {v}")

asyncio.run(main())
