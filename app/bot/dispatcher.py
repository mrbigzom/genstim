from aiogram import Dispatcher
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.handlers import router
from app.bot.middlewares import DatabaseSessionMiddleware
from app.providers.background_removal import BackgroundRemovalProvider
from app.providers.meme import MemeProvider
from app.providers.passport_photo import PassportPhotoProvider
from app.providers.pixel_avatar import PixelAvatarProvider
from app.providers.qr_code import QrCodeProvider
from app.providers.sticker import StickerProvider


def create_dispatcher(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    background_removal_provider: BackgroundRemovalProvider,
    qr_code_provider: QrCodeProvider,
    meme_provider: MemeProvider,
    pixel_avatar_provider: PixelAvatarProvider,
    passport_photo_provider: PassportPhotoProvider,
    sticker_provider: StickerProvider,
    background_max_file_size: int,
    background_max_pixels: int,
) -> Dispatcher:
    dispatcher = Dispatcher(
        background_removal_provider=background_removal_provider,
        qr_code_provider=qr_code_provider,
        meme_provider=meme_provider,
        pixel_avatar_provider=pixel_avatar_provider,
        passport_photo_provider=passport_photo_provider,
        sticker_provider=sticker_provider,
        background_max_file_size=background_max_file_size,
        background_max_pixels=background_max_pixels,
    )
    dispatcher.update.middleware(DatabaseSessionMiddleware(session_factory))
    dispatcher.include_router(router)
    return dispatcher
