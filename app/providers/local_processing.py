import asyncio
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from PIL.Image import DecompressionBombError
from pillow_heif import register_heif_opener

register_heif_opener()

SUPPORTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
SUPPORTED_PIL_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF"}

class LocalProcessingError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def run_with_timeout[T](
    function: Callable[..., T],
    *args: object,
    timeout_seconds: float,
) -> T:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(function, *args),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        raise LocalProcessingError("provider_timeout") from exc
    except LocalProcessingError:
        raise
    except Exception as exc:
        raise LocalProcessingError("processing_error") from exc


def load_image(image_path: Path, content_type: str, max_pixels: int) -> Image.Image:
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise LocalProcessingError("unsupported_format")

    try:
        with Image.open(image_path) as source:
            if source.format not in SUPPORTED_PIL_FORMATS:
                raise LocalProcessingError("unsupported_format")
            if source.width * source.height > max_pixels:
                raise LocalProcessingError("image_too_large")
            source.load()
            return ImageOps.exif_transpose(source).copy()
    except LocalProcessingError:
        raise
    except DecompressionBombError as exc:
        raise LocalProcessingError("image_too_large") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise LocalProcessingError("invalid_image") from exc


def png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
