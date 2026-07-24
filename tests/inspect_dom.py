import json, asyncio, websockets, urllib.request

async def extract():
    tabs = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
    linkedin = next((t for t in tabs if t['type'] == 'page' and 'linkedin.com/feed' in t['url']), None)
    if not linkedin:
        print('No LinkedIn tab found')
        return
    
    ws_url = linkedin['webSocketDebuggerUrl']
    
    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        msg_id = 1
        
        # First, dump the feed container structure
        js = """
        (() => {
            // Find the main feed container
            const feed = document.querySelector('.feed-identity-module, .scaffold-finite-scroll, main.scaffold-finite-scroll__content, div.scaffold-finite-scroll');
            
            // Get all data-urn elements (post containers)
            const urns = document.querySelectorAll('[data-urn]');
            const urnData = Array.from(urns).slice(0, 5).map(el => ({
                urn: el.getAttribute('data-urn'),
                tag: el.tagName,
                classes: el.className.substring(0, 200),
                childCount: el.children.length,
                textPreview: el.textContent.substring(0, 100)
            }));
            
            // Get top-level structure
            const main = document.querySelector('main');
            const mainClasses = main ? main.className : 'none';
            
            // Check for specific LinkedIn feed selectors
            const feedItems = document.querySelectorAll('.feed-shared-update-v2');
            const updateItems = document.querySelectorAll('[class*="update-components"]');
            const sharedItems = document.querySelectorAll('[class*="feed-shared"]');
            
            return JSON.stringify({
                mainClasses: mainClasses,
                feedSelector: feed ? feed.className.substring(0, 200) : 'not found',
                urnCount: urns.length,
                urnData: urnData,
                feedItemCount: feedItems.length,
                updateItemCount: updateItems.length,
                sharedItemCount: sharedItems.length,
                bodySnippet: document.body.innerHTML.substring(0, 3000)
            });
        })()
        """
        
        await ws.send(json.dumps({
            'id': msg_id,
            'method': 'Runtime.evaluate',
            'params': {'expression': js, 'returnByValue': True}
        }))
        
        resp = json.loads(await ws.recv())
        value = resp.get('result', {}).get('result', {}).get('value', '{}')
        data = json.loads(value)
        
        print(f'Feed selector: {data.get("feedSelector")}')
        print(f'URN elements: {data.get("urnCount")}')
        print(f'Feed items: {data.get("feedItemCount")}')
        print(f'Update items: {data.get("updateItemCount")}')
        print(f'Shared items: {data.get("sharedItemCount")}')
        print(f'\nURN data:')
        for item in data.get('urnData', []):
            print(f'  {item}')
        
        print(f'\n--- Body HTML (first 5000 chars) ---')
        print(data.get('bodySnippet', '')[:5000])

asyncio.run(extract())
