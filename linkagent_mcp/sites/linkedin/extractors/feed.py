"""
Feed page extractor — extracts posts from the LinkedIn feed.
"""

from ....core.base import BaseExtractor
from ....core.models import Post


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

        const skipAuthors = ['Start a post', 'Sort by', 'Feed post', 'Recommended for you', 'Show more'];
        if (post.author && !skipAuthors.includes(post.author) && !posts.find(p => p.author === post.author)) posts.push(post);
    }

    return JSON.stringify({url: location.href, title: document.title, postCount: posts.length, posts});
})()
"""


class FeedExtractor(BaseExtractor):
    """Extracts posts from the LinkedIn feed page."""

    async def extract(self, **kwargs) -> dict:
        url = await self._get_url()
        if "linkedin.com/feed" not in url:
            return {"error": f"Not on feed page. Current URL: {url}"}

        raw = await self._eval(EXTRACT_FEED_JS)
        if not raw:
            return {"error": "Empty response from CDP"}

        try:
            data = __import__("json").loads(raw)
        except Exception as e:
            return {"error": f"Failed to parse response: {e}"}

        if "error" in data:
            return data

        posts = []
        for p in data.get("posts", []):
            posts.append(Post(
                author=p.get("author", ""),
                headline=p.get("headline", ""),
                text=p.get("text", ""),
                time=p.get("time", ""),
                link=p.get("link", ""),
                likes=p.get("likes", ""),
                comments=p.get("comments", ""),
                reposts=p.get("reposts", ""),
            ).__dict__)

        return {
            "url": data.get("url", url),
            "title": data.get("title", ""),
            "post_count": len(posts),
            "posts": posts,
        }
