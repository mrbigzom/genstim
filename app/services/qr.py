from io import BytesIO
from typing import Literal, cast

import qrcode
from PIL import Image, ImageDraw
from qrcode.constants import ERROR_CORRECT_H
from qrcode.exceptions import DataOverflowError

QRSize = Literal[512, 768, 1024]
QRStyle = Literal["plain", "background", "frame"]

ALLOWED_QR_SIZES: tuple[QRSize, ...] = (512, 768, 1024)
ALLOWED_QR_STYLES: tuple[QRStyle, ...] = ("plain", "background", "frame")
MAX_QR_CONTENT_BYTES = 1_000
QUIET_ZONE_MODULES = 4


class QRCodeInputError(ValueError):
    """Raised when QR Designer input cannot produce a supported QR image."""


def normalize_qr_content(content: str) -> str:
    normalized = content.strip()
    if not normalized:
        raise QRCodeInputError("QR content must not be empty")
    if len(normalized.encode("utf-8")) > MAX_QR_CONTENT_BYTES:
        raise QRCodeInputError("QR content is too long")
    return normalized


def _validate_options(size: int, style: str) -> tuple[QRSize, QRStyle]:
    if size not in ALLOWED_QR_SIZES:
        raise QRCodeInputError("Unsupported QR image size")
    if style not in ALLOWED_QR_STYLES:
        raise QRCodeInputError("Unsupported QR style")
    return cast(QRSize, size), cast(QRStyle, style)


def _canvas_for_style(size: QRSize, style: QRStyle) -> Image.Image:
    background = (235, 244, 255) if style == "background" else (255, 255, 255)
    return Image.new("RGB", (size, size), background)


def generate_qr_png(content: str, *, size: int, style: str = "plain") -> bytes:
    """Generate a square, lossless QR PNG with high error correction."""
    normalized = normalize_qr_content(content)
    selected_size, selected_style = _validate_options(size, style)

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=1,
        border=QUIET_ZONE_MODULES,
    )
    qr.add_data(normalized)
    try:
        qr.make(fit=True)
    except DataOverflowError as error:
        raise QRCodeInputError("QR content is too long") from error

    module_count = qr.modules_count + 2 * QUIET_ZONE_MODULES
    outer_padding = max(24, selected_size // 16)
    if selected_style == "frame":
        outer_padding += max(12, selected_size // 48)
    box_size = (selected_size - 2 * outer_padding) // module_count
    if box_size < 1:
        raise QRCodeInputError("QR content does not fit the selected image size")

    qr.box_size = box_size
    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    canvas = _canvas_for_style(selected_size, selected_style)
    offset = ((selected_size - qr_image.width) // 2, (selected_size - qr_image.height) // 2)
    canvas.paste(qr_image, offset)

    if selected_style == "frame":
        frame_gap = max(8, selected_size // 64)
        frame_width = max(4, selected_size // 128)
        left = offset[0] - frame_gap - frame_width
        top = offset[1] - frame_gap - frame_width
        right = offset[0] + qr_image.width + frame_gap + frame_width - 1
        bottom = offset[1] + qr_image.height + frame_gap + frame_width - 1
        ImageDraw.Draw(canvas).rectangle(
            (left, top, right, bottom),
            outline="black",
            width=frame_width,
        )

    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()
