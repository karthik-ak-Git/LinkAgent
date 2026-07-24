"""Debug profile page h1 structure."""
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

        await navigate('https://www.linkedin.com/in/satyanadella/')
        await asyncio.sleep(12)

        print('=== Profile DOM ===')
        
        title = await evaluate('document.title')
        print(f'Title: {title}')
        
        # All h1 elements
        h1_all = await evaluate('document.querySelectorAll("h1").length')
        print(f'h1 count: {h1_all}')
        
        h1_texts = await evaluate("""
            Array.from(document.querySelectorAll("h1")).map(e => e.innerText).join(" | ")
        """)
        print(f'h1 texts: {h1_texts}')
        
        # Check h2 elements
        h2_texts = await evaluate("""
            Array.from(document.querySelectorAll("h2")).slice(0, 5).map(e => e.innerText).join(" | ")
        """)
        print(f'h2 texts (first 5): {h2_texts}')
        
        # Check for specific text patterns
        body = await evaluate('document.body?.innerText?.substring(0, 800) || "EMPTY"')
        print(f'\nBody:\n{body}')

asyncio.run(main())
