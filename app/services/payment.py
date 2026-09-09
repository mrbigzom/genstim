from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.payments.catalog import CREDIT_PACKAGES, STARS_CURRENCY, CreditPackage
from app.repositories.payment import PaymentRepository
from app.repositories.user import UserRepository

PENDING = "pending"
FULFILLED = "fulfilled"
CANCELLED = "cancelled"
REFUNDED = "refunded"


class PaymentError(Exception):
    pass


class CreditPackageNotFoundError(PaymentError):
    pass


class PaymentValidationError(PaymentError):
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
    credits_added: int
    balance: int


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        catalog: Mapping[str, CreditPackage] = CREDIT_PACKAGES,
    ) -> None:
        self.session = session
        self.catalog = catalog
        self.repository = PaymentRepository(session)
        self.users = UserRepository(session)

    def credit_package(self, package_id: str) -> CreditPackage:
        package = self.catalog.get(package_id)
        if package is None or package.stars_amount <= 0 or package.credits <= 0:
            raise CreditPackageNotFoundError(package_id)
        return package

    async def create_pending(
        self, *, user_id: int, telegram_user_id: int, package_id: str
    ) -> Payment:
        package = self.credit_package(package_id)
        return await self.repository.create(
            Payment(
                user_id=user_id,
                telegram_user_id=telegram_user_id,
                product_id=package.id,
                amount=package.stars_amount,
                credits_purchased=package.credits,
                currency=STARS_CURRENCY,
                invoice_payload=f"genstim:credits:v1:{uuid4().hex}",
                status=PENDING,
            )
        )

    def build_invoice(
        self, payment: Payment, *, title: str, description: str
    ) -> InvoiceRequest:
        package = self.credit_package(payment.product_id)
        self._validate_catalog_fields(payment, package)
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
            self._validate_duplicate(
                existing,
                telegram_user_id=telegram_user_id,
                invoice_payload=invoice_payload,
                currency=currency,
                amount=amount,
            )
            user = await self.users.get_by_id_for_update(existing.user_id)
            if user is None:
                raise PaymentValidationError("Payment user no longer exists")
            return PaymentReceipt(existing, True, 0, user.credits)

        payment = await self.repository.get_by_payload_for_update(invoice_payload)
        if payment is not None and payment.telegram_payment_charge_id is not None:
            self._validate_duplicate(
                payment,
                telegram_user_id=telegram_user_id,
                invoice_payload=invoice_payload,
                currency=currency,
                amount=amount,
                telegram_payment_charge_id=telegram_payment_charge_id,
            )
            user = await self.users.get_by_id_for_update(payment.user_id)
            if user is None:
                raise PaymentValidationError("Payment user no longer exists")
            return PaymentReceipt(payment, True, 0, user.credits)

        self._validate_payment(
            payment,
            telegram_user_id=telegram_user_id,
            invoice_payload=invoice_payload,
            currency=currency,
            amount=amount,
            required_status=(PENDING, CANCELLED),
        )
        assert payment is not None
        user = await self.users.get_by_id_for_update(payment.user_id)
        if user is None or user.telegram_id != telegram_user_id:
            raise PaymentValidationError("Payment user does not match")

        now = datetime.now(UTC)
        user.credits += payment.credits_purchased
        payment.telegram_payment_charge_id = telegram_payment_charge_id
        payment.status = FULFILLED
        payment.paid_at = now
        payment.fulfilled_at = now
        await self.session.flush()
        return PaymentReceipt(payment, False, payment.credits_purchased, user.credits)

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
        package = self.credit_package(payment.product_id)
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
        self._validate_catalog_fields(payment, package)

    @staticmethod
    def _validate_catalog_fields(payment: Payment, package: CreditPackage) -> None:
        if (
            payment.currency != STARS_CURRENCY
            or payment.amount != package.stars_amount
            or payment.credits_purchased != package.credits
        ):
            raise PaymentValidationError("Payment does not match the package catalog")

    @staticmethod
    def _validate_duplicate(
        payment: Payment,
        *,
        telegram_user_id: int,
        invoice_payload: str,
        currency: str,
        amount: int,
        telegram_payment_charge_id: str | None = None,
    ) -> None:
        if (
            payment.telegram_user_id != telegram_user_id
            or payment.invoice_payload != invoice_payload
            or payment.currency != currency
            or payment.amount != amount
            or (
                telegram_payment_charge_id is not None
                and payment.telegram_payment_charge_id != telegram_payment_charge_id
            )
        ):
            raise PaymentValidationError("Charge id belongs to another payment")
