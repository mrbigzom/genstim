from io import BytesIO
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
from PIL import Image

from app.providers.background_removal import (
    BackgroundRemovalProvider,
    BackgroundRemovalProviderError,
)
from app.providers.local_processing import (
    LocalProcessingError,
    load_image,
    run_with_timeout,
)

PASSPORT_BACKGROUNDS = {
    "white": (255, 255, 255, 255),
    "light_gray": (235, 238, 241, 255),
    "light_blue": (215, 235, 250, 255),
}
PASSPORT_SIZE = (413, 531)


class PassportPhotoProvider(Protocol):
    async def create(self, image_path: Path, content_type: str, background: str) -> bytes: ...


class LocalPassportPhotoProvider:
    def __init__(
        self,
        background_removal_provider: BackgroundRemovalProvider,
        *,
        timeout_seconds: float = 15.0,
        max_pixels: int = 25_000_000,
    ) -> None:
        self.background_removal_provider = background_removal_provider
        self.timeout_seconds = timeout_seconds
        self.max_pixels = max_pixels

    async def create(self, image_path: Path, content_type: str, background: str) -> bytes:
        if background not in PASSPORT_BACKGROUNDS:
            raise LocalProcessingError("invalid_input")
        try:
            cutout = await self.background_removal_provider.remove_background(
                image_path, content_type
            )
        except BackgroundRemovalProviderError as exc:
            raise LocalProcessingError(exc.code) from exc
        return await run_with_timeout(
            _compose_passport,
            image_path,
            content_type,
            cutout,
            background,
            self.max_pixels,
            timeout_seconds=self.timeout_seconds,
        )


def _compose_passport(
    image_path: Path,
    content_type: str,
    cutout: bytes,
    background: str,
    max_pixels: int,
) -> bytes:
    source = load_image(image_path, content_type, max_pixels).convert("RGB")
    try:
        subject = Image.open(BytesIO(cutout)).convert("RGBA")
        subject.load()
    except Exception as exc:
        raise LocalProcessingError("processing_error") from exc
    if subject.size != source.size:
        raise LocalProcessingError("processing_error")

    face = _detect_largest_face(source)
    canvas = Image.new("RGBA", PASSPORT_SIZE, PASSPORT_BACKGROUNDS[background])
    if face is not None:
        x, y, width, height = face
        scale = (PASSPORT_SIZE[1] * 0.42) / height
        destination_x = PASSPORT_SIZE[0] / 2 - (x + width / 2) * scale
        destination_y = PASSPORT_SIZE[1] * 0.39 - (y + height / 2) * scale
        positioned = subject.transform(
            PASSPORT_SIZE,
            Image.Transform.AFFINE,
            (
                1 / scale,
                0,
                -destination_x / scale,
                0,
                1 / scale,
                -destination_y / scale,
            ),
            Image.Resampling.BICUBIC,
        )
        canvas.paste(positioned, (0, 0), positioned)
    else:
        alpha_box = subject.getchannel("A").getbbox()
        if alpha_box is None:
            raise LocalProcessingError("processing_error")
        cropped = subject.crop(alpha_box)
        cropped.thumbnail(
            (round(PASSPORT_SIZE[0] * 0.94), PASSPORT_SIZE[1]),
            Image.Resampling.LANCZOS,
        )
        destination_x = (PASSPORT_SIZE[0] - cropped.width) // 2
        destination_y = PASSPORT_SIZE[1] - cropped.height
        canvas.paste(cropped, (destination_x, destination_y), cropped)

    output = BytesIO()
    canvas.convert("RGB").save(output, format="PNG", optimize=True, dpi=(300, 300))
    return output.getvalue()


def _detect_largest_face(image: Image.Image) -> tuple[int, int, int, int] | None:
    grayscale = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
    detector = cv2.CascadeClassifier(
        str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
    )
    if detector.empty():
        return None
    faces = detector.detectMultiScale(
        grayscale,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
    )
    if len(faces) == 0:
        return None
    x, y, width, height = max(faces, key=lambda item: int(item[2]) * int(item[3]))
    return int(x), int(y), int(width), int(height)
