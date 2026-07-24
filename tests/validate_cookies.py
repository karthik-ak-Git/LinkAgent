"""Validate LinkedIn cookies with an HTTP request."""
import json, os
from pathlib import Path
import httpx

cookies = json.loads(
    (Path(os.environ["LOCALAPPDATA"]) / "mcp-server-linkedin" / "cookies.json").read_text()
)
jar = {}
for c in cookies:
    jar[c["name"]] = c["value"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

r = httpx.get(
    "https://www.linkedin.com/feed/",
    cookies=jar,
    headers=headers,
    follow_redirects=True,
)
print(f"Status: {r.status_code}")
print(f"Final URL: {r.url}")
if "login" in str(r.url).lower():
    print("EXPIRED — redirected to login")
elif r.status_code == 200:
    feed_found = "feed" in r.text.lower()[:2000]
    print(f"VALID! Feed content detected: {feed_found}")
else:
    print(f"Unexpected response: {r.text[:500]}")
