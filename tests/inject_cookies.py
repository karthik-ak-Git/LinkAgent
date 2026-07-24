"""Inject cookies into the Playwright persistent profile and validate."""
import asyncio, json, os
from pathlib import Path
from patchright.async_api import async_playwright

PROFILE_DIR = Path.home() / ".linkedin-mcp" / "profile"
COOKIE_PATH = Path.home() / ".linkedin-mcp" / "cookies.json"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 720},
            locale="en-US",
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # Navigate to feed first (will show login)
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        print(f"Before cookie injection: {page.url}")
        
        # Inject cookies
        cookies = json.loads(COOKIE_PATH.read_text())
        await browser.add_cookies(cookies)
        print(f"Injected {len(cookies)} cookies")
        
        # Reload
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        print(f"After cookie injection: {page.url}")
        
        title = await page.title()
        print(f"Page title: {title}")
        
        if "login" in str(page.url).lower():
            print("Still at login - cookies may be expired or browser detected")
            # Check if cookies have necessary fields
            for c in cookies:
                if c["name"] in ("li_at", "JSESSIONID", "bcookie"):
                    print(f"  {c['name']}: present={'value' in c}, domain={c.get('domain')}")
        else:
            print("SUCCESS! Authenticated session!")
        
        input("Press Enter to close browser...")
        await browser.close()

asyncio.run(main())
