from loguru import logger

logger.add("telegram_bot/telegram_bot.log", rotation="1 MB", level="INFO", format="{time} | {level} | {message}")
