from collections.abc import Callable
from io import BytesIO
from threading import Lock
from typing import Any

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
SUPPORTED_IMAGE_FORMATS = frozenset({"JPEG", "PNG"})
BACKGROUND_MODEL = "u2netp"


class BackgroundRemovalError(Exception):
    """Base error for input validation and local background removal."""


class InvalidImageError(BackgroundRemovalError):
    """Raised when input is empty, corrupt, or uses an unsupported format."""


class ImageTooLargeError(BackgroundRemovalError):
    """Raised when input exceeds the byte or pixel limit."""


class BackgroundProcessingError(BackgroundRemovalError):
    """Raised when the local model cannot produce a valid transparent PNG."""


_session: Any | None = None
_session_lock = Lock()


def get_background_session() -> Any:
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                from rembg import new_session

                _session = new_session(BACKGROUND_MODEL)
    return _session


def remove_with_rembg(data: bytes, **options: object) -> object:
    from rembg import remove

    return remove(data, **options)


def validate_source_image(data: bytes) -> None:
    if not data:
        raise InvalidImageError("Image data is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageTooLargeError("Image file is too large")

    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in SUPPORTED_IMAGE_FORMATS:
                raise InvalidImageError("Only JPEG and PNG images are supported")
            width, height = image.size
            if width < 1 or height < 1:
                raise InvalidImageError("Image dimensions are invalid")
            if width * height > MAX_IMAGE_PIXELS:
                raise ImageTooLargeError("Image dimensions are too large")
            image.verify()
    except ImageTooLargeError:
        raise
    except Image.DecompressionBombError as error:
        raise ImageTooLargeError("Image dimensions are too large") from error
    except (OSError, SyntaxError, UnidentifiedImageError) as error:
        raise InvalidImageError("Image data is corrupt or unsupported") from error


class BackgroundRemovalService:
    def __init__(
        self,
        *,
        remover: Callable[..., object] = remove_with_rembg,
        session_provider: Callable[[], object] = get_background_session,
    ) -> None:
        self._remover = remover
        self._session_provider = session_provider

    def remove_background(self, data: bytes) -> bytes:
        validate_source_image(data)
        try:
            result = self._remover(
                data,
                session=self._session_provider(),
                force_return_bytes=True,
            )
        except Exception as error:
            raise BackgroundProcessingError("Local background removal failed") from error

        if not isinstance(result, bytes) or not result:
            raise BackgroundProcessingError("Background remover returned no image")

        try:
            with Image.open(BytesIO(result)) as image:
                image.load()
                if image.format != "PNG" or "A" not in image.getbands():
                    raise BackgroundProcessingError(
                        "Background remover did not return a transparent PNG"
                    )
        except BackgroundProcessingError:
            raise
        except (OSError, SyntaxError, UnidentifiedImageError) as error:
            raise BackgroundProcessingError(
                "Background remover returned a corrupt image"
            ) from error
        return result
