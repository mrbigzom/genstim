import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.common import ensure_user
from app.bot.keyboards.payments import payment_continue, payment_waiting
from app.locales.messages import get_text
from app.services.payment import (
    PaymentService,
    PaymentValidationError,
    ProductNotPayableError,
)

logger = logging.getLogger(__name__)
router = Router(name="payments")


@router.callback_query(F.data.startswith("stars:buy:"))
async def create_stars_invoice(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    user = await ensure_user(callback.from_user, session)
    product_id = (callback.data or "").removeprefix("stars:buy:")
    service = PaymentService(session)
    try:
        product = service.payable_product(product_id)
        payment = await service.create_pending(
            user_id=user.id,
            telegram_user_id=user.telegram_id,
            product_id=product.id,
        )
        product_name = get_text(user.language, product.name_key)
        invoice = service.build_invoice(
            payment,
            title=product_name,
            description=get_text(
                user.language, "payment_invoice_description", product=product_name
            ),
        )
    except (ProductNotPayableError, PaymentValidationError):
        await callback.answer(get_text(user.language, "payment_error"), show_alert=True)
        return

    await callback.answer()
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=invoice.title,
        description=invoice.description,
        payload=invoice.payload,
        currency=invoice.currency,
        prices=[LabeledPrice(label=invoice.title, amount=invoice.amount)],
    )
    if callback.message:
        await callback.message.answer(
            get_text(user.language, "payment_waiting"),
            reply_markup=payment_waiting(user.language, payment.id),
        )


@router.callback_query(F.data == "stars:offer:cancel")
async def cancel_stars_offer(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(callback.from_user, session)
    await callback.answer()
    if callback.message:
        await callback.message.answer(get_text(user.language, "payment_cancelled"))


@router.callback_query(F.data.startswith("stars:cancel:"))
async def cancel_pending_payment(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(callback.from_user, session)
    try:
        payment_id = int((callback.data or "").removeprefix("stars:cancel:"))
    except ValueError:
        await callback.answer(get_text(user.language, "payment_error"), show_alert=True)
        return
    cancelled = await PaymentService(session).cancel_pending(
        payment_id=payment_id, telegram_user_id=user.telegram_id
    )
    await callback.answer()
    if callback.message:
        key = "payment_cancelled" if cancelled else "payment_not_pending"
        await callback.message.answer(get_text(user.language, key))


@router.pre_checkout_query()
async def process_pre_checkout(
    query: PreCheckoutQuery,
    session: AsyncSession,
) -> None:
    user = await ensure_user(query.from_user, session)
    try:
        await PaymentService(session).validate_pre_checkout(
            telegram_user_id=user.telegram_id,
            invoice_payload=query.invoice_payload,
            currency=query.currency,
            amount=query.total_amount,
        )
    except (ProductNotPayableError, PaymentValidationError) as exc:
        logger.warning(
            "Rejected Stars pre-checkout user_id=%s error=%s", user.id, type(exc).__name__
        )
        await query.answer(
            ok=False,
            error_message=get_text(user.language, "payment_validation_error"),
        )
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, session: AsyncSession) -> None:
    if message.from_user is None or message.successful_payment is None:
        return
    user = await ensure_user(message.from_user, session)
    successful = message.successful_payment
    service = PaymentService(session)
    try:
        receipt = await service.record_successful_payment(
            telegram_user_id=user.telegram_id,
            invoice_payload=successful.invoice_payload,
            currency=successful.currency,
            amount=successful.total_amount,
            telegram_payment_charge_id=successful.telegram_payment_charge_id,
        )
        product = service.payable_product(receipt.payment.product_id)
    except (ProductNotPayableError, PaymentValidationError) as exc:
        logger.error(
            "Could not record successful Stars payment user_id=%s error=%s",
            user.id,
            type(exc).__name__,
        )
        await message.answer(get_text(user.language, "payment_error"))
        return

    # Telegram has already charged the user. Persist the receipt before any reply can fail.
    await session.commit()

    if receipt.duplicate:
        await message.answer(get_text(user.language, "payment_duplicate"))
        return
    await message.answer(
        get_text(
            user.language,
            "payment_success",
            product=get_text(user.language, product.name_key),
        ),
        reply_markup=payment_continue(user.language, product.feature_callback),
    )
