#!/usr/bin/env python3
"""
Test LinkedIn data extraction using Chrome DevTools Protocol directly.
This extracts data without needing the extension loaded.
"""

import json
import asyncio
import websockets
import sys

async def extract_via_cdp(ws_url):
    """Extract page data via CDP WebSocket."""
    async with websockets.connect(ws_url) as ws:
        # Get page URL
        await ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": "window.location.href"}
        }))
        resp = json.loads(await ws.recv())
        url = resp.get('result', {}).get('result', {}).get('value', '')

        # Get page title
        await ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": "document.title"}
        }))
        resp = json.loads(await ws.recv())
        title = resp.get('result', {}).get('result', {}).get('value', '')

        # Extract meta tags
        await ws.send(json.dumps({
            "id": 3,
            "method": "Runtime.evaluate",
            "params": {"expression": """
                (() => {
                    const metas = {};
                    document.querySelectorAll('meta').forEach(meta => {
                        const name = meta.getAttribute('name') || meta.getAttribute('property');
                        const content = meta.getAttribute('content');
                        if (name && content) metas[name] = content;
                    });
                    return JSON.stringify(metas);
                })()
            """}
        }))
        resp = json.loads(await ws.recv())
        meta_str = resp.get('result', {}).get('result', {}).get('value', '{}')
        meta = json.loads(meta_str)

        # Extract headings
        await ws.send(json.dumps({
            "id": 4,
            "method": "Runtime.evaluate",
            "params": {"expression": """
                (() => {
                    const headings = [];
                    document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
                        headings.push({
                            level: parseInt(h.tagName[1]),
                            text: h.textContent.trim(),
                        });
                    });
                    return JSON.stringify(headings);
                })()
            """}
        }))
        resp = json.loads(await ws.recv())
        headings_str = resp.get('result', {}).get('result', {}).get('value', '[]')
        headings = json.loads(headings_str)

        # Extract links
        await ws.send(json.dumps({
            "id": 5,
            "method": "Runtime.evaluate",
            "params": {"expression": """
                (() => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        links.push({
                            href: a.href,
                            text: a.textContent.trim().substring(0, 100),
                        });
                    });
                    return JSON.stringify(links.slice(0, 100));
                })()
            """}
        }))
        resp = json.loads(await ws.recv())
        links_str = resp.get('result', {}).get('result', {}).get('value', '[]')
        links = json.loads(links_str)

        # Extract images
        await ws.send(json.dumps({
            "id": 6,
            "method": "Runtime.evaluate",
            "params": {"expression": """
                (() => {
                    const images = [];
                    document.querySelectorAll('img').forEach(img => {
                        images.push({
                            src: img.src,
                            alt: img.alt || '',
                        });
                    });
                    return JSON.stringify(images.slice(0, 50));
                })()
            """}
        }))
        resp = json.loads(await ws.recv())
        images_str = resp.get('result', {}).get('result', {}).get('value', '[]')
        images = json.loads(images_str)

        # Extract text content
        await ws.send(json.dumps({
            "id": 7,
            "method": "Runtime.evaluate",
            "params": {"expression": """
                (() => {
                    const main = document.querySelector('main, article, [role="main"]');
                    const target = main || document.body;
                    const clone = target.cloneNode(true);
                    clone.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                    return clone.textContent.replace(/\\s+/g, ' ').trim().substring(0, 5000);
                })()
            """}
        }))
        resp = json.loads(await ws.recv())
        text = resp.get('result', {}).get('result', {}).get('value', '')

        # Extract posts (LinkedIn specific)
        await ws.send(json.dumps({
            "id": 8,
            "method": "Runtime.evaluate",
            "params": {"expression": """
                (() => {
                    const posts = [];
                    // LinkedIn uses various selectors for posts
                    const postSelectors = [
                        '.feed-shared-update-v2',
                        '.activity-item',
                        '.feed-item',
                        '[data-urn]',
                    ];
                    
                    for (const selector of postSelectors) {
                        document.querySelectorAll(selector).forEach(post => {
                            const author = post.querySelector('.feed-shared-actor__name, .actor-name');
                            const content = post.querySelector('.feed-shared-text, .feed-shared-comment');
                            const time = post.querySelector('.feed-shared-actor__description, time');
                            
                            if (author || content) {
                                posts.push({
                                    author: author ? author.textContent.trim() : '',
                                    content: content ? content.textContent.trim().substring(0, 500) : '',
                                    time: time ? time.textContent.trim() : '',
                                });
                            }
                        });
                        if (posts.length > 0) break;
                    }
                    
                    return JSON.stringify(posts.slice(0, 20));
                })()
            """}
        }))
        resp = json.loads(await ws.recv())
        posts_str = resp.get('result', {}).get('result', {}).get('value', '[]')
        posts = json.loads(posts_str)

        return {
            'url': url,
            'title': title,
            'meta': meta,
            'headings': headings,
            'links': links,
            'images': images,
            'text': text,
            'posts': posts,
            'timestamp': __import__('time').time() * 1000,
        }


async def main():
    if len(sys.argv) > 1:
        ws_url = sys.argv[1]
    else:
        print("Usage: python test-cdp-extract.py <ws-url>")
        print("Example: python test-cdp-extract.py ws://localhost:9222/devtools/browser/...")
        sys.exit(1)

    try:
        data = await extract_via_cdp(ws_url)
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
