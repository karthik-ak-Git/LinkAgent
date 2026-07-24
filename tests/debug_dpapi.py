"""Try decrypting cookies with DPAPI directly."""
import win32crypt, sqlite3, shutil, tempfile
from pathlib import Path

cookie_db = Path.home() / "AppData" / "Roaming" / "Opera Software" / "Opera GX Stable" / "Default" / "Network" / "Cookies"
tmp = Path(tempfile.gettempdir()) / "ck_dpapi"
shutil.copy2(cookie_db, tmp)

conn = sqlite3.connect(tmp)
c = conn.cursor()
c.execute("SELECT name, encrypted_value FROM cookies WHERE name in ('li_at', 'JSESSIONID', 'bcookie')")

for name, enc in c.fetchall():
    name_s = name.decode() if isinstance(name, bytes) else name
    print(f"[{name_s}] encrypted_value={len(enc)} bytes")
    print(f"  first 20 hex: {enc[:20].hex()}")

    # DPAPI on entire blob
    try:
        dec = win32crypt.CryptUnprotectData(enc, None, None, None, 0)
        print(f"  DPAPI(raw) OK: {repr(dec[1][:80])}")
    except Exception as e:
        print(f"  DPAPI(raw) FAILED: {e}")

    # DPAPI on just ct+tag (skip v10+nonce)
    if enc[:3] == b"v10":
        payload = enc[15:]
        try:
            dec = win32crypt.CryptUnprotectData(payload, None, None, None, 0)
            print(f"  DPAPI(ct+tag) OK: {repr(dec[1][:80])}")
        except Exception as e:
            print(f"  DPAPI(ct+tag) FAILED: {e}")

conn.close()
tmp.unlink(missing_ok=True)
