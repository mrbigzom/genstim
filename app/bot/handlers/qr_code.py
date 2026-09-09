from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.credits import reject_if_insufficient
from app.bot.handlers.common import ensure_user
from app.bot.keyboards.payments import buy_credits_button
from app.bot.states import QrCodeStates
from app.credits.catalog import get_feature_credit_cost
from app.locales.messages import get_text
from app.providers.qr_code import QR_MAX_CHARACTERS, PillowQrCodeProvider, QrCodeProvider
from app.services.background_removal import InsufficientCreditsError
from app.services.local_generation import LocalGenerationFailedError, LocalGenerationService

router = Router(name="qr_code")


@router.callback_query(F.data == "feature:qr")
async def choose_qr_code(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await ensure_user(callback.from_user, session)
    await callback.answer()
    if await reject_if_insufficient(
        target=callback,
        state=state,
        language=user.language,
        balance=user.credits,
        feature="qr_designer",
    ):
        return
    await state.set_state(QrCodeStates.waiting_for_payload)
    if callback.message:
        await callback.message.answer(
            get_text(
                user.language,
                "qr_prompt",
                max_characters=QR_MAX_CHARACTERS,
                cost=get_feature_credit_cost("qr_designer"),
            )
        )


@router.message(QrCodeStates.waiting_for_payload, F.text)
async def process_qr_code(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    qr_code_provider: QrCodeProvider,
) -> None:
    if message.from_user is None or message.text is None:
        return
    user = await ensure_user(message.from_user, session)
    await message.answer(get_text(user.language, "qr_processing"))
    try:
        result = await LocalGenerationService(session).process(
            user_id=user.id,
            feature="qr_designer",
            operation=lambda: qr_code_provider.generate(message.text or ""),
        )
    except InsufficientCreditsError as exc:
        await state.clear()
        await message.answer(
            get_text(
                user.language,
                "credits_insufficient",
                balance=exc.balance,
                cost=exc.required,
            ),
            reply_markup=buy_credits_button(user.language),
        )
        return
    except LocalGenerationFailedError as exc:
        key = "qr_too_long" if exc.code == "input_too_long" else "qr_invalid"
        await message.answer(
            get_text(user.language, key, max_characters=QR_MAX_CHARACTERS)
        )
        return

    await message.answer_document(
        BufferedInputFile(result.content, filename="genstim-qr.png"),
        caption=get_text(user.language, "qr_success", credits=result.remaining_credits),
    )
    await state.clear()


def default_qr_code_provider() -> QrCodeProvider:
    return PillowQrCodeProvider()
