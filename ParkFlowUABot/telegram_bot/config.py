import os
from dotenv import load_dotenv
from telegram_bot.logger import logger

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")

logger.info("Завантажено конфігурацію Telegram-бота")
logger.debug(f"API_BASE_URL = {API_BASE_URL}")
logger.debug(f"BOT_TOKEN = {BOT_TOKEN}")
