"""
Login script that opens Opera GX directly for LinkedIn login,
then extracts cookies to the default MCP profile.
"""
import asyncio
import subprocess
import time
import json
from pathlib import Path

OPERA_GX_PATH = str(Path.home() / "AppData" / "Local" / "Programs" / "Opera GX" / "opera.exe")
DEFAULT_PROFILE = Path.home() / ".linkedin-mcp" / "profile"
DEFAULT_COOKIE_PATH = DEFAULT_PROFILE / "Default" / "Network" / "Cookies"
COOKIES_JSON_PATH = Path.home() / ".linkedin-mcp" / "cookies.json"

def open_opera_gx():
    """Open Opera GX to LinkedIn login page."""
    print("Opening Opera GX to LinkedIn login...")
    subprocess.Popen([OPERA_GX_PATH, "https://www.linkedin.com/login"])
    print("Please log in to LinkedIn in the browser window that opened.")
    print("Waiting 60 seconds for login to complete...")
    time.sleep(60)

def extract_cookies_from_profile():
    """Extract cookies from Opera GX profile using browser_cookie3."""
    try:
        import browser_cookie3
        
        print("Extracting cookies from Opera GX...")
        cj = browser_cookie3.opera_gx(domain_name='.linkedin.com')
        
        cookies = []
        for cookie in cj:
            cookies.append({
                'name': cookie.name,
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path,
                'secure': cookie.secure,
                'httpOnly': cookie.has_nonstandard_attr('HttpOnly'),
                'sameSite': 'Lax',
                'expires': cookie.expires if cookie.expires else -1,
            })
        
        print(f"Extracted {len(cookies)} cookies")
        return cookies
    except Exception as e:
        print(f"Error extracting cookies: {e}")
        return None

def write_cookies_to_profile(cookies):
    """Write cookies to the default MCP profile's cookies.json."""
    COOKIES_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(COOKIES_JSON_PATH, 'w') as f:
        json.dump(cookies, f, indent=2)
    
    print(f"Cookies written to {COOKIES_JSON_PATH}")
    
    # Check for li_at cookie
    li_at = [c for c in cookies if c['name'] == 'li_at']
    if li_at:
        print(f"✓ Found li_at cookie (expires: {li_at[0]['expires']})")
        return True
    else:
        print("✗ Warning: li_at cookie not found")
        return False

def main():
    print("=" * 50)
    print("LinkedIn MCP Server - Opera GX Login Helper")
    print("=" * 50)
    print()
    
    # Step 1: Open Opera GX
    open_opera_gx()
    
    # Step 2: Extract cookies
    cookies = extract_cookies_from_profile()
    if not cookies:
        print("Failed to extract cookies. Please try again.")
        return
    
    # Step 3: Write to default profile
    if write_cookies_to_profile(cookies):
        print()
        print("=" * 50)
        print("SUCCESS! Cookies have been saved.")
        print("You can now run the MCP server:")
        print("  cd to the linkedin-mcp directory")
        print("  python -m linkedin_mcp_server")
        print("=" * 50)
    else:
        print("Cookie extraction may have failed. Please check.")

if __name__ == "__main__":
    main()
