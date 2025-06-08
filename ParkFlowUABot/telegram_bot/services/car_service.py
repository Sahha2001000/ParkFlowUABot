import aiohttp
from loguru import logger
from telegram_bot.services.api_service import API_BASE_URL

async def add_car_phone(phone_number: str, car_data: dict):
    url = f"{API_BASE_URL}/cars/phone/{phone_number}"
    logger.info(f"[API] Надсилання авто для телефону {phone_number}: {car_data}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=car_data) as resp:
                response_data = await resp.json(content_type=None)

                if resp.status == 201:
                    logger.success(f"[API] Авто успішно додано для {phone_number}")
                    return True

                elif resp.status == 200 and response_data.get("message") == "Авто з таким номером вже додано":
                    logger.warning(f"[API] Авто вже існує для {phone_number}")
                    return "duplicate"

                else:
                    logger.error(f"[API] Не вдалося додати авто. Статус: {resp.status}, Відповідь: {response_data}")
                    return False

    except Exception as e:
        logger.exception(f"[API] Виняток при додаванні авто для {phone_number}")
        return False
async def get_user_cars(phone_number: str) -> list[dict]:
    url = f"{API_BASE_URL}/cars/phone/{phone_number}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    logger.info(f"[API] Отримано авто для {phone_number}: {data}")
                    return data if isinstance(data, list) else []
                else:
                    logger.warning(f"[API] Не вдалося отримати список авто. Статус: {resp.status}")
                    return []
    except Exception as e:
        logger.exception("[API] Виняток при отриманні авто")
        return []

async def delete_car_by_id(phone_number: str, plate: str) -> bool:
    url = f"{API_BASE_URL}/cars/phone/{phone_number}/{plate}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(url) as resp:
                if resp.status in (200, 204):
                    logger.success(f"[API] Авто з номером {plate} видалено для {phone_number}")
                    return True
                else:
                    logger.warning(f"[API] Не вдалося видалити авто {plate}. Статус: {resp.status}")
                    return False
    except Exception as e:
        logger.exception("[API] Виняток при видаленні авто")
        return False

async def update_car_by_id(phone_number: str, plate: str, update_data: dict) -> bool:
    url = f"{API_BASE_URL}/cars/phone/{phone_number}/{plate}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=update_data) as resp:
                if resp.status in (200, 204):
                    logger.success(f"[API] Авто {plate} оновлено для {phone_number}")
                    return True
                else:
                    logger.warning(f"[API] Не вдалося оновити авто {plate}. Статус: {resp.status}")
                    return False
    except Exception as e:
        logger.exception("[API] Виняток при оновленні авто")
        return False