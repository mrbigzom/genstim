from aiogram import Dispatcher
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.handlers import router
from app.bot.middlewares import DatabaseSessionMiddleware


def create_dispatcher(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.update.middleware(DatabaseSessionMiddleware(session_factory))
    dispatcher.include_router(router)
    return dispatcher
