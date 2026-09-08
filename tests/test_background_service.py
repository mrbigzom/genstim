from io import BytesIO

import pytest
from PIL import Image

import app.services.background as background_module
from app.services.background import (
    MAX_IMAGE_BYTES,
    BackgroundProcessingError,
    BackgroundRemovalService,
    ImageTooLargeError,
    InvalidImageError,
)


def make_image(image_format: str, *, size: tuple[int, int] = (32, 32)) -> bytes:
    image = Image.new("RGB", size, "white")
    for x in range(size[0] // 4, size[0] * 3 // 4):
        for y in range(size[1] // 4, size[1] * 3 // 4):
            image.putpixel((x, y), (0, 0, 0))
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def local_test_remover(data: bytes, **_: object) -> bytes:
    source = Image.open(BytesIO(data)).convert("RGBA")
    alpha = Image.new("L", source.size)
    for x in range(source.width):
        for y in range(source.height):
            alpha.putpixel((x, y), 0 if sum(source.getpixel((x, y))[:3]) > 700 else 255)
    source.putalpha(alpha)
    output = BytesIO()
    source.save(output, format="PNG")
    return output.getvalue()


def service(remover: object = local_test_remover) -> BackgroundRemovalService:
    return BackgroundRemovalService(
        remover=remover,  # type: ignore[arg-type]
        session_provider=lambda: object(),
    )


@pytest.mark.parametrize("image_format", ["JPEG", "PNG"])
def test_background_removal_accepts_jpeg_and_png(image_format: str) -> None:
    result = service().remove_background(make_image(image_format))
    image = Image.open(BytesIO(result))

    assert image.format == "PNG"
    assert image.mode == "RGBA"


def test_background_removal_produces_transparent_background() -> None:
    result = service().remove_background(make_image("PNG"))
    image = Image.open(BytesIO(result)).convert("RGBA")

    assert image.getpixel((0, 0))[3] == 0
    assert image.getpixel((16, 16))[3] == 255


@pytest.mark.parametrize("data", [b"", b"not an image"])
def test_background_removal_rejects_invalid_input(data: bytes) -> None:
    with pytest.raises(InvalidImageError):
        service().remove_background(data)


def test_background_removal_rejects_unsupported_image_format() -> None:
    with pytest.raises(InvalidImageError, match="JPEG and PNG"):
        service().remove_background(make_image("GIF"))


def test_background_removal_rejects_oversized_file() -> None:
    with pytest.raises(ImageTooLargeError, match="file"):
        service().remove_background(b"x" * (MAX_IMAGE_BYTES + 1))


def test_background_removal_rejects_oversized_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(background_module, "MAX_IMAGE_PIXELS", 10)
    with pytest.raises(ImageTooLargeError, match="dimensions"):
        service().remove_background(make_image("PNG", size=(4, 4)))


def test_background_removal_wraps_model_errors() -> None:
    def failing_remover(data: bytes, **kwargs: object) -> bytes:
        raise RuntimeError("model failure")

    with pytest.raises(BackgroundProcessingError) as error:
        service(failing_remover).remove_background(make_image("JPEG"))

    assert isinstance(error.value.__cause__, RuntimeError)


def test_background_removal_rejects_output_without_alpha() -> None:
    def opaque_remover(data: bytes, **kwargs: object) -> bytes:
        return make_image("PNG")

    with pytest.raises(BackgroundProcessingError, match="transparent PNG"):
        service(opaque_remover).remove_background(make_image("PNG"))
