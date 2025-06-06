from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from loguru import logger

router = Router()

# Клавіатура для повторної спроби
retry_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔁 Спробувати ще раз")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Обробник кнопки "Спробувати ще раз"
@router.message(F.text == "🔁 Спробувати ще раз")
async def retry_action(message: Message):
    logger.info(f"[ERROR_HANDLER] Користувач {message.from_user.id} натиснув '🔁 Спробувати ще раз'")
    await message.answer(
        "🔁 Будь ласка, повторіть вашу дію або введіть /start.",
        reply_markup=retry_keyboard
    )

# Загальний обробник усіх неочікуваних повідомлень
@router.message()
async def fallback_handler(message: Message):
    logger.warning(f"[ERROR_HANDLER] Невідоме повідомлення від {message.from_user.id}: '{message.text}'")
    await message.answer(
        "⛔ Невідома команда. Будь ласка, скористайтеся меню або введіть /start."
    )


