from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
import time
import uuid
from typing import Any


MEMORY_POLICY = "untrusted_cache"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _requirement_input(value: Any, index: int) -> dict[str, Any]:
    if isinstance(value, dict):
        text = _clean(value.get("text") or value.get("requirement") or value.get("query"))
        return {
            "id": _clean(value.get("id")) or f"R{index}",
            "text": text,
            "type": _clean(value.get("type")) or "constraint",
            "required": bool(value.get("required", True)),
            "origin": _clean(value.get("origin")) or "user",
        }
    return {
        "id": f"R{index}",
        "text": _clean(value),
        "type": "constraint",
        "required": True,
        "origin": "user",
    }


def _infer_requirements(original: str) -> list[dict[str, Any]]:
    """Create a conservative, inspectable requirement inventory.

    This is intentionally deterministic. It does not pretend to understand the
    task perfectly; it preserves the complete request and surfaces material terms
    so a later agent can correct the inventory explicitly.
    """
    original = _clean(original)
    requirements = [{
        "id": "R1",
        "text": original,
        "type": "request",
        "required": True,
        "origin": "user_exact",
    }]
    seen = {original.casefold()}

    def add(text: str, kind: str) -> None:
        text = _clean(text)
        if not text or text.casefold() in seen:
            return
        seen.add(text.casefold())
        requirements.append({
            "id": f"R{len(requirements) + 1}",
            "text": text,
            "type": kind,
            "required": True,
            "origin": "detected",
        })

    # Preserve explicit enumerations, quantities, and named source requests.
    for match in re.findall(r"\b\d+(?:\s*(?:to|[-–])\s*\d+)?\b", original, flags=re.I):
        add(match, "constraint")
    for match in re.findall(r"\b(?:official|primary source|notification|notice|pdf|regulation|directive|circular|problem statement)s?\b", original, flags=re.I):
        add(match, "source")
    for match in re.findall(r"\b(?:comes under|belongs to|classified as|compare|versus|between)\b", original, flags=re.I):
        add(match, "relation")

    # Terms are search hints, not hidden assumptions. The exact request remains R1.
    stopwords = {
        "the", "and", "for", "with", "from", "what", "which", "does", "come",
        "comes", "under", "this", "that", "your", "you", "are", "was", "were",
        "have", "has", "had", "can", "could", "should", "would", "about", "into",
        "need", "want", "please", "tell", "give", "find", "use", "using", "also",
    }
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", original)
    for word in words:
        if word.casefold() not in stopwords:
            add(word, "domain_anchor" if word.isupper() else "term")
    return requirements


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    type: str = "constraint"
    required: bool = True
    origin: str = "user"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RequestSpec:
    """Immutable request record. Hypotheses and evidence never overwrite it."""
    request_id: str
    original_request: str
    requirements: tuple[Requirement, ...]
    primary_sources: tuple[str, ...]
    scope: tuple[str, ...]
    checksum: str
    created_at: str

    @staticmethod
    def create(
        original: str,
        requirements: list[Any] | tuple[Any, ...] | None = None,
        primary_sources: list[str] | tuple[str, ...] | None = None,
        scope: list[str] | tuple[str, ...] | None = None,
    ) -> "RequestSpec":
        original = _clean(original)
        if not original:
            raise ValueError("The original request must not be empty")
        raw = list(requirements) if requirements is not None else _infer_requirements(original)
        parsed = tuple(
            Requirement(**_requirement_input(item, i + 1))
            for i, item in enumerate(raw)
            if _requirement_input(item, i + 1)["text"]
        )
        if not parsed:
            raise ValueError("At least one non-empty requirement is required")
        sources = tuple(_clean(x) for x in (primary_sources or []) if _clean(x))
        scopes = tuple(_clean(x) for x in (scope or []) if _clean(x))
        checksum_payload = {
            "original_request": original,
            "requirements": [r.to_dict() for r in parsed],
            "primary_sources": sources,
            "scope": scopes,
        }
        checksum = stable_hash(checksum_payload)[:16]
        return RequestSpec(
            request_id=str(uuid.uuid4()),
            original_request=original,
            requirements=parsed,
            primary_sources=sources,
            scope=scopes,
            checksum=checksum,
            created_at=utc_now(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "original_request": self.original_request,
            "requirements": [r.to_dict() for r in self.requirements],
            "primary_sources": list(self.primary_sources),
            "scope": list(self.scope),
            "checksum": self.checksum,
            "created_at": self.created_at,
            "memory_policy": MEMORY_POLICY,
        }


@dataclass
class Source:
    source_id: str
    url: str
    title: str = ""
    domain: str = ""
    source_type: str = "secondary"
    authority: float = 0.5
    freshness: float = 0.5
    content_hash: str = ""
    status: str = "retrieved"
    retrieved_at: str = field(default_factory=utc_now)
    published_at: str | None = None
    locator: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Evidence:
    evidence_id: str
    source_id: str
    claim: str
    excerpt: str
    locator: str = ""
    confidence: float = 0.0
    retrieved_at: str = field(default_factory=utc_now)
    content_hash: str = ""
    status: str = "observed"
    supports_claim_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    claim_id: str
    text: str
    requirement_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    status: str = "unverified"
    confidence: float = 0.0
    epistemic_status: str = "unverified"
    provenance: list[str] = field(default_factory=list)
    correction_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Contradiction:
    contradiction_id: str
    claim_ids: list[str]
    evidence_ids: list[str] = field(default_factory=list)
    description: str = ""
    status: str = "open"
    detected_at: str = field(default_factory=utc_now)
    resolution: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Correction:
    correction_id: str
    text: str
    received_at: str = field(default_factory=utc_now)
    incorporated: bool = False
    retired_claim_ids: list[str] = field(default_factory=list)
    new_requirement_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Audit:
    audit_id: str
    created_at: str
    metrics: dict[str, Any]
    findings: list[str]
    gate_pass: bool
    final: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchState:
    task_id: str
    request: RequestSpec
    status: str = "queued"
    requirements: list[dict[str, Any]] = field(default_factory=list)
    queries_budget: int = 500
    queries_used: int = 0
    queries: list[dict[str, Any]] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    corrections: list[Correction] = field(default_factory=list)
    audits: list[Audit] = field(default_factory=list)
    coverage: float = 0.0
    trace: list[dict[str, Any]] = field(default_factory=list)
    memory_policy: str = MEMORY_POLICY
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def progress(self) -> dict[str, Any]:
        counts = {status: 0 for status in ("covered", "partial", "missing", "disputed", "stale")}
        for requirement in self.requirements:
            status = requirement.get("status", "missing")
            counts[status] = counts.get(status, 0) + 1
        claim_counts: dict[str, int] = {}
        for claim in self.claims:
            claim_counts[claim.status] = claim_counts.get(claim.status, 0) + 1
        latest_audit = self.audits[-1].to_dict() if self.audits else None
        return {
            "task_id": self.task_id,
            "status": self.status,
            "coverage": self.coverage,
            "request_checksum": self.request.checksum,
            "request_integrity": self.request.checksum == self._recompute_checksum(),
            "queries_used": self.queries_used,
            "queries_budget": self.queries_budget,
            "requirements": counts,
            "claims": claim_counts,
            "sources": len(self.sources),
            "evidence": len(self.evidence),
            "open_contradictions": sum(c.status == "open" for c in self.contradictions),
            "corrections": len(self.corrections),
            "memory_policy": self.memory_policy,
            "latest_audit": latest_audit,
        }

    def _recompute_checksum(self) -> str:
        return stable_hash({
            "original_request": self.request.original_request,
            "requirements": [r.to_dict() for r in self.request.requirements],
            "primary_sources": list(self.request.primary_sources),
            "scope": list(self.request.scope),
        })[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "request": self.request.to_dict(),
            "requirements": self.requirements,
            "queries_budget": self.queries_budget,
            "queries_used": self.queries_used,
            "queries": self.queries,
            "sources": [s.to_dict() for s in self.sources],
            "evidence": [e.to_dict() for e in self.evidence],
            "claims": [c.to_dict() for c in self.claims],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "corrections": [c.to_dict() for c in self.corrections],
            "audits": [a.to_dict() for a in self.audits],
            "coverage": self.coverage,
            "trace": self.trace,
            "memory_policy": self.memory_policy,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
