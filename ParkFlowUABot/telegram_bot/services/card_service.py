import aiohttp
from loguru import logger
from telegram_bot.services.api_service import API_BASE_URL


async def add_card(phone_number: str, card_data: dict):
    url = f"{API_BASE_URL}/cards/phone/{phone_number}"
    logger.debug(f"[CARD][ADD] POST {url} | Data: {card_data}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=card_data) as resp:
                data = await resp.json(content_type=None)
                logger.debug(f"[CARD][ADD] Status: {resp.status} | Response: {data}")
                if resp.status == 201:
                    return True
                elif resp.status == 200 and data.get("message") == "Картка вже існує":
                    return "duplicate"
                return False
    except Exception as e:
        logger.exception(f"[CARD][ADD] Помилка при додаванні картки: {e}")
        return False


async def get_user_cards(phone_number: str) -> list[dict]:
    url = f"{API_BASE_URL}/cards/phone/{phone_number}"
    logger.debug(f"[CARD][GET] GET {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    logger.debug(f"[CARD][GET] Status: {resp.status} | Response: {data}")
                    return data
                logger.warning(f"[CARD][GET] Status: {resp.status} | Empty result")
                return []
    except Exception as e:
        logger.exception(f"[CARD][GET] Помилка при отриманні карток: {e}")
        return []


async def delete_card_by_id(card_id: int) -> bool:
    url = f"{API_BASE_URL}/cards/{card_id}"
    logger.debug(f"[CARD][DELETE] DELETE {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(url) as resp:
                logger.debug(f"[CARD][DELETE] Status: {resp.status}")
                return resp.status in (200, 204)
    except Exception as e:
        logger.exception(f"[CARD][DELETE] Помилка при видаленні картки: {e}")
        return False


async def update_card_by_id(card_id: int, updated_data: dict) -> bool:
    url = f"{API_BASE_URL}/cards/{card_id}"
    logger.debug(f"[CARD][UPDATE] PUT {url} | Data: {updated_data}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=updated_data) as resp:
                logger.debug(f"[CARD][UPDATE] Status: {resp.status}")
                return resp.status == 200
    except Exception as e:
        logger.exception(f"[CARD][UPDATE] Помилка при оновленні картки: {e}")
        return False
