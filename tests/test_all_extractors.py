"""Test all 5 extractors with fresh tabs for each test."""
import sys, os, asyncio, json, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import websockets

async def create_new_tab(browser_ws, url="about:blank"):
    msg_id = 0
    async with websockets.connect(browser_ws, max_size=50*1024*1024) as ws:
        msg_id += 1
        await ws.send(json.dumps({"id": msg_id, "method": "Target.createTarget", "params": {"url": url}}))
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == msg_id:
                return resp["result"]["targetId"]

async def test_extractor(browser_ws, name, url, check_fn):
    """Create fresh tab, navigate, test, close."""
    target_id = await create_new_tab(browser_ws)
    
    pages = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json/list', timeout=5).read())
    tab = None
    for p in pages:
        if p.get('id') == target_id:
            tab = p
            break
    
    if not tab:
        return name, 'FAIL', 'Could not find new tab'
    
    ws_url = tab['webSocketDebuggerUrl']
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

        await send_cmd("Page.navigate", {"url": url})
        await asyncio.sleep(10)

        title = await evaluate('document.title')
        result = await evaluate(check_fn)
        
        # Close the tab
        msg_id += 1
        async with websockets.connect(browser_ws, max_size=50*1024*1024) as bws:
            await bws.send(json.dumps({"id": msg_id, "method": "Target.closeTarget", "params": {"targetId": target_id}}))
            await bws.recv()
        
        return name, title, result

async def main():
    ver = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=5).read())
    browser_ws = ver['webSocketDebuggerUrl']

    tests = [
        ("Feed", "https://www.linkedin.com/feed/",
         '(() => { const s = document.querySelector(\'section[aria-label="Primary content"]\'); return s ? s.innerText.substring(0, 200) : "NOT FOUND"; })()'),
        ("Search", "https://www.linkedin.com/search/results/people/?keywords=software+engineer",
         'document.querySelectorAll("[role=listitem]").length'),
        ("Jobs", "https://www.linkedin.com/jobs/search/?keywords=python",
         'document.querySelectorAll(".job-card-container").length'),
        ("Profile", "https://www.linkedin.com/in/satyanadella/",
         '(() => { const h2s = [...document.querySelectorAll("h2")]; const name = h2s.find(h => { const t = h.innerText.trim(); return t && t.length > 1 && t.length < 60 && !t.includes("notifications") && !t.includes("Ad"); }); return name ? name.innerText.trim() : "NOT FOUND"; })()'),
        ("Company", "https://www.linkedin.com/company/microsoft/",
         'document.querySelector("h1")?.innerText || "NOT FOUND"'),
    ]

    results = {}
    for name, url, check in tests:
        print(f'Testing {name}...')
        tab_name, title, result = await test_extractor(browser_ws, name, url, check)
        
        if name == "Feed":
            ok = result and 'NOT FOUND' not in str(result) and 'Something went wrong' not in str(result)
        elif name in ("Search", "Jobs"):
            try:
                ok = int(result) > 0
            except:
                ok = False
        else:
            ok = result and result not in ('NOT FOUND', 'Something went wrong')
        
        results[name] = 'PASS' if ok else 'FAIL'
        print(f'  Title: {title}')
        print(f'  Result: {str(result)[:100]}')
        print(f'  -> {results[name]}\n')
        await asyncio.sleep(2)

    print('='*40)
    print('SUMMARY')
    print('='*40)
    for name, status in results.items():
        print(f'  {name}: {status}')
    passed = sum(1 for v in results.values() if v == 'PASS')
    print(f'\n  {passed}/{len(results)} passed')

asyncio.run(main())
