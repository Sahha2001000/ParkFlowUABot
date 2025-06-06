import aiohttp
from loguru import logger
from telegram_bot.services.api_service import API_BASE_URL

async def get_user_bookings(phone_number: str):
    url = f"{API_BASE_URL}/bookings/phone/{phone_number}"
    logger.debug(f"[BOOKING_SERVICE] Запит бронювань користувача: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    bookings = await response.json()
                    logger.debug(f"[BOOKING_SERVICE] Бронювання: {bookings}")
                    return bookings
                else:
                    error = await response.text()
                    logger.error(f"[BOOKING_SERVICE] {response.status} – {error}")
                    return []
    except Exception as e:
        logger.exception(f"[BOOKING_SERVICE] Виняток при запиті бронювань: {e}")
        return []

