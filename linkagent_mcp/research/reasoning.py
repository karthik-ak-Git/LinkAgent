from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ReasoningPolicy:
    """A compact execution contract, not an exposure of private reasoning."""

    name: str
    version: str
    token_budget: int
    private_reasoning_exposed: bool
    steps: tuple[str, ...]
    output_contract: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = list(self.steps)
        data["output_contract"] = list(self.output_contract)
        return data


DEFAULT_POLICY = ReasoningPolicy(
    name="concise-evidence-first",
    version="1.0",
    token_budget=1200,
    private_reasoning_exposed=False,
    steps=(
        "Preserve the exact request and material constraints.",
        "Inspect the task IR and identify missing evidence.",
        "Prefer primary sources and record exact excerpts.",
        "Challenge the current interpretation with disconfirming evidence.",
        "Record corrections as state transitions, never as appended prose.",
        "Audit coverage, contradictions, freshness, and request integrity.",
        "Return supported claims, unknowns, and next evidence only.",
    ),
    output_contract=(
        "Lead with the direct answer only when supported.",
        "Cite source URL and excerpt provenance for material claims.",
        "State unsupported, stale, ambiguous, and contradicted items explicitly.",
        "Never use memory or model confidence as a substitute for evidence.",
    ),
)


def initialize(
    task: str = "",
    execution_mode: str = "background",
    token_budget: int = 1200,
    browser_mode: str = "existing",
) -> dict[str, Any]:
    """Initialize a compact, auditable execution envelope.

    The tool deliberately does not request or reveal private chain-of-thought.
    It gives the agent a short, deterministic checklist and output contract.
    """
    try:
        budget = max(256, min(int(token_budget), 8000))
    except (TypeError, ValueError):
        budget = DEFAULT_POLICY.token_budget
    mode = execution_mode if execution_mode in {"interactive", "background"} else "background"
    browser = browser_mode if browser_mode in {"existing", "hidden_tab"} else "existing"
    policy = ReasoningPolicy(
        name=DEFAULT_POLICY.name,
        version=DEFAULT_POLICY.version,
        token_budget=budget,
        private_reasoning_exposed=False,
        steps=DEFAULT_POLICY.steps,
        output_contract=DEFAULT_POLICY.output_contract,
    )
    return {
        "policy": policy.to_dict(),
        "execution": {
            "task": task,
            "mode": mode,
            "background_supported": True,
            "browser": "existing_regular_profile",
            "browser_requested_mode": browser,
            "incognito_default": False,
            "hidden_tabs_use_existing_session": True,
        },
        "guidance": [
            "Use a concise private checklist; do not reveal private reasoning.",
            "A query plan is not evidence.",
            "A correction retires the active hypothesis and starts revalidation.",
            "Do not declare completion until the final audit passes.",
        ],
    }
