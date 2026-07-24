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
            if (!primarySection) return JSON.stringify({error: 'No primary section'});
            
            // Get all comment buttons to identify post boundaries
            const commentBtns = primarySection.querySelectorAll('button[aria-label*="Comment"]');
            
            // For each comment button, traverse up to find the post container
            for (const btn of commentBtns) {
                let container = btn.parentElement;
                // Walk up until we find a container with enough content
                for (let i = 0; i < 15; i++) {
                    if (container.parentElement) container = container.parentElement;
                    const text = container.innerText || '';
                    if (text.length > 200) break;
                }
                
                const text = container.innerText || '';
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                
                const post = {};
                
                // First non-empty line is usually "Feed post" or author name
                for (const line of lines) {
                    if (line === 'Feed post' || line === 'From your activity' || line.startsWith('Promoted')) {
                        continue;
                    }
                    // Author line: "Name • 3rd+"
                    if (line.includes('•') && (line.includes('3rd') || line.includes('2nd') || line.includes('1st'))) {
                        post.author = line.split('•')[0].trim();
                        break;
                    }
                    // Or just a name as first meaningful line
                    if (line.length > 2 && line.length < 100 && !line.includes('Follow') && !line.includes('Sort by')) {
                        post.author = line;
                        break;
                    }
                }
                
                // Find headline (usually after author)
                let foundAuthor = false;
                for (const line of lines) {
                    if (line === post.author) { foundAuthor = true; continue; }
                    if (foundAuthor && !post.headline) {
                        if (line.length > 10 && line.length < 200 && !line.match(/^\\d+[hmd]/) && line !== 'Follow') {
                            post.headline = line;
                        }
                    }
                    // Time
                    if (!post.time && line.match(/^[\\d]+[hmd]$/)) {
                        post.time = line;
                    }
                }
                
                // Find main post text (longer paragraph)
                let postTextLines = [];
                let inPost = false;
                for (const line of lines) {
                    if (line.length > 50 && !line.includes('Follow') && !line.includes('Feed post') && !line.includes('Sort by') && !line.includes('Recommended')) {
                        postTextLines.push(line);
                    }
                }
                if (postTextLines.length > 0) {
                    post.text = postTextLines.join(' ').substring(0, 1000);
                }
                
                // Find engagement numbers
                const nums = [];
                for (const line of lines) {
                    if (line.match(/^\\d+[kKmM]?$/) && parseInt(line.replace(/[kKmM]/, '')) < 100000) {
                        nums.push(line);
                    }
                }
                if (nums.length >= 3) {
                    post.likes = nums[0];
                    post.comments = nums[1];
                    post.reposts = nums[2];
                }
                
                // Find link
                const links = container.querySelectorAll('a[href]');
                for (const link of links) {
                    const href = link.href;
                    if (href && (href.includes('/pulse/') || href.includes('/posts/') || href.includes('/in/') || href.includes('github.com'))) {
                        post.link = href;
                        break;
                    }
                }
                
                // Deduplicate by author
                if (post.author && !posts.find(p => p.author === post.author)) {
                    posts.push(post);
                }
            }
            
            return JSON.stringify({
                url: location.href,
                title: document.title,
                postCount: posts.length,
                posts: posts
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
        print(f'Title: {data.get("title")}')
        print(f'Posts found: {data.get("postCount")}')
        
        for i, post in enumerate(data.get('posts', []), 1):
            print(f'\n{"="*60}')
            print(f'POST {i}')
            print(f'{"="*60}')
            print(f'  Author: {post.get("author", "N/A")}')
            print(f'  Headline: {post.get("headline", "N/A")}')
            print(f'  Time: {post.get("time", "N/A")}')
            print(f'  Text: {post.get("text", "N/A")[:300]}')
            print(f'  Link: {post.get("link", "N/A")}')
            print(f'  Likes: {post.get("likes", "N/A")} | Comments: {post.get("comments", "N/A")} | Reposts: {post.get("reposts", "N/A")}')

asyncio.run(extract())
