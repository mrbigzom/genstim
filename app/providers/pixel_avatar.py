from pathlib import Path
from typing import Protocol

from PIL import Image, ImageOps

from app.providers.local_processing import load_image, png_bytes, run_with_timeout

PIXEL_LEVELS = {"coarse": 24, "medium": 40, "fine": 64}


class PixelAvatarProvider(Protocol):
    async def pixelate(self, image_path: Path, content_type: str, level: str) -> bytes: ...


class PillowPixelAvatarProvider:
    def __init__(self, *, timeout_seconds: float = 15.0, max_pixels: int = 25_000_000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_pixels = max_pixels

    async def pixelate(self, image_path: Path, content_type: str, level: str) -> bytes:
        return await run_with_timeout(
            _pixelate,
            image_path,
            content_type,
            level,
            self.max_pixels,
            timeout_seconds=self.timeout_seconds,
        )


def _pixelate(image_path: Path, content_type: str, level: str, max_pixels: int) -> bytes:
    grid_size = PIXEL_LEVELS.get(level)
    if grid_size is None:
        from app.providers.local_processing import LocalProcessingError

        raise LocalProcessingError("invalid_input")
    source = load_image(image_path, content_type, max_pixels).convert("RGB")
    square = ImageOps.fit(source, (512, 512), method=Image.Resampling.LANCZOS)
    reduced = square.resize((grid_size, grid_size), Image.Resampling.BOX)
    reduced = reduced.quantize(colors=48, method=Image.Quantize.MEDIANCUT).convert("RGB")
    result = reduced.resize((512, 512), Image.Resampling.NEAREST)
    return png_bytes(result)
