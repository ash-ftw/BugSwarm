from __future__ import annotations

import asyncio

from bugswarm_worker.agents.explorer import run_explorer_agent
from bugswarm_worker.queue import celery_app


@celery_app.task(name="bugswarm.run_agent")
def run_agent(job: dict) -> None:
    asyncio.run(run_explorer_agent(job))
