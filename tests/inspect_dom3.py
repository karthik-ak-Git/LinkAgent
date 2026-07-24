import json, asyncio, websockets, urllib.request, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def extract():
    tabs = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
    linkedin = next((t for t in tabs if t['type'] == 'page' and 'linkedin.com/feed' in t['url']), None)
    if not linkedin:
        print('No LinkedIn tab found')
        return
    
    ws_url = linkedin['webSocketDebuggerUrl']
    
    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        msg_id = 1
        
        # Extract posts using the actual LinkedIn DOM structure
        js = """
        (() => {
            const posts = [];
            
            // Find all article/post containers - LinkedIn uses div with data-urn or role="article"
            // Try multiple strategies
            
            // Strategy 1: Find elements that contain author + content patterns
            const allText = document.body.innerText;
            
            // Strategy 2: Find post-like structures by looking for "Like" and "Comment" buttons near content
            const likeButtons = document.querySelectorAll('button[aria-label*="Like"], button[aria-label*="like"]');
            const commentButtons = document.querySelectorAll('button[aria-label*="Comment"], button[aria-label*="comment"]');
            
            // Strategy 3: Find profile-like aria labels (e.g. "Sundar Pichai...")
            const profileDivs = document.querySelectorAll('div[aria-label*="Profile"]');
            
            // Strategy 4: Find "Sort by" which is above the feed
            const sortDiv = document.querySelector('[aria-label*="Sort by"]');
            
            // Get the primary content section
            const primarySection = document.querySelector('section[aria-label="Primary content"]');
            const primaryHTML = primarySection ? primarySection.innerHTML.substring(0, 500) : 'not found';
            const primaryText = primarySection ? primarySection.innerText.substring(0, 3000) : 'not found';
            
            // Try to get individual post blocks
            // Look for repeated structures with timestamps
            const timeElements = document.querySelectorAll('time');
            const timeData = Array.from(timeElements).slice(0, 20).map(t => ({
                text: t.textContent,
                datetime: t.getAttribute('datetime'),
                parentText: t.parentElement ? t.parentElement.textContent.substring(0, 100) : ''
            }));
            
            return JSON.stringify({
                likeCount: likeButtons.length,
                commentCount: commentButtons.length,
                profileCount: profileDivs.length,
                timeCount: timeElements.length,
                timeData: timeData,
                primaryTextPreview: primaryText.substring(0, 2000)
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
        
        print(f'Like buttons: {data.get("likeCount")}')
        print(f'Comment buttons: {data.get("commentCount")}')
        print(f'Profile divs: {data.get("profileCount")}')
        print(f'Time elements: {data.get("timeCount")}')
        
        print(f'\n--- Time data ---')
        for t in data.get('timeData', []):
            print(f'  {t["text"]} ({t["datetime"]})')
        
        print(f'\n--- Primary content text ---')
        print(data.get('primaryTextPreview', ''))

asyncio.run(extract())
