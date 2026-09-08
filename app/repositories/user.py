from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def get_by_id_for_update(self, user_id: int) -> User | None:
        return await self.session.scalar(
            select(User).where(User.id == user_id).with_for_update()
        )

    async def get_by_referral_code(self, referral_code: str) -> User | None:
        return await self.session.scalar(
            select(User).where(User.referral_code == referral_code)
        )

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user
