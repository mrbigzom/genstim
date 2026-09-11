from unittest.mock import AsyncMock

from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers import router as handlers_router
from app.bot.handlers.common import create_command
from app.bot.keyboards.create import FEATURES, VISIBLE_FEATURES, create_menu
from app.bot.keyboards.main import MENU_BUTTONS, main_menu


def test_main_menu_contains_required_english_labels() -> None:
    keyboard = main_menu("en")
    labels = [button.text for row in keyboard.keyboard for button in row]

    assert labels == [
        "🎨 Create",
        "💎 Credits",
        "🌐 Language",
        "❓ Help",
    ]


def test_main_menu_contains_required_russian_labels() -> None:
    keyboard = main_menu("ru")
    labels = [button.text for row in keyboard.keyboard for button in row]

    assert labels == [
        "🎨 Создать",
        "💎 Кредиты",
        "🌐 Язык",
        "❓ Помощь",
    ]


def test_hidden_main_menu_labels_are_kept_for_future_use() -> None:
    assert MENU_BUTTONS["en"]["tools"] == "🛠 AI Tools"
    assert MENU_BUTTONS["ru"]["tools"] == "🛠 AI-инструменты"
    assert MENU_BUTTONS["en"]["history"] == "🖼 My Creations"
    assert MENU_BUTTONS["ru"]["history"] == "🖼 Мои работы"
    assert MENU_BUTTONS["en"]["invite"] == "🎁 Invite Friends"
    assert MENU_BUTTONS["ru"]["invite"] == "🎁 Пригласить друзей"


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


async def test_create_command_clears_active_flow_and_shows_working_tools(
    session: AsyncSession,
) -> None:
    class Message:
        from_user = TelegramUser(
            id=8101,
            is_bot=False,
            first_name="Creator",
            language_code="ru",
        )
        answer = AsyncMock()

    class State:
        clear = AsyncMock()

    message = Message()
    state = State()
    await create_command(
        message,  # type: ignore[arg-type]
        session,
        state,  # type: ignore[arg-type]
    )

    state.clear.assert_awaited_once()
    markup = message.answer.await_args.kwargs["reply_markup"]
    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert labels == [FEATURES[feature]["ru"] for feature in VISIBLE_FEATURES]


def test_create_navigation_has_priority_over_feature_flows() -> None:
    router_names = [item.name for item in handlers_router.sub_routers]
    navigation_index = router_names.index("navigation")
    assert navigation_index < router_names.index("qr_code")
    assert navigation_index < router_names.index("meme")
    assert navigation_index < router_names.index("local_images")


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
