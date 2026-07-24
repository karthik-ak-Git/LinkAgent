import asyncio, json, urllib.request, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from linkagent_mcp.cdp.client import CDPClient

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
    
    print(f'Tab: {target["url"]}')
    client = CDPClient(target['webSocketDebuggerUrl'])
    
    await client.navigate('https://www.linkedin.com/feed/')
    await asyncio.sleep(8)
    
    url = await client.evaluate('window.location.href')
    print(f'URL after nav: {url}')
    
    title = await client.evaluate('document.title')
    print(f'Title: {title}')
    
    # Check full page body
    body = await client.evaluate('document.body?.innerText?.substring(0, 500) || "EMPTY"')
    print(f'Body (first 500): {body}')
    
    # Check if page is still loading
    ready = await client.evaluate('document.readyState')
    print(f'ReadyState: {ready}')

asyncio.run(main())
