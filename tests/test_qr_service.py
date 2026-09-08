from io import BytesIO

import pytest
import zxingcpp
from PIL import Image

from app.services.qr import MAX_QR_CONTENT_BYTES, QRCodeInputError, generate_qr_png


def decode_qr(image_bytes: bytes) -> str:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    result = zxingcpp.read_barcode(image)
    assert result is not None
    return result.text


@pytest.mark.parametrize(
    "content",
    ["Hello, GenStim!", "Привет, GenStim!", "https://example.com/path?q=qr"],
)
def test_qr_round_trip_for_text_and_url(content: str) -> None:
    assert decode_qr(generate_qr_png(content, size=512)) == content


@pytest.mark.parametrize("size", [512, 768, 1024])
@pytest.mark.parametrize("style", ["plain", "background", "frame"])
def test_every_qr_size_and_style_is_decodable(size: int, style: str) -> None:
    image_bytes = generate_qr_png("https://genstim.example/verify", size=size, style=style)
    image = Image.open(BytesIO(image_bytes))

    assert image.format == "PNG"
    assert image.size == (size, size)
    assert decode_qr(image_bytes) == "https://genstim.example/verify"


@pytest.mark.parametrize("content", ["", "   ", "\n\t"])
def test_qr_rejects_empty_content(content: str) -> None:
    with pytest.raises(QRCodeInputError, match="empty"):
        generate_qr_png(content, size=512)


def test_qr_rejects_content_over_byte_limit() -> None:
    content = "x" * (MAX_QR_CONTENT_BYTES + 1)
    with pytest.raises(QRCodeInputError, match="too long"):
        generate_qr_png(content, size=512)


@pytest.mark.parametrize(
    ("size", "style", "message"),
    [(500, "plain", "size"), (512, "neon", "style")],
)
def test_qr_rejects_unsupported_options(size: int, style: str, message: str) -> None:
    with pytest.raises(QRCodeInputError, match=message):
        generate_qr_png("valid", size=size, style=style)
