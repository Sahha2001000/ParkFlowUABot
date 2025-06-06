from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from loguru import logger

from telegram_bot.services.api_service import is_api_available

router = Router()

# Клавіатура для надання номера телефону
contact_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📞 Надати номер телефону", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Клавіатура для повторної спроби
retry_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔁 Спробувати ще раз")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    logger.info(f"/start викликано користувачем: telegram_id={message.from_user.id}")

    if not await is_api_available():
        logger.warning("Сервер API недоступний при виклику /start")
        await message.answer(
            "⚠️ *Сервер тимчасово недоступний.*\nБудь ласка, спробуйте пізніше.",
            parse_mode="Markdown",
            reply_markup=retry_keyboard
        )
        return

    logger.debug("Надсилання запиту на номер телефону користувача")
    await message.answer(
        "👋 Вітаємо у *ParkFlowUABot*!\n"
        "Будь ласка, надайте свій номер телефону:",
        parse_mode="Markdown",
        reply_markup=contact_keyboard
    )

@router.message(F.text == "🔁 Спробувати ще раз")
async def retry_start(message: Message, state: FSMContext):
    logger.info(f"Користувач {message.from_user.id} натиснув 'Спробувати ще раз'")
    await start(message, state)
