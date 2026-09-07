from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def language_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="English 🇬🇧", callback_data="language:en"),
                InlineKeyboardButton(text="Русский 🇷🇺", callback_data="language:ru"),
            ]
        ]
    )
