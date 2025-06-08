from datetime import datetime

import aiohttp
import pytz
from loguru import logger
from telegram_bot.services.api_service import API_BASE_URL


async def get_all_cities():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/parking/cities") as response:
            return await response.json()


async def get_parkings_by_city(city_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/parking/parkings") as response:
            data = await response.json()
            return [p for p in data if p["city_id"] == city_id]


async def get_available_spots(parking_id: int):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_BASE_URL}/parking/spots/available",
            params={"parking_id": parking_id}
        ) as response:
            return await response.json()

async def get_user_cars(phone_number: str):
    url = f"{API_BASE_URL}/cars/phone/{phone_number}"

    logger.debug(f"[CARS] Запит авто користувача: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"[CARS] Отримано авто: {data}")
                    return data
                else:
                    text = await response.text()
                    logger.error(f"[CARS] Помилка {response.status}: {text}")
                    return []
    except Exception as e:
        logger.exception(f"[CARS] Виняток при отриманні авто: {e}")
        return []




async def book_spot(spot_id: int, car_id: int, phone_number: str, card_number: str = "1111"):
    url = f"{API_BASE_URL}/bookings/phone/{phone_number}"
    payload = {
        "spot_id": spot_id,
        "car_id": car_id,
        "card_number": card_number
    }

    logger.debug(f"[BOOKING] Надсилаємо запит до {url} з даними: {payload}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 201:
                    data = await response.json()
                    logger.success(f"[BOOKING] Бронювання створено: {data}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"[BOOKING] Помилка створення: {response.status} – {error_text}")
                    return None
    except Exception as e:
        logger.exception(f"[BOOKING] Виняток при запиті: {e}")
        return None



async def book_spot(
    spot_id: int,
    car_id: int,
    phone_number: str,
    duration_hours: float,
    card_id: int,
    occupied_from: str = None
):
    url = f"{API_BASE_URL}/bookings/phone/{phone_number}"
    payload = {
        "spot_id": spot_id,
        "car_id": car_id,
        "duration_hours": duration_hours,
        "card_id": card_id
    }

    if occupied_from:
        kyiv_tz = pytz.timezone("Europe/Kyiv")
        # конвертуємо str → datetime
        if isinstance(occupied_from, str):
            occupied_from_dt = datetime.fromisoformat(occupied_from)
        else:
            occupied_from_dt = occupied_from

        # додаємо таймзону, якщо її нема
        if occupied_from_dt.tzinfo is None:
            occupied_from_dt = kyiv_tz.localize(occupied_from_dt)

        payload["occupied_from"] = occupied_from_dt.isoformat()

    logger.debug(f"[BOOKING_SERVICE] Запит на бронювання: {payload}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 201:
                    data = await response.json()
                    logger.success(f"[BOOKING_SERVICE] Бронювання успішне: {data}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"[BOOKING_SERVICE] {response.status} – {error_text}")
                    return None
    except Exception as e:
        logger.exception(f"[BOOKING_SERVICE] Виняток при створенні бронювання: {e}")
        return None

async def get_spot_by_id(spot_id: int):
    url = f"{API_BASE_URL}/parking/spot/{spot_id}"
    logger.debug(f"[PARKING_SERVICE] Запит місця: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"[PARKING_SERVICE] Місце отримано: {data}")
                    return data
                else:
                    error = await response.text()
                    logger.error(f"[PARKING_SERVICE] {response.status} – {error}")
                    return {}
    except Exception as e:
        logger.exception(f"[PARKING_SERVICE] Помилка при отриманні місця: {e}")
        return {}

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

