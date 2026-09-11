from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import ensure_user
from app.lead_finder import NICHE_LABELS, NICHES
from app.lead_finder.service import LEAD_STATUSES, LeadFinderService
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

@router.message(Command("leads"))
async def leads_command(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    admin_telegram_id: int | None,
) -> None:
    if message.from_user is None:
        return

    fallback_language = detect_language(message.from_user.language_code)
    if admin_telegram_id is None or message.from_user.id != admin_telegram_id:
        await message.answer(get_text(fallback_language, "admin_leads_unauthorized"))
        return

    admin = await ensure_user(message.from_user, session)
    niche = (command.args or "").strip() or None
    if niche is not None and niche not in NICHES:
        await message.answer(
            get_text(
                admin.language,
                "admin_leads_usage",
                niches=", ".join(NICHES),
            )
        )
        return

    leads = await LeadFinderService(session).best_new(niche=niche)
    if not leads:
        await message.answer(get_text(admin.language, "admin_leads_empty"))
        return

    items = []
    for index, lead in enumerate(leads, start=1):
        items.append(
            get_text(
                admin.language,
                "admin_lead_item",
                index=index,
                lead_id=lead.id,
                name=lead.name,
                niche=NICHE_LABELS[lead.niche].get(admin.language, lead.niche),
                score=lead.score,
                contact=lead.contact or "-",
                url=lead.url,
                reason=lead.reason_fit,
                draft=LeadFinderService.draft_message(lead, admin.language),
            )
        )
    await message.answer(
        get_text(admin.language, "admin_leads_header", items="\n\n".join(items))
    )


@router.message(Command("leadstatus"))
async def lead_status_command(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    admin_telegram_id: int | None,
) -> None:
    if message.from_user is None:
        return

    fallback_language = detect_language(message.from_user.language_code)
    if admin_telegram_id is None or message.from_user.id != admin_telegram_id:
        await message.answer(get_text(fallback_language, "admin_leads_unauthorized"))
        return

    admin = await ensure_user(message.from_user, session)
    parts = (command.args or "").split()
    if len(parts) != 2 or parts[1] not in LEAD_STATUSES:
        await message.answer(
            get_text(
                admin.language,
                "admin_lead_status_usage",
                statuses=", ".join(LEAD_STATUSES),
            )
        )
        return
    try:
        lead_id = int(parts[0])
    except ValueError:
        await message.answer(
            get_text(
                admin.language,
                "admin_lead_status_usage",
                statuses=", ".join(LEAD_STATUSES),
            )
        )
        return

    lead = await LeadFinderService(session).set_status(
        lead_id=lead_id,
        status=parts[1],
    )
    if lead is None:
        await message.answer(
            get_text(admin.language, "admin_lead_not_found", lead_id=lead_id)
        )
        return
    await message.answer(
        get_text(
            admin.language,
            "admin_lead_status_updated",
            lead_id=lead.id,
            status=lead.status,
        )
    )
