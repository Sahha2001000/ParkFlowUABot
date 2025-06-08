from telegram_bot.handlers.start_handler import router as start_router
from telegram_bot.handlers.registration_handler import router as registration_router
from telegram_bot.handlers.settings_handler import router as settings_router
from telegram_bot.handlers.error_handler import router as error_router
from telegram_bot.handlers.car_handler import router as car_router
from telegram_bot.handlers.card_handler import router as card_router
from telegram_bot.handlers.booking_handler import router as booking_router
from telegram_bot.handlers.feedback_handler import router as feedback_router  # ✅ додано

from telegram_bot.logger import logger

logger.debug("Імпортовано start_handler")
logger.debug("Імпортовано registration_handler")
logger.debug("Імпортовано settings_handler")
logger.debug("Імпортовано error_handler")
logger.debug("Імпортовано car_handler")
logger.debug("Імпортовано card_handler")
logger.debug("Імпортовано booking_handler")
logger.debug("Імпортовано feedback_handler")

all_handlers = [
    booking_router,
    start_router,
    registration_router,
    car_router,
    card_router,
    feedback_router,
    settings_router,
    error_router
]

logger.info("Усі router-и імпортовано успішно")
