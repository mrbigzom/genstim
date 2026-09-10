from io import BytesIO
from pathlib import Path
from time import sleep

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation import Generation
from app.providers.background_removal import (
    BackgroundRemovalProviderError,
    BackgroundRemovalTimeoutError,
    RembgBackgroundRemovalProvider,
)
from app.services.background_removal import (
    BackgroundRemovalFailedError,
    BackgroundRemovalService,
    InsufficientCreditsError,
)
from app.services.generation import GenerationService
from app.services.image_files import temporary_work_directory
from app.services.user import UserService


def make_image_bytes(image_format: str, *, size: tuple[int, int] = (10, 10)) -> bytes:
    image = Image.new("RGBA" if image_format == "PNG" else "RGB", size, "red")
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


PNG_RESULT = make_image_bytes("PNG")


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


async def test_successful_processing_charges_configured_credits_and_completes_record(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    user = await create_user(session)
    user.credits = 10
    input_path = tmp_path / "input.jpg"
    input_path.write_bytes(b"jpeg")
    provider = SuccessfulProvider()

    result = await BackgroundRemovalService(session, provider).process(
        user_id=user.id,
        image_path=input_path,
        content_type="image/jpeg",
    )

    assert result.image == PNG_RESULT
    assert result.remaining_credits == 5
    assert user.credits == 5
    assert result.generation.status == "completed"
    assert result.generation.credits_spent == 5
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
    user.credits = 10
    provider = FailingProvider(BackgroundRemovalProviderError("provider_unavailable"))

    with pytest.raises(BackgroundRemovalFailedError) as error:
        await BackgroundRemovalService(session, provider).process(
            user_id=user.id,
            image_path=tmp_path / "input.jpg",
            content_type="image/jpeg",
        )

    record = await session.scalar(select(Generation))
    assert error.value.code == "provider_unavailable"
    assert user.credits == 10
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
    user.credits = 10
    provider = FailingProvider(BackgroundRemovalTimeoutError())

    with pytest.raises(BackgroundRemovalFailedError) as error:
        await BackgroundRemovalService(session, provider).process(
            user_id=user.id,
            image_path=tmp_path / "input.jpg",
            content_type="image/jpeg",
        )

    record = await session.scalar(select(Generation))
    assert error.value.code == "provider_timeout"
    assert user.credits == 10
    assert record is not None
    assert record.error_code == "provider_timeout"


async def test_credit_is_charged_only_for_the_successful_attempt(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    user = await create_user(session)
    user.credits = 10
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
    assert user.credits == 5
    assert result.remaining_credits == 5
    assert [record.credits_spent for record in records] == [0, 5]


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
    user.credits = 10
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


async def test_rembg_provider_processes_locally_and_reuses_session(tmp_path: Path) -> None:
    input_path = tmp_path / "input.jpg"
    input_path.write_bytes(make_image_bytes("JPEG"))
    session = object()
    session_calls = 0
    processing_calls = 0

    def create_session(model_name: str) -> object:
        nonlocal session_calls
        session_calls += 1
        assert model_name == "u2netp"
        return session

    def remove_background(
        image_bytes: bytes,
        *,
        session: object,
        force_return_bytes: bool,
    ) -> bytes:
        nonlocal processing_calls
        processing_calls += 1
        assert image_bytes.startswith(b"\xff\xd8\xff")
        assert session is not None
        assert force_return_bytes is True
        return PNG_RESULT

    provider = RembgBackgroundRemovalProvider(
        session_factory=create_session,
        remove_function=remove_background,
    )

    first = await provider.remove_background(input_path, "image/jpeg")
    second = await provider.remove_background(input_path, "image/jpeg")

    assert first == PNG_RESULT
    assert second == PNG_RESULT
    assert session_calls == 1
    assert processing_calls == 2


async def test_rembg_provider_rejects_unsupported_format(tmp_path: Path) -> None:
    input_path = tmp_path / "input.gif"
    input_path.write_bytes(make_image_bytes("GIF"))
    provider = RembgBackgroundRemovalProvider(session_factory=lambda _: object())

    with pytest.raises(BackgroundRemovalProviderError) as error:
        await provider.remove_background(input_path, "image/gif")

    assert error.value.code == "unsupported_format"


async def test_rembg_provider_rejects_corrupted_image(tmp_path: Path) -> None:
    input_path = tmp_path / "broken.jpg"
    input_path.write_bytes(b"\xff\xd8\xffcorrupted")
    provider = RembgBackgroundRemovalProvider(session_factory=lambda _: object())

    with pytest.raises(BackgroundRemovalProviderError) as error:
        await provider.remove_background(input_path, "image/jpeg")

    assert error.value.code == "invalid_image"


async def test_rembg_provider_rejects_excessive_pixel_count(tmp_path: Path) -> None:
    input_path = tmp_path / "large.png"
    input_path.write_bytes(make_image_bytes("PNG", size=(11, 10)))
    provider = RembgBackgroundRemovalProvider(
        max_pixels=100,
        session_factory=lambda _: object(),
    )

    with pytest.raises(BackgroundRemovalProviderError) as error:
        await provider.remove_background(input_path, "image/png")

    assert error.value.code == "image_too_large"


async def test_rembg_provider_maps_processing_error(tmp_path: Path) -> None:
    input_path = tmp_path / "input.jpg"
    input_path.write_bytes(make_image_bytes("JPEG"))

    def fail_processing(*_: object, **__: object) -> bytes:
        raise RuntimeError("inference failed")

    provider = RembgBackgroundRemovalProvider(
        session_factory=lambda _: object(),
        remove_function=fail_processing,
    )

    with pytest.raises(BackgroundRemovalProviderError) as error:
        await provider.remove_background(input_path, "image/jpeg")

    assert error.value.code == "processing_error"


async def test_rembg_provider_enforces_processing_timeout(tmp_path: Path) -> None:
    input_path = tmp_path / "input.jpg"
    input_path.write_bytes(make_image_bytes("JPEG"))

    def slow_processing(*_: object, **__: object) -> bytes:
        sleep(0.05)
        return PNG_RESULT

    provider = RembgBackgroundRemovalProvider(
        timeout_seconds=0.001,
        session_factory=lambda _: object(),
        remove_function=slow_processing,
    )

    with pytest.raises(BackgroundRemovalTimeoutError):
        await provider.remove_background(input_path, "image/jpeg")
