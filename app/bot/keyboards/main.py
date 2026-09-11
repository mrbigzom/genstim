from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MENU_BUTTONS = {
    "en": {
        "create": "🎨 Create",
        "tools": "🛠 AI Tools",
        "credits": "💎 Credits",
        "history": "🖼 My Creations",
        "invite": "🎁 Invite Friends",
        "language": "🌐 Language",
        "help": "❓ Help",
    },
    "ru": {
        "create": "🎨 Создать",
        "tools": "🛠 AI-инструменты",
        "credits": "💎 Кредиты",
        "history": "🖼 Мои работы",
        "invite": "🎁 Пригласить друзей",
        "language": "🌐 Язык",
        "help": "❓ Помощь",
    },
}


def main_menu(language: str) -> ReplyKeyboardMarkup:
    labels = MENU_BUTTONS[language if language in MENU_BUTTONS else "en"]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=labels["create"])],
            [KeyboardButton(text=labels["credits"])],
            [KeyboardButton(text=labels["language"])],
            [KeyboardButton(text=labels["help"])],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def button_texts(action: str) -> set[str]:
    return {language[action] for language in MENU_BUTTONS.values()}
