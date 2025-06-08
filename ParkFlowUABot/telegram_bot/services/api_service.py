from telegram_bot.config import API_BASE_URL
import aiohttp

# Перевірка доступності API
async def is_api_available():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health") as resp:
                return resp.status == 200
    except:
        return False
