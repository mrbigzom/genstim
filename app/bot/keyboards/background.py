from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def background_navigation(language: str) -> InlineKeyboardMarkup:
    selected = language if language in {"en", "ru"} else "en"
    labels = {
        "en": {"back": "Back to Create", "cancel": "Cancel"},
        "ru": {"back": "Назад в Create", "cancel": "Отмена"},
    }[selected]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=labels["back"], callback_data="background:back"),
                InlineKeyboardButton(text=labels["cancel"], callback_data="background:cancel"),
            ]
        ]
    )
