from __future__ import annotations

import re
from typing import Any


class CoverageAnalyzer:
    """Deterministic evidence and request-fidelity gates.

    Confidence is not treated as coverage. A claim is covered only when its
    supporting evidence and required request fields are present and usable.
    """

    def __init__(self, threshold: float = 0.9):
        self.threshold = max(0.0, min(float(threshold), 1.0))

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        return 1.0 if denominator == 0 else numerator / denominator

    @staticmethod
    def _anchor_present(anchor: str, evidence_text: str) -> bool:
        tokens = re.findall(r"[a-z0-9]+", anchor.casefold())
        ignored = {"domain", "anchor", "exact", "request", "term", "constraint", "relation"}
        significant = [token for token in tokens if token not in ignored]
        if not significant:
            return True
        return sum(token in evidence_text for token in significant) / len(significant) >= 0.5

    def compute_metrics(self, state) -> dict[str, Any]:
        requirements = state.requirements
        required = [r for r in requirements if r.get("required", True)]
        covered = [r for r in required if r.get("status") == "covered"]
        partial = [r for r in required if r.get("status") == "partial"]
        missing = [r for r in required if r.get("status") in {"missing", "disputed", "stale"}]

        active_claims = [c for c in state.claims if c.status not in {"retired", "rejected"}]
        supported_claims = [c for c in active_claims if c.status == "supported"]
        unverifed_claims = [c for c in active_claims if c.status in {"unverified", "insufficient_data", "ambiguous"}]
        contradicted_claims = [c for c in active_claims if c.status == "contradicted"]

        constraint_requirements = [r for r in required if r.get("type") in {"constraint", "relation", "source"}]
        constraint_covered = [r for r in constraint_requirements if r.get("status") == "covered"]
        domain_requirements = [r for r in required if r.get("type") in {"domain_anchor", "term", "entity"}]
        domain_covered = [r for r in domain_requirements if r.get("status") == "covered"]

        primary_required = list(state.request.primary_sources)
        primary_sources = [s for s in state.sources if s.source_type == "primary" and s.status in {"retrieved", "verified"}]
        if primary_required:
            primary_urls = {s.url.casefold().rstrip("/") for s in primary_sources}
            primary_numerator = sum(
                1 for requested in primary_required
                if any(requested.casefold().rstrip("/") in url or url in requested.casefold().rstrip("/") for url in primary_urls)
            )
        else:
            primary_numerator = len(primary_sources)
            primary_required = []

        used_evidence_ids = {eid for claim in active_claims for eid in claim.evidence_ids}
        used_evidence = [e for e in state.evidence if e.evidence_id in used_evidence_ids]
        used_sources = [s for s in state.sources if any(e.source_id == s.source_id for e in used_evidence)]
        evidence_text = " ".join(
            [e.claim + " " + e.excerpt for e in used_evidence]
            + [s.domain + " " + s.title for s in used_sources]
        ).casefold()
        domain_anchors = [r["text"].casefold() for r in domain_requirements if r.get("text")]
        if not domain_anchors or not used_sources:
            domain_alignment = 1.0 if not domain_anchors else 0.0
        else:
            domain_alignment = self._ratio(
                sum(self._anchor_present(anchor, evidence_text) for anchor in domain_anchors),
                len(domain_anchors),
            )

        corrections_recorded = len(state.corrections)
        corrections_inc = sum(c.incorporated for c in state.corrections)
        freshness_relevant = [s for s in state.sources if s.status in {"retrieved", "verified"}]
        fresh_sources = [s for s in freshness_relevant if s.freshness >= self.threshold or s.status == "verified"]
        freshness_compliance = self._ratio(len(fresh_sources), len(freshness_relevant))

        metrics = {
            "request_preservation_ratio": self._ratio(len(covered), len(required)),
            "constraint_preservation": self._ratio(len(constraint_covered), len(constraint_requirements)),
            "domain_alignment": domain_alignment,
            "evidence_coverage": self._ratio(len(supported_claims), len(active_claims)),
            "correction_incorporation_rate": self._ratio(corrections_inc, corrections_recorded),
            "primary_source_compliance": self._ratio(primary_numerator, len(primary_required)),
            "freshness_compliance": freshness_compliance,
            "final_request_coverage": self._ratio(len(covered), len(required)),
            "requirements_total": len(required),
            "requirements_covered": len(covered),
            "requirements_partial": len(partial),
            "requirements_missing": len(missing),
            "claims_total": len(active_claims),
            "claims_supported": len(supported_claims),
            "claims_unverified": len(unverifed_claims),
            "claims_contradicted": len(contradicted_claims),
            "sources_total": len(state.sources),
            "evidence_total": len(state.evidence),
            "open_contradictions": sum(c.status == "open" for c in state.contradictions),
            "request_checksum": state.request.checksum,
            "request_integrity": state.request.checksum == state._recompute_checksum(),
        }
        return metrics

    def compute(self, state) -> float:
        return self.compute_metrics(state)["final_request_coverage"]

    def findings(self, state, metrics: dict[str, Any]) -> list[str]:
        findings: list[str] = []
        if not metrics["request_integrity"]:
            findings.append("Immutable request checksum mismatch")
        if metrics["requirements_missing"]:
            findings.append(f"{metrics['requirements_missing']} required request fields remain missing, disputed, or stale")
        if metrics["constraint_preservation"] < 1.0:
            findings.append("One or more explicit constraints or relations are not represented in supported evidence")
        if metrics["domain_alignment"] < 1.0:
            findings.append("Retrieved evidence is not aligned to every domain-defining requirement")
        if metrics["freshness_compliance"] < 1.0 and state.sources:
            findings.append("One or more retrieved sources do not meet the freshness policy")
        if metrics["claims_unverified"]:
            findings.append(f"{metrics['claims_unverified']} material claims are not supported by verified evidence")
        if metrics["claims_contradicted"] or metrics["open_contradictions"]:
            findings.append("Unresolved contradiction evidence remains")
        if metrics["primary_source_compliance"] < 1.0 and state.request.primary_sources:
            findings.append("One or more required primary sources have not been inspected")
        if metrics["correction_incorporation_rate"] < 1.0 and state.corrections:
            findings.append("A user correction has not been incorporated into the task state")
        if metrics["evidence_coverage"] < self.threshold:
            findings.append(f"Evidence coverage {metrics['evidence_coverage']:.2f} is below {self.threshold:.2f}")
        if not state.evidence:
            findings.append("No evidence has been ingested; planning is not evidence")
        return findings

    def gate_pass(self, state) -> bool:
        metrics = self.compute_metrics(state)
        return not self.findings(state, metrics)
