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
        
        js = """
        (() => {
            const posts = [];
            const primarySection = document.querySelector('section[aria-label="Primary content"]');
            if (!primarySection) return JSON.stringify({error: 'No primary section found'});
            
            // Find all "Feed post" markers - each post starts with "Feed post" text
            const allDivs = primarySection.querySelectorAll('div');
            let currentPost = null;
            
            for (const div of allDivs) {
                const text = div.textContent.trim();
                const ariaLabel = div.getAttribute('aria-label') || '';
                
                // Profile labels contain author info (e.g. "Sundar Pichai ... 3rd+")
                if (ariaLabel.includes('Profile') && ariaLabel.includes('3rd')) {
                    if (currentPost && currentPost.author) {
                        posts.push(currentPost);
                    }
                    currentPost = {author: ariaLabel.split(' ')[0]};
                }
                
                // Look for headline/role text near author
                if (currentPost && !currentPost.headline) {
                    if (text.includes(' at ') || text.includes('Founder') || text.includes('CEO') || text.includes('Director') || text.includes('Student')) {
                        if (text.length < 200 && !text.includes('Follow')) {
                            currentPost.headline = text.substring(0, 150);
                        }
                    }
                }
                
                // Time indicators (e.g. "20h", "23h")
                if (text.match(/^\\d+[hmd]$/) && currentPost && !currentPost.time) {
                    currentPost.time = text;
                }
                
                // Post text - look for longer content blocks
                if (currentPost && !currentPost.text) {
                    if (text.length > 50 && text.length < 2000 && !text.includes('Follow') && !text.includes('Feed post') && !text.includes('Recommended')) {
                        currentPost.text = text.substring(0, 500);
                    }
                }
                
                // Links in posts
                if (currentPost && !currentPost.link) {
                    const links = div.querySelectorAll('a[href*="linkedin.com"], a[href*="http"]');
                    for (const link of links) {
                        if (link.href && !link.href.includes('linkedin.com/feed') && !link.href.includes('linkedin.com/messaging')) {
                            currentPost.link = link.href;
                            break;
                        }
                    }
                }
            }
            if (currentPost && currentPost.author) posts.push(currentPost);
            
            // Also try to extract engagement counts from buttons
            const commentButtons = document.querySelectorAll('button[aria-label*="Comment"]');
            const postsWithComments = commentButtons.length;
            
            return JSON.stringify({
                url: location.href,
                postCount: posts.length,
                posts: posts.slice(0, 10)
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
        
        print(f'URL: {data.get("url")}')
        print(f'Posts found: {data.get("postCount")}')
        
        for i, post in enumerate(data.get('posts', []), 1):
            print(f'\n{"="*60}')
            print(f'POST {i}')
            print(f'{"="*60}')
            for k, v in post.items():
                print(f'  {k}: {v}')

asyncio.run(extract())
