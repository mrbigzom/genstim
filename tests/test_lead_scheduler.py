import asyncio
import logging
from unittest.mock import AsyncMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lead_finder.scheduler import LeadScheduler, scan_enabled_lead_sources
from app.lead_finder.service import LeadFinderService
from app.lead_finder.types import LeadCandidate
from app.lead_finder.web import PublicWebsiteError
from app.models.lead import Lead
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


async def test_source_error_does_not_stop_following_source(
    session: AsyncSession,
    monkeypatch,
    caplog,
) -> None:
    first = LeadSource(url="https://broken.example/leads", enabled=True)
    second = LeadSource(url="https://working.example/leads", enabled=True)
    session.add_all([first, second])
    await session.flush()

    candidate = LeadCandidate(
        name="Working Company",
        source="website",
        url=second.url,
        niche="designers",
        contact="hello@example.com",
        reason_fit="design services available",
        score=80,
    )

    class Scanner:
        scan = AsyncMock(side_effect=[PublicWebsiteError("blocked"), candidate])

    save_candidate = AsyncMock(return_value=(object(), True))
    monkeypatch.setattr(LeadFinderService, "save_candidate", save_candidate)

    scanner = Scanner()
    with caplog.at_level(logging.ERROR, logger="app.lead_finder.scheduler"):
        await scan_enabled_lead_sources(session, scanner)  # type: ignore[arg-type]

    assert scanner.scan.await_count == 2
    scanner.scan.assert_any_await(url=first.url)
    scanner.scan.assert_any_await(url=second.url)
    save_candidate.assert_awaited_once_with(candidate)
    assert first.last_scanned_at is None
    assert second.last_scanned_at is not None
    assert f"source_id={first.id}" in caplog.text
    assert f"source_url={first.url}" in caplog.text


async def test_repeated_source_scan_does_not_duplicate_lead(
    session: AsyncSession,
) -> None:
    source = LeadSource(url="https://example.com/leads", enabled=True)
    session.add(source)
    await session.flush()

    candidate = LeadCandidate(
        name="Example Company",
        source="website",
        url="https://example.com/jobs/designer",
        niche="designers",
        contact="hello@example.com",
        reason_fit="design services available",
        score=80,
    )

    class Scanner:
        scan = AsyncMock(return_value=candidate)

    scanner = Scanner()
    await scan_enabled_lead_sources(session, scanner)  # type: ignore[arg-type]
    await scan_enabled_lead_sources(session, scanner)  # type: ignore[arg-type]

    leads = list(await session.scalars(select(Lead)))
    assert scanner.scan.await_count == 2
    assert len(leads) == 1
    assert leads[0].source == candidate.source
    assert leads[0].url == candidate.url


async def test_scheduler_continues_after_job_error() -> None:
    completed_after_error = asyncio.Event()
    calls = 0

    async def job() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary failure")
        completed_after_error.set()

    scheduler = LeadScheduler(interval_seconds=0.01, job=job)
    scheduler.start()
    try:
        await asyncio.wait_for(completed_after_error.wait(), timeout=0.5)
    finally:
        await scheduler.stop()

    assert calls >= 2
