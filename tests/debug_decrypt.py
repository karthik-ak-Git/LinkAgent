"""Debug decryption of one cookie value step by step."""
import sqlite3, shutil, tempfile, json
from pathlib import Path
from base64 import b64decode

OPERA_PROFILE = Path.home() / "AppData" / "Roaming" / "Opera Software" / "Opera GX Stable" / "Default"
cookie_db = OPERA_PROFILE / "Network" / "Cookies"
local_state = OPERA_PROFILE.parent / "Local State"

import win32crypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Get key
with open(local_state) as f:
    state = json.load(f)
enc_key = b64decode(state["os_crypt"]["encrypted_key"])
payload = enc_key[5:]  # strip "DPAPI"
master_key = win32crypt.CryptUnprotectData(payload, None, None, None, 0)[1]
print(f"Master key ({len(master_key)} bytes): {master_key.hex()}")

# Copy DB
tmp = Path(tempfile.gettempdir()) / "ck_dbg"
shutil.copy2(cookie_db, tmp)
conn = sqlite3.connect(tmp)
c = conn.cursor()

# Get ALL LinkedIn cookies including value + encrypted_value
c.execute("SELECT host_key, name, value, encrypted_value FROM cookies WHERE host_key LIKE '%linkedin%'")
rows = c.fetchall()
conn.close()
tmp.unlink(missing_ok=True)

print(f"\nFound {len(rows)} LinkedIn cookies\n")

for hk, name, value, enc in rows:
    name_s = name.decode() if isinstance(name, bytes) else name
    if name_s not in ("li_at", "JSESSIONID", "bcookie", "li_theme", "li_theme_set", "lang"):
        continue

    value_s = value.decode() if isinstance(value, bytes) else value
    print(f"[{name_s}] plaintext_value={repr(value_s[:60])}")

    if not enc or len(enc) < 15:
        print(f"  -> No encrypted value or too short")
        continue

    print(f"  encrypted_value: {len(enc)} bytes, hex[:30]: {enc[:30].hex()}")

    if enc[:3] == b"v10":
        nonce = enc[3:15]
        ct_tag = enc[15:]

        # Try approach 1: decrypt without AAD
        try:
            plain = AESGCM(master_key).decrypt(nonce, ct_tag, None)
            print(f"  Approach 1 (AESGCM, None): {len(plain)} bytes, hex[:30]={plain[:30].hex()}")
            try:
                print(f"    utf8='{plain.decode('utf-8')}'")
            except:
                print(f"    NOT valid utf-8")
        except Exception as e:
            print(f"  Approach 1 FAILED: {type(e).__name__}: {e}")

        # Try approach 2: with empty aad
        try:
            plain2 = AESGCM(master_key).decrypt(nonce, ct_tag, b"")
            print(f"  Approach 2 (AESGCM, b''): {len(plain2)} bytes, hex[:30]={plain2[:30].hex()}")
            try:
                print(f"    utf8='{plain2.decode('utf-8')}'")
            except:
                print(f"    NOT valid utf-8")
        except Exception as e:
            print(f"  Approach 2 FAILED: {type(e).__name__}: {e}")

        # Try approach 3: ct and tag separate (PyCryptodome style)
        ct = enc[15:-16]
        tag = enc[-16:]
        try:
            plain3 = AESGCM(master_key).decrypt(nonce, ct + tag, None)
            print(f"  Approach 3 (sep ct+tag): {len(plain3)} bytes, hex[:30]={plain3[:30].hex()}")
        except Exception as e:
            print(f"  Approach 3 FAILED: {type(e).__name__}: {e}")

        # Try approach 4: key might not be the master key directly.
        # Some browser versions derive a key. Try raw AES-256-GCM
        # with the actual encrypted value as-is
        try:
            from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes
            ciph = Cipher(algorithms.AES(master_key), modes.GCM(nonce, tag))
            dec = ciph.decryptor()
            # GCM decryptor requires finalize_with_tag
            dec.authenticate_additional_data(b"")
            p4 = dec.update(ct) + dec.finalize_with_tag(tag)
            print(f"  Approach 4 (manual Cipher): {len(p4)} bytes, hex[:30]={p4[:30].hex()}")
        except Exception as e:
            print(f"  Approach 4 FAILED: {type(e).__name__}: {e}")

    print()

