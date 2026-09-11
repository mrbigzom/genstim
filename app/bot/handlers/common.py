import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ErrorEvent, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import ensure_user
from app.bot.keyboards.create import create_menu
from app.bot.keyboards.language import language_menu
from app.bot.keyboards.main import button_texts, main_menu
from app.bot.keyboards.payments import credit_packages
from app.bot.states import (
    BackgroundRemovalStates,
    MemeStates,
    PassportPhotoStates,
    PixelAvatarStates,
    QrCodeStates,
    StickerStates,
)
from app.locales.messages import get_text
from app.services.generation import GenerationService
from app.services.user import UserService

logger = logging.getLogger(__name__)
router = Router(name="common")
navigation_router = Router(name="navigation")

PRIVACY_URL = "https://github.com/mrbigzom/genstim/blob/main/PRIVACY.md"
TERMS_URL = "https://github.com/mrbigzom/genstim/blob/main/TERMS.md"


def referral_from_start(command: CommandObject) -> str | None:
    if command.args and command.args.startswith("ref_"):
        return command.args.removeprefix("ref_") or None
    return None


@router.message(CommandStart())
async def start(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return
    user, created = await UserService(session).get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        telegram_language=message.from_user.language_code,
        referral_code=referral_from_start(command),
    )
    await state.clear()
    key = "welcome" if created else "welcome_back"
    await message.answer(get_text(user.language, key), reply_markup=main_menu(user.language))


@router.message(Command("help"))
@router.message(F.text.in_(button_texts("help")))
async def help_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    await message.answer(get_text(user.language, "help"), reply_markup=main_menu(user.language))


@navigation_router.message(Command("create"))
@navigation_router.message(F.text.in_(button_texts("create")))
async def create_command(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    await state.clear()
    await message.answer(get_text(user.language, "create"), reply_markup=create_menu(user.language))


@router.message(Command("tools"))
@router.message(F.text.in_(button_texts("tools")))
async def tools_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    await message.answer(get_text(user.language, "tools"), reply_markup=create_menu(user.language))


@router.callback_query(
    F.data.startswith("feature:")
    & (F.data != "feature:qr")
    & (F.data != "feature:background")
)
async def feature_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await ensure_user(callback.from_user, session)
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer(get_text(user.language, "feature_pending"))


@router.message(Command("credits"))
@router.message(F.text.in_(button_texts("credits")))
async def credits_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    await message.answer(
        get_text(user.language, "credits_store", credits=user.credits),
        reply_markup=credit_packages(user.language),
    )


@router.message(Command("history"))
@router.message(F.text.in_(button_texts("history")))
async def history_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    generations = await GenerationService(session).completed_history(user.id)
    if not generations:
        await message.answer(get_text(user.language, "history_empty"))
        return

    items = []
    for index, generation in enumerate(generations, start=1):
        completed_at = generation.completed_at or generation.created_at
        items.append(
            get_text(
                user.language,
                "history_item",
                index=index,
                feature=get_text(user.language, f"feature_{generation.feature}"),
                credits=generation.credits_spent,
                date=completed_at.strftime("%Y-%m-%d %H:%M UTC"),
            )
        )
    await message.answer(
        get_text(user.language, "history_header", items="\n\n".join(items))
    )


@router.message(Command("invite"))
@router.message(F.text.in_(button_texts("invite")))
async def invite_command(message: Message, session: AsyncSession, bot: Bot) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    bot_user = await bot.get_me()
    link = f"https://t.me/{bot_user.username}?start=ref_{user.referral_code}"
    await message.answer(get_text(user.language, "invite", link=link))


@router.message(Command("language"))
@router.message(F.text.in_(button_texts("language")))
async def language_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    await message.answer(get_text(user.language, "language"), reply_markup=language_menu())


@router.callback_query(F.data.in_({"language:en", "language:ru"}))
async def language_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    language = callback.data.split(":", maxsplit=1)[1] if callback.data else "en"
    user = await ensure_user(callback.from_user, session)
    await UserService(session).set_language(user, language)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            get_text(language, "language_changed"),
            reply_markup=main_menu(language),
        )


@router.message(Command("support"))
async def support_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    await message.answer(get_text(user.language, "support"))


@router.message(Command("paysupport"))
async def payment_support_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    await message.answer(get_text(user.language, "paysupport"))


@router.message(Command("terms"))
async def terms_command(message: Message) -> None:
    await message.answer(TERMS_URL)


@router.message(Command("privacy"))
async def privacy_command(message: Message) -> None:
    await message.answer(PRIVACY_URL)


@router.message()
async def unknown_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    if await state.get_state() == BackgroundRemovalStates.waiting_for_image.state:
        await message.answer(get_text(user.language, "background_only_images"))
        return
    current_state = await state.get_state()
    if current_state in {
        PixelAvatarStates.waiting_for_image.state,
        PassportPhotoStates.waiting_for_image.state,
        StickerStates.waiting_for_image.state,
    }:
        await message.answer(get_text(user.language, "local_only_images"))
        return
    if current_state == QrCodeStates.waiting_for_payload.state:
        await message.answer(get_text(user.language, "qr_only_text"))
        return
    if current_state in {
        MemeStates.waiting_for_top_text.state,
        MemeStates.waiting_for_bottom_text.state,
    }:
        await message.answer(get_text(user.language, "meme_only_text"))
        return
    await message.answer(get_text(user.language, "unknown"), reply_markup=main_menu(user.language))


@router.error()
async def error_handler(event: ErrorEvent) -> bool:
    exception = event.exception
    logger.error(
        "Unhandled error while processing Telegram update",
        exc_info=(type(exception), exception, exception.__traceback__),
    )
    message = event.update.message
    if message is not None:
        await message.answer(get_text("en", "error"))
    return True
