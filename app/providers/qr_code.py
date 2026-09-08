from io import BytesIO
from typing import Protocol

import qrcode
from qrcode.constants import ERROR_CORRECT_M
from qrcode.exceptions import DataOverflowError

from app.providers.local_processing import LocalProcessingError, run_with_timeout

QR_MAX_CHARACTERS = 1024
QR_MAX_BYTES = 2048


class QrCodeProvider(Protocol):
    async def generate(self, payload: str) -> bytes: ...


class PillowQrCodeProvider:
    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def generate(self, payload: str) -> bytes:
        normalized = payload.strip()
        if not normalized:
            raise LocalProcessingError("invalid_input")
        if len(normalized) > QR_MAX_CHARACTERS or len(normalized.encode("utf-8")) > QR_MAX_BYTES:
            raise LocalProcessingError("input_too_long")
        return await run_with_timeout(
            _generate_qr,
            normalized,
            timeout_seconds=self.timeout_seconds,
        )


def _generate_qr(payload: str) -> bytes:
    code = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=12,
        border=4,
    )
    try:
        code.add_data(payload)
        code.make(fit=True)
    except DataOverflowError as exc:
        raise LocalProcessingError("input_too_long") from exc
    image = code.make_image(fill_color="black", back_color="white")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
