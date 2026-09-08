import asyncio
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import ensure_user
from app.bot.keyboards.qr import qr_size_menu, qr_style_menu
from app.locales.messages import get_text
from app.services.qr import (
    ALLOWED_QR_SIZES,
    ALLOWED_QR_STYLES,
    QRCodeInputError,
    generate_qr_png,
    normalize_qr_content,
)

logger = logging.getLogger(__name__)
router = Router(name="qr_designer")


class QRDesignerStates(StatesGroup):
    waiting_for_content = State()
    waiting_for_size = State()
    waiting_for_style = State()


@router.callback_query(F.data == "feature:qr")
async def start_qr_designer(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await ensure_user(callback.from_user, session)
    await state.clear()
    await state.set_state(QRDesignerStates.waiting_for_content)
    await state.update_data(qr_language=user.language)
    await callback.answer()
    if callback.message:
        await callback.message.answer(get_text(user.language, "qr_enter_content"))


@router.message(QRDesignerStates.waiting_for_content)
async def receive_qr_content(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    language = str(data.get("qr_language", "en"))
    try:
        content = normalize_qr_content(message.text or "")
    except QRCodeInputError:
        await message.answer(get_text(language, "qr_invalid_content"))
        return

    await state.update_data(qr_content=content)
    await state.set_state(QRDesignerStates.waiting_for_size)
    await message.answer(
        get_text(language, "qr_choose_size"),
        reply_markup=qr_size_menu(language),
    )


@router.callback_query(QRDesignerStates.waiting_for_size, F.data.startswith("qr:size:"))
async def receive_qr_size(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    language = str(data.get("qr_language", "en"))
    try:
        size = int((callback.data or "").rsplit(":", maxsplit=1)[1])
    except (IndexError, ValueError):
        size = 0
    if size not in ALLOWED_QR_SIZES:
        await callback.answer(get_text(language, "qr_invalid_option"), show_alert=True)
        return

    await state.update_data(qr_size=size)
    await state.set_state(QRDesignerStates.waiting_for_style)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            get_text(language, "qr_choose_style"),
            reply_markup=qr_style_menu(language),
        )


@router.callback_query(QRDesignerStates.waiting_for_style, F.data.startswith("qr:style:"))
async def receive_qr_style(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    language = str(data.get("qr_language", "en"))
    style = (callback.data or "").rsplit(":", maxsplit=1)[-1]
    if style not in ALLOWED_QR_STYLES:
        await callback.answer(get_text(language, "qr_invalid_option"), show_alert=True)
        return
    await callback.answer()

    try:
        image = await asyncio.to_thread(
            generate_qr_png,
            str(data.get("qr_content", "")),
            size=int(data.get("qr_size", 0)),
            style=style,
        )
    except (TypeError, ValueError, QRCodeInputError):
        logger.exception("QR Designer failed to generate an image")
        if callback.message:
            await callback.message.answer(get_text(language, "qr_generation_failed"))
        return

    await state.clear()
    if callback.message:
        await callback.message.answer_document(
            BufferedInputFile(image, filename="genstim-qr.png"),
            caption=get_text(language, "qr_ready"),
        )


@router.callback_query(F.data == "qr:cancel")
async def cancel_qr_designer(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    language = str(data.get("qr_language", "en"))
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer(get_text(language, "qr_cancelled"))
