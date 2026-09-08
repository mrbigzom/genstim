"""Run local providers on synthetic data without storing user content."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np
from PIL import Image, ImageDraw

from app.providers.background_removal import RembgBackgroundRemovalProvider
from app.providers.meme import PillowMemeProvider
from app.providers.passport_photo import LocalPassportPhotoProvider
from app.providers.pixel_avatar import PillowPixelAvatarProvider
from app.providers.qr_code import PillowQrCodeProvider
from app.providers.sticker import LocalStickerProvider


async def process(source: Path) -> dict[str, int]:
    background = RembgBackgroundRemovalProvider(model_name="u2netp")
    qr_payload = "https://example.com/genstim-smoke"
    qr = await PillowQrCodeProvider().generate(qr_payload)
    qr_matrix = cv2.imdecode(np.frombuffer(qr, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(qr_matrix)
    if decoded != qr_payload:
        raise RuntimeError("QR decode check failed")

    outputs = {
        "qr": qr,
        "meme": await PillowMemeProvider().generate("classic", "GenStim", "CPU smoke"),
        "pixel": await PillowPixelAvatarProvider().pixelate(source, "image/png", "medium"),
        "passport": await LocalPassportPhotoProvider(background).create(
            source, "image/png", "white"
        ),
        "sticker": await LocalStickerProvider(background).create(source, "image/png"),
    }
    return {name: len(content) for name, content in outputs.items()}


def create_synthetic_portrait(path: Path) -> None:
    image = Image.new("RGB", (480, 640), "#d9edf7")
    draw = ImageDraw.Draw(image)
    draw.ellipse((135, 65, 345, 275), fill="#e5a56c", outline="#4a2d20", width=8)
    draw.ellipse((190, 145, 210, 165), fill="#1f2937")
    draw.ellipse((270, 145, 290, 165), fill="#1f2937")
    draw.arc((190, 160, 290, 225), 10, 170, fill="#7f1d1d", width=6)
    draw.polygon(((80, 640), (125, 295), (355, 295), (400, 640)), fill="#1d4ed8")
    image.save(path, format="PNG")


def main() -> None:
    with TemporaryDirectory(prefix="genstim-smoke-") as directory:
        source = Path(directory) / "synthetic.png"
        create_synthetic_portrait(source)
        results = asyncio.run(process(source))
    for feature, byte_count in results.items():
        print(f"{feature}: ok ({byte_count} bytes)")


if __name__ == "__main__":
    main()
