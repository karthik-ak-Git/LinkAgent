#!/usr/bin/env python3
"""
Test LinkedIn data extraction by simulating content script behavior.
This tests the extraction logic without needing the extension running.
"""

import json
from html.parser import HTMLParser

class LinkedInExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data = {
            'url': 'https://www.linkedin.com/feed/',
            'title': '',
            'meta': {},
            'headings': [],
            'links': [],
            'images': [],
            'forms': [],
            'text': '',
            'posts': [],
        }
        self.current_tag = None
        self.current_attrs = {}
        self.text_buffer = []
        self.in_post = False
        self.current_post = {}

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.current_attrs = dict(attrs)

        if tag == 'title':
            self.text_buffer = []
        elif tag == 'meta':
            name = self.current_attrs.get('name') or self.current_attrs.get('property', '')
            content = self.current_attrs.get('content', '')
            if name and content:
                self.data['meta'][name] = content
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text_buffer = []
        elif tag == 'a':
            href = self.current_attrs.get('href', '')
            if href and not href.startswith('#'):
                self.data['links'].append({
                    'href': href,
                    'text': '',
                    'title': self.current_attrs.get('title', ''),
                })
        elif tag == 'img':
            src = self.current_attrs.get('src', '')
            if src:
                self.data['images'].append({
                    'src': src,
                    'alt': self.current_attrs.get('alt', ''),
                })
        elif tag == 'form':
            self.data['forms'].append({
                'action': self.current_attrs.get('action', ''),
                'method': self.current_attrs.get('method', 'GET'),
                'fields': [],
            })
        elif tag in ('input', 'select', 'textarea'):
            if self.data['forms']:
                self.data['forms'][-1]['fields'].append({
                    'type': self.current_attrs.get('type', tag),
                    'name': self.current_attrs.get('name', ''),
                    'id': self.current_attrs.get('id', ''),
                    'placeholder': self.current_attrs.get('placeholder', ''),
                })

    def handle_endtag(self, tag):
        if tag == 'title' and self.text_buffer:
            self.data['title'] = ''.join(self.text_buffer).strip()
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6') and self.text_buffer:
            level = int(tag[1])
            text = ''.join(self.text_buffer).strip()
            if text:
                self.data['headings'].append({
                    'level': level,
                    'text': text,
                })
        elif tag == 'a' and self.data['links']:
            self.data['links'][-1]['text'] = ''.join(self.text_buffer).strip()[:100]

    def handle_data(self, data):
        if self.current_tag in ('title', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a'):
            self.text_buffer.append(data)
        elif self.current_tag not in ('script', 'style', 'noscript'):
            self.data['text'] += data + ' '

    def get_extracted_data(self):
        # Clean up text
        self.data['text'] = ' '.join(self.data['text'].split())[:5000]
        # Limit arrays
        self.data['links'] = self.data['links'][:100]
        self.data['images'] = self.data['images'][:50]
        return self.data


def extract_from_file(html_file):
    """Extract data from an HTML file."""
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    extractor = LinkedInExtractor()
    extractor.feed(html_content)
    return extractor.get_extracted_data()


def extract_from_url(url):
    """Extract data from a URL (simulated)."""
    # This would normally use the browser to get the page
    # For now, return simulated data
    return {
        'url': url,
        'title': 'LinkedIn Feed',
        'meta': {
            'og:title': 'LinkedIn',
            'og:description': 'LinkedIn is a professional network',
        },
        'headings': [
            {'level': 1, 'text': 'LinkedIn Feed'},
            {'level': 2, 'text': 'Posts'},
        ],
        'links': [
            {'href': 'https://linkedin.com/feed/', 'text': 'Feed', 'title': ''},
            {'href': 'https://linkedin.com/network/', 'text': 'Network', 'title': ''},
        ],
        'images': [],
        'forms': [],
        'text': 'LinkedIn feed content would appear here...',
        'timestamp': __import__('time').time() * 1000,
    }


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source.startswith('http'):
            data = extract_from_url(source)
        else:
            data = extract_from_file(source)
    else:
        # Default test
        data = extract_from_url('https://www.linkedin.com/feed/')

    print(json.dumps(data, indent=2))
