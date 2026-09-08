from io import BytesIO
from pathlib import Path
from time import sleep

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation import Generation
from app.providers.local_processing import LocalProcessingError, run_with_timeout
from app.providers.meme import PillowMemeProvider
from app.providers.passport_photo import PASSPORT_SIZE, LocalPassportPhotoProvider
from app.providers.pixel_avatar import PillowPixelAvatarProvider
from app.providers.qr_code import QR_MAX_CHARACTERS, PillowQrCodeProvider
from app.providers.sticker import STICKER_MAX_BYTES, STICKER_SIZE, LocalStickerProvider
from app.services.background_removal import InsufficientCreditsError
from app.services.generation import GenerationService
from app.services.local_generation import LocalGenerationFailedError, LocalGenerationService
from app.services.user import UserService


def image_bytes(
    image_format: str = "PNG",
    *,
    size: tuple[int, int] = (320, 400),
    transparent: bool = False,
) -> bytes:
    mode = "RGBA" if transparent else "RGB"
    background = (0, 0, 0, 0) if transparent else "white"
    image = Image.new(mode, size, background)
    draw = ImageDraw.Draw(image)
    draw.ellipse((80, 35, 240, 195), fill=(230, 170, 120, 255) if transparent else "orange")
    draw.rectangle((60, 180, 260, 400), fill=(30, 90, 180, 255) if transparent else "blue")
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def write_image(path: Path, image_format: str = "PNG") -> Path:
    path.write_bytes(image_bytes(image_format))
    return path


class FakeBackgroundProvider:
    async def remove_background(self, image_path: Path, content_type: str) -> bytes:
        assert content_type == "image/png"
        return image_bytes(transparent=True)


async def create_user(session: AsyncSession, telegram_id: int = 5001):
    user, _ = await UserService(session).get_or_create(
        telegram_id=telegram_id,
        username="local-tools",
        first_name="Local",
        telegram_language="en",
    )
    return user


async def test_qr_code_is_decodable() -> None:
    payload = "https://example.com/genstim?source=test"
    result = await PillowQrCodeProvider().generate(payload)
    matrix = cv2.imdecode(np.frombuffer(result, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(matrix)
    assert decoded == payload


async def test_qr_code_rejects_long_payload() -> None:
    with pytest.raises(LocalProcessingError) as error:
        await PillowQrCodeProvider().generate("x" * (QR_MAX_CHARACTERS + 1))
    assert error.value.code == "input_too_long"


async def test_meme_generator_outputs_png_with_expected_size() -> None:
    result = await PillowMemeProvider().generate("classic", "TOP TEXT", "НИЖНИЙ ТЕКСТ")
    with Image.open(BytesIO(result)) as image:
        assert image.format == "PNG"
        assert image.size == (1024, 1024)


async def test_pixel_avatar_has_limited_palette_and_nearest_neighbor_blocks(
    tmp_path: Path,
) -> None:
    source = write_image(tmp_path / "source.png")
    result = await PillowPixelAvatarProvider().pixelate(source, "image/png", "coarse")
    with Image.open(BytesIO(result)) as image:
        assert image.size == (512, 512)
        assert len(image.convert("RGB").getcolors(maxcolors=257) or []) <= 48
        assert image.getpixel((0, 0)) == image.getpixel((10, 10))


async def test_passport_photo_uses_selected_solid_background(tmp_path: Path) -> None:
    source = write_image(tmp_path / "source.png")
    provider = LocalPassportPhotoProvider(FakeBackgroundProvider())
    result = await provider.create(source, "image/png", "light_blue")
    with Image.open(BytesIO(result)) as image:
        assert image.format == "PNG"
        assert image.size == PASSPORT_SIZE
        assert image.getpixel((0, 0)) == (215, 235, 250)
        assert image.info["dpi"][0] == pytest.approx(300, abs=1)


async def test_sticker_matches_telegram_static_file_limits(tmp_path: Path) -> None:
    source = write_image(tmp_path / "source.png")
    result = await LocalStickerProvider(FakeBackgroundProvider()).create(source, "image/png")
    assert len(result) <= STICKER_MAX_BYTES
    with Image.open(BytesIO(result)) as image:
        assert image.format == "WEBP"
        assert image.size == (STICKER_SIZE, STICKER_SIZE)
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 0


async def test_local_generation_charges_only_on_success_and_appears_in_history(
    session: AsyncSession,
) -> None:
    user = await create_user(session)

    async def fail() -> bytes:
        raise LocalProcessingError("processing_error")

    with pytest.raises(LocalGenerationFailedError):
        await LocalGenerationService(session).process(
            user_id=user.id,
            feature="qr_designer",
            operation=fail,
        )
    assert user.credits == 3

    result = await LocalGenerationService(session).process(
        user_id=user.id,
        feature="qr_designer",
        operation=lambda: PillowQrCodeProvider().generate("success"),
    )
    records = list(await session.scalars(select(Generation).order_by(Generation.id)))
    history = await GenerationService(session).completed_history(user.id)
    assert result.remaining_credits == 2
    assert [record.status for record in records] == ["failed", "completed"]
    assert [record.credits_spent for record in records] == [0, 1]
    assert [record.id for record in history] == [result.generation.id]


async def test_local_generation_with_no_credits_does_not_run_operation(
    session: AsyncSession,
) -> None:
    user = await create_user(session, telegram_id=5002)
    user.credits = 0
    called = False

    async def operation() -> bytes:
        nonlocal called
        called = True
        return b"unused"

    with pytest.raises(InsufficientCreditsError):
        await LocalGenerationService(session).process(
            user_id=user.id,
            feature="meme_generator",
            operation=operation,
        )
    assert called is False
    assert list(await session.scalars(select(Generation))) == []


async def test_local_processing_timeout_has_specific_error() -> None:
    def slow_operation() -> bytes:
        sleep(0.05)
        return b"late"

    with pytest.raises(LocalProcessingError) as error:
        await run_with_timeout(slow_operation, timeout_seconds=0.001)
    assert error.value.code == "provider_timeout"


async def test_corrupted_image_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "broken.png"
    source.write_bytes(b"not-an-image")
    with pytest.raises(LocalProcessingError) as error:
        await PillowPixelAvatarProvider().pixelate(source, "image/png", "medium")
    assert error.value.code == "invalid_image"
