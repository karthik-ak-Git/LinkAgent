"""Take screenshot to see what LinkedIn actually shows."""
import sys, os, asyncio, json, urllib.request, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import websockets

async def main():
    pages = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json/list', timeout=5).read())
    target = None
    for p in pages:
        u = p.get('url', '')
        if 'linkedin.com' in u:
            target = p
            break
    if not target:
        for p in pages:
            u = p.get('url', '')
            if u.startswith('http') and 'extension' not in u and 'chrome://' not in u:
                target = p
                break
    if not target:
        target = pages[0]

    ws_url = target['webSocketDebuggerUrl']
    print(f'Tab: {target["url"]}')
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

        async def navigate(url):
            return await send_cmd("Page.navigate", {"url": url})

        await navigate('https://www.linkedin.com/feed/')
        await asyncio.sleep(10)

        resp = await send_cmd("Page.captureScreenshot", {"format": "png"})
        data = resp.get("result", {}).get("data", "")
        if data:
            img_path = os.path.join(os.path.dirname(__file__), 'linkedin_feed.png')
            with open(img_path, 'wb') as f:
                f.write(base64.b64decode(data))
            print(f'Screenshot saved: {img_path}')
        else:
            print('No screenshot data')

        # Check cookies
        resp = await send_cmd("Network.getCookies")
        cookies = resp.get("result", {}).get("cookies", [])
        li_cookies = [c for c in cookies if 'linkedin' in c.get('domain', '')]
        print(f'\nLinkedIn cookies: {len(li_cookies)}')
        for c in li_cookies[:10]:
            print(f'  {c["name"]}: {c.get("value", "")[:30]}...')

asyncio.run(main())
