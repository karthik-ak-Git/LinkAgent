"""Extract LinkedIn cookies from Opera GX — matches official linkedin-mcp-server logic."""
import json, os, shutil, sqlite3, tempfile, hashlib
from pathlib import Path
from base64 import b64decode
import ctypes, ctypes.wintypes

ROAMING = os.environ.get("APPDATA", "")
OPERA_ROOT = Path(ROAMING) / r"Opera Software\Opera GX Stable"
COOKIE_DB = OPERA_ROOT / "Default" / "Network" / "Cookies"
LOCAL_STATE = OPERA_ROOT / "Local State"

# Must match linkedin_mcp_server/browser_import/extract.py
_HOST_KEY_PREFIX_LEN = 32
_HOST_KEY_PREFIX_MIN_VERSION = 24


def _windows_master_key(local_state_path: Path) -> bytes:
    """Decrypt DPAPI-protected AES-256 master key (via ctypes, matches official code)."""
    payload = json.loads(local_state_path.read_text())
    encrypted_key = b64decode(payload["os_crypt"]["encrypted_key"])
    assert encrypted_key[:5] == b"DPAPI", "Missing DPAPI prefix"
    blob_in = encrypted_key[5:]

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf_in = ctypes.create_string_buffer(blob_in, len(blob_in))
    blob_in_struct = DATA_BLOB(len(blob_in), buf_in)
    blob_out = DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(ctypes.byref(blob_in_struct), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise RuntimeError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def decrypt_gcm(blob: bytes, master_key: bytes, host_key: str, store_version: int) -> str:
    """Decrypt a v10 cookie, stripping SHA256(host_key) prefix when store_version >= 24."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = blob[3:15]
    ciphertext = blob[15:]
    plaintext = AESGCM(master_key).decrypt(nonce, ciphertext, None)
    if store_version >= _HOST_KEY_PREFIX_MIN_VERSION:
        # First 32 bytes are SHA256(host_key) — verify it for sanity
        expected = hashlib.sha256(host_key.encode()).digest()
        actual = plaintext[:_HOST_KEY_PREFIX_LEN]
        if actual == expected:
            plaintext = plaintext[_HOST_KEY_PREFIX_LEN:]
        else:
            print(f"    WARNING: host_key prefix mismatch (store_v{store_version})")
            plaintext = plaintext[_HOST_KEY_PREFIX_LEN:]  # strip anyway
    return plaintext.decode("utf-8", errors="replace")


print("=== Opera GX LinkedIn Cookie Extractor ===\n")
print(f"Root:    {OPERA_ROOT}")
print(f"DB:      {COOKIE_DB}")
print(f"State:   {LOCAL_STATE}")

if not COOKIE_DB.exists():
    print("ERROR: Cookie DB not found."); exit(1)

# Copy DB (close Opera GX first!)
tmp = Path(tempfile.gettempdir()) / "opgx_cookies_tmp"
try:
    shutil.copy2(COOKIE_DB, tmp)
except PermissionError:
    print("ERROR: Close Opera GX first (cookie DB locked).")
    exit(1)

conn = sqlite3.connect(tmp)
c = conn.cursor()

# Read store version (matches official _meta_version())
try:
    c.execute("SELECT value FROM meta WHERE key='version'")
    row = c.fetchone()
    store_version = int(row[0]) if row and row[0] is not None else 0
except (sqlite3.Error, ValueError):
    store_version = 0
print(f"Store version: {store_version}")
print(f"Host prefix strip needed: {store_version >= _HOST_KEY_PREFIX_MIN_VERSION}")

# Resolve column names (matches official _cookie_columns())
c.execute("PRAGMA table_info(cookies)")
cols = {row[1] for row in c.fetchall()}
secure_col = "is_secure" if "is_secure" in cols else "secure"
httponly_col = "is_httponly" if "is_httponly" in cols else "httponly"

# Get LinkedIn cookies
c.execute(f"SELECT host_key, name, value, encrypted_value, path, expires_utc, "
          f"{secure_col} AS secure_col, {httponly_col} AS httponly_col, samesite "
          f"FROM cookies WHERE host_key LIKE '%linkedin%'")
rows = c.fetchall()
conn.close()
tmp.unlink(missing_ok=True)

if not rows:
    print("\nNo LinkedIn cookies found! Log into linkedin.com in Opera GX first.")
    exit(1)

print(f"\nFound {len(rows)} LinkedIn cookies")

# Get master key
master_key = _windows_master_key(LOCAL_STATE)
print(f"Master key: {master_key.hex()[:16]}... ({len(master_key)} bytes)")

# Decrypt
decrypted = {}
for row in rows:
    host_key = row[0].decode() if isinstance(row[0], bytes) else row[0]
    name = row[1].decode() if isinstance(row[1], bytes) else row[1]
    value = row[2].decode() if isinstance(row[2], bytes) else row[2]
    enc_val = row[3] if row[3] else b""

    if not value and enc_val and enc_val[:3] == b"v10":
        try:
            value = decrypt_gcm(enc_val, master_key, host_key, store_version)
        except Exception as e:
            print(f"  {name}: decrypt failed: {e}")
            continue

    decrypted[name] = value

# Report
print("\n--- Critical Cookies ---")
for c in ["li_at", "JSESSIONID", "bcookie"]:
    val = decrypted.get(c, "")
    status = "OK" if val else "MISSING"
    preview = val[:40] if val else ""
    print(f"  {c}: {status}  {repr(preview)}")

if all(decrypted.get(c) for c in ["li_at", "JSESSIONID", "bcookie"]):
    target_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "mcp-server-linkedin"
    target_dir.mkdir(parents=True, exist_ok=True)
    output = [
        {"domain": "www.linkedin.com", "name": c, "value": decrypted[c],
         "path": "/", "secure": True, "httpOnly": True}
        for c in ["li_at", "JSESSIONID", "bcookie"]
    ]
    with open(target_dir / "cookies.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to: {target_dir / 'cookies.json'}")
else:
    print("\nCould not extract all critical cookies.")
