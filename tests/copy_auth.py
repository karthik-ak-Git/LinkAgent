"""Copy auth files from Opera GX profile to ~/.linkedin-mcp."""
import json, os, shutil
from pathlib import Path

src = Path(os.environ["APPDATA"]) / "Opera Software"
dst = Path.home() / ".linkedin-mcp"

for f in ("cookies.json", "source-state.json"):
    shutil.copy2(src / f, dst / f)
    print(f"Copied {src / f} -> {dst / f}")

# Also ensure profile dir exists with content
profile_dir = dst / "profile"
profile_dir.mkdir(parents=True, exist_ok=True)
(profile_dir / ".keep").write_text("")

# Show source state
state = json.loads((dst / "source-state.json").read_text())
print(f"\nSource runtime: {state['source_runtime_id']}")
print(f"Login generation: {state['login_generation']}")
print(f"Cookie count: {len(json.loads((dst / 'cookies.json').read_text()))}")
