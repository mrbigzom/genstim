from io import BytesIO
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageFilter

from app.providers.background_removal import (
    BackgroundRemovalProvider,
    BackgroundRemovalProviderError,
)
from app.providers.local_processing import LocalProcessingError, run_with_timeout

STICKER_SIZE = 512
STICKER_MAX_BYTES = 512 * 1024


class StickerProvider(Protocol):
    async def create(self, image_path: Path, content_type: str) -> bytes: ...


class LocalStickerProvider:
    def __init__(
        self,
        background_removal_provider: BackgroundRemovalProvider,
        *,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.background_removal_provider = background_removal_provider
        self.timeout_seconds = timeout_seconds

    async def create(self, image_path: Path, content_type: str) -> bytes:
        try:
            cutout = await self.background_removal_provider.remove_background(
                image_path, content_type
            )
        except BackgroundRemovalProviderError as exc:
            raise LocalProcessingError(exc.code) from exc
        return await run_with_timeout(
            _create_sticker,
            cutout,
            timeout_seconds=self.timeout_seconds,
        )


def _create_sticker(cutout: bytes) -> bytes:
    try:
        subject = Image.open(BytesIO(cutout)).convert("RGBA")
        subject.load()
    except Exception as exc:
        raise LocalProcessingError("processing_error") from exc
    alpha_box = subject.getchannel("A").getbbox()
    if alpha_box is None:
        raise LocalProcessingError("processing_error")
    subject = subject.crop(alpha_box)
    subject.thumbnail((440, 440), Image.Resampling.LANCZOS)

    alpha = subject.getchannel("A")
    padding = 12
    padded_alpha = Image.new(
        "L",
        (subject.width + padding * 2, subject.height + padding * 2),
        0,
    )
    padded_alpha.paste(alpha, (padding, padding))
    outline_alpha = padded_alpha.filter(ImageFilter.MaxFilter(21))
    outline = Image.new("RGBA", padded_alpha.size, "white")
    outline.putalpha(outline_alpha)
    outline.paste(subject, (padding, padding), subject)

    canvas = Image.new("RGBA", (STICKER_SIZE, STICKER_SIZE), (0, 0, 0, 0))
    destination = ((STICKER_SIZE - outline.width) // 2, (STICKER_SIZE - outline.height) // 2)
    canvas.paste(outline, destination, outline)
    return _encode_webp(canvas)


def _encode_webp(image: Image.Image) -> bytes:
    for lossless, quality in ((True, 100), (False, 92), (False, 82), (False, 72)):
        output = BytesIO()
        image.save(output, format="WEBP", lossless=lossless, quality=quality, method=6)
        result = output.getvalue()
        if len(result) <= STICKER_MAX_BYTES:
            return result
    raise LocalProcessingError("output_too_large")
