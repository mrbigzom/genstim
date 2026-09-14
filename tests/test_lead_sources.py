from unittest.mock import AsyncMock

import pytest
from aiogram.filters import CommandObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.admin import lead_source_add_command
from app.locales.messages import get_text
from app.services.lead_source import (
    DuplicateLeadSourceError,
    InvalidLeadSourceURLError,
    LeadSourceService,
)

ADMIN_ID = 9001


async def public_resolver(hostname: str, port: int) -> set[str]:
    assert hostname == "example.com"
    assert port in {80, 443}
    return {"93.184.216.34"}


async def private_resolver(hostname: str, port: int) -> set[str]:
    return {"10.0.0.8"}


async def test_add_list_duplicate_remove_and_reenable_source(
    session: AsyncSession,
) -> None:
    service = LeadSourceService(session, resolver=public_resolver)
    source, created = await service.add("HTTPS://Example.COM:443/leads#section")

    assert created is True
    assert source.url == "https://example.com/leads"
    assert source.enabled is True
    assert source.created_at is not None
    assert source.last_scanned_at is None
    assert await service.list_all() == [source]

    with pytest.raises(DuplicateLeadSourceError):
        await service.add("https://example.com/leads")

    removed = await service.remove(source.id)
    assert removed is source
    assert source.enabled is False

    restored, created = await service.add("https://example.com/leads")
    assert restored.id == source.id
    assert created is False
    assert restored.enabled is True


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/leads",
        "http://localhost/leads",
        "http://127.0.0.1/leads",
        "http://10.0.0.1/leads",
        "http://169.254.1.1/leads",
        "http://[::1]/leads",
        "https://example.com:0/leads",
        "https://user:password@example.com/leads",
    ],
)
async def test_rejects_non_public_source_urls(
    session: AsyncSession,
    url: str,
) -> None:
    with pytest.raises(InvalidLeadSourceURLError):
        await LeadSourceService(session, resolver=public_resolver).add(url)


async def test_rejects_hostname_that_resolves_to_private_ip(
    session: AsyncSession,
) -> None:
    with pytest.raises(InvalidLeadSourceURLError, match="public IP"):
        await LeadSourceService(session, resolver=private_resolver).add(
            "https://internal.example/leads"
        )


async def test_non_admin_cannot_add_source(session: AsyncSession) -> None:
    class Message:
        from_user = TelegramUser(
            id=9999,
            is_bot=False,
            first_name="User",
            language_code="en",
        )
        answer = AsyncMock()

    message = Message()
    await lead_source_add_command(
        message,  # type: ignore[arg-type]
        CommandObject(command="leadsource_add", args="https://example.com"),
        session,
        ADMIN_ID,
    )

    message.answer.assert_awaited_once_with(
        get_text("en", "admin_leadsource_unauthorized")
    )
    assert await LeadSourceService(session, resolver=public_resolver).list_all() == []
