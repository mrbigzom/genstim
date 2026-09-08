import asyncio
import logging
from io import BytesIO
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.utils import ensure_user
from app.bot.keyboards.background import background_navigation
from app.bot.keyboards.create import create_menu
from app.locales.messages import get_text
from app.services.background import (
    MAX_IMAGE_BYTES,
    BackgroundProcessingError,
    BackgroundRemovalService,
    ImageTooLargeError,
    InvalidImageError,
)

logger = logging.getLogger(__name__)
router = Router(name="background_removal")
background_service = BackgroundRemovalService()

SUPPORTED_DOCUMENT_MIME_TYPES = frozenset({"image/jpeg", "image/png"})
SUPPORTED_DOCUMENT_SUFFIXES = frozenset({".jpeg", ".jpg", ".png"})


class BackgroundRemovalStates(StatesGroup):
    waiting_for_image = State()


def _document_is_supported(message: Message) -> bool:
    document = message.document
    if document is None:
        return False
    suffix = Path(document.file_name or "").suffix.lower()
    return (
        document.mime_type in SUPPORTED_DOCUMENT_MIME_TYPES
        or suffix in SUPPORTED_DOCUMENT_SUFFIXES
    )


def _image_download(message: Message) -> tuple[str, int | None] | None:
    if message.photo:
        photo = message.photo[-1]
        return photo.file_id, photo.file_size
    if _document_is_supported(message) and message.document:
        return message.document.file_id, message.document.file_size
    return None


@router.callback_query(F.data == "feature:background")
async def start_background_removal(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await ensure_user(callback.from_user, session)
    await state.clear()
    await state.set_state(BackgroundRemovalStates.waiting_for_image)
    await state.update_data(background_language=user.language)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            get_text(user.language, "background_send_image"),
            reply_markup=background_navigation(user.language),
        )


@router.message(BackgroundRemovalStates.waiting_for_image, Command("cancel"))
async def cancel_background_command(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    language = str(data.get("background_language", "en"))
    await state.clear()
    await message.answer(get_text(language, "background_cancelled"))


@router.message(BackgroundRemovalStates.waiting_for_image)
async def receive_background_image(message: Message, bot: Bot, state: FSMContext) -> None:
    data = await state.get_data()
    language = str(data.get("background_language", "en"))
    downloadable = _image_download(message)
    if downloadable is None:
        await message.answer(
            get_text(language, "background_invalid_image"),
            reply_markup=background_navigation(language),
        )
        return

    file_id, file_size = downloadable
    if file_size is not None and file_size > MAX_IMAGE_BYTES:
        await message.answer(
            get_text(language, "background_too_large"),
            reply_markup=background_navigation(language),
        )
        return

    await message.answer(get_text(language, "background_processing"))
    source = BytesIO()
    try:
        await bot.download(file_id, destination=source)
        result = await asyncio.to_thread(background_service.remove_background, source.getvalue())
    except ImageTooLargeError:
        await message.answer(
            get_text(language, "background_too_large"),
            reply_markup=background_navigation(language),
        )
        return
    except InvalidImageError:
        await message.answer(
            get_text(language, "background_invalid_image"),
            reply_markup=background_navigation(language),
        )
        return
    except BackgroundProcessingError:
        logger.exception("Local background removal failed")
        await message.answer(
            get_text(language, "background_failed"),
            reply_markup=background_navigation(language),
        )
        return
    except Exception:
        logger.exception("Background image download failed")
        await message.answer(
            get_text(language, "background_failed"),
            reply_markup=background_navigation(language),
        )
        return

    await state.clear()
    await message.answer_document(
        BufferedInputFile(result, filename="genstim-no-background.png"),
        caption=get_text(language, "background_ready"),
    )


async def _finish_background_flow(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    back: bool,
) -> None:
    data = await state.get_data()
    language = str(data.get("background_language", "en"))
    await state.clear()
    await callback.answer()
    if callback.message:
        if back:
            await callback.message.answer(
                get_text(language, "create"),
                reply_markup=create_menu(language),
            )
        else:
            await callback.message.answer(get_text(language, "background_cancelled"))


@router.callback_query(F.data == "background:back")
async def back_from_background(callback: CallbackQuery, state: FSMContext) -> None:
    await _finish_background_flow(callback, state, back=True)


@router.callback_query(F.data == "background:cancel")
async def cancel_background(callback: CallbackQuery, state: FSMContext) -> None:
    await _finish_background_flow(callback, state, back=False)
