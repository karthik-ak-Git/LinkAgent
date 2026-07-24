"""Inspect actual DOM to understand current LinkedIn structure."""
import sys, os, asyncio, json, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import websockets

async def main():
    pages = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json/list', timeout=5).read())
    target = None
    for p in pages:
        u = p.get('url', '')
        if u.startswith('http') and 'extension' not in u and 'chrome://' not in u:
            target = p
            break
    if not target:
        target = pages[0]

    ws_url = target['webSocketDebuggerUrl']
    msg_id = 0

    async with websockets.connect(ws_url, max_size=50*1024*1024) as ws:
        async def send_cmd(method, params=None):
            nonlocal msg_id
            msg_id += 1
            msg = {"id": msg_id, "method": method}
            if params:
                msg["params"] = params
            await ws.send(json.dumps(msg))
            while True:
                resp = json.loads(await ws.recv())
                if resp.get("id") == msg_id:
                    return resp

        async def evaluate(expr):
            resp = await send_cmd("Runtime.evaluate", {
                "expression": expr,
                "returnByValue": True,
            })
            result = resp.get("result", {}).get("result", {})
            return result.get("value")

        async def navigate(url):
            return await send_cmd("Page.navigate", {"url": url})

        # --- FEED ---
        print('=== FEED ===')
        await navigate('https://www.linkedin.com/feed/')
        await asyncio.sleep(10)
        
        title = await evaluate('document.title')
        print(f'Title: {title}')
        
        body = await evaluate('document.body?.innerText?.substring(0, 500) || "EMPTY"')
        print(f'Body:\n{body}\n')
        
        # Check various selectors
        checks = [
            'document.querySelectorAll("section").length',
            'document.querySelectorAll("section[aria-label]").length',
            'document.querySelectorAll("div.feed-shared-update-v2").length',
            'document.querySelectorAll("[data-urn]").length',
            'document.querySelectorAll("article").length',
            'document.querySelectorAll("div").length',
        ]
        for c in checks:
            r = await evaluate(c)
            print(f'  {c.split("(")[1].split(")")[0]}: {r}')
        
        # Get first 1000 chars of HTML structure
        html = await evaluate('document.body?.innerHTML?.substring(0, 1000) || "EMPTY"')
        print(f'\nHTML snippet:\n{html[:1000]}')

asyncio.run(main())
