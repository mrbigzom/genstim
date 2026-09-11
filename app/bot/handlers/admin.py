from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import ensure_user
from app.locales.messages import get_text
from app.services.user import MAX_ADMIN_CREDIT_TOP_UP, UserService, detect_language

router = Router(name="admin")
MAX_TELEGRAM_USER_ID = (1 << 63) - 1


@router.message(Command("addcredits"))
async def add_credits_command(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    admin_telegram_id: int | None,
) -> None:
    if message.from_user is None:
        return

    fallback_language = detect_language(message.from_user.language_code)
    if admin_telegram_id is None or message.from_user.id != admin_telegram_id:
        await message.answer(get_text(fallback_language, "admin_credit_unauthorized"))
        return

    admin = await ensure_user(message.from_user, session)
    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.answer(get_text(admin.language, "admin_credit_usage"))
        return

    try:
        telegram_user_id = int(parts[0])
        amount = int(parts[1])
    except ValueError:
        await message.answer(get_text(admin.language, "admin_credit_usage"))
        return

    if amount <= 0 or amount > MAX_ADMIN_CREDIT_TOP_UP:
        await message.answer(
            get_text(
                admin.language,
                "admin_credit_invalid_amount",
                maximum=MAX_ADMIN_CREDIT_TOP_UP,
            )
        )
        return

    if telegram_user_id <= 0 or telegram_user_id > MAX_TELEGRAM_USER_ID:
        await message.answer(
            get_text(
                admin.language,
                "admin_credit_user_not_found",
                telegram_user_id=telegram_user_id,
            )
        )
        return

    user = await UserService(session).add_credits(
        telegram_id=telegram_user_id,
        amount=amount,
    )
    if user is None:
        await message.answer(
            get_text(
                admin.language,
                "admin_credit_user_not_found",
                telegram_user_id=telegram_user_id,
            )
        )
        return

    await message.answer(
        get_text(
            admin.language,
            "admin_credit_success",
            telegram_user_id=user.telegram_id,
            amount=amount,
            balance=user.credits,
        )
    )
