from app.bot.keyboards.qr import qr_size_menu, qr_style_menu


def test_qr_size_menu_has_supported_sizes_and_cancel() -> None:
    keyboard = qr_size_menu("en")
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert callbacks == ["qr:size:512", "qr:size:768", "qr:size:1024", "qr:cancel"]


def test_qr_style_menu_is_localized() -> None:
    keyboard = qr_style_menu("ru")
    labels = [button.text for row in keyboard.inline_keyboard for button in row]

    assert labels == ["Обычный", "Светлый фон", "Рамка", "Отмена"]
