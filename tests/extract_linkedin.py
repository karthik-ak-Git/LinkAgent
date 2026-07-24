import json, asyncio, websockets, urllib.request

async def extract():
    tabs = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
    linkedin = next((t for t in tabs if t['type'] == 'page' and 'linkedin.com/feed' in t['url']), None)
    if not linkedin:
        print('No LinkedIn tab found')
        return
    
    ws_url = linkedin['webSocketDebuggerUrl']
    print(f'Tab: {linkedin["id"]}')
    
    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        # Extract page data via CDP
        msg_id = 1
        
        # Run JS to extract feed posts
        js = """
        (() => {
            const posts = [];
            const feedItems = document.querySelectorAll('article.feed-shared-update-v2, div.feed-shared-update-v2, div[data-urn]');
            
            for (const item of Array.from(feedItems).slice(0, 20)) {
                const post = {};
                
                // Author
                const authorEl = item.querySelector('.feed-shared-actor__name, .update-components-actor__name, span.feed-shared-actor__title span[aria-hidden="true"]');
                if (authorEl) post.author = authorEl.textContent.trim();
                
                // Author title/headline
                const headlineEl = item.querySelector('.feed-shared-actor__description, .update-components-actor__description');
                if (headlineEl) post.headline = headlineEl.textContent.trim();
                
                // Post text
                const textEl = item.querySelector('.feed-shared-text, .feed-shared-update-v2__description, .update-components-text');
                if (textEl) post.text = textEl.textContent.trim().substring(0, 500);
                
                // Time
                const timeEl = item.querySelector('.feed-shared-actor__subline span, time');
                if (timeEl) post.time = timeEl.getAttribute('datetime') || timeEl.textContent.trim();
                
                // Link
                const linkEl = item.querySelector('a[href*="linkedin.com"]');
                if (linkEl) post.link = linkEl.href;
                
                // Image
                const imgEl = item.querySelector('img.feed-shared-image, .feed-shared-image img');
                if (imgEl) post.image = imgEl.src;
                
                // Engagement
                const likesEl = item.querySelector('.social-details-social-counts__reactions-count, .feed-shared-social-action-count');
                if (likesEl) post.likes = likesEl.textContent.trim();
                
                if (Object.keys(post).length > 0) posts.push(post);
            }
            
            return JSON.stringify({url: location.href, title: document.title, postCount: posts.length, posts: posts});
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
        print(f'Title: {data.get("title")}')
        print(f'Posts found: {data.get("postCount")}')
        
        for i, post in enumerate(data.get('posts', [])[:5], 1):
            print(f'\n--- Post {i} ---')
            for k, v in post.items():
                print(f'  {k}: {v[:200] if isinstance(v, str) else v}')

asyncio.run(extract())
