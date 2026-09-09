from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payment: Payment) -> Payment:
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_id_for_update(self, payment_id: int) -> Payment | None:
        return await self.session.scalar(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )

    async def get_by_payload_for_update(self, payload: str) -> Payment | None:
        return await self.session.scalar(
            select(Payment)
            .where(Payment.invoice_payload == payload)
            .with_for_update()
        )

    async def get_by_charge_id(self, charge_id: str) -> Payment | None:
        return await self.session.scalar(
            select(Payment)
            .where(Payment.telegram_payment_charge_id == charge_id)
            .with_for_update()
        )
