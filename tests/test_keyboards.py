from app.bot.keyboards.create import FEATURES, VISIBLE_FEATURES, create_menu
from app.bot.keyboards.main import MENU_BUTTONS, main_menu


def test_main_menu_contains_required_english_labels() -> None:
    keyboard = main_menu("en")
    labels = [button.text for row in keyboard.keyboard for button in row]

    assert labels == [
        "🎨 Create",
        "💎 Credits",
        "🖼 My Creations",
        "🎁 Invite Friends",
        "🌐 Language",
        "❓ Help",
    ]


def test_main_menu_contains_required_russian_labels() -> None:
    keyboard = main_menu("ru")
    labels = [button.text for row in keyboard.keyboard for button in row]

    assert labels == [
        "🎨 Создать",
        "💎 Кредиты",
        "🖼 Мои работы",
        "🎁 Пригласить друзей",
        "🌐 Язык",
        "❓ Помощь",
    ]


def test_hidden_ai_tools_labels_are_kept_for_future_use() -> None:
    assert MENU_BUTTONS["en"]["tools"] == "🛠 AI Tools"
    assert MENU_BUTTONS["ru"]["tools"] == "🛠 AI-инструменты"


def test_create_menu_exposes_only_working_cpu_tools() -> None:
    keyboard = create_menu("en")
    labels = [button.text for row in keyboard.inline_keyboard for button in row]

    assert len(FEATURES) == 14
    assert labels == [FEATURES[feature]["en"] for feature in VISIBLE_FEATURES]
    assert VISIBLE_FEATURES == (
        "stickers",
        "memes",
        "pixel",
        "passport",
        "background",
        "qr",
    )


def test_hidden_feature_definitions_are_kept_for_future_stages() -> None:
    assert {
        "avatar",
        "pet",
        "family",
        "baby",
        "game",
        "roast",
        "enhance",
        "anime",
    } <= FEATURES.keys()
