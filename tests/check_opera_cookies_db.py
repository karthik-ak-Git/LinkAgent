"""Check Opera GX profile cookie DB for LinkedIn cookies."""
import sqlite3, shutil
from pathlib import Path
from datetime import datetime

opera_profile = Path.home() / "AppData" / "Roaming" / "Opera Software" / "Opera GX Stable"
# Could be Default/Network/Cookies or just Network/Cookies
for candidate in [opera_profile / "Default" / "Network" / "Cookies",
                  opera_profile / "Network" / "Cookies",
                  opera_profile / "Default" / "Cookies",
                  opera_profile / "Cookies"]:
    print(f"{candidate}: exists={candidate.exists()}, size={candidate.stat().st_size if candidate.exists() else 0}")

# Check the most likely one
db = opera_profile / "Default" / "Network" / "Cookies"
if db.exists():
    tmp = opera_profile / "tmp_cookies_check_opera.db"
    shutil.copy2(db, tmp)
    try:
        conn = sqlite3.connect(str(tmp))
        cur = conn.execute("SELECT host_key, name, value, expires_utc FROM cookies WHERE host_key LIKE '%linkedin%'")
        rows = cur.fetchall()
        print(f"\nLinkedIn cookies in Opera GX: {len(rows)}")
        for row in rows:
            host, name, val, expires = row
            expiry = datetime.fromtimestamp(expires / 1_000_000) if expires else "session"
            print(f"  {host:30s} {name:15s} {val[:40]:40s} expires={expiry}")
        conn.close()
    finally:
        tmp.unlink(missing_ok=True)
