# telegram_bot/services/feedback_service.py

import aiohttp
import logging
from telegram_bot.config import API_BASE_URL

logger = logging.getLogger(__name__)

FEEDBACK_API = f"{API_BASE_URL}/feedback"

# 🔸 Надіслати відгук
async def send_feedback(user_id: int, text: str):
    payload = {
        "user_id": user_id,
        "text": text
    }

    logger.info(f"[FEEDBACK_SERVICE] Відправка відгуку: {payload}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(FEEDBACK_API, json=payload) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    logger.info(f"[FEEDBACK_SERVICE] Відгук збережено: {data}")
                    return data
                else:
                    error_text = await resp.text()
                    logger.warning(f"[FEEDBACK_SERVICE] Статус {resp.status}, відповідь: {error_text}")
                    return None
    except aiohttp.ClientError as e:
        logger.exception(f"[FEEDBACK_SERVICE] HTTP-помилка: {e}")
        return None
    except Exception as e:
        logger.exception(f"[FEEDBACK_SERVICE] Невідома помилка: {e}")
        return None


# 🔹 Отримати всі відгуки
async def get_all_feedbacks():
    logger.info("[FEEDBACK_SERVICE] Запит усіх відгуків")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(FEEDBACK_API) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"[FEEDBACK_SERVICE] Отримано {len(data)} відгуків")
                    return data
                else:
                    error_text = await resp.text()
                    logger.warning(f"[FEEDBACK_SERVICE] Помилка {resp.status}, відповідь: {error_text}")
                    return []
    except aiohttp.ClientError as e:
        logger.exception(f"[FEEDBACK_SERVICE] HTTP-помилка: {e}")
        return []
    except Exception as e:
        logger.exception(f"[FEEDBACK_SERVICE] Невідома помилка: {e}")
        return []
