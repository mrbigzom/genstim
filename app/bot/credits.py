from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.payments import buy_credits_button
from app.credits.catalog import get_feature_credit_cost
from app.locales.messages import get_text


async def reject_if_insufficient(
    *,
    target: CallbackQuery | Message,
    state: FSMContext,
    language: str,
    balance: int,
    feature: str,
) -> bool:
    cost = get_feature_credit_cost(feature)
    if balance >= cost:
        return False
    await state.clear()
    message = getattr(target, "message", target)
    if message:
        await message.answer(
            get_text(language, "credits_insufficient", balance=balance, cost=cost),
            reply_markup=buy_credits_button(language),
        )
    return True
