"""Copy extracted cookies to the correct locations and create valid source state."""
import os, json, shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

src_cookies = Path(os.environ["LOCALAPPDATA"]) / "mcp-server-linkedin" / "cookies.json"
auth_root = Path.home() / ".linkedin-mcp"
profile_dir = auth_root / "profile"

# 1. Ensure profile dir exists (needs to be non-empty dir)
profile_dir.mkdir(parents=True, exist_ok=True)
(profile_dir / ".keep").write_text("")

# 2. Copy cookies to auth root (parent of profile/)
dst_cookies = auth_root / "cookies.json"
shutil.copy2(src_cookies, dst_cookies)
print(f"Cookies -> {dst_cookies}")

# 3. Write valid source-state.json
state = {
    "version": 1,
    "source_runtime_id": "windows-amd64-host",
    "login_generation": str(uuid4()),
    "created_at": datetime.now(timezone.utc).isoformat(),
    "profile_path": str(profile_dir.resolve()),
    "cookies_path": str(dst_cookies.resolve()),
    "user_agent": None,
}
source_state_path = auth_root / "source-state.json"
source_state_path.write_text(json.dumps(state, indent=2))
print(f"Source state -> {source_state_path}")
print(json.dumps(state, indent=2))

# 4. Validate: load and verify
cs = json.loads(dst_cookies.read_text())
print(f"\nCookies OK: {len(cs)} entries")
for c in cs:
    print(f"  {c['name']}: {c['value'][:40]}")

print(f"\nProfile dir OK: {profile_dir.exists() and any(profile_dir.iterdir())}")
print(f"Source state OK: {source_state_path.exists()}")
print(f"Cookies exists: {dst_cookies.exists()}")
