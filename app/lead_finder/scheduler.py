import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

ScheduledJob = Callable[[], Awaitable[None]]


async def lead_finder_placeholder_job() -> None:
    logger.info("Lead Finder scheduled placeholder job invoked")


class LeadScheduler:
    def __init__(self, *, interval_seconds: float, job: ScheduledJob) -> None:
        if interval_seconds <= 0:
            raise ValueError("Scheduler interval must be positive")
        self.interval_seconds = interval_seconds
        self.job = job
        self._task: asyncio.Task[None] | None = None

    def start(self) -> asyncio.Task[None]:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(
                self._run(),
                name="lead-finder-scheduler",
            )
            logger.info(
                "Lead Finder scheduler started interval_seconds=%s",
                self.interval_seconds,
            )
        return self._task

    async def stop(self) -> None:
        if self._task is None:
            return
        if not self._task.done():
            self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)
        self._task = None
        logger.info("Lead Finder scheduler stopped")

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)
            try:
                await self.job()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Lead Finder scheduled placeholder job failed")
