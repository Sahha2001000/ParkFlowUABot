import aiohttp
import logging
from telegram_bot.config import API_BASE_URL

logger = logging.getLogger(__name__)

# Створення нового користувача
async def create_user(telegram_id: int, first_name: str, last_name: str, phone_number: str, email: str = None):
    url = f"{API_BASE_URL}/users/register"
    payload = {
        "telegram_id": telegram_id,
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": phone_number,
        "email": email
    }

    logger.info(f"Відправка запиту на створення користувача: {payload}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                logger.info(f"Відповідь API: {response.status}")

                if response.status in [200, 201]:
                    try:
                        data = await response.json()
                        logger.info(f"Користувача створено успішно: {data}")
                        return data
                    except Exception as json_err:
                        logger.error(f"Не вдалося розпарсити JSON: {json_err}")
                        return None
                else:
                    error_text = await response.text()
                    logger.warning(f"API повернув неуспішний статус: {response.status}, текст: {error_text}")
                    return None

    except aiohttp.ClientError as e:
        logger.exception(f"Помилка HTTP-з'єднання: {e}")
        return None
    except Exception as e:
        logger.exception(f"Невідома помилка у create_user: {e}")
        return None

async def get_user_by_phone(phone_number: str):
    url = f"{API_BASE_URL}/users/by-phone"
    params = {"phone_number": phone_number}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                logger.info(f"Виконано GET {url} з параметрами {params}, статус: {resp.status}")

                if resp.status == 200:
                    try:
                        data = await resp.json()
                        logger.info(f"Користувач знайдений: {data}")
                        return data
                    except Exception as json_err:
                        logger.error(f"Помилка розбору JSON відповіді: {json_err}")
                        return None

                # Тепер 404 також сприймається як помилка API (не дозволяємо продовжити)
                error_text = await resp.text()
                logger.error(f"❌ API повернув помилку: статус {resp.status}, відповідь: {error_text}")
                raise Exception("Помилка відповіді API")

    except aiohttp.ClientError as e:
        logger.exception(f"Помилка з'єднання з API у get_user_by_phone: {e}")
        raise Exception("Помилка з'єднання з API")
    except Exception as e:
        logger.exception(f"Невідома помилка у get_user_by_phone: {e}")
        raise Exception("Невідома помилка у get_user_by_phone")


# Оновлення користувача
async def update_user_by_phone(phone_number: str, update_data: dict):
    url = f"{API_BASE_URL}/users/update"
    params = {"phone_number": phone_number}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(url, params=params, json=update_data) as resp:
                if resp.status in [200, 204]:
                    logger.info("Користувача успішно оновлено.")
                    return True
                else:
                    logger.warning(f"Помилка оновлення користувача: {resp.status}")
                    return False
    except Exception as e:
        logger.exception("Помилка при оновленні користувача.")
        return False

# Видалення користувача
async def delete_user_by_phone(phone_number: str):
    url = f"{API_BASE_URL}/users/delete"
    params = {"phone_number": phone_number}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, params=params) as resp:
                if resp.status in [200, 204]:
                    logger.info("Користувача успішно видалено.")
                    return True
                else:
                    logger.warning(f"Помилка при видаленні користувача: {resp.status}")
                    return False
    except Exception as e:
        logger.exception("Помилка при видаленні користувача.")
        return False

