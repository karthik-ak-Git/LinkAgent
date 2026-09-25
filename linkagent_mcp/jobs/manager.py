from __future__ import annotations

import asyncio

from ..research.engine import ResearchEngine


class JobManager:
    def __init__(self, engine: ResearchEngine):
        self.engine = engine
        self.tasks: dict[str, asyncio.Task] = {}

    def create(self, query: str, **kwargs):
        state = self.engine.create_job(query, **kwargs)
        if kwargs.get("background"):
            self.tasks[state.task_id] = asyncio.create_task(
                self.engine.run_background(state.task_id)
            )
        return state

    def status(self, job_id: str):
        return self.engine.get(job_id)

    def cancel(self, job_id: str):
        task = self.tasks.get(job_id)
        if task and not task.done():
            task.cancel()
        state = self.engine.get(job_id)
        if state:
            state.status = "cancelled"
            state.touch()
            state.trace.append({"event": "cancelled", "job_id": job_id})
        return state
