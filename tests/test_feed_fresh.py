"""Test Feed extractor in isolation with a fresh approach."""
import sys, os, asyncio, json, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import websockets

async def main():
    # Use the browser-level WebSocket to create a new tab
    ver = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=5).read())
    browser_ws = ver['webSocketDebuggerUrl']
    
    msg_id = 0
    async with websockets.connect(browser_ws, max_size=50*1024*1024) as ws:
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
        
        # Create a new target
        resp = await send_cmd("Target.createTarget", {"url": "about:blank"})
        target_id = resp["result"]["targetId"]
        print(f"Created target: {target_id}")
    
    # Now connect to the new tab
    pages = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json/list', timeout=5).read())
    new_tab = None
    for p in pages:
        if p.get('id') == target_id:
            new_tab = p
            break
    
    if not new_tab:
        print("Failed to find new tab")
        return
    
    ws_url = new_tab['webSocketDebuggerUrl']
    print(f'New tab: {ws_url}')
    
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

        # Navigate to LinkedIn feed
        print('\nNavigating to LinkedIn feed...')
        await navigate('https://www.linkedin.com/feed/')
        await asyncio.sleep(12)

        title = await evaluate('document.title')
        print(f'Title: {title}')
        
        url = await evaluate('window.location.href')
        print(f'URL: {url}')
        
        # Check if we got redirected to login
        if 'login' in url or 'authwall' in url:
            print('REDIRECTED TO LOGIN - Session expired!')
            return
        
        body = await evaluate('document.body?.innerText?.substring(0, 500) || "EMPTY"')
        print(f'\nBody:\n{body}')
        
        # Check the actual DOM
        sections = await evaluate('document.querySelectorAll("section").length')
        print(f'\nSections: {sections}')
        
        aria_sections = await evaluate('document.querySelectorAll("section[aria-label]").length')
        print(f'Aria-labeled sections: {aria_sections}')
        
        # Get all aria-labels on sections
        labels = await evaluate("""
            Array.from(document.querySelectorAll("section[aria-label]"))
                .map(s => s.getAttribute("aria-label")).join(", ")
        """)
        print(f'Section labels: {labels}')
        
        # Check for feed items
        feed_items = await evaluate('document.querySelectorAll("[data-urn]").length')
        print(f'Feed items [data-urn]: {feed_items}')
        
        # Check for error messages
        errors = await evaluate("""
            (() => {
                const body = document.body?.innerText || '';
                if (body.includes('Something went wrong')) return 'Something went wrong detected';
                if (body.includes('sign in')) return 'Sign in prompt detected';
                if (body.includes('Page not found')) return 'Page not found';
                return 'No error detected';
            })()
        """)
        print(f'Error check: {errors}')

asyncio.run(main())
