import asyncio
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.lead_finder.scheduler import LeadScheduler, scan_enabled_lead_sources
from app.lead_finder.service import LeadFinderService
from app.lead_finder.types import LeadCandidate
from app.models.lead_source import LeadSource


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


async def test_scheduled_scan_processes_only_enabled_sources(
    session: AsyncSession,
    monkeypatch,
) -> None:
    enabled = LeadSource(url="https://enabled.example/", enabled=True)
    disabled = LeadSource(url="https://disabled.example/", enabled=False)
    session.add_all([enabled, disabled])
    await session.flush()

    candidate = LeadCandidate(
        name="Example Studio",
        source="website",
        url=enabled.url,
        niche="designers",
        contact="hello@example.com",
        reason_fit="design services available",
        score=80,
    )

    class Scanner:
        scan = AsyncMock(return_value=candidate)

    save_candidate = AsyncMock(return_value=(object(), True))
    monkeypatch.setattr(LeadFinderService, "save_candidate", save_candidate)

    scanner = Scanner()
    await scan_enabled_lead_sources(session, scanner)  # type: ignore[arg-type]

    scanner.scan.assert_awaited_once_with(url=enabled.url)
    save_candidate.assert_awaited_once_with(candidate)
    assert enabled.last_scanned_at is not None
    assert disabled.last_scanned_at is None
