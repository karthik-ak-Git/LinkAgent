"""Extract LinkedIn cookies from Opera GX and save for mcp-server-linkedin."""
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from base64 import b64decode

ROAMING = os.environ.get("APPDATA", "")
OPERA_PROFILE = Path(ROAMING) / r"Opera Software\Opera GX Stable\Default"
COOKIE_DB = OPERA_PROFILE / "Network" / "Cookies"
LOCAL_STATE = OPERA_PROFILE.parent / "Local State"  # Opera GX Stable\Local State

print("=== Opera GX LinkedIn Cookie Extractor ===\n")

if not COOKIE_DB.exists():
    print(f"Cookie DB not found: {COOKIE_DB}")
    exit(1)
if not LOCAL_STATE.exists():
    print(f"Local State not found: {LOCAL_STATE}")
    exit(1)

print(f"Cookie DB:   {COOKIE_DB}")
print(f"Local State: {LOCAL_STATE}")

# Decryption helpers
CRYPT = None
try:
    import win32crypt
    CRYPT = win32crypt
except ImportError:
    pass

AES = None
try:
    from Crypto.Cipher import AES as CryptoAES
    AES = CryptoAES
except ImportError:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        AES = AESGCM
    except ImportError:
        pass


def get_encryption_key():
    with open(LOCAL_STATE, "r", encoding="utf-8") as f:
        state = json.load(f)
    enc_key_b64 = state.get("os_crypt", {}).get("encrypted_key")
    if not enc_key_b64:
        print("ERROR: No encrypted_key in Local State")
        exit(1)
    enc_key = b64decode(enc_key_b64)
    if enc_key.startswith(b"DPAPI"):
        enc_key = enc_key[5:]
    if CRYPT:
        key = CRYPT.CryptUnprotectData(enc_key, None, None, None, 0)[1]
        print(f"  Decryption key obtained ({len(key)} bytes via DPAPI)")
        return key
    else:
        print("ERROR: win32crypt not available, cannot decrypt key")
        exit(1)


def decrypt_value(enc_value, key):
    if not enc_value:
        return ""
    # v10 format: 'v10' + nonce (12 bytes) + ciphertext + tag (16 bytes)
    if enc_value.startswith(b"v10") or enc_value.startswith(b"v11"):
        version = enc_value[:3].decode()
        nonce = enc_value[3:15]
        ciphertext = enc_value[15:-16]
        tag = enc_value[-16:]
        if CRYPT and version == b"v10":
            try:
                from Crypto.Cipher import AES as CryptoAES
                cipher = CryptoAES.new(key, CryptoAES.MODE_GCM, nonce=nonce)
                return cipher.decrypt(ciphertext).decode("utf-8")
            except ImportError:
                pass
        try:
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, ciphertext + tag, None).decode("utf-8")
        except Exception as e:
            print(f"    AES-GCM decrypt failed: {e}")
            return ""
    # Fallback: try DPAPI
    try:
        if CRYPT:
            return CRYPT.CryptUnprotectData(enc_value, None, None, None, 0)[1].decode("utf-8")
    except Exception:
        pass
    return ""


# Copy DB (avoid lock issues)
tmp = Path(tempfile.gettempdir()) / "opgx_cookies_tmp"
try:
    shutil.copy2(COOKIE_DB, tmp)
except PermissionError:
    print("\nERROR: Opera GX is running — close it first to unlock the cookie DB.")
    print("(Or import via browser extension: EditThisCookie -> export -> JSON)")
    exit(1)

# Extract
conn = sqlite3.connect(tmp)
conn.text_factory = bytes
cursor = conn.cursor()

try:
    cursor.execute(
        "SELECT host_key, name, value, path, expires_utc, is_secure, is_httponly, "
        "has_expires, encrypted_value "
        "FROM cookies WHERE host_key LIKE '%linkedin%'"
    )
except sqlite3.OperationalError:
    cursor.execute(
        "SELECT host_key, name, value, path, expires_utc, is_secure, is_httponly, "
        "has_expires, encrypted_value "
        "FROM cookies WHERE host LIKE '%linkedin%'"
    )

rows = cursor.fetchall()
conn.close()
tmp.unlink(missing_ok=True)

if not rows:
    print("\nNo LinkedIn cookies found in Opera GX!")
    print("Make sure you're logged into linkedin.com in Opera GX.")
    exit(1)

print(f"\nRaw cookies found: {len(rows)}")
decryption_key = get_encryption_key()

# Decrypt
decrypted = {}
for row in rows:
    host = (row[0].decode() if isinstance(row[0], bytes) else row[0]).lstrip(".")
    name = row[1].decode() if isinstance(row[1], bytes) else row[1]
    value = row[2].decode() if isinstance(row[2], bytes) else row[2]
    path = row[3].decode() if isinstance(row[3], bytes) else row[3]
    enc_val = row[8] if len(row) > 8 else b""

    if not value and enc_val:
        value = decrypt_value(enc_val, decryption_key)

    decrypted[name] = value
    print(f"  {name}: {'<set>' if value else '<empty>'}")

# Check critical cookies
needed = {"li_at", "JSESSIONID", "bcookie"}
found = set(decrypted.keys())
missing = needed - found
empty = {n for n in needed if n in found and not decrypted[n]}

print()
print(f"li_at:      {'OK' if decrypted.get('li_at') else 'MISSING'}")
print(f"JSESSIONID: {'OK' if decrypted.get('JSESSIONID') else 'MISSING'}")
print(f"bcookie:    {'OK' if decrypted.get('bcookie') else 'MISSING'}")

if missing or empty:
    print("\nMissing critical cookies — session may not work for scraping.")
    if not decrypted.get("li_at"):
        print("\nSuggested fix:")
        print("  1. Close Opera GX")
        print("  2. Open Opera GX, go to linkedin.com, log in")
        print("  3. Re-run this script")
    exit(1)

# Save cookies.json
target_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "mcp-server-linkedin"
target_dir.mkdir(parents=True, exist_ok=True)

output = [
    {
        "domain": "www.linkedin.com",
        "name": name,
        "value": value,
        "path": "/",
        "secure": True,
        "httpOnly": True,
    }
    for name, value in decrypted.items()
    if value and name in needed
]

cookie_file = target_dir / "cookies.json"
with open(cookie_file, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nSaved {len(output)} cookies to: {cookie_file}")
print("\nNow you can run the MCP server and it will use these cookies.")
