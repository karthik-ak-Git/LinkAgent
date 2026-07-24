"""Full live test — navigates to each page URL before extracting."""
import asyncio, sys, json
from websockets.asyncio.client import connect

async def get_ws_url():
    import urllib.request
    data = json.loads(urllib.request.urlopen("http://localhost:9222/json").read())
    for t in data:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
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
        if resp.get("id") == msg_id:
            return

async def wait(ms):
    await asyncio.sleep(ms / 1000)

async def main():
    ws_url = await get_ws_url()
    print(f"Connected to: {ws_url}")
    async with connect(ws_url, max_size=2**24) as ws:
        mid = 0
        def next_mid():
            nonlocal mid; mid += 1; return mid

        # Enable Page events
        await ws.send(json.dumps({"id": next_mid(), "method": "Page.enable"}))

        # ====== FEED ======
        print("\n=== FEED ===")
        await navigate(ws, "https://www.linkedin.com/feed/", next_mid())
        await wait(3000)
        feed_js = """
        (() => {
            const section = document.querySelector('section[aria-label="Primary content"]');
            if (!section) return JSON.stringify({error: "No feed section", url: location.href});
            const buttons = [...section.querySelectorAll('button')].filter(b => /Comment|\\u00a7/.test(b.getAttribute("aria-label") || ""));
            const items = buttons.length > 0 ? buttons : [section];
            const posts = [];
            for (const item of [...items].slice(0, 3)) {
                const post = item.closest('[role="article"]') || item;
                const text = post.innerText;
                const lines = text.split('\\n').filter(l => l.trim().length > 0);
                posts.push({lines: lines.slice(0, 8), char_count: text.length});
            }
            return JSON.stringify({url: location.href, post_count: posts.length, posts: posts});
        })()
        """
        feed = json.loads(await evaluate(ws, feed_js, next_mid()))
        print(f"URL: {feed.get('url')}")
        print(f"Posts: {feed.get('post_count')}")
        for i, p in enumerate(feed.get("posts", [])):
            print(f"  Post {i+1}: {p['lines'][:4]}...")

        # ====== PROFILE ======
        print("\n=== PROFILE ===")
        await navigate(ws, "https://www.linkedin.com/in/satyanadella/", next_mid())
        await wait(3000)
        profile_js = """
        (() => {
            const h2s = [...document.querySelectorAll("h2")].map(h => h.innerText.trim());
            const body = document.body.innerText;
            return JSON.stringify({url: location.href, h2_count: h2s.length, h2s: h2s.slice(0, 10), body_len: body.length});
        })()
        """
        prof = json.loads(await evaluate(ws, profile_js, next_mid()))
        print(f"URL: {prof.get('url')}")
        print(f"H2 count: {prof.get('h2_count')}")
        print(f"H2s: {prof.get('h2s')}")

        # ====== COMPANY ======
        print("\n=== COMPANY ===")
        await navigate(ws, "https://www.linkedin.com/company/microsoft/", next_mid())
        await wait(3000)
        company_js = """
        (() => {
            const h1 = document.querySelector("h1");
            const h2s = [...document.querySelectorAll("h2")].map(h => h.innerText.trim());
            const body = document.body.innerText;
            const followerMatch = body.match(/(\\d[\\d,.]*[MK]?\\s*followers)/i);
            const employeeMatch = body.match(/(\\d[\\d,.]*[MK+]*\\s*employees)/i);
            return JSON.stringify({
                url: location.href,
                name: h1 ? h1.innerText.trim() : "",
                h2s: h2s.slice(0, 10),
                followers: followerMatch ? followerMatch[1] : "",
                employees: employeeMatch ? employeeMatch[1] : "",
                body_len: body.length
            });
        })()
        """
        comp = json.loads(await evaluate(ws, company_js, next_mid()))
        print(f"URL: {comp.get('url')}")
        print(f"Name: {comp.get('name')}")
        print(f"H2s: {comp.get('h2s')}")
        print(f"Followers: {comp.get('followers')}")
        print(f"Employees: {comp.get('employees')}")

        # ====== SEARCH ======
        print("\n=== SEARCH ===")
        await navigate(ws, "https://www.linkedin.com/search/results/people/?keywords=software+engineer", next_mid())
        await wait(3000)
        search_js = """
        (() => {
            const url = location.href;
            const listitems = document.querySelectorAll('[role="listitem"]');
            const results = [];
            for (const item of [...listitems].slice(0, 3)) {
                const link = item.querySelector('a[href*="/in/"]');
                const nameSpan = link ? link.querySelector('span[aria-hidden="true"]') : null;
                const lines = item.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
                results.push({
                    name: nameSpan ? nameSpan.innerText.trim() : (lines[0] || ""),
                    link: link ? link.href : "",
                    lines: lines.slice(0, 5)
                });
            }
            return JSON.stringify({url, listitem_count: listitems.length, results});
        })()
        """
        search = json.loads(await evaluate(ws, search_js, next_mid()))
        print(f"URL: {search.get('url')}")
        print(f"Listitem count: {search.get('listitem_count')}")
        for i, r in enumerate(search.get("results", [])):
            print(f"  Result {i+1}: {r.get('name')} | {r.get('link', '')[:60]}")

        # ====== JOBS ======
        print("\n=== JOBS ===")
        await navigate(ws, "https://www.linkedin.com/jobs/search/?keywords=python+developer", next_mid())
        await wait(4000)
        jobs_js = """
        (() => {
            const url = location.href;
            const listitems = document.querySelectorAll('[role="listitem"]');
            const body = document.body.innerText;
            const bodyPreview = body.substring(0, 500);
            const results = [];
            for (const item of [...listitems].slice(0, 3)) {
                const lines = item.innerText.split('\\n').map(l => l.trim()).filter(Boolean);
                results.push({lines: lines.slice(0, 6)});
            }
            return JSON.stringify({url, listitem_count: listitems.length, body_len: body.length, body_preview: bodyPreview, results});
        })()
        """
        jobs = json.loads(await evaluate(ws, jobs_js, next_mid()))
        print(f"URL: {jobs.get('url')}")
        print(f"Listitem count: {jobs.get('listitem_count')}")
        print(f"Body length: {jobs.get('body_len')}")
        print(f"Body preview: {jobs.get('body_preview', '')[:300]}")
        for i, r in enumerate(jobs.get("results", [])):
            print(f"  Job {i+1}: {r.get('lines', [])[:4]}")

asyncio.run(main())
