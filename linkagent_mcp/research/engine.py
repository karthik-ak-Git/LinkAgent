from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .contradiction import ContradictionDetector
from .coverage import CoverageAnalyzer
from .deduplication import Deduplicator
from .models import (
    Audit,
    Claim,
    Correction,
    Evidence,
    RequestSpec,
    ResearchState,
    Source,
    utc_now,
    stable_hash,
)
from .reasoning import initialize as initialize_reasoning


class ResearchEngine:
    """Evidence-first research controller.

    The engine deliberately separates planning from evidence. Creating a job
    never marks claims as researched. Evidence must be ingested with source and
    excerpt metadata before the coverage gate can pass.
    """

    def __init__(self, browser_manager=None, max_queries=500, coverage_threshold=0.9, workers=5):
        self.bm = browser_manager
        self.max_queries = self._budget(max_queries)
        self.threshold = float(coverage_threshold)
        self.workers = max(1, int(workers))
        self.jobs: dict[str, ResearchState] = {}
        self.coverage_analyzer = CoverageAnalyzer(self.threshold)
        self.contradiction_detector = ContradictionDetector()
        self.dedup = Deduplicator()

    @staticmethod
    def _budget(value: Any) -> int:
        try:
            return max(1, min(int(value), 500))
        except (TypeError, ValueError):
            return 500

    def get(self, job_id: str) -> ResearchState | None:
        return self.jobs.get(job_id)

    def create_job(self, query: str, **kwargs: Any) -> ResearchState:
        requirements = kwargs.get("requirements")
        primary_sources = kwargs.get("primary_sources") or []
        scope = kwargs.get("scope") or []
        request = RequestSpec.create(
            query,
            requirements=requirements,
            primary_sources=primary_sources,
            scope=scope,
        )
        budget = self._budget(kwargs.get("max_queries", self.max_queries))
        state = ResearchState(
            task_id=request.request_id,
            request=request,
            status="queued",
            requirements=[
                {**requirement.to_dict(), "status": "missing", "evidence_ids": [], "notes": ""}
                for requirement in request.requirements
            ],
            queries_budget=budget,
        )
        state.trace.append({
            "event": "request_captured",
            "request_checksum": request.checksum,
            "exact_request": request.original_request,
            "memory_policy": state.memory_policy,
        })
        self.jobs[state.task_id] = state
        return state

    def _find_claim(self, state: ResearchState, text: str) -> Claim | None:
        normalized = " ".join(text.casefold().split())
        for claim in state.claims:
            if " ".join(claim.text.casefold().split()) == normalized:
                return claim
        return None

    def _find_evidence(self, state: ResearchState, evidence_id: str) -> Evidence | None:
        return next((item for item in state.evidence if item.evidence_id == evidence_id), None)

    def _find_source(self, state: ResearchState, source_id: str) -> Source | None:
        return next((item for item in state.sources if item.source_id == source_id), None)

    def _sync_requirements(self, state: ResearchState) -> None:
        for requirement in state.requirements:
            related = [c for c in state.claims if requirement["id"] in c.requirement_ids]
            if any(c.status == "contradicted" for c in related):
                requirement["status"] = "disputed"
            elif related and all(c.status == "supported" for c in related):
                requirement["status"] = "covered"
                requirement["evidence_ids"] = sorted({eid for c in related for eid in c.evidence_ids})
            elif related:
                requirement["status"] = "partial"
                requirement["evidence_ids"] = sorted({eid for c in related for eid in c.evidence_ids})
            else:
                requirement["status"] = "missing"
                requirement["evidence_ids"] = []
        state.coverage = self.coverage_analyzer.compute(state)
        state.touch()

    def _claim_status_from_evidence(self, state: ResearchState, claim: Claim) -> str:
        evidence = [self._find_evidence(state, eid) for eid in claim.evidence_ids]
        evidence = [item for item in evidence if item is not None]
        if evidence and all(item.status == "verified" for item in evidence):
            return "supported"
        if evidence:
            return "unverified"
        return "unverified"

    def add_claim(
        self,
        job_id: str,
        text: str,
        requirement_ids: list[str] | None = None,
        evidence_ids: list[str] | None = None,
        status: str = "unverified",
    ) -> dict[str, Any]:
        state = self._require_job(job_id)
        text = " ".join(str(text or "").split())
        if not text:
            raise ValueError("Claim text must not be empty")
        requirement_ids = list(requirement_ids or ["R1"])
        evidence_ids = list(evidence_ids or [])
        unknown_evidence = [eid for eid in evidence_ids if self._find_evidence(state, eid) is None]
        if unknown_evidence:
            raise ValueError(f"Unknown evidence IDs: {', '.join(unknown_evidence)}")
        claim = self._find_claim(state, text)
        if claim is None:
            claim = Claim(claim_id=f"C-{len(state.claims) + 1}", text=text)
            state.claims.append(claim)
        for requirement_id in requirement_ids:
            if requirement_id not in claim.requirement_ids:
                claim.requirement_ids.append(requirement_id)
        for evidence_id in evidence_ids:
            if evidence_id not in claim.evidence_ids:
                claim.evidence_ids.append(evidence_id)
        claim.provenance = sorted({
            self._find_evidence(state, evidence_id).source_id
            for evidence_id in claim.evidence_ids
            if self._find_evidence(state, evidence_id) is not None
        })
        claim.status = status if status in {"supported", "partially_supported", "unverified", "ambiguous", "insufficient_data"} else self._claim_status_from_evidence(state, claim)
        claim.epistemic_status = claim.status
        claim.updated_at = utc_now()
        self._sync_requirements(state)
        state.trace.append({
            "event": "claim_recorded",
            "claim_id": claim.claim_id,
            "status": claim.status,
            "evidence_ids": claim.evidence_ids,
        })
        return claim.to_dict()

    def ingest_source(
        self,
        job_id: str,
        url: str,
        title: str = "",
        content: str = "",
        excerpt: str = "",
        source_type: str = "secondary",
        primary: bool = False,
        verified: bool = False,
        claim: str = "",
        requirement_ids: list[str] | None = None,
        locator: str = "",
        published_at: str | None = None,
        freshness: float | None = None,
    ) -> dict[str, Any]:
        state = self._require_job(job_id)
        url = str(url or "").strip()
        if not url:
            raise ValueError("Source URL must not be empty")
        content = str(content or "")
        excerpt = str(excerpt or content[:2000]).strip()
        if not excerpt:
            raise ValueError("Source content or excerpt must not be empty")
        domain = urlparse(url).netloc.casefold().removeprefix("www.")
        content_hash = stable_hash({"url": url, "content": content or excerpt})
        if self.dedup.is_duplicate(self.dedup.canonical(url), content_hash):
            existing = next((s for s in state.sources if s.content_hash == content_hash), None)
            return {"duplicate": True, "source": existing.to_dict() if existing else None}
        source = Source(
            source_id=f"S-{len(state.sources) + 1}",
            url=url,
            title=title,
            domain=domain,
            source_type="primary" if primary or source_type.casefold() in {"primary", "official"} else "secondary",
            authority=1.0 if primary or source_type.casefold() in {"primary", "official"} else 0.5,
            freshness=float(freshness) if freshness is not None else (1.0 if verified else 0.5),
            content_hash=content_hash,
            status="verified" if verified else "retrieved",
            published_at=published_at,
            locator=locator,
        )
        evidence = Evidence(
            evidence_id=f"E-{len(state.evidence) + 1}",
            source_id=source.source_id,
            claim=claim or title or url,
            excerpt=excerpt[:10000],
            locator=locator,
            confidence=1.0 if verified else 0.0,
            content_hash=content_hash,
            status="verified" if verified else "observed",
        )
        state.sources.append(source)
        state.evidence.append(evidence)
        if claim:
            self.add_claim(
                job_id,
                claim,
                requirement_ids=requirement_ids,
                evidence_ids=[evidence.evidence_id],
                status="supported" if verified else "unverified",
            )
        else:
            self._sync_requirements(state)
        state.trace.append({
            "event": "source_ingested",
            "source_id": source.source_id,
            "evidence_id": evidence.evidence_id,
            "source_type": source.source_type,
            "verified": verified,
        })
        return {
            "source": source.to_dict(),
            "evidence": evidence.to_dict(),
            "requirements": state.requirements,
        }

    def build_plan(self, job_id: str, max_queries: int | None = None, rebuild: bool = False) -> list[dict[str, Any]]:
        state = self._require_job(job_id)
        if state.queries and not rebuild:
            return state.queries
        original = state.request.original_request
        budget = min(state.queries_budget, self._budget(max_queries or state.queries_budget))
        candidates: list[tuple[str, str]] = [
            (original, "exact_request"),
            (f"{original} primary source", "primary_source_discovery"),
            (f"{original} contradiction alternative evidence", "counter_evidence"),
        ]
        for source in state.request.primary_sources:
            candidates.append((f"{original} {source}", "required_primary_source"))
        for requirement in state.request.requirements[:12]:
            if requirement.text.casefold() != original.casefold():
                candidates.append((f"{original} {requirement.text}", "requirement_preservation"))
        for scope in state.request.scope[:5]:
            candidates.append((f"{original} scope {scope}", "scope_constraint"))
        for correction in state.corrections:
            candidates.append((f"{original} correction {correction.text}", "correction_integration"))
        plan: list[dict[str, Any]] = []
        seen: set[str] = set()
        for query, purpose in candidates:
            normalized = " ".join(query.split())
            key = normalized.casefold()
            if key in seen:
                continue
            seen.add(key)
            plan.append({
                "query_id": f"Q-{len(plan) + 1}",
                "text": normalized,
                "purpose": purpose,
                "preserves_request": original.casefold() in normalized.casefold(),
                "request_checksum": state.request.checksum,
            })
            if len(plan) >= budget:
                break
        state.queries = plan
        state.queries_used = len(plan)
        state.touch()
        state.trace.append({"event": "plan_built", "queries": len(plan), "request_checksum": state.request.checksum})
        return plan

    def apply_correction(
        self,
        job_id: str,
        correction: str,
        requirements: list[Any] | None = None,
    ) -> dict[str, Any]:
        state = self._require_job(job_id)
        correction = " ".join(str(correction or "").split())
        if not correction:
            raise ValueError("Correction must not be empty")
        retired: list[str] = []
        for claim in state.claims:
            if claim.status not in {"retired", "rejected"}:
                claim.status = "retired"
                claim.epistemic_status = "retired"
                claim.updated_at = utc_now()
                retired.append(claim.claim_id)
        new_requirements = list(requirements or [{"text": correction, "type": "correction", "required": True}])
        new_ids: list[str] = []
        for index, item in enumerate(new_requirements, start=1):
            if isinstance(item, dict):
                text = str(item.get("text") or item.get("requirement") or "").strip()
                kind = str(item.get("type") or "correction")
                required = bool(item.get("required", True))
            else:
                text = str(item).strip()
                kind = "correction"
                required = True
            if not text:
                continue
            requirement_id = f"R-C{len(state.corrections) + 1}-{index}"
            state.requirements.append({
                "id": requirement_id,
                "text": text,
                "type": kind,
                "required": required,
                "origin": "user_correction",
                "status": "missing",
                "evidence_ids": [],
                "notes": "",
            })
            new_ids.append(requirement_id)
        correction_record = Correction(
            correction_id=f"COR-{len(state.corrections) + 1}",
            text=correction,
            incorporated=bool(new_ids),
            retired_claim_ids=retired,
            new_requirement_ids=new_ids,
        )
        state.corrections.append(correction_record)
        state.queries = []
        state.status = "correction_recorded"
        self._sync_requirements(state)
        state.trace.append({
            "event": "correction_recorded",
            "correction_id": correction_record.correction_id,
            "retired_claim_ids": retired,
            "new_requirement_ids": new_ids,
            "original_request_preserved": True,
        })
        return correction_record.to_dict()

    def audit(self, job_id: str, final: bool = False) -> dict[str, Any]:
        state = self._require_job(job_id)
        self._sync_requirements(state)
        metrics = self.coverage_analyzer.compute_metrics(state)
        findings = self.coverage_analyzer.findings(state, metrics)
        passed = not findings
        audit = Audit(
            audit_id=f"A-{len(state.audits) + 1}",
            created_at=utc_now(),
            metrics=metrics,
            findings=findings,
            gate_pass=passed,
            final=final,
        )
        state.audits.append(audit)
        state.status = "complete" if passed and final else "verified" if passed else "blocked"
        state.touch()
        state.trace.append({
            "event": "audit_completed",
            "audit_id": audit.audit_id,
            "gate_pass": passed,
            "final": final,
        })
        return audit.to_dict()

    def synthesize(self, job_id: str) -> dict[str, Any]:
        state = self._require_job(job_id)
        self._sync_requirements(state)
        supported = [claim.to_dict() for claim in state.claims if claim.status == "supported"]
        unresolved = [claim.to_dict() for claim in state.claims if claim.status != "supported"]
        missing = [item for item in state.requirements if item.get("status") != "covered"]
        return {
            "task_id": state.task_id,
            "supported_claims": supported,
            "unresolved_claims": unresolved,
            "uncovered_requirements": missing,
            "open_contradictions": [item.to_dict() for item in state.contradictions if item.status == "open"],
            "sources": [item.to_dict() for item in state.sources],
            "answer_policy": "Use only supported claims; state unknowns and contradictions explicitly.",
            "memory_policy": state.memory_policy,
            "audit": self.audit(job_id, final=False),
        }

    def context(self, job_id: str) -> dict[str, Any]:
        state = self._require_job(job_id)
        plan = self.build_plan(job_id)
        return {
            "task_id": state.task_id,
            "request": state.request.to_dict(),
            "requirements": state.requirements,
            "plan": plan,
            "memory_policy": state.memory_policy,
            "reasoning": initialize_reasoning(
                task=state.request.original_request,
                execution_mode="background",
                browser_mode="existing",
            ),
            "progress": state.progress(),
            "next_action": "Retrieve sources, then call research_ingest with exact excerpts and provenance.",
        }

    def export(self, job_id: str) -> dict[str, Any]:
        return self._require_job(job_id).to_dict()

    async def run_background(self, job_id: str) -> None:
        state = self._require_job(job_id)
        state.status = "planning"
        self.build_plan(job_id)
        if not state.evidence:
            state.status = "awaiting_evidence"
            state.trace.append({
                "event": "planning_complete_without_evidence",
                "message": "A query plan is not evidence; retrieval and ingestion are required.",
            })
            return
        self.audit(job_id, final=False)

    def _require_job(self, job_id: str) -> ResearchState:
        state = self.jobs.get(job_id)
        if state is None:
            raise KeyError(f"Unknown research job: {job_id}")
        return state
