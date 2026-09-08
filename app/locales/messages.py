from typing import Literal

Language = Literal["en", "ru"]

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": (
            "Welcome to <b>GenStim AI</b>! 🎨\n\n"
            "You have 3 free credits. Your Telegram language was detected as English. "
            "You can change it any time with /language."
        ),
        "welcome_back": "Welcome back to <b>GenStim AI</b>! Choose an option below.",
        "help": (
            "<b>GenStim AI commands</b>\n\n"
            "/create — choose a creation tool\n"
            "/tools — browse AI tools\n"
            "/credits — check your balance\n"
            "/history — view your creations\n"
            "/invite — invite friends\n"
            "/language — change language\n"
            "/support — contact support\n"
            "/paysupport — payment support\n"
            "/terms — Terms of Service\n"
            "/privacy — Privacy Policy"
        ),
        "create": "Choose what you would like to create:",
        "tools": "Choose an AI tool:",
        "feature_pending": "This feature is being prepared 🚀",
        "qr_enter_content": "Send the text or URL to encode in the QR code.",
        "qr_invalid_content": (
            "Send non-empty text or a URL up to 1,000 UTF-8 bytes. "
            "Images and other attachments are not supported."
        ),
        "qr_choose_size": "Choose the output image size:",
        "qr_choose_style": "Choose a QR style:",
        "qr_invalid_option": "That QR option is not supported. Please choose from the menu.",
        "qr_generation_failed": "The QR image could not be generated. Please try again.",
        "qr_ready": "Your QR code is ready. The PNG is sent without recompression.",
        "qr_cancelled": "QR Designer cancelled.",
        "credits": "Your balance: <b>{credits} credits</b> 💎",
        "history": "You do not have any creations yet. Start with /create 🎨",
        "invite": (
            "Invite friends with your personal link:\n{link}\n\n"
            "Referral rewards will be available in a future update."
        ),
        "language": "Choose your language:",
        "language_changed": "Language changed to English 🇬🇧",
        "support": (
            "Need help? Send your question to @GenStimAI_bot. "
            "Please do not send passwords, tokens, or payment card details."
        ),
        "paysupport": (
            "Payments are not enabled in this MVP yet. For a payment-related question, "
            "contact @GenStimAI_bot."
        ),
        "unknown": "I did not recognize that option. Please use the menu or /help.",
        "error": "Something went wrong. Please try again in a moment.",
    },
    "ru": {
        "welcome": (
            "Добро пожаловать в <b>GenStim AI</b>! 🎨\n\n"
            "Вам начислено 3 бесплатных кредита. Язык Telegram определён как русский. "
            "Изменить его можно в любой момент командой /language."
        ),
        "welcome_back": "С возвращением в <b>GenStim AI</b>! Выберите действие ниже.",
        "help": (
            "<b>Команды GenStim AI</b>\n\n"
            "/create — выбрать инструмент создания\n"
            "/tools — посмотреть AI-инструменты\n"
            "/credits — проверить баланс\n"
            "/history — открыть мои работы\n"
            "/invite — пригласить друзей\n"
            "/language — изменить язык\n"
            "/support — связаться с поддержкой\n"
            "/paysupport — поддержка по оплате\n"
            "/terms — условия использования\n"
            "/privacy — политика конфиденциальности"
        ),
        "create": "Выберите, что хотите создать:",
        "tools": "Выберите AI-инструмент:",
        "feature_pending": "Эта функция готовится 🚀",
        "qr_enter_content": "Отправьте текст или URL, который нужно записать в QR-код.",
        "qr_invalid_content": (
            "Отправьте непустой текст или URL размером до 1 000 байт UTF-8. "
            "Изображения и другие вложения не поддерживаются."
        ),
        "qr_choose_size": "Выберите размер готового изображения:",
        "qr_choose_style": "Выберите оформление QR-кода:",
        "qr_invalid_option": "Этот вариант не поддерживается. Выберите пункт из меню.",
        "qr_generation_failed": "Не удалось создать QR-код. Попробуйте ещё раз.",
        "qr_ready": "QR-код готов. PNG отправлен без сжатия.",
        "qr_cancelled": "Создание QR-кода отменено.",
        "credits": "Ваш баланс: <b>{credits} кредита</b> 💎",
        "history": "У вас пока нет созданных работ. Начните с /create 🎨",
        "invite": (
            "Приглашайте друзей по персональной ссылке:\n{link}\n\n"
            "Реферальные награды появятся в одном из следующих обновлений."
        ),
        "language": "Выберите язык:",
        "language_changed": "Язык изменён на русский 🇷🇺",
        "support": (
            "Нужна помощь? Отправьте вопрос боту @GenStimAI_bot. "
            "Не присылайте пароли, токены и данные банковских карт."
        ),
        "paysupport": (
            "Платежи в этом MVP пока не подключены. По вопросам оплаты обратитесь "
            "к @GenStimAI_bot."
        ),
        "unknown": "Не удалось распознать пункт. Используйте меню или команду /help.",
        "error": "Что-то пошло не так. Попробуйте ещё раз через минуту.",
    },
}


def get_text(language: str, key: str, **values: object) -> str:
    selected = language if language in TEXTS else "en"
    return TEXTS[selected][key].format(**values)
