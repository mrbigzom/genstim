from dataclasses import dataclass

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.payments import payment_offer
from app.locales.messages import get_text
from app.payments.catalog import get_product
from app.services.payment import PaymentService

PAYMENT_ID_STATE_KEY = "stars_payment_id"


@dataclass(frozen=True, slots=True)
class FeatureAccess:
    blocked: bool
    payment_id: int | None = None


async def check_feature_access(
    *,
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user_id: int,
    language: str,
    product_id: str,
) -> FeatureAccess:
    product = get_product(product_id)
    if product is None or product.paid_amount is None:
        return FeatureAccess(blocked=False)

    payment = await PaymentService(session).authorize_available(
        user_id=user_id, product_id=product_id
    )
    if payment is not None:
        await state.clear()
        await state.update_data(**{PAYMENT_ID_STATE_KEY: payment.id})
        return FeatureAccess(blocked=False, payment_id=payment.id)

    await state.clear()
    if callback.message:
        await callback.message.answer(
            get_text(
                language,
                "payment_cost",
                product=get_text(language, product.name_key),
                amount=product.paid_amount,
            ),
            reply_markup=payment_offer(language, product.id, product.paid_amount),
        )
    return FeatureAccess(blocked=True)
