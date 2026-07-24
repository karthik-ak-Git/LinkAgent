"""Change source_runtime_id to trigger bridge cookie import flow."""
import json
from pathlib import Path

auth_root = Path.home() / ".linkedin-mcp"
state_path = auth_root / "source-state.json"
state = json.loads(state_path.read_text())

# Change to a fake runtime ID so it goes through the bridge flow
state["source_runtime_id"] = "windows-amd64-docker"
state["login_generation"] = __import__("uuid").uuid4().hex[:12]

state_path.write_text(json.dumps(state, indent=2))
print(f"Updated source-state.json: source_runtime_id={state['source_runtime_id']}")
print(f"  login_generation={state['login_generation']}")
