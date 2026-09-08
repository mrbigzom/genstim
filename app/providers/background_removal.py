import asyncio
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Protocol

from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError
from pillow_heif import register_heif_opener
from rembg import new_session, remove

register_heif_opener()

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SUPPORTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
SUPPORTED_PIL_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF"}
REMBG_MODEL_NAME = "u2netp"

RemoveFunction = Callable[..., bytes]
SessionFactory = Callable[[str], object]


class BackgroundRemovalProvider(Protocol):
    async def remove_background(self, image_path: Path, content_type: str) -> bytes: ...


class BackgroundRemovalProviderError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class BackgroundRemovalTimeoutError(BackgroundRemovalProviderError):
    def __init__(self) -> None:
        super().__init__("provider_timeout")


class _InvalidImageError(Exception):
    pass


class _ImageDimensionsError(Exception):
    pass


class RembgBackgroundRemovalProvider:
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        max_pixels: int = 25_000_000,
        max_concurrency: int = 1,
        model_name: str = REMBG_MODEL_NAME,
        remove_function: RemoveFunction = remove,
        session_factory: SessionFactory = new_session,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_pixels = max_pixels
        self.model_name = model_name
        self.remove_function = remove_function
        self.session_factory = session_factory
        self._session: object | None = None
        self._session_lock = asyncio.Lock()
        self._inference_slots = asyncio.Semaphore(max_concurrency)

    async def remove_background(self, image_path: Path, content_type: str) -> bytes:
        if content_type not in SUPPORTED_CONTENT_TYPES:
            raise BackgroundRemovalProviderError("unsupported_format")

        try:
            image_bytes = await asyncio.to_thread(
                _read_and_validate_image,
                image_path,
                self.max_pixels,
            )
        except _ImageDimensionsError as exc:
            raise BackgroundRemovalProviderError("image_too_large") from exc
        except _InvalidImageError as exc:
            raise BackgroundRemovalProviderError("invalid_image") from exc

        session = await self._get_session()
        try:
            async with self._inference_slots:
                output = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.remove_function,
                        image_bytes,
                        session=session,
                        force_return_bytes=True,
                    ),
                    timeout=self.timeout_seconds,
                )
        except TimeoutError as exc:
            raise BackgroundRemovalTimeoutError() from exc
        except Exception as exc:
            raise BackgroundRemovalProviderError("processing_error") from exc

        if not isinstance(output, bytes) or not _is_transparent_png(output):
            raise BackgroundRemovalProviderError("processing_error")
        return output

    async def _get_session(self) -> object:
        if self._session is not None:
            return self._session

        async with self._session_lock:
            if self._session is not None:
                return self._session
            try:
                session = await asyncio.wait_for(
                    asyncio.to_thread(self.session_factory, self.model_name),
                    timeout=self.timeout_seconds,
                )
            except TimeoutError as exc:
                raise BackgroundRemovalTimeoutError() from exc
            except Exception as exc:
                raise BackgroundRemovalProviderError("processing_error") from exc
            if session is None:
                raise BackgroundRemovalProviderError("processing_error")
            self._session = session
        return self._session


def _read_and_validate_image(image_path: Path, max_pixels: int) -> bytes:
    image_bytes = image_path.read_bytes()
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.format not in SUPPORTED_PIL_FORMATS:
                raise _InvalidImageError
            if image.width * image.height > max_pixels:
                raise _ImageDimensionsError
            image.verify()
    except DecompressionBombError as exc:
        raise _ImageDimensionsError from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise _InvalidImageError from exc
    return image_bytes


def _is_transparent_png(image_bytes: bytes) -> bool:
    if not image_bytes.startswith(PNG_SIGNATURE):
        return False
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            has_alpha_channel = image.format == "PNG" and "A" in image.getbands()
            image.verify()
            return has_alpha_channel
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return False
