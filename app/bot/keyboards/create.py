from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

FEATURES = {
    "avatar": {"en": "🎨 AI Avatars", "ru": "🎨 AI-аватары"},
    "stickers": {"en": "😎 Stickers", "ru": "😎 Стикеры"},
    "memes": {"en": "😂 Memes", "ru": "😂 Мемы"},
    "pet": {"en": "🐾 Pet AI", "ru": "🐾 Питомцы AI"},
    "family": {"en": "❤️ Couple & Family", "ru": "❤️ Пара и семья"},
    "baby": {"en": "👶 Baby", "ru": "👶 Ребёнок"},
    "anime": {"en": "🎌 Anime", "ru": "🎌 Аниме"},
    "game": {"en": "🎮 Game Character", "ru": "🎮 Игровой персонаж"},
    "pixel": {"en": "🧱 Pixel Avatar", "ru": "🧱 Пиксельный аватар"},
    "passport": {"en": "📸 Passport Photo", "ru": "📸 Фото на документы"},
    "enhance": {"en": "✨ Photo Enhance", "ru": "✨ Улучшить фото"},
    "background": {"en": "✂️ Background Removal", "ru": "✂️ Удалить фон"},
    "roast": {"en": "🔥 Roast Me", "ru": "🔥 Прожарь меня"},
    "qr": {"en": "🔳 QR Designer", "ru": "🔳 QR-дизайнер"},
}


def create_menu(language: str) -> InlineKeyboardMarkup:
    selected = language if language in {"en", "ru"} else "en"
    rows: list[list[InlineKeyboardButton]] = []
    items = list(FEATURES.items())
    for index in range(0, len(items), 2):
        rows.append(
            [
                InlineKeyboardButton(
                    text=labels[selected],
                    callback_data=f"feature:{feature}",
                )
                for feature, labels in items[index : index + 2]
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
