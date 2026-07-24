import sys, io, json, asyncio
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request

CDP_BASE = "http://localhost:9222"

def get_cdp_tabs():
    return json.loads(urllib.request.urlopen(f"{CDP_BASE}/json").read())

def find_linkedin_tab():
    tabs = get_cdp_tabs()
    for t in tabs:
        if t["type"] == "page" and "linkedin.com/feed" in t.get("url", ""):
            return t
    return None

EXTRACT_FEED_JS = """
(() => {
    const posts = [];
    const primarySection = document.querySelector('section[aria-label="Primary content"]');
    if (!primarySection) return JSON.stringify({error: 'No primary section', url: location.href});

    const commentBtns = primarySection.querySelectorAll('button[aria-label*="Comment"]');

    for (const btn of commentBtns) {
        let container = btn.parentElement;
        for (let i = 0; i < 15; i++) {
            if (container.parentElement) container = container.parentElement;
            const text = container.innerText || '';
            if (text.length > 200) break;
        }

        const text = container.innerText || '';
        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

        const post = {};
        for (const line of lines) {
            if (line === 'Feed post' || line === 'From your activity' || line.startsWith('Promoted')) continue;
            if (line.includes('•') && (line.includes('3rd') || line.includes('2nd') || line.includes('1st'))) {
                post.author = line.split('•')[0].trim();
                break;
            }
            if (line.length > 2 && line.length < 100 && !line.includes('Follow') && !line.includes('Sort by')) {
                post.author = line;
                break;
            }
        }

        let foundAuthor = false;
        for (const line of lines) {
            if (line === post.author) { foundAuthor = true; continue; }
            if (foundAuthor && !post.headline) {
                if (line.length > 10 && line.length < 200 && !line.match(/^\\d+[hmd]/) && line !== 'Follow') {
                    post.headline = line;
                }
            }
            if (!post.time && line.match(/^[\\d]+[hmd]$/)) post.time = line;
        }

        let postTextLines = [];
        for (const line of lines) {
            if (line.length > 50 && !line.includes('Follow') && !line.includes('Feed post') && !line.includes('Sort by') && !line.includes('Recommended')) {
                postTextLines.push(line);
            }
        }
        if (postTextLines.length > 0) post.text = postTextLines.join(' ').substring(0, 2000);

        const nums = [];
        for (const line of lines) {
            if (line.match(/^\\d+[kKmM]?$/) && parseInt(line.replace(/[kKmM]/, '')) < 100000) nums.push(line);
        }
        if (nums.length >= 3) { post.likes = nums[0]; post.comments = nums[1]; post.reposts = nums[2]; }

        const links = container.querySelectorAll('a[href]');
        for (const link of links) {
            const href = link.href;
            if (href && (href.includes('/pulse/') || href.includes('/posts/') || href.includes('/in/') || href.includes('github.com'))) {
                post.link = href;
                break;
            }
        }

        if (post.author && !posts.find(p => p.author === post.author)) posts.push(post);
    }

    return JSON.stringify({url: location.href, title: document.title, postCount: posts.length, posts});
})()
"""

async def cdp_eval(ws_url, expression):
    import websockets
    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        msg = json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expression, "returnByValue": True}})
        await ws.send(msg)
        resp = json.loads(await ws.recv())
        return resp.get("result", {}).get("result", {}).get("value")

async def test():
    tab = find_linkedin_tab()
    if not tab:
        print("No LinkedIn tab found")
        return
    print(f"Tab: {tab['id']} - {tab.get('title', '')[:50]}")
    result = await cdp_eval(tab['webSocketDebuggerUrl'], EXTRACT_FEED_JS)
    data = json.loads(result)
    print(f"Posts extracted: {data.get('postCount', 0)}")
    for i, p in enumerate(data.get('posts', [])[:5], 1):
        author = p.get('author', 'N/A')
        headline = p.get('headline', 'N/A')[:60]
        text = p.get('text', 'N/A')[:80]
        likes = p.get('likes', '-')
        print(f"  {i}. {author} | {headline}")
        print(f"     {text}...")
        print(f"     Likes: {likes}")

asyncio.run(test())
