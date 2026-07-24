"""Copy extracted cookies to the official profile directory."""
import os, json, shutil
from pathlib import Path

src = Path(os.environ["LOCALAPPDATA"]) / "mcp-server-linkedin" / "cookies.json"
dst_dir = Path.home() / ".linkedin-mcp" / "profile"
dst_dir.mkdir(parents=True, exist_ok=True)
dst = dst_dir / "cookies.json"

shutil.copy2(src, dst)

state = {"source_runtime_id": "direct_extract", "login_generation": 1}
(dst_dir / "source-state.json").write_text(json.dumps(state))

print(f"Copied cookies to {dst}")
cs = json.loads(dst.read_text())
print(f"Cookies: {len(cs)}")
for c in cs:
    print(f"  {c['name']}: {c['value'][:40]}")
print(f"Source state written")
