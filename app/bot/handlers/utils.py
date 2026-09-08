from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user import UserService


async def ensure_user(telegram_user: TelegramUser, session: AsyncSession) -> User:
    user, _ = await UserService(session).get_or_create(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        telegram_language=telegram_user.language_code,
    )
    return user
