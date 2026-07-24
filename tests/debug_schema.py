import sqlite3, shutil, tempfile
from pathlib import Path

cookie_db = Path.home() / "AppData" / "Roaming" / "Opera Software" / "Opera GX Stable" / "Default" / "Network" / "Cookies"
tmp = Path(tempfile.gettempdir()) / "ck_schema_test"
shutil.copy2(cookie_db, tmp)

conn = sqlite3.connect(tmp)
c = conn.cursor()

c.execute("SELECT sql FROM sqlite_master WHERE name='cookies'")
print("SCHEMA:", c.fetchone()[0])

c.execute("PRAGMA table_info(cookies)")
print("\nCOLUMNS:")
for r in c.fetchall():
    print(f"  {r}")

conn.close()
tmp.unlink(missing_ok=True)
