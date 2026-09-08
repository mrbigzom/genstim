import asyncio
import logging

import uvicorn
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.api import create_api
from app.bot.commands import set_bot_commands
from app.bot.dispatcher import create_dispatcher
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import create_database
from app.providers.background_removal import RembgBackgroundRemovalProvider

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    engine, session_factory = create_database(
        settings.database_url,
        echo=settings.environment.lower() == "local-sql-debug",
    )
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    background_removal_provider = RembgBackgroundRemovalProvider(
        timeout_seconds=settings.background_removal_timeout_seconds,
        max_pixels=settings.background_removal_max_pixels,
        max_concurrency=settings.background_removal_max_concurrency,
    )
    dispatcher = create_dispatcher(
        session_factory,
        background_removal_provider=background_removal_provider,
        background_max_file_size=settings.background_removal_max_file_mb * 1024 * 1024,
        background_max_pixels=settings.background_removal_max_pixels,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            create_api(),
            host=settings.api_host,
            port=settings.api_port,
            log_config=None,
        )
    )

    tasks: set[asyncio.Task[object]] = set()

    try:
        await set_bot_commands(bot)
        logger.info("Starting GenStim AI bot and HTTP server")
        api_task = asyncio.create_task(server.serve(), name="api-server")
        bot_task = asyncio.create_task(
            dispatcher.start_polling(
                bot,
                handle_signals=False,
                close_bot_session=False,
            ),
            name="telegram-polling",
        )
        tasks = {api_task, bot_task}
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        server.should_exit = True
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await bot.session.close()
        await engine.dispose()
        logger.info("GenStim AI stopped")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
