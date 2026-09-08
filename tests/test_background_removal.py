from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation import Generation
from app.providers.background_removal import (
    BackgroundRemovalProviderError,
    BackgroundRemovalTimeoutError,
    PhotoroomBackgroundRemovalProvider,
)
from app.services.background_removal import (
    BackgroundRemovalFailedError,
    BackgroundRemovalService,
    InsufficientCreditsError,
)
from app.services.generation import GenerationService
from app.services.image_files import temporary_work_directory
from app.services.user import UserService

PNG_RESULT = b"\x89PNG\r\n\x1a\nresult"


class SuccessfulProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def remove_background(self, image_path: Path, content_type: str) -> bytes:
        self.calls += 1
        assert content_type == "image/jpeg"
        return PNG_RESULT


class FailingProvider:
    def __init__(self, error: BackgroundRemovalProviderError) -> None:
        self.error = error
        self.calls = 0

    async def remove_background(self, image_path: Path, content_type: str) -> bytes:
        self.calls += 1
        raise self.error


async def create_user(session: AsyncSession, telegram_id: int = 1001):
    user, _ = await UserService(session).get_or_create(
        telegram_id=telegram_id,
        username="tester",
        first_name="Test",
        telegram_language="en",
    )
    return user


async def test_successful_processing_charges_one_credit_and_completes_record(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    user = await create_user(session)
    input_path = tmp_path / "input.jpg"
    input_path.write_bytes(b"jpeg")
    provider = SuccessfulProvider()

    result = await BackgroundRemovalService(session, provider).process(
        user_id=user.id,
        image_path=input_path,
        content_type="image/jpeg",
    )

    assert result.image == PNG_RESULT
    assert result.remaining_credits == 2
    assert user.credits == 2
    assert result.generation.status == "completed"
    assert result.generation.credits_spent == 1
    assert result.generation.completed_at is not None
    assert result.generation.error_code is None
    assert provider.calls == 1


async def test_insufficient_credits_does_not_call_provider_or_create_record(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    user = await create_user(session)
    user.credits = 0
    await session.flush()
    provider = SuccessfulProvider()

    with pytest.raises(InsufficientCreditsError):
        await BackgroundRemovalService(session, provider).process(
            user_id=user.id,
            image_path=tmp_path / "unused.jpg",
            content_type="image/jpeg",
        )

    records = list(await session.scalars(select(Generation)))
    assert provider.calls == 0
    assert user.credits == 0
    assert records == []


async def test_provider_error_records_failure_without_charging_credit(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    user = await create_user(session)
    provider = FailingProvider(BackgroundRemovalProviderError("provider_unavailable"))

    with pytest.raises(BackgroundRemovalFailedError) as error:
        await BackgroundRemovalService(session, provider).process(
            user_id=user.id,
            image_path=tmp_path / "input.jpg",
            content_type="image/jpeg",
        )

    record = await session.scalar(select(Generation))
    assert error.value.code == "provider_unavailable"
    assert user.credits == 3
    assert record is not None
    assert record.status == "failed"
    assert record.credits_spent == 0
    assert record.error_code == "provider_unavailable"
    assert record.completed_at is not None


async def test_timeout_records_specific_error_without_charging_credit(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    user = await create_user(session)
    provider = FailingProvider(BackgroundRemovalTimeoutError())

    with pytest.raises(BackgroundRemovalFailedError) as error:
        await BackgroundRemovalService(session, provider).process(
            user_id=user.id,
            image_path=tmp_path / "input.jpg",
            content_type="image/jpeg",
        )

    record = await session.scalar(select(Generation))
    assert error.value.code == "provider_timeout"
    assert user.credits == 3
    assert record is not None
    assert record.error_code == "provider_timeout"


async def test_credit_is_charged_only_for_the_successful_attempt(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    user = await create_user(session)
    failed_service = BackgroundRemovalService(
        session,
        FailingProvider(BackgroundRemovalProviderError("provider_error")),
    )
    with pytest.raises(BackgroundRemovalFailedError):
        await failed_service.process(
            user_id=user.id,
            image_path=tmp_path / "input.jpg",
            content_type="image/jpeg",
        )

    result = await BackgroundRemovalService(session, SuccessfulProvider()).process(
        user_id=user.id,
        image_path=tmp_path / "input.jpg",
        content_type="image/jpeg",
    )

    records = list(await session.scalars(select(Generation).order_by(Generation.id)))
    assert user.credits == 2
    assert result.remaining_credits == 2
    assert [record.credits_spent for record in records] == [0, 1]


def test_temporary_work_directory_is_removed_after_error(tmp_path: Path) -> None:
    work_directory: Path | None = None

    with pytest.raises(RuntimeError, match="processing failed"):
        with temporary_work_directory(parent=tmp_path) as directory:
            work_directory = directory
            (directory / "private-photo.jpg").write_bytes(b"private")
            raise RuntimeError("processing failed")

    assert work_directory is not None
    assert not work_directory.exists()


async def test_history_contains_only_completed_generation(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    user = await create_user(session)
    with pytest.raises(BackgroundRemovalFailedError):
        await BackgroundRemovalService(
            session,
            FailingProvider(BackgroundRemovalProviderError("provider_error")),
        ).process(
            user_id=user.id,
            image_path=tmp_path / "failed.jpg",
            content_type="image/jpeg",
        )
    successful = await BackgroundRemovalService(session, SuccessfulProvider()).process(
        user_id=user.id,
        image_path=tmp_path / "success.jpg",
        content_type="image/jpeg",
    )

    history = await GenerationService(session).completed_history(user.id)

    assert [record.id for record in history] == [successful.generation.id]
    assert history[0].feature == "background_removal"


async def test_photoroom_provider_retries_temporary_error(tmp_path: Path) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        assert request.headers["x-api-key"] == "test-key"
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(200, content=PNG_RESULT, headers={"content-type": "image/png"})

    async def no_sleep(_: float) -> None:
        return None

    input_path = tmp_path / "input.jpg"
    input_path.write_bytes(b"jpeg")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = PhotoroomBackgroundRemovalProvider(
            api_key="test-key",
            max_retries=1,
            client=client,
            sleep=no_sleep,
        )
        result = await provider.remove_background(input_path, "image/jpeg")

    assert result == PNG_RESULT
    assert attempts == 2


async def test_photoroom_provider_maps_timeout_after_retries(tmp_path: Path) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("timed out", request=request)

    async def no_sleep(_: float) -> None:
        return None

    input_path = tmp_path / "input.jpg"
    input_path.write_bytes(b"jpeg")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = PhotoroomBackgroundRemovalProvider(
            api_key="test-key",
            max_retries=1,
            client=client,
            sleep=no_sleep,
        )
        with pytest.raises(BackgroundRemovalTimeoutError):
            await provider.remove_background(input_path, "image/jpeg")

    assert attempts == 2
