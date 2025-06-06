from telegram_bot.handlers.start_handler import router as start_router
from telegram_bot.handlers.registration_handler import router as registration_router
from telegram_bot.handlers.settings_handler import router as settings_router
from telegram_bot.handlers.error_handler import router as error_router
from telegram_bot.handlers.car_handler import router as car_router

from telegram_bot.handlers.card_handler import router as card_router
from telegram_bot.handlers.booking_handler import router as booking_router  # ⬅️ Додай це

from telegram_bot.logger import logger

logger.debug("Імпортовано start_handler")
logger.debug("Імпортовано registration_handler")
logger.debug("Імпортовано settings_handler")
logger.debug("Імпортовано error_handler")
logger.debug("Імпортовано car_handler")
logger.debug("Імпортовано parking_handler")
logger.debug("Імпортовано card_handler")
logger.debug("Імпортовано booking_handler")  # ⬅️ Додай це

all_handlers = [
    booking_router,  # ⬅️ Додай сюди
    start_router,
    registration_router,
    car_router,
    card_router,

    settings_router,
    error_router
]

logger.info("Усі router-и імпортовано успішно")
