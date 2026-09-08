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
        "background_send_image": (
            "Send a JPEG or PNG image. Maximum file size: 10 MB; "
            "maximum resolution: 25 megapixels."
        ),
        "background_invalid_image": "Send a valid JPEG or PNG image.",
        "background_too_large": "That image is too large. Use a file under 10 MB and 25 MP.",
        "background_processing": "Removing the background locally…",
        "background_failed": "The background could not be removed. Try another image.",
        "background_ready": "Done — your transparent PNG is ready.",
        "background_cancelled": "Background Removal cancelled.",
        "credits": "Your balance: <b>{credits} credits</b> 💎",
        "history_empty": "You do not have any creations yet. Start with /create 🎨",
        "history_header": "<b>Your recent creations</b>\n\n{items}",
        "history_item": (
            "{index}. {feature}\n✅ Completed · {credits} credit\n{date}"
        ),
        "feature_background_removal": "✂️ Background Removal",
        "background_prompt": (
            "Send a JPEG, PNG, WebP, or HEIC image (up to {max_mb} MB). "
            "The result costs 1 credit, charged only after successful processing."
        ),
        "background_only_images": "Please send an image, not text or another file.",
        "background_unsupported_format": (
            "This image format is not supported. Please send a JPEG, PNG, WebP, or HEIC image."
        ),
        "background_too_large": "The image is too large. Maximum size: {max_mb} MB.",
        "background_processing": (
            "⏳ Removing the background… This usually takes a few seconds."
        ),
        "background_success": (
            "✅ Background removed. Remaining balance: <b>{credits} credits</b>."
        ),
        "background_insufficient": (
            "You do not have enough credits. Background Removal requires 1 credit."
        ),
        "background_timeout": (
            "Local image processing took too long. No credit was charged. "
            "Please send the image again."
        ),
        "background_provider_error": (
            "The image could not be processed right now. No credit was charged. "
            "Please try again later."
        ),
        "background_corrupted_image": (
            "The image is damaged or cannot be decoded. No credit was charged. "
            "Please send another image."
        ),
        "background_dimensions_too_large": (
            "The image dimensions are too large. Maximum: {max_megapixels} megapixels. "
            "No credit was charged."
        ),
        "background_transfer_error": (
            "I could not download or send the image. No credit was charged if processing "
            "did not complete. Please try again."
        ),
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
        "background_send_image": (
            "Отправьте изображение JPEG или PNG. Максимальный размер файла — 10 МБ, "
            "разрешение — 25 мегапикселей."
        ),
        "background_invalid_image": "Отправьте корректное изображение JPEG или PNG.",
        "background_too_large": (
            "Изображение слишком большое. Используйте файл до 10 МБ и 25 Мп."
        ),
        "background_processing": "Удаляю фон локально…",
        "background_failed": "Не удалось удалить фон. Попробуйте другое изображение.",
        "background_ready": "Готово — PNG с прозрачным фоном создан.",
        "background_cancelled": "Удаление фона отменено.",
        "credits": "Ваш баланс: <b>{credits} кредита</b> 💎",
        "history_empty": "У вас пока нет созданных работ. Начните с /create 🎨",
        "history_header": "<b>Ваши последние работы</b>\n\n{items}",
        "history_item": (
            "{index}. {feature}\n✅ Готово · {credits} кредит\n{date}"
        ),
        "feature_background_removal": "✂️ Удаление фона",
        "background_prompt": (
            "Отправьте изображение JPEG, PNG, WebP или HEIC размером до {max_mb} МБ. "
            "Стоимость — 1 кредит; он спишется только после успешной обработки."
        ),
        "background_only_images": "Отправьте изображение, а не текст или другой файл.",
        "background_unsupported_format": (
            "Этот формат не поддерживается. Отправьте изображение JPEG, PNG, WebP или HEIC."
        ),
        "background_too_large": "Изображение слишком большое. Максимум: {max_mb} МБ.",
        "background_processing": (
            "⏳ Удаляю фон… Обычно это занимает несколько секунд."
        ),
        "background_success": (
            "✅ Фон удалён. Осталось: <b>{credits} кредитов</b>."
        ),
        "background_insufficient": (
            "Недостаточно кредитов. Для удаления фона нужен 1 кредит."
        ),
        "background_timeout": (
            "Локальная обработка заняла слишком много времени. Кредит не списан. "
            "Отправьте изображение ещё раз."
        ),
        "background_provider_error": (
            "Сейчас не удалось обработать изображение. Кредит не списан. "
            "Попробуйте позже."
        ),
        "background_corrupted_image": (
            "Изображение повреждено или не читается. Кредит не списан. "
            "Отправьте другое изображение."
        ),
        "background_dimensions_too_large": (
            "Слишком большое разрешение изображения. Максимум: {max_megapixels} Мп. "
            "Кредит не списан."
        ),
        "background_transfer_error": (
            "Не удалось скачать или отправить изображение. Если обработка не завершилась, "
            "кредит не списан. Попробуйте ещё раз."
        ),
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
