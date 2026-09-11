from unittest.mock import AsyncMock

import pytest
from aiogram.filters import CommandObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.admin import lead_status_command, leads_command
from app.lead_finder.extractors import extract_public_page
from app.lead_finder.service import LeadFinderService
from app.lead_finder.types import LeadCandidate
from app.locales.messages import get_text

ADMIN_ID = 9001


class FakeMessage:
    def __init__(self, telegram_id: int = ADMIN_ID, *, language_code: str = "en") -> None:
        self.from_user = TelegramUser(
            id=telegram_id,
            is_bot=False,
            first_name="Admin",
            language_code=language_code,
        )
        self.answer = AsyncMock()


def command(name: str, args: str = "") -> CommandObject:
    return CommandObject(command=name, args=args)


def candidate(*, url: str = "https://example.com/lead", score: int = 80) -> LeadCandidate:
    return LeadCandidate(
        name="Example Studio",
        source="website",
        url=url,
        niche="designers",
        contact="hello@example.com",
        reason_fit="design services available",
        score=score,
    )


async def test_public_page_extractor_finds_contact_and_scores_business_signals() -> None:
    result = extract_public_page(
        html=(
            "<html><head><title>Design Studio</title></head><body>"
            "Graphic design portfolio. <a href='mailto:hello@example.com'>Email</a>"
            "</body></html>"
        ),
        url="https://example.com",
        niche="designers",
    )

    assert result.name == "Design Studio"
    assert result.contact == "hello@example.com"
    assert result.score > 50
    assert "design" in result.reason_fit


async def test_service_deduplicates_and_updates_status(session: AsyncSession) -> None:
    service = LeadFinderService(session)

    lead, created = await service.save_candidate(candidate())
    same_lead, duplicate = await service.save_candidate(
        candidate(score=95)
    )

    assert created is True
    assert duplicate is False
    assert same_lead.id == lead.id
    assert same_lead.score == 95

    updated = await service.set_status(lead_id=lead.id, status="contacted")
    assert updated is lead
    assert updated.status == "contacted"
    assert "Designers" in service.draft_message(lead, "en")


async def test_service_rejects_invalid_candidate(session: AsyncSession) -> None:
    invalid = candidate(score=101)

    with pytest.raises(ValueError, match="score"):
        await LeadFinderService(session).save_candidate(invalid)


async def test_admin_can_list_and_update_leads(session: AsyncSession) -> None:
    service = LeadFinderService(session)
    lead, _ = await service.save_candidate(candidate())
    message = FakeMessage()

    await leads_command(message, command("leads"), session, ADMIN_ID)

    listing = message.answer.await_args.args[0]
    assert "Example Studio" in listing
    assert str(lead.id) in listing
    assert "Designers" in listing

    message.answer.reset_mock()
    await lead_status_command(
        message,
        command("leadstatus", f"{lead.id} contacted"),
        session,
        ADMIN_ID,
    )

    assert lead.status == "contacted"
    message.answer.assert_awaited_once_with(
        get_text("en", "admin_lead_status_updated", lead_id=lead.id, status="contacted")
    )


async def test_non_admin_cannot_list_leads(session: AsyncSession) -> None:
    message = FakeMessage(telegram_id=9999)

    await leads_command(message, command("leads"), session, ADMIN_ID)

    message.answer.assert_awaited_once_with(
        get_text("en", "admin_leads_unauthorized")
    )
