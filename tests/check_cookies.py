"""Check if the Playwright profile has LinkedIn cookies."""
import sqlite3, shutil
from pathlib import Path
from datetime import datetime

dst_profile = Path.home() / ".linkedin-mcp" / "profile"
cookies_db = dst_profile / "Default" / "Network" / "Cookies"

if not cookies_db.exists():
    print(f"Cookie DB not found at {cookies_db}")
else:
    # Copy to avoid lock issues
    tmp = dst_profile / "tmp_cookies_check.db"
    shutil.copy2(cookies_db, tmp)
    try:
        conn = sqlite3.connect(str(tmp))
        cur = conn.execute("SELECT host_key, name, value, expires_utc FROM cookies WHERE host_key LIKE '%linkedin%'")
        rows = cur.fetchall()
        print(f"LinkedIn cookies in profile: {len(rows)}")
        for row in rows:
            host, name, val, expires = row
            expiry = datetime.fromtimestamp(expires / 1_000_000) if expires else "session"
            print(f"  {host:30s} {name:15s} {val[:30]:30s} expires={expiry}")
        conn.close()
    finally:
        tmp.unlink(missing_ok=True)

# Also check cookies.json
cookies_json = dst_profile.parent / "cookies.json"
if cookies_json.exists():
    import json
    cs = json.loads(cookies_json.read_text())
    li = [c for c in cs if c["name"] == "li_at"]
    print(f"\ncookies.json: {len(cs)} total, li_at: {len(li)}")
