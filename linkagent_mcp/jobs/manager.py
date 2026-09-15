import asyncio, uuid
from ..research.engine import ResearchEngine
class JobManager:
    def __init__(self, engine: ResearchEngine):
        self.engine=engine; self.tasks={}
    def create(self, query, **kw):
        st=self.engine.create_job(query, **kw)
        if kw.get("background"):
            t=asyncio.create_task(self.engine.run_background(st.task_id))
            self.tasks[st.task_id]=t
        return st
    def status(self, job_id): return self.engine.get(job_id)
    def cancel(self, job_id):
        if job_id in self.tasks: self.tasks[job_id].cancel()
        st=self.engine.get(job_id)
        if st: st.status="cancelled"
        return st
