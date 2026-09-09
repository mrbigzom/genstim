from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.common import ensure_user
from app.bot.payments import PAYMENT_ID_STATE_KEY, check_feature_access
from app.bot.states import QrCodeStates
from app.locales.messages import get_text
from app.providers.qr_code import QR_MAX_CHARACTERS, PillowQrCodeProvider, QrCodeProvider
from app.services.background_removal import InsufficientCreditsError
from app.services.local_generation import LocalGenerationFailedError, LocalGenerationService
from app.services.payment import PaymentNotAuthorizedError

router = Router(name="qr_code")


@router.callback_query(F.data == "feature:qr")
async def choose_qr_code(
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
        product_id="qr_designer",
    )
    if access.blocked:
        return
    if access.payment_id is None and user.credits < 1:
        await state.clear()
        if callback.message:
            await callback.message.answer(get_text(user.language, "local_insufficient"))
        return
    await state.set_state(QrCodeStates.waiting_for_payload)
    if callback.message:
        await callback.message.answer(
            get_text(user.language, "qr_prompt", max_characters=QR_MAX_CHARACTERS)
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
    data = await state.get_data()
    payment_id_value = data.get(PAYMENT_ID_STATE_KEY)
    payment_id = int(payment_id_value) if payment_id_value is not None else None
    await message.answer(get_text(user.language, "qr_processing"))
    try:
        result = await LocalGenerationService(session).process(
            user_id=user.id,
            feature="qr_designer",
            operation=lambda: qr_code_provider.generate(message.text or ""),
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
