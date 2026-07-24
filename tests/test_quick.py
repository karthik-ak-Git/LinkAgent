import asyncio, json, urllib.request, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from linkagent_mcp.cdp.client import CDPClient

async def test():
    data = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json/list', timeout=5).read())
    # Use the first available tab
    tab = data[0]
    url = tab['url']
    print(f'Using tab: {url}')
    client = CDPClient(tab['webSocketDebuggerUrl'])
    
    # Navigate to LinkedIn feed
    await client.navigate('https://www.linkedin.com/feed/')
    await asyncio.sleep(5)
    
    title = await client.evaluate('document.title')
    print(f'Title: {title}')
    
    # Check for Primary content section
    r = await client.evaluate("""
        (() => {
            const section = document.querySelector('section[aria-label="Primary content"]');
            return section ? section.innerText.substring(0, 200) : 'NOT FOUND';
        })()
    """)
    print(f'Feed content: {str(r)[:200]}')
    print('PASS' if r and r != 'NOT FOUND' else 'FAIL')

asyncio.run(test())
