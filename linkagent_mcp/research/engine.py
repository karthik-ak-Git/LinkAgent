import asyncio, hashlib, time, uuid
from .models import RequestSpec, ResearchState, Source, Evidence, Claim
from .coverage import CoverageAnalyzer
from .contradiction import ContradictionDetector
from .deduplication import Deduplicator

class ResearchEngine:
    def __init__(self, browser_manager=None, max_queries=500, coverage_threshold=0.9, workers=5):
        self.bm=browser_manager; self.max_queries=max_queries; self.threshold=coverage_threshold; self.workers=workers
        self.jobs: dict[str,ResearchState]={}
        self.coverage_analyzer=CoverageAnalyzer(self.threshold)
        self.contradiction_detector=ContradictionDetector()
        self.dedup=Deduplicator()
        self._rate_limiter={} # domain -> last_time

    def create_job(self, query: str, **kw) -> ResearchState:
        # Immutable RequestSpec per §11
        reqs=[{"id":"R1","text":query,"type":"objective","status":"missing"}]
        spec=RequestSpec.create(query, reqs)
        st=ResearchState(task_id=spec.request_id, requirements=spec.requirements, queries_budget=kw.get("max_queries",self.max_queries))
        st.trace.append({"event":"job_created","query":query,"ts":time.time()})
        self.jobs[st.task_id]=st
        return st

    def get(self, job_id): return self.jobs.get(job_id)

    async def run_background(self, job_id):
        st=self.jobs[job_id]; st.status="investigating"
        sem=asyncio.Semaphore(self.workers)
        # Adaptive loop §40: stop when coverage >= threshold or budget exhausted
        while st.queries_used < st.queries_budget:
            cov=self.coverage_analyzer.compute(st)
            st.coverage=cov
            if self.coverage_analyzer.gate_pass(st):
                break
            # gap detection -> next query (simplified)
            async with sem:
                st.queries_used+=1
                await asyncio.sleep(0.01) # placeholder for real query execution
                st.trace.append({"event":"query_executed","queries_used":st.queries_used})
            # contradiction check
            self.contradiction_detector.scan(st)
            if st.queries_used>=3: # demo stop
                break
        st.status="completed"
        st.trace.append({"event":"completed","coverage":st.coverage,"queries_used":st.queries_used})

    def apply_correction(self, job_id, new_query: str):
        st=self.jobs[job_id]
        st.trace.append({"event":"correction","new_query":new_query})
        # Invalidate hypotheses §13
        for c in st.claims: c.status="unverified"
        st.requirements=[{"id":"R1","text":new_query,"type":"objective","status":"missing"}]
        st.coverage=0
