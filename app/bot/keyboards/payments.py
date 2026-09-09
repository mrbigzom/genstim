from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def payment_offer(language: str, product_id: str, amount: int) -> InlineKeyboardMarkup:
    pay = f"Pay {amount} ⭐" if language == "en" else f"Оплатить {amount} ⭐"
    cancel = "Cancel" if language == "en" else "Отмена"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=pay, callback_data=f"stars:buy:{product_id}")],
            [InlineKeyboardButton(text=cancel, callback_data="stars:offer:cancel")],
        ]
    )


def payment_waiting(language: str, payment_id: int) -> InlineKeyboardMarkup:
    cancel = "Cancel payment" if language == "en" else "Отменить оплату"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=cancel,
                    callback_data=f"stars:cancel:{payment_id}",
                )
            ]
        ]
    )


def payment_continue(language: str, feature_callback: str) -> InlineKeyboardMarkup:
    label = "Continue" if language == "en" else "Продолжить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"feature:{feature_callback}",
                )
            ]
        ]
    )
