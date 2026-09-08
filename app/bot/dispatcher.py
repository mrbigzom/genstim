from aiogram import Dispatcher
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.handlers import router
from app.bot.middlewares import DatabaseSessionMiddleware
from app.providers.background_removal import BackgroundRemovalProvider


def create_dispatcher(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    background_removal_provider: BackgroundRemovalProvider,
    background_max_file_size: int,
) -> Dispatcher:
    dispatcher = Dispatcher(
        background_removal_provider=background_removal_provider,
        background_max_file_size=background_max_file_size,
    )
    dispatcher.update.middleware(DatabaseSessionMiddleware(session_factory))
    dispatcher.include_router(router)
    return dispatcher
