from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.qr import ALLOWED_QR_SIZES, ALLOWED_QR_STYLES

STYLE_LABELS = {
    "plain": {"en": "Plain", "ru": "Обычный"},
    "background": {"en": "Light background", "ru": "Светлый фон"},
    "frame": {"en": "Frame", "ru": "Рамка"},
}


def _language(language: str) -> str:
    return language if language in {"en", "ru"} else "en"


def qr_size_menu(language: str) -> InlineKeyboardMarkup:
    selected = _language(language)
    cancel = "Cancel" if selected == "en" else "Отмена"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{size}×{size}", callback_data=f"qr:size:{size}")
                for size in ALLOWED_QR_SIZES
            ],
            [InlineKeyboardButton(text=cancel, callback_data="qr:cancel")],
        ]
    )


def qr_style_menu(language: str) -> InlineKeyboardMarkup:
    selected = _language(language)
    cancel = "Cancel" if selected == "en" else "Отмена"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=STYLE_LABELS[style][selected],
                    callback_data=f"qr:style:{style}",
                )
                for style in ALLOWED_QR_STYLES
            ],
            [InlineKeyboardButton(text=cancel, callback_data="qr:cancel")],
        ]
    )
