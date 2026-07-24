"""Restore correct runtime_id for source profile."""
import json
from pathlib import Path
from uuid import uuid4

auth_root = Path.home() / ".linkedin-mcp"
state_path = auth_root / "source-state.json"
state = json.loads(state_path.read_text())

# Restore to match current runtime so it goes through source profile path
state["source_runtime_id"] = "windows-amd64-host"
state["login_generation"] = str(uuid4())

state_path.write_text(json.dumps(state, indent=2))
print(f"Restored source_runtime_id={state['source_runtime_id']}")
print(f"  login_generation={state['login_generation']}")
