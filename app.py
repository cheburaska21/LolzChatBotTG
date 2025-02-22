from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from logger_config import setup_logger, get_logger
from handlers import main_router

import asyncio
from config import TOKEN_BOT
from contextlib import suppress


setup_logger()
logger = get_logger(__name__)


async def main():
    logger.info("Starting the Bot")

    bot = Bot(token=TOKEN_BOT, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(main_router)

    bot_task = asyncio.create_task(dp.start_polling(bot))
    await asyncio.gather(bot_task)

if __name__ == '__main__':
    with suppress(KeyboardInterrupt, SystemExit):
        asyncio.run(main())