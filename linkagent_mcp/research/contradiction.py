from __future__ import annotations

from .models import Contradiction


class ContradictionDetector:
    """Record explicit contradictions; do not infer them from confidence."""

    def scan(self, state) -> list[Contradiction]:
        return [item for item in state.contradictions if item.status == "open"]

    def add(
        self,
        state,
        claim_ids: list[str],
        description: str,
        evidence_ids: list[str] | None = None,
    ) -> Contradiction:
        item = Contradiction(
            contradiction_id=f"X-{len(state.contradictions) + 1}",
            claim_ids=list(dict.fromkeys(claim_ids)),
            evidence_ids=list(evidence_ids or []),
            description=description,
        )
        state.contradictions.append(item)
        for claim in state.claims:
            if claim.claim_id in item.claim_ids:
                claim.status = "contradicted"
                claim.epistemic_status = "contradicted"
        state.trace.append({
            "event": "contradiction_recorded",
            "contradiction_id": item.contradiction_id,
            "claim_ids": item.claim_ids,
        })
        return item

    def resolve(self, state, contradiction_id: str, resolution: str) -> bool:
        for item in state.contradictions:
            if item.contradiction_id == contradiction_id:
                item.status = "resolved"
                item.resolution = resolution
                state.trace.append({
                    "event": "contradiction_resolved",
                    "contradiction_id": contradiction_id,
                })
                return True
        return False
