import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.common import ensure_user
from app.bot.keyboards.local_tools import passport_backgrounds, pixel_levels
from app.bot.states import PassportPhotoStates, PixelAvatarStates, StickerStates
from app.locales.messages import get_text
from app.providers.passport_photo import PASSPORT_BACKGROUNDS, PassportPhotoProvider
from app.providers.pixel_avatar import PIXEL_LEVELS, PixelAvatarProvider
from app.providers.sticker import StickerProvider
from app.services.background_removal import InsufficientCreditsError
from app.services.image_files import (
    SUPPORTED_IMAGE_TYPES,
    detect_image_content_type,
    temporary_work_directory,
)
from app.services.local_generation import LocalGenerationFailedError, LocalGenerationService

logger = logging.getLogger(__name__)
router = Router(name="local_images")

ImageOperation = Callable[[Path, str], Awaitable[bytes]]


@router.callback_query(F.data == "feature:pixel")
async def choose_pixel_avatar(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await ensure_user(callback.from_user, session)
    await callback.answer()
    if not await _has_credit(callback, state, user.language, user.credits):
        return
    await state.set_state(PixelAvatarStates.choosing_level)
    if callback.message:
        await callback.message.answer(
            get_text(user.language, "pixel_choose_level"),
            reply_markup=pixel_levels(user.language),
        )


@router.callback_query(
    PixelAvatarStates.choosing_level,
    F.data.startswith("pixel:level:"),
)
async def select_pixel_level(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    background_max_file_size: int,
) -> None:
    user = await ensure_user(callback.from_user, session)
    level = (callback.data or "").rsplit(":", maxsplit=1)[-1]
    if level not in PIXEL_LEVELS:
        await callback.answer(get_text(user.language, "local_invalid"), show_alert=True)
        return
    await callback.answer()
    await state.update_data(level=level)
    await state.set_state(PixelAvatarStates.waiting_for_image)
    if callback.message:
        await callback.message.answer(
            get_text(
                user.language,
                "pixel_image_prompt",
                max_mb=background_max_file_size // (1024 * 1024),
            )
        )


@router.callback_query(F.data == "feature:passport")
async def choose_passport_photo(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await ensure_user(callback.from_user, session)
    await callback.answer()
    if not await _has_credit(callback, state, user.language, user.credits):
        return
    await state.set_state(PassportPhotoStates.choosing_background)
    if callback.message:
        await callback.message.answer(
            get_text(user.language, "passport_choose_background"),
            reply_markup=passport_backgrounds(user.language),
        )


@router.callback_query(
    PassportPhotoStates.choosing_background,
    F.data.startswith("passport:background:"),
)
async def select_passport_background(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    background_max_file_size: int,
) -> None:
    user = await ensure_user(callback.from_user, session)
    background = (callback.data or "").rsplit(":", maxsplit=1)[-1]
    if background not in PASSPORT_BACKGROUNDS:
        await callback.answer(get_text(user.language, "local_invalid"), show_alert=True)
        return
    await callback.answer()
    await state.update_data(background=background)
    await state.set_state(PassportPhotoStates.waiting_for_image)
    if callback.message:
        await callback.message.answer(
            get_text(
                user.language,
                "passport_image_prompt",
                max_mb=background_max_file_size // (1024 * 1024),
            )
        )


@router.callback_query(F.data == "feature:stickers")
async def choose_sticker(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    background_max_file_size: int,
) -> None:
    user = await ensure_user(callback.from_user, session)
    await callback.answer()
    if not await _has_credit(callback, state, user.language, user.credits):
        return
    await state.set_state(StickerStates.waiting_for_image)
    if callback.message:
        await callback.message.answer(
            get_text(
                user.language,
                "sticker_image_prompt",
                max_mb=background_max_file_size // (1024 * 1024),
            )
        )


@router.message(PixelAvatarStates.waiting_for_image, F.photo | F.document)
async def process_pixel_avatar(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    pixel_avatar_provider: PixelAvatarProvider,
    background_max_file_size: int,
    background_max_pixels: int,
) -> None:
    data = await state.get_data()
    level = str(data.get("level", ""))
    await _process_image(
        message=message,
        session=session,
        state=state,
        bot=bot,
        operation=lambda path, content_type: pixel_avatar_provider.pixelate(
            path, content_type, level
        ),
        feature="pixel_avatar",
        filename="genstim-pixel-avatar.png",
        processing_key="pixel_processing",
        success_key="pixel_success",
        max_file_size=background_max_file_size,
        max_pixels=background_max_pixels,
    )


@router.message(PassportPhotoStates.waiting_for_image, F.photo | F.document)
async def process_passport_photo(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    passport_photo_provider: PassportPhotoProvider,
    background_max_file_size: int,
    background_max_pixels: int,
) -> None:
    data = await state.get_data()
    background = str(data.get("background", ""))
    await _process_image(
        message=message,
        session=session,
        state=state,
        bot=bot,
        operation=lambda path, content_type: passport_photo_provider.create(
            path, content_type, background
        ),
        feature="passport_photo",
        filename="genstim-passport-photo.png",
        processing_key="passport_processing",
        success_key="passport_success",
        max_file_size=background_max_file_size,
        max_pixels=background_max_pixels,
    )


@router.message(StickerStates.waiting_for_image, F.photo | F.document)
async def process_sticker(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    sticker_provider: StickerProvider,
    background_max_file_size: int,
    background_max_pixels: int,
) -> None:
    await _process_image(
        message=message,
        session=session,
        state=state,
        bot=bot,
        operation=sticker_provider.create,
        feature="sticker",
        filename="genstim-sticker.webp",
        processing_key="sticker_processing",
        success_key="sticker_success",
        max_file_size=background_max_file_size,
        max_pixels=background_max_pixels,
    )


async def _has_credit(
    callback: CallbackQuery,
    state: FSMContext,
    language: str,
    credits: int,
) -> bool:
    if credits >= 1:
        return True
    await state.clear()
    if callback.message:
        await callback.message.answer(get_text(language, "local_insufficient"))
    return False


async def _process_image(
    *,
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    operation: ImageOperation,
    feature: str,
    filename: str,
    processing_key: str,
    success_key: str,
    max_file_size: int,
    max_pixels: int,
) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    upload = _get_image_upload(message)
    if upload is None:
        await message.answer(get_text(user.language, "local_unsupported_format"))
        return
    file_id, declared_content_type, file_size = upload
    if file_size is not None and file_size > max_file_size:
        await message.answer(
            get_text(user.language, "local_too_large", max_mb=max_file_size // (1024 * 1024))
        )
        return

    await message.answer(get_text(user.language, processing_key))
    try:
        with temporary_work_directory() as work_directory:
            image_path = work_directory / "input"
            await bot.download(file_id, destination=image_path)
            if image_path.stat().st_size > max_file_size:
                await message.answer(
                    get_text(
                        user.language,
                        "local_too_large",
                        max_mb=max_file_size // (1024 * 1024),
                    )
                )
                return
            content_type = await asyncio.to_thread(_validated_content_type, image_path)
            if content_type is None or not _content_types_compatible(
                declared_content_type, content_type
            ):
                await message.answer(get_text(user.language, "local_unsupported_format"))
                return
            result = await LocalGenerationService(session).process(
                user_id=user.id,
                feature=feature,
                operation=lambda: operation(image_path, content_type),
            )
            await message.answer_document(
                BufferedInputFile(result.content, filename=filename),
                caption=get_text(
                    user.language,
                    success_key,
                    credits=result.remaining_credits,
                ),
            )
    except InsufficientCreditsError:
        await state.clear()
        await message.answer(get_text(user.language, "local_insufficient"))
        return
    except LocalGenerationFailedError as exc:
        key = {
            "provider_timeout": "local_timeout",
            "unsupported_format": "local_unsupported_format",
            "invalid_image": "local_corrupted_image",
            "image_too_large": "local_dimensions_too_large",
            "output_too_large": "sticker_output_too_large",
        }.get(exc.code, "local_processing_error")
        await message.answer(
            get_text(
                user.language,
                key,
                max_megapixels=max_pixels // 1_000_000,
            )
        )
        return
    except Exception as exc:
        logger.error(
            "Failed to download or deliver local image user_id=%s feature=%s error_type=%s",
            user.id,
            feature,
            type(exc).__name__,
        )
        await message.answer(get_text(user.language, "local_transfer_error"))
        return
    await state.clear()


def _get_image_upload(message: Message) -> tuple[str, str, int | None] | None:
    if message.photo:
        photo = message.photo[-1]
        return photo.file_id, "image/jpeg", photo.file_size
    document = message.document
    if document is None or document.mime_type not in SUPPORTED_IMAGE_TYPES:
        return None
    return document.file_id, document.mime_type, document.file_size


def _validated_content_type(image_path: Path) -> str | None:
    with image_path.open("rb") as image_file:
        return detect_image_content_type(image_file.read(16))


def _content_types_compatible(declared: str, detected: str) -> bool:
    return declared == detected or {declared, detected} <= {"image/heic", "image/heif"}
