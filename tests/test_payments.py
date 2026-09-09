from unittest.mock import AsyncMock

import pytest
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.credits import reject_if_insufficient
from app.bot.handlers.payments import create_stars_invoice, process_pre_checkout
from app.bot.keyboards.payments import buy_credits_button, credit_packages
from app.credits.catalog import FEATURE_CREDIT_COSTS
from app.models.payment import Payment
from app.payments.catalog import CREDIT_PACKAGES, STARS_CURRENCY
from app.services.background_removal import InsufficientCreditsError
from app.services.local_generation import LocalGenerationService
from app.services.payment import (
    FULFILLED,
    CreditPackageNotFoundError,
    PaymentService,
    PaymentValidationError,
)
from app.services.user import UserService


async def create_user(session: AsyncSession, telegram_id: int = 7001):
    user, _ = await UserService(session).get_or_create(
        telegram_id=telegram_id,
        username="stars-tester",
        first_name="Stars",
        telegram_language="en",
    )
    return user


async def pending_payment(
    session: AsyncSession, package_id: str = "credits_30", telegram_id: int = 7001
) -> tuple[Payment, object]:
    user = await create_user(session, telegram_id)
    payment = await PaymentService(session).create_pending(
        user_id=user.id,
        telegram_user_id=user.telegram_id,
        package_id=package_id,
    )
    return payment, user


async def pay(session: AsyncSession, payment: Payment, charge_id: str = "stars-charge-1"):
    return await PaymentService(session).record_successful_payment(
        telegram_user_id=payment.telegram_user_id,
        invoice_payload=payment.invoice_payload,
        currency=STARS_CURRENCY,
        amount=payment.amount,
        telegram_payment_charge_id=charge_id,
    )


def test_credit_package_catalog() -> None:
    assert {
        package_id: (package.stars_amount, package.credits)
        for package_id, package in CREDIT_PACKAGES.items()
    } == {
        "credits_10": (10, 10),
        "credits_30": (25, 30),
        "credits_65": (50, 65),
    }


def test_function_cost_catalog() -> None:
    assert FEATURE_CREDIT_COSTS == {
        "background_removal": 1,
        "qr_designer": 1,
        "meme_generator": 1,
        "pixel_avatar": 1,
        "passport_photo": 1,
        "sticker": 1,
    }


async def test_invoice_uses_xtr_and_package_price(session: AsyncSession) -> None:
    payment, user = await pending_payment(session)
    invoice = PaymentService(session).build_invoice(
        payment,
        title="30 GenStim credits",
        description="Add credits",
    )

    assert invoice.payload == payment.invoice_payload
    assert invoice.currency == "XTR"
    assert invoice.amount == 25
    assert payment.credits_purchased == 30
    assert payment.status == "pending"
    assert user.credits == 3


async def test_unknown_package_is_rejected(session: AsyncSession) -> None:
    user = await create_user(session)
    with pytest.raises(CreditPackageNotFoundError):
        await PaymentService(session).create_pending(
            user_id=user.id,
            telegram_user_id=user.telegram_id,
            package_id="credits_unknown",
        )


async def test_invoice_handler_omits_provider_token(session: AsyncSession) -> None:
    telegram_user = TelegramUser(id=7002, is_bot=False, first_name="Invoice")

    class Message:
        answer = AsyncMock()

    class Callback:
        from_user = telegram_user
        data = "stars:buy:credits_30"
        message = Message()
        answer = AsyncMock()

    class Bot:
        send_invoice = AsyncMock()

    callback = Callback()
    bot = Bot()
    await create_stars_invoice(callback, session, bot)  # type: ignore[arg-type]

    invoice_kwargs = bot.send_invoice.await_args.kwargs
    assert invoice_kwargs["currency"] == "XTR"
    assert invoice_kwargs["prices"][0].amount == 25
    assert "provider_token" not in invoice_kwargs


async def test_invalid_package_callback_does_not_create_invoice(
    session: AsyncSession,
) -> None:
    telegram_user = TelegramUser(id=7003, is_bot=False, first_name="Invalid")

    class Callback:
        from_user = telegram_user
        data = "stars:buy:credits_fake"
        message = None
        answer = AsyncMock()

    class Bot:
        send_invoice = AsyncMock()

    callback = Callback()
    bot = Bot()
    await create_stars_invoice(callback, session, bot)  # type: ignore[arg-type]

    bot.send_invoice.assert_not_awaited()
    callback.answer.assert_awaited_once()


async def test_pre_checkout_query_is_confirmed(session: AsyncSession) -> None:
    payment, user = await pending_payment(session)

    class Query:
        from_user = TelegramUser(
            id=payment.telegram_user_id, is_bot=False, first_name="Stars"
        )
        invoice_payload = payment.invoice_payload
        currency = STARS_CURRENCY
        total_amount = payment.amount
        answer = AsyncMock()

    query = Query()
    await process_pre_checkout(query, session)  # type: ignore[arg-type]

    query.answer.assert_awaited_once_with(ok=True)
    assert user.credits == 3


async def test_wrong_payload_is_rejected(session: AsyncSession) -> None:
    payment, _ = await pending_payment(session)

    with pytest.raises(PaymentValidationError, match="Unknown invoice"):
        await PaymentService(session).validate_pre_checkout(
            telegram_user_id=payment.telegram_user_id,
            invoice_payload="genstim:credits:v1:wrong",
            currency=STARS_CURRENCY,
            amount=payment.amount,
        )


async def test_wrong_amount_is_rejected(session: AsyncSession) -> None:
    payment, _ = await pending_payment(session)

    with pytest.raises(PaymentValidationError, match="does not match"):
        await PaymentService(session).validate_pre_checkout(
            telegram_user_id=payment.telegram_user_id,
            invoice_payload=payment.invoice_payload,
            currency=STARS_CURRENCY,
            amount=payment.amount + 1,
        )


async def test_successful_payment_adds_credits_and_is_stored(
    session: AsyncSession,
) -> None:
    payment, user = await pending_payment(session)
    starting_balance = user.credits
    receipt = await pay(session, payment)

    assert receipt.duplicate is False
    assert receipt.credits_added == 30
    assert receipt.balance == starting_balance + 30
    assert user.credits == starting_balance + 30
    assert payment.status == FULFILLED
    assert payment.telegram_payment_charge_id == "stars-charge-1"
    assert payment.invoice_payload.startswith("genstim:credits:v1:")
    assert payment.paid_at is not None
    assert payment.fulfilled_at is not None


async def test_repeated_successful_payment_is_idempotent(
    session: AsyncSession,
) -> None:
    payment, user = await pending_payment(session)
    starting_balance = user.credits
    first = await pay(session, payment)
    second = await pay(session, payment)

    assert first.duplicate is False
    assert second.duplicate is True
    assert second.credits_added == 0
    assert second.payment.id == first.payment.id
    assert user.credits == starting_balance + 30


async def test_function_is_blocked_when_balance_is_insufficient(
    session: AsyncSession,
) -> None:
    user = await create_user(session)
    user.credits = 0
    calls = 0

    async def operation() -> bytes:
        nonlocal calls
        calls += 1
        return b"should not run"

    with pytest.raises(InsufficientCreditsError):
        await LocalGenerationService(session).process(
            user_id=user.id,
            feature="qr_designer",
            operation=operation,
        )

    assert calls == 0


async def test_one_function_run_deducts_credits_once(session: AsyncSession) -> None:
    user = await create_user(session)
    calls = 0

    async def operation() -> bytes:
        nonlocal calls
        calls += 1
        return b"qr-result"

    result = await LocalGenerationService(session).process(
        user_id=user.id,
        feature="qr_designer",
        operation=operation,
    )

    assert calls == 1
    assert result.generation.credits_spent == 1
    assert user.credits == 2


async def test_insufficient_message_has_buy_credits_button() -> None:
    class Message:
        answer = AsyncMock()

    class Callback:
        message = Message()

    class State:
        clear = AsyncMock()

    callback = Callback()
    state = State()
    blocked = await reject_if_insufficient(
        target=callback,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        language="en",
        balance=0,
        feature="qr_designer",
    )

    assert blocked is True
    state.clear.assert_awaited_once()
    kwargs = callback.message.answer.await_args.kwargs
    assert "reply_markup" in kwargs
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == "stars:packages"


def test_credit_keyboards_use_server_package_ids() -> None:
    callbacks = [row[0].callback_data for row in credit_packages("en").inline_keyboard]
    assert callbacks == [f"stars:buy:{package_id}" for package_id in CREDIT_PACKAGES]
    assert buy_credits_button("ru").inline_keyboard[0][0].callback_data == "stars:packages"
