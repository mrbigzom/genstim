from app.bot.keyboards.create import FEATURES, create_menu
from app.bot.keyboards.main import MENU_BUTTONS, main_menu


def test_main_menu_contains_required_english_labels() -> None:
    keyboard = main_menu("en")
    labels = [button.text for row in keyboard.keyboard for button in row]

    assert labels == [
        "🎨 Create",
        "🛠 AI Tools",
        "💎 Credits",
        "🖼 My Creations",
        "🎁 Invite Friends",
        "🌐 Language",
        "❓ Help",
    ]


def test_main_menu_contains_required_russian_labels() -> None:
    assert set(MENU_BUTTONS["ru"].values()) == {
        "🎨 Создать",
        "🛠 AI-инструменты",
        "💎 Кредиты",
        "🖼 Мои работы",
        "🎁 Пригласить друзей",
        "🌐 Язык",
        "❓ Помощь",
    }


def test_create_menu_exposes_all_placeholders() -> None:
    keyboard = create_menu("en")
    labels = [button.text for row in keyboard.inline_keyboard for button in row]

    assert len(FEATURES) == 14
    assert labels == [feature["en"] for feature in FEATURES.values()]
