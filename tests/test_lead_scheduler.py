import asyncio

from app.lead_finder.scheduler import LeadScheduler


async def test_scheduler_starts_and_invokes_registered_job() -> None:
    invoked = asyncio.Event()

    async def job() -> None:
        invoked.set()

    scheduler = LeadScheduler(interval_seconds=0.01, job=job)
    task = scheduler.start()

    assert task.get_name() == "lead-finder-scheduler"
    assert scheduler.start() is task
    await asyncio.wait_for(invoked.wait(), timeout=0.5)

    await scheduler.stop()
    assert task.done()
