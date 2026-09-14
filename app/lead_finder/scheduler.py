import asyncio
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.lead_finder.service import LeadFinderService
from app.lead_finder.web import PublicWebsiteError, PublicWebsiteScanner
from app.services.lead_source import LeadSourceService

logger = logging.getLogger(__name__)

ScheduledJob = Callable[[], Awaitable[None]]


async def scan_enabled_lead_sources(
    session: AsyncSession,
    scanner: PublicWebsiteScanner,
) -> None:
    source_service = LeadSourceService(session)
    lead_service = LeadFinderService(session)
    sources = await source_service.list_enabled()
    logger.info("Lead Finder scheduled scan started source_count=%s", len(sources))

    for source in sources:
        try:
            candidate = await scanner.scan(url=source.url)
        except PublicWebsiteError as exc:
            logger.warning(
                "Lead source scan skipped source_id=%s error_type=%s",
                source.id,
                type(exc).__name__,
            )
            continue
        await source_service.mark_scanned(source)
        if candidate is not None:
            await lead_service.save_candidate(candidate)

    logger.info("Lead Finder scheduled scan completed source_count=%s", len(sources))


def create_lead_scan_job(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    scanner: PublicWebsiteScanner | None = None,
) -> ScheduledJob:
    website_scanner = scanner or PublicWebsiteScanner()

    async def job() -> None:
        async with session_factory() as session:
            try:
                await scan_enabled_lead_sources(session, website_scanner)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return job


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
                logger.exception("Lead Finder scheduled scan failed")
