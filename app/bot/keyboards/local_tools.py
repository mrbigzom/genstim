from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def meme_templates(language: str) -> InlineKeyboardMarkup:
    labels = {
        "en": {"classic": "🙂 Classic", "breaking": "🚨 Breaking", "choice": "🅰️ A or B"},
        "ru": {"classic": "🙂 Классика", "breaking": "🚨 Срочно", "choice": "🅰️ А или Б"},
    }
    selected = language if language in labels else "en"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"meme:template:{template}",
                )
            ]
            for template, label in labels[selected].items()
        ]
    )


def pixel_levels(language: str) -> InlineKeyboardMarkup:
    labels = {
        "en": {"coarse": "Large pixels", "medium": "Medium pixels", "fine": "Fine pixels"},
        "ru": {"coarse": "Крупные пиксели", "medium": "Средние пиксели", "fine": "Мелкие пиксели"},
    }
    selected = language if language in labels else "en"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"pixel:level:{level}",
                )
            ]
            for level, label in labels[selected].items()
        ]
    )


def passport_backgrounds(language: str) -> InlineKeyboardMarkup:
    labels = {
        "en": {"white": "White", "light_gray": "Light gray", "light_blue": "Light blue"},
        "ru": {"white": "Белый", "light_gray": "Светло-серый", "light_blue": "Светло-голубой"},
    }
    selected = language if language in labels else "en"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"passport:background:{background}",
                )
            ]
            for background, label in labels[selected].items()
        ]
    )
