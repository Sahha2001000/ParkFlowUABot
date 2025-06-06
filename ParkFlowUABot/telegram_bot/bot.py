# telegram_bot/bot.py

import asyncio
from aiogram import Bot, Dispatcher
from telegram_bot.config import BOT_TOKEN
from telegram_bot.handlers import all_handlers
from telegram_bot.logger import logger  #  єдиний логер для всього проєкту

logger.info("Запуск Telegram-бота...")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    for handler in all_handlers:
        dp.include_router(handler)
        logger.debug(f"Router {handler} підключено до Dispatcher")

    logger.info("Усі router-и підключено. Стартуємо polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception(f"❌ Фатальна помилка при запуску бота: {e}")
