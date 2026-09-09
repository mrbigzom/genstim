from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.payments.catalog import CREDIT_PACKAGES


def credit_packages(language: str) -> InlineKeyboardMarkup:
    rows = []
    for package in CREDIT_PACKAGES.values():
        label = (
            f"{package.credits} credits — {package.stars_amount} ⭐"
            if language == "en"
            else f"{package.credits} кредитов — {package.stars_amount} ⭐"
        )
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"stars:buy:{package.id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def buy_credits_button(language: str) -> InlineKeyboardMarkup:
    label = "Buy credits" if language == "en" else "Купить кредиты"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data="stars:packages")]
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
