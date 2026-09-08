from io import BytesIO
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont

from app.providers.local_processing import LocalProcessingError, run_with_timeout

MEME_MAX_TEXT_LENGTH = 160
MEME_TEMPLATES = ("classic", "breaking", "choice")


class MemeProvider(Protocol):
    async def generate(self, template: str, top_text: str, bottom_text: str) -> bytes: ...


class PillowMemeProvider:
    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def generate(self, template: str, top_text: str, bottom_text: str) -> bytes:
        if template not in MEME_TEMPLATES:
            raise LocalProcessingError("invalid_input")
        if max(len(top_text), len(bottom_text)) > MEME_MAX_TEXT_LENGTH:
            raise LocalProcessingError("input_too_long")
        if not top_text.strip() and not bottom_text.strip():
            raise LocalProcessingError("invalid_input")
        return await run_with_timeout(
            _generate_meme,
            template,
            top_text.strip(),
            bottom_text.strip(),
            timeout_seconds=self.timeout_seconds,
        )


def _generate_meme(template: str, top_text: str, bottom_text: str) -> bytes:
    image = _draw_template(template)
    draw = ImageDraw.Draw(image)
    _draw_fitted_text(draw, top_text, (36, 30, 988, 310), align="top")
    _draw_fitted_text(draw, bottom_text, (36, 714, 988, 994), align="bottom")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _draw_template(template: str) -> Image.Image:
    image = Image.new("RGB", (1024, 1024), "#18202a")
    draw = ImageDraw.Draw(image)
    if template == "classic":
        for y in range(1024):
            shade = 30 + y * 45 // 1024
            draw.line((0, y, 1024, y), fill=(shade, shade + 10, shade + 18))
        draw.ellipse((285, 295, 739, 749), fill="#f4b942", outline="#ffffff", width=12)
        draw.ellipse((405, 430, 465, 490), fill="#20242b")
        draw.ellipse((559, 430, 619, 490), fill="#20242b")
        draw.arc((395, 455, 629, 650), 15, 165, fill="#20242b", width=16)
    elif template == "breaking":
        image.paste("#273043", (0, 0, 1024, 1024))
        draw.rectangle((0, 310, 1024, 714), fill="#d7263d")
        draw.polygon(((0, 714), (1024, 310), (1024, 714)), fill="#f49d37")
        draw.rectangle((0, 472, 1024, 552), fill="#ffffff")
        draw.text((512, 512), "!", font=_font(150), fill="#111827", anchor="mm")
    else:
        image.paste("#eef2ff", (0, 0, 1024, 1024))
        draw.rectangle((0, 312, 506, 712), fill="#2563eb")
        draw.rectangle((518, 312, 1024, 712), fill="#ef4444")
        draw.text((253, 512), "A", font=_font(180), fill="white", anchor="mm")
        draw.text((771, 512), "B", font=_font(180), fill="white", anchor="mm")
    return image


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size=size)
    except OSError:
        return ImageFont.load_default(size=size)


def _draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    *,
    align: str,
) -> None:
    if not text:
        return
    left, top, right, bottom = box
    max_width = right - left
    max_height = bottom - top
    for font_size in range(78, 23, -2):
        font = _font(font_size)
        lines = _wrap_text(draw, text, font, max_width)
        candidate = "\n".join(lines)
        bounds = draw.multiline_textbbox(
            (0, 0), candidate, font=font, spacing=8, align="center", stroke_width=5
        )
        height = bounds[3] - bounds[1]
        if height <= max_height:
            y = top if align == "top" else bottom - height
            draw.multiline_text(
                ((left + right) // 2, y),
                candidate,
                font=font,
                fill="white",
                stroke_width=5,
                stroke_fill="black",
                anchor="ma",
                align="center",
                spacing=8,
            )
            return
    raise LocalProcessingError("input_too_long")


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if draw.textlength(candidate, font=font) <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines
