import asyncio
import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.common import ensure_user
from app.bot.payments import PAYMENT_ID_STATE_KEY, check_feature_access
from app.bot.states import BackgroundRemovalStates
from app.locales.messages import get_text
from app.providers.background_removal import BackgroundRemovalProvider
from app.services.background_removal import (
    BackgroundRemovalFailedError,
    BackgroundRemovalService,
    InsufficientCreditsError,
)
from app.services.image_files import (
    SUPPORTED_IMAGE_TYPES,
    detect_image_content_type,
    temporary_work_directory,
)
from app.services.payment import PaymentNotAuthorizedError

logger = logging.getLogger(__name__)
router = Router(name="background_removal")


@router.callback_query(F.data == "feature:background")
async def choose_background_removal(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    background_max_file_size: int,
) -> None:
    user = await ensure_user(callback.from_user, session)
    await callback.answer()
    access = await check_feature_access(
        callback=callback,
        session=session,
        state=state,
        user_id=user.id,
        language=user.language,
        product_id="background_removal",
    )
    if access.blocked:
        return
    if access.payment_id is None and user.credits < 1:
        await state.clear()
        if callback.message:
            await callback.message.answer(get_text(user.language, "background_insufficient"))
        return

    await state.set_state(BackgroundRemovalStates.waiting_for_image)
    if callback.message:
        await callback.message.answer(
            get_text(
                user.language,
                "background_prompt",
                max_mb=background_max_file_size // (1024 * 1024),
            )
        )


@router.message(BackgroundRemovalStates.waiting_for_image, F.photo | F.document)
async def process_background_image(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    background_removal_provider: BackgroundRemovalProvider,
    background_max_file_size: int,
    background_max_pixels: int,
) -> None:
    if message.from_user is None:
        return
    user = await ensure_user(message.from_user, session)
    state_data = await state.get_data()
    payment_id_value = state_data.get(PAYMENT_ID_STATE_KEY)
    payment_id = int(payment_id_value) if payment_id_value is not None else None
    upload = _get_image_upload(message)
    if upload is None:
        await message.answer(get_text(user.language, "background_unsupported_format"))
        return

    file_id, declared_content_type, file_size = upload
    if file_size is not None and file_size > background_max_file_size:
        await message.answer(
            get_text(
                user.language,
                "background_too_large",
                max_mb=background_max_file_size // (1024 * 1024),
            )
        )
        return

    await message.answer(get_text(user.language, "background_processing"))
    try:
        with temporary_work_directory() as work_directory:
            image_path = work_directory / "input"
            await bot.download(file_id, destination=image_path)

            if image_path.stat().st_size > background_max_file_size:
                await message.answer(
                    get_text(
                        user.language,
                        "background_too_large",
                        max_mb=background_max_file_size // (1024 * 1024),
                    )
                )
                return

            content_type = await asyncio.to_thread(_validated_content_type, image_path)
            if content_type is None or not _content_types_compatible(
                declared_content_type,
                content_type,
            ):
                await message.answer(get_text(user.language, "background_unsupported_format"))
                return

            result = await BackgroundRemovalService(
                session,
                background_removal_provider,
            ).process(
                user_id=user.id,
                image_path=image_path,
                content_type=content_type,
                payment_id=payment_id,
                telegram_user_id=user.telegram_id,
            )
            await message.answer_document(
                BufferedInputFile(
                    result.image,
                    filename="genstim-background-removed.png",
                ),
                caption=get_text(
                    user.language,
                    "background_success",
                    credits=result.remaining_credits,
                ),
            )
    except InsufficientCreditsError:
        await state.clear()
        await message.answer(get_text(user.language, "background_insufficient"))
        return
    except PaymentNotAuthorizedError:
        await state.clear()
        await message.answer(get_text(user.language, "payment_required"))
        return
    except BackgroundRemovalFailedError as exc:
        message_key = {
            "provider_timeout": "background_timeout",
            "unsupported_format": "background_unsupported_format",
            "invalid_image": "background_corrupted_image",
            "image_too_large": "background_dimensions_too_large",
        }.get(exc.code, "background_provider_error")
        await message.answer(
            get_text(
                user.language,
                message_key,
                max_megapixels=background_max_pixels // 1_000_000,
            )
        )
        return
    except Exception as exc:
        logger.error(
            "Failed to download or deliver background removal image user_id=%s error_type=%s",
            user.id,
            type(exc).__name__,
        )
        await message.answer(get_text(user.language, "background_transfer_error"))
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
