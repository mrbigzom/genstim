from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.common import ensure_user
from app.bot.keyboards.local_tools import meme_templates
from app.bot.payments import PAYMENT_ID_STATE_KEY, check_feature_access
from app.bot.states import MemeStates
from app.locales.messages import get_text
from app.providers.meme import MEME_MAX_TEXT_LENGTH, MemeProvider
from app.services.background_removal import InsufficientCreditsError
from app.services.local_generation import LocalGenerationFailedError, LocalGenerationService
from app.services.payment import PaymentNotAuthorizedError

router = Router(name="meme")


@router.callback_query(F.data == "feature:memes")
async def choose_meme(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await ensure_user(callback.from_user, session)
    await callback.answer()
    access = await check_feature_access(
        callback=callback,
        session=session,
        state=state,
        user_id=user.id,
        language=user.language,
        product_id="meme_generator",
    )
    if access.blocked:
        return
    if access.payment_id is None and user.credits < 1:
        await state.clear()
        if callback.message:
            await callback.message.answer(get_text(user.language, "local_insufficient"))
        return
    await state.set_state(MemeStates.choosing_template)
    if callback.message:
        await callback.message.answer(
            get_text(user.language, "meme_choose_template"),
            reply_markup=meme_templates(user.language),
        )


@router.callback_query(MemeStates.choosing_template, F.data.startswith("meme:template:"))
async def select_meme_template(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await ensure_user(callback.from_user, session)
    template = (callback.data or "").rsplit(":", maxsplit=1)[-1]
    if template not in {"classic", "breaking", "choice"}:
        await callback.answer(get_text(user.language, "local_invalid"), show_alert=True)
        return
    await callback.answer()
    await state.update_data(template=template)
    await state.set_state(MemeStates.waiting_for_top_text)
    if callback.message:
        await callback.message.answer(
            get_text(user.language, "meme_top_prompt", max_characters=MEME_MAX_TEXT_LENGTH)
        )


@router.message(MemeStates.waiting_for_top_text, F.text)
async def receive_meme_top(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None or message.text is None:
        return
    user = await ensure_user(message.from_user, session)
    if len(message.text) > MEME_MAX_TEXT_LENGTH:
        await message.answer(
            get_text(user.language, "meme_text_too_long", max_characters=MEME_MAX_TEXT_LENGTH)
        )
        return
    await state.update_data(top_text="" if message.text.strip() == "-" else message.text)
    await state.set_state(MemeStates.waiting_for_bottom_text)
    await message.answer(
        get_text(user.language, "meme_bottom_prompt", max_characters=MEME_MAX_TEXT_LENGTH)
    )


@router.message(MemeStates.waiting_for_bottom_text, F.text)
async def receive_meme_bottom(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    meme_provider: MemeProvider,
) -> None:
    if message.from_user is None or message.text is None:
        return
    user = await ensure_user(message.from_user, session)
    if len(message.text) > MEME_MAX_TEXT_LENGTH:
        await message.answer(
            get_text(user.language, "meme_text_too_long", max_characters=MEME_MAX_TEXT_LENGTH)
        )
        return
    data = await state.get_data()
    payment_id_value = data.get(PAYMENT_ID_STATE_KEY)
    payment_id = int(payment_id_value) if payment_id_value is not None else None
    template = str(data.get("template", ""))
    top_text = str(data.get("top_text", ""))
    bottom_text = "" if message.text.strip() == "-" else message.text
    await message.answer(get_text(user.language, "meme_processing"))
    try:
        result = await LocalGenerationService(session).process(
            user_id=user.id,
            feature="meme_generator",
            operation=lambda: meme_provider.generate(template, top_text, bottom_text),
            payment_id=payment_id,
            telegram_user_id=user.telegram_id,
        )
    except InsufficientCreditsError:
        await state.clear()
        await message.answer(get_text(user.language, "local_insufficient"))
        return
    except PaymentNotAuthorizedError:
        await state.clear()
        await message.answer(get_text(user.language, "payment_required"))
        return
    except LocalGenerationFailedError as exc:
        key = "meme_text_too_long" if exc.code == "input_too_long" else "local_processing_error"
        await message.answer(
            get_text(user.language, key, max_characters=MEME_MAX_TEXT_LENGTH)
        )
        return
    await message.answer_document(
        BufferedInputFile(result.content, filename="genstim-meme.png"),
        caption=get_text(user.language, "meme_success", credits=result.remaining_credits),
    )
    await state.clear()
