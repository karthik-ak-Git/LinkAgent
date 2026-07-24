"""Test: inject cookies.json into Playwright persistent context, then check /feed/."""
import asyncio, json, sys
from pathlib import Path
from patchright.async_api import async_playwright

PROFILE = Path.home() / ".linkedin-mcp" / "profile"
COOKIES_JSON = PROFILE.parent / "cookies.json"

async def main():
    if not COOKIES_JSON.exists():
        print(f"Missing {COOKIES_JSON}")
        return
    cookies = json.loads(COOKIES_JSON.read_text())
    print(f"Loaded {len(cookies)} cookies from cookies.json")

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            headless=True,
            no_viewport=True,
        )

        # Inject cookies
        cookie_list = []
        for c in cookies:
            entry = {
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", "").lstrip("."),
                "path": c.get("path", "/"),
                "secure": c.get("secure", True),
                "httpOnly": c.get("httpOnly", True),
                "sameSite": c.get("sameSite", "Lax"),
            }
            if c.get("expirationDate"):
                entry["expires"] = int(c["expirationDate"])
            cookie_list.append(entry)

        await ctx.add_cookies(cookie_list)
        print(f"Injected {len(cookie_list)} cookies")

        # Check /feed/
        page = await ctx.new_page()
        try:
            resp = await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
            final_url = page.url
            print(f"Final URL: {final_url}")
            if "login" in final_url.lower():
                print("FAIL: Redirected to login page")
            elif "feed" in final_url.lower():
                print("SUCCESS: On the feed page!")
            else:
                print(f"UNKNOWN: landed on {final_url}")
        except Exception as e:
            print(f"Navigation error: {e}")

        await ctx.close()

asyncio.run(main())
