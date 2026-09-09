from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.payments import create_stars_invoice, process_pre_checkout
from app.models.payment import Payment
from app.payments.catalog import PRODUCT_CATALOG, STARS_CURRENCY
from app.services.local_generation import LocalGenerationService
from app.services.payment import (
    AUTHORIZED,
    FULFILLED,
    PAID,
    PaymentNotAuthorizedError,
    PaymentService,
    PaymentValidationError,
)
from app.services.user import UserService


@pytest.fixture
def paid_qr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        PRODUCT_CATALOG,
        "qr_designer",
        replace(
            PRODUCT_CATALOG["qr_designer"],
            stars_amount=25,
            payments_enabled=True,
        ),
    )


async def create_user(session: AsyncSession, telegram_id: int = 7001):
    user, _ = await UserService(session).get_or_create(
        telegram_id=telegram_id,
        username="stars-tester",
        first_name="Stars",
        telegram_language="en",
    )
    return user


async def pending_payment(session: AsyncSession, telegram_id: int = 7001) -> Payment:
    user = await create_user(session, telegram_id)
    return await PaymentService(session).create_pending(
        user_id=user.id,
        telegram_user_id=user.telegram_id,
        product_id="qr_designer",
    )


async def pay(session: AsyncSession, payment: Payment, charge_id: str = "stars-charge-1"):
    return await PaymentService(session).record_successful_payment(
        telegram_user_id=payment.telegram_user_id,
        invoice_payload=payment.invoice_payload,
        currency=STARS_CURRENCY,
        amount=payment.amount,
        telegram_payment_charge_id=charge_id,
    )


async def test_invoice_uses_xtr_and_catalog_price(
    session: AsyncSession, paid_qr: None
) -> None:
    payment = await pending_payment(session)
    invoice = PaymentService(session).build_invoice(
        payment,
        title="QR Designer",
        description="One QR code",
    )

    assert invoice.payload == payment.invoice_payload
    assert invoice.currency == "XTR"
    assert invoice.amount == 25
    assert payment.status == "pending"


async def test_invoice_handler_omits_provider_token(
    session: AsyncSession, paid_qr: None
) -> None:
    telegram_user = TelegramUser(id=7002, is_bot=False, first_name="Invoice")

    class Message:
        answer = AsyncMock()

    class Callback:
        from_user = telegram_user
        data = "stars:buy:qr_designer"
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


async def test_pre_checkout_query_is_confirmed(
    session: AsyncSession, paid_qr: None
) -> None:
    payment = await pending_payment(session)

    class Query:
        from_user = TelegramUser(id=payment.telegram_user_id, is_bot=False, first_name="Stars")
        invoice_payload = payment.invoice_payload
        currency = STARS_CURRENCY
        total_amount = payment.amount
        answer = AsyncMock()

    query = Query()
    await process_pre_checkout(query, session)  # type: ignore[arg-type]

    query.answer.assert_awaited_once_with(ok=True)


async def test_successful_payment_is_stored(
    session: AsyncSession, paid_qr: None
) -> None:
    payment = await pending_payment(session)
    receipt = await pay(session, payment)

    assert receipt.duplicate is False
    assert payment.status == PAID
    assert payment.telegram_payment_charge_id == "stars-charge-1"
    assert payment.invoice_payload.startswith("genstim:v1:")
    assert payment.paid_at is not None


async def test_wrong_payload_is_rejected(session: AsyncSession, paid_qr: None) -> None:
    payment = await pending_payment(session)

    with pytest.raises(PaymentValidationError, match="Unknown invoice"):
        await PaymentService(session).validate_pre_checkout(
            telegram_user_id=payment.telegram_user_id,
            invoice_payload="genstim:v1:wrong",
            currency=STARS_CURRENCY,
            amount=payment.amount,
        )


async def test_wrong_amount_is_rejected(session: AsyncSession, paid_qr: None) -> None:
    payment = await pending_payment(session)

    with pytest.raises(PaymentValidationError, match="does not match"):
        await PaymentService(session).validate_pre_checkout(
            telegram_user_id=payment.telegram_user_id,
            invoice_payload=payment.invoice_payload,
            currency=STARS_CURRENCY,
            amount=payment.amount + 1,
        )


async def test_repeated_successful_payment_is_idempotent(
    session: AsyncSession, paid_qr: None
) -> None:
    payment = await pending_payment(session)
    first = await pay(session, payment)
    second = await pay(session, payment)

    assert first.duplicate is False
    assert second.duplicate is True
    assert second.payment.id == first.payment.id


async def test_function_cannot_start_before_successful_payment(
    session: AsyncSession, paid_qr: None
) -> None:
    payment = await pending_payment(session)
    user = await create_user(session)
    called = False

    async def operation() -> bytes:
        nonlocal called
        called = True
        return b"should not run"

    with pytest.raises(PaymentNotAuthorizedError):
        await LocalGenerationService(session).process(
            user_id=user.id,
            feature="qr_designer",
            operation=operation,
            payment_id=payment.id,
            telegram_user_id=user.telegram_id,
        )

    assert called is False


async def test_one_payment_starts_exactly_one_generation(
    session: AsyncSession, paid_qr: None
) -> None:
    payment = await pending_payment(session)
    user = await create_user(session)
    await pay(session, payment)
    authorized = await PaymentService(session).authorize_available(
        user_id=user.id, product_id="qr_designer"
    )
    assert authorized is not None
    assert authorized.status == AUTHORIZED
    calls = 0

    async def operation() -> bytes:
        nonlocal calls
        calls += 1
        return b"qr-result"

    result = await LocalGenerationService(session).process(
        user_id=user.id,
        feature="qr_designer",
        operation=operation,
        payment_id=payment.id,
        telegram_user_id=user.telegram_id,
    )
    assert payment.status == FULFILLED
    assert payment.generation_id == result.generation.id
    assert result.generation.credits_spent == 0
    assert user.credits == 3

    with pytest.raises(PaymentNotAuthorizedError):
        await LocalGenerationService(session).process(
            user_id=user.id,
            feature="qr_designer",
            operation=operation,
            payment_id=payment.id,
            telegram_user_id=user.telegram_id,
        )

    assert calls == 1
