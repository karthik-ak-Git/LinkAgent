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
        
        # Use aria labels and data attributes to find posts
        js = """
        (() => {
            // Find all accessible post containers by aria labels
            const feed = document.querySelector('[aria-label*="feed"], [aria-label*="Feed"], main');
            const feedInfo = feed ? {tag: feed.tagName, ariaLabel: feed.getAttribute('aria-label'), classes: feed.className.substring(0,100)} : null;
            
            // Get all link elements with aria-labels
            const links = document.querySelectorAll('a[aria-label]');
            const linkData = Array.from(links).slice(0, 30).map(l => ({
                label: l.getAttribute('aria-label'),
                href: l.href ? l.href.substring(0, 100) : ''
            }));
            
            // Get buttons/interactive elements
            const buttons = document.querySelectorAll('button[aria-label]');
            const btnData = Array.from(buttons).slice(0, 30).map(b => ({
                label: b.getAttribute('aria-label')
            }));
            
            // Get sections
            const sections = document.querySelectorAll('section[aria-label]');
            const sectionData = Array.from(sections).map(s => ({
                label: s.getAttribute('aria-label'),
                childText: s.textContent.substring(0, 200)
            }));
            
            // Get divs with aria-label
            const labeledDivs = document.querySelectorAll('div[aria-label]');
            const divData = Array.from(labeledDivs).slice(0, 30).map(d => ({
                label: d.getAttribute('aria-label'),
                textPreview: d.textContent.substring(0, 150)
            }));
            
            return JSON.stringify({
                feedInfo: feedInfo,
                links: linkData,
                buttons: btnData,
                sections: sectionData,
                labeledDivs: divData,
                // Check for specific LinkedIn structure
                hasFeed: !!document.querySelector('.scaffold-finite-scroll'),
                hasMain: !!document.querySelector('main'),
                mainAria: document.querySelector('main') ? document.querySelector('main').getAttribute('aria-label') : null
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
        
        print(f'Feed info: {data.get("feedInfo")}')
        print(f'Has feed: {data.get("hasFeed")}')
        print(f'Has main: {data.get("hasMain")}')
        print(f'Main aria: {data.get("mainAria")}')
        
        print(f'\n--- Sections ---')
        for s in data.get('sections', []):
            print(f'  {s["label"]}: {s["childText"][:100]}')
        
        print(f'\n--- Labeled Divs (first 15) ---')
        for d in data.get('labeledDivs', [])[:15]:
            print(f'  {d["label"]}: {d["textPreview"][:80]}')
        
        print(f'\n--- Links (first 10) ---')
        for l in data.get('links', [])[:10]:
            print(f'  {l["label"]}: {l["href"]}')

asyncio.run(extract())
