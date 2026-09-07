from aiogram import Bot
from aiogram.types import BotCommand

COMMANDS_EN = [
    BotCommand(command="start", description="Open GenStim AI"),
    BotCommand(command="create", description="Create with AI"),
    BotCommand(command="tools", description="Browse AI tools"),
    BotCommand(command="credits", description="Check credits"),
    BotCommand(command="history", description="My creations"),
    BotCommand(command="invite", description="Invite friends"),
    BotCommand(command="language", description="Change language"),
    BotCommand(command="help", description="Help"),
    BotCommand(command="support", description="Support"),
    BotCommand(command="paysupport", description="Payment support"),
    BotCommand(command="terms", description="Terms of Service"),
    BotCommand(command="privacy", description="Privacy Policy"),
]

COMMANDS_RU = [
    BotCommand(command="start", description="Открыть GenStim AI"),
    BotCommand(command="create", description="Создать с AI"),
    BotCommand(command="tools", description="AI-инструменты"),
    BotCommand(command="credits", description="Проверить кредиты"),
    BotCommand(command="history", description="Мои работы"),
    BotCommand(command="invite", description="Пригласить друзей"),
    BotCommand(command="language", description="Изменить язык"),
    BotCommand(command="help", description="Помощь"),
    BotCommand(command="support", description="Поддержка"),
    BotCommand(command="paysupport", description="Поддержка по оплате"),
    BotCommand(command="terms", description="Условия использования"),
    BotCommand(command="privacy", description="Конфиденциальность"),
]


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(COMMANDS_EN)
    await bot.set_my_commands(COMMANDS_RU, language_code="ru")
