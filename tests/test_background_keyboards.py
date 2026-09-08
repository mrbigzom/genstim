from app.bot.keyboards.background import background_navigation


def test_background_navigation_has_back_and_cancel() -> None:
    keyboard = background_navigation("ru")
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert callbacks == ["background:back", "background:cancel"]
