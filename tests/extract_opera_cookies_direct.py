"""
Extract LinkedIn cookies from Opera GX using direct SQLite access.
"""
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

OPERA_COOKIES_DB = Path.home() / "AppData" / "Roaming" / "Opera Software" / "Opera GX Stable" / "Default" / "Network" / "Cookies"
COOKIES_JSON_PATH = Path.home() / ".linkedin-mcp" / "cookies.json"

def extract_cookies():
    """Copy the cookie DB and extract LinkedIn cookies."""
    if not OPERA_COOKIES_DB.exists():
        print(f"Cookie DB not found at: {OPERA_COOKIES_DB}")
        return None
    
    # Copy the database to a temp file (avoids lock issues)
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    try:
        shutil.copy2(OPERA_COOKIES_DB, tmp_path)
        print(f"Copied cookie database to: {tmp_path}")
        
        conn = sqlite3.connect(str(tmp_path))
        cursor = conn.cursor()
        
        # Query for LinkedIn cookies
        cursor.execute("""
            SELECT name, encrypted_value, host_key, path, is_secure, is_httponly, expires_utc, samesite
            FROM cookies 
            WHERE host_key LIKE '%linkedin.com%'
        """)
        
        cookies = []
        for row in cursor.fetchall():
            name, encrypted_value, domain, path, secure, httponly, expires, samesite = row
            
            # On Windows, encrypted_value starts with v10/v11 prefix
            # For now, we'll store the encrypted value and note that decryption is needed
            cookies.append({
                'name': name,
                'value': encrypted_value.hex() if encrypted_value else '',
                'domain': domain,
                'path': path,
                'secure': bool(secure),
                'httpOnly': bool(httponly),
                'sameSite': 'Lax',
                'expires': expires,
                'encrypted': True,
                'needs_decryption': True
            })
        
        conn.close()
        print(f"Found {len(cookies)} LinkedIn cookies")
        
        # Check for li_at
        li_at = [c for c in cookies if c['name'] == 'li_at']
        if li_at:
            print(f"✓ Found li_at cookie")
        else:
            print("✗ li_at cookie not found")
        
        return cookies
        
    finally:
        tmp_path.unlink(missing_ok=True)

def main():
    print("=" * 50)
    print("Opera GX Cookie Extractor")
    print("=" * 50)
    
    cookies = extract_cookies()
    if cookies:
        # Save to file
        COOKIES_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(COOKIES_JSON_PATH, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"\nCookies saved to: {COOKIES_JSON_PATH}")
        print("\nNote: These cookies are encrypted. We need to decrypt them.")
        print("Let me try a different approach using win32crypt...")

if __name__ == "__main__":
    main()
