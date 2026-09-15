from dataclasses import dataclass, field
import hashlib, uuid, time

@dataclass(frozen=True)
class RequestSpec:
    request_id: str
    original_request: str
    requirements: list[dict]
    checksum: str
    @staticmethod
    def create(original: str, requirements: list[dict]):
        cs=hashlib.sha256(original.encode()).hexdigest()[:16]
        return RequestSpec(str(uuid.uuid4()), original, requirements, cs)

@dataclass
class Source:
    source_id: str; url: str; title: str=""; domain: str=""; source_type: str="secondary"; authority: float=0.5; freshness: float=0.5; content_hash: str=""; status: str="verified"
@dataclass
class Evidence:
    evidence_id: str; source_id: str; claim: str; excerpt: str; confidence: float=0.8
@dataclass
class Claim:
    claim_id: str; text: str; requirement_ids: list[str]=field(default_factory=list); evidence_ids: list[str]=field(default_factory=list); status: str="unverified"; confidence: float=0.5

@dataclass
class ResearchState:
    task_id: str; status: str="queued"
    requirements: list[dict]=field(default_factory=list)
    queries_budget: int=500; queries_used: int=0
    sources: list[Source]=field(default_factory=list)
    claims: list[Claim]=field(default_factory=list)
    coverage: float=0.0
    trace: list[dict]=field(default_factory=list)
    def progress(self): return {"task_id":self.task_id,"status":self.status,"coverage":self.coverage,"queries_used":self.queries_used,"queries_budget":self.queries_budget}
