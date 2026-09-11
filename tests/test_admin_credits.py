from unittest.mock import AsyncMock

import pytest
from aiogram.filters import CommandObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.admin import add_credits_command
from app.locales.messages import get_text
from app.services.user import DEFAULT_CREDITS, MAX_ADMIN_CREDIT_TOP_UP, UserService

ADMIN_ID = 9001
TARGET_ID = 9002


class FakeMessage:
    def __init__(self, telegram_id: int, *, language_code: str = "en") -> None:
        self.from_user = TelegramUser(
            id=telegram_id,
            is_bot=False,
            first_name="Admin",
            language_code=language_code,
        )
        self.answer = AsyncMock()


def command(args: str) -> CommandObject:
    return CommandObject(command="addcredits", args=args)


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    *,
    language: str = "en",
):
    user, _ = await UserService(session).get_or_create(
        telegram_id=telegram_id,
        username=None,
        first_name="User",
        telegram_language=language,
    )
    return user


async def test_admin_can_add_credits(session: AsyncSession) -> None:
    await create_user(session, ADMIN_ID, language="ru")
    target = await create_user(session, TARGET_ID)
    message = FakeMessage(ADMIN_ID, language_code="en")

    await add_credits_command(
        message,  # type: ignore[arg-type]
        command(f"{TARGET_ID} 25"),
        session,
        ADMIN_ID,
    )

    assert target.credits == DEFAULT_CREDITS + 25
    response = message.answer.await_args.args[0]
    assert str(TARGET_ID) in response
    assert "Начислено: <b>25</b>" in response
    assert f"Новый баланс: <b>{DEFAULT_CREDITS + 25} кредитов</b>" in response


async def test_non_admin_cannot_add_credits(session: AsyncSession) -> None:
    target = await create_user(session, TARGET_ID)
    message = FakeMessage(9003)

    await add_credits_command(
        message,  # type: ignore[arg-type]
        command(f"{TARGET_ID} 25"),
        session,
        ADMIN_ID,
    )

    assert target.credits == DEFAULT_CREDITS
    message.answer.assert_awaited_once_with(
        get_text("en", "admin_credit_unauthorized")
    )


@pytest.mark.parametrize("amount", [0, -1, MAX_ADMIN_CREDIT_TOP_UP + 1])
async def test_invalid_credit_amount_is_rejected(
    session: AsyncSession,
    amount: int,
) -> None:
    await create_user(session, ADMIN_ID)
    target = await create_user(session, TARGET_ID)
    message = FakeMessage(ADMIN_ID)

    await add_credits_command(
        message,  # type: ignore[arg-type]
        command(f"{TARGET_ID} {amount}"),
        session,
        ADMIN_ID,
    )

    assert target.credits == DEFAULT_CREDITS
    message.answer.assert_awaited_once_with(
        get_text(
            "en",
            "admin_credit_invalid_amount",
            maximum=MAX_ADMIN_CREDIT_TOP_UP,
        )
    )


async def test_one_command_increases_balance_exactly_once(session: AsyncSession) -> None:
    await create_user(session, ADMIN_ID)
    target = await create_user(session, TARGET_ID)
    message = FakeMessage(ADMIN_ID)

    await add_credits_command(
        message,  # type: ignore[arg-type]
        command(f"{TARGET_ID} 7"),
        session,
        ADMIN_ID,
    )

    await session.refresh(target)
    assert target.credits == DEFAULT_CREDITS + 7
    message.answer.assert_awaited_once()


async def test_unknown_user_is_rejected(session: AsyncSession) -> None:
    await create_user(session, ADMIN_ID)
    message = FakeMessage(ADMIN_ID)

    await add_credits_command(
        message,  # type: ignore[arg-type]
        command("999999 10"),
        session,
        ADMIN_ID,
    )

    message.answer.assert_awaited_once_with(
        get_text(
            "en",
            "admin_credit_user_not_found",
            telegram_user_id=999999,
        )
    )
