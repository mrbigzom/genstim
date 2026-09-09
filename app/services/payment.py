from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.payments.catalog import PRODUCT_CATALOG, STARS_CURRENCY, Product
from app.repositories.payment import PaymentRepository

PENDING = "pending"
PAID = "paid"
AUTHORIZED = "authorized"
PROCESSING = "processing"
FULFILLED = "fulfilled"
FAILED = "failed"
CANCELLED = "cancelled"
REFUNDED = "refunded"


class PaymentError(Exception):
    pass


class ProductNotPayableError(PaymentError):
    pass


class PaymentValidationError(PaymentError):
    pass


class PaymentNotAuthorizedError(PaymentError):
    pass


@dataclass(frozen=True, slots=True)
class InvoiceRequest:
    title: str
    description: str
    payload: str
    currency: str
    amount: int


@dataclass(frozen=True, slots=True)
class PaymentReceipt:
    payment: Payment
    duplicate: bool


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        catalog: Mapping[str, Product] = PRODUCT_CATALOG,
    ) -> None:
        self.session = session
        self.catalog = catalog
        self.repository = PaymentRepository(session)

    def payable_product(self, product_id: str) -> Product:
        product = self.catalog.get(product_id)
        if product is None or product.paid_amount is None:
            raise ProductNotPayableError(product_id)
        if product.paid_amount <= 0:
            raise ProductNotPayableError(product_id)
        return product

    async def create_pending(
        self, *, user_id: int, telegram_user_id: int, product_id: str
    ) -> Payment:
        product = self.payable_product(product_id)
        return await self.repository.create(
            Payment(
                user_id=user_id,
                telegram_user_id=telegram_user_id,
                product_id=product.id,
                amount=product.paid_amount,
                currency=STARS_CURRENCY,
                invoice_payload=f"genstim:v1:{uuid4().hex}",
                status=PENDING,
            )
        )

    def build_invoice(
        self, payment: Payment, *, title: str, description: str
    ) -> InvoiceRequest:
        product = self.payable_product(payment.product_id)
        if payment.amount != product.paid_amount or payment.currency != STARS_CURRENCY:
            raise PaymentValidationError("Payment no longer matches the product catalog")
        return InvoiceRequest(
            title=title,
            description=description,
            payload=payment.invoice_payload,
            currency=STARS_CURRENCY,
            amount=payment.amount,
        )

    async def validate_pre_checkout(
        self,
        *,
        telegram_user_id: int,
        invoice_payload: str,
        currency: str,
        amount: int,
    ) -> Payment:
        payment = await self.repository.get_by_payload_for_update(invoice_payload)
        self._validate_payment(
            payment,
            telegram_user_id=telegram_user_id,
            invoice_payload=invoice_payload,
            currency=currency,
            amount=amount,
            required_status=PENDING,
        )
        assert payment is not None
        return payment

    async def record_successful_payment(
        self,
        *,
        telegram_user_id: int,
        invoice_payload: str,
        currency: str,
        amount: int,
        telegram_payment_charge_id: str,
    ) -> PaymentReceipt:
        existing = await self.repository.get_by_charge_id(telegram_payment_charge_id)
        if existing is not None:
            if (
                existing.telegram_user_id == telegram_user_id
                and existing.invoice_payload == invoice_payload
                and existing.currency == currency
                and existing.amount == amount
            ):
                return PaymentReceipt(existing, duplicate=True)
            raise PaymentValidationError("Charge id belongs to another payment")

        payment = await self.repository.get_by_payload_for_update(invoice_payload)
        if payment is not None and payment.telegram_payment_charge_id is not None:
            if (
                payment.telegram_payment_charge_id == telegram_payment_charge_id
                and payment.telegram_user_id == telegram_user_id
                and payment.currency == currency
                and payment.amount == amount
            ):
                return PaymentReceipt(payment, duplicate=True)
            raise PaymentValidationError("Invoice was already linked to another charge")
        self._validate_payment(
            payment,
            telegram_user_id=telegram_user_id,
            invoice_payload=invoice_payload,
            currency=currency,
            amount=amount,
            required_status=(PENDING, CANCELLED),
        )
        assert payment is not None
        payment.telegram_payment_charge_id = telegram_payment_charge_id
        payment.status = PAID
        payment.paid_at = datetime.now(UTC)
        await self.session.flush()
        return PaymentReceipt(payment, duplicate=False)

    async def authorize_available(self, *, user_id: int, product_id: str) -> Payment | None:
        product = self.payable_product(product_id)
        payment = await self.repository.get_available_for_update(user_id, product.id)
        if payment is None:
            return None
        self._validate_catalog_fields(payment, product)
        if payment.status == PAID:
            payment.status = AUTHORIZED
            payment.authorized_at = datetime.now(UTC)
            await self.session.flush()
        return payment

    async def claim_for_processing(
        self,
        *,
        payment_id: int,
        user_id: int,
        telegram_user_id: int,
        product_id: str,
    ) -> Payment:
        product = self.payable_product(product_id)
        payment = await self.repository.get_by_id_for_update(payment_id)
        if (
            payment is None
            or payment.user_id != user_id
            or payment.telegram_user_id != telegram_user_id
            or payment.product_id != product.id
            or payment.status != AUTHORIZED
            or payment.telegram_payment_charge_id is None
        ):
            raise PaymentNotAuthorizedError(product_id)
        self._validate_catalog_fields(payment, product)
        payment.status = PROCESSING
        payment.service_started_at = datetime.now(UTC)
        await self.session.flush()
        return payment

    async def mark_fulfilled(self, payment: Payment, *, generation_id: int) -> None:
        if payment.status != PROCESSING or payment.generation_id is not None:
            raise PaymentNotAuthorizedError(payment.product_id)
        payment.status = FULFILLED
        payment.generation_id = generation_id
        payment.fulfilled_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_failed(self, payment: Payment, *, error_code: str) -> None:
        if payment.status != PROCESSING:
            return
        payment.status = FAILED
        payment.error_code = error_code
        payment.failed_at = datetime.now(UTC)
        await self.session.flush()

    async def cancel_pending(self, *, payment_id: int, telegram_user_id: int) -> bool:
        payment = await self.repository.get_by_id_for_update(payment_id)
        if (
            payment is None
            or payment.telegram_user_id != telegram_user_id
            or payment.status != PENDING
        ):
            return False
        payment.status = CANCELLED
        await self.session.flush()
        return True

    def _validate_payment(
        self,
        payment: Payment | None,
        *,
        telegram_user_id: int,
        invoice_payload: str,
        currency: str,
        amount: int,
        required_status: str | tuple[str, ...],
    ) -> None:
        if payment is None:
            raise PaymentValidationError("Unknown invoice payload")
        product = self.payable_product(payment.product_id)
        allowed_statuses = (
            (required_status,) if isinstance(required_status, str) else required_status
        )
        if (
            payment.invoice_payload != invoice_payload
            or payment.telegram_user_id != telegram_user_id
            or payment.currency != currency
            or payment.amount != amount
            or payment.status not in allowed_statuses
        ):
            raise PaymentValidationError("Payment data does not match the invoice")
        self._validate_catalog_fields(payment, product)

    @staticmethod
    def _validate_catalog_fields(payment: Payment, product: Product) -> None:
        if payment.currency != STARS_CURRENCY or payment.amount != product.paid_amount:
            raise PaymentValidationError("Payment does not match the product catalog")
