import aiohttp
from loguru import logger
from telegram_bot.services.api_service import API_BASE_URL


async def add_card(phone_number: str, card_data: dict):
    url = f"{API_BASE_URL}/cards/phone/{phone_number}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=card_data) as resp:
                data = await resp.json(content_type=None)
                if resp.status == 201:
                    return True
                elif resp.status == 200 and data.get("message") == "Картка вже існує":
                    return "duplicate"
                return False
    except Exception:
        logger.exception("[CARD] Помилка при додаванні картки")
        return False


async def get_user_cards(phone_number: str) -> list[dict]:
    url = f"{API_BASE_URL}/cards/phone/{phone_number}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json(content_type=None)
                return []
    except Exception:
        logger.exception("[CARD] Помилка при отриманні карток")
        return []


async def delete_card_by_id(card_id: int) -> bool:
    url = f"{API_BASE_URL}/cards/{card_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(url) as resp:
                return resp.status in (200, 204)
    except Exception:
        logger.exception("[CARD] Помилка при видаленні картки")
        return False
