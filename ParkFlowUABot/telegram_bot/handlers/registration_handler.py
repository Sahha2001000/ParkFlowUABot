from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from loguru import logger
from aiohttp import ClientConnectorError

from telegram_bot.services.api_service import is_api_available
from telegram_bot.services.user_service import get_user_by_phone, create_user
from telegram_bot.keyboards.menu import main_menu

router = Router()

class Registration(StatesGroup):
    first_name = State()
    last_name = State()
    email = State()

# --- Контакт ---
@router.message(F.contact)
async def handle_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    telegram_id = message.from_user.id

    logger.info(f"[REGISTRATION] Отримано контакт від telegram_id={telegram_id}, phone={phone}")

    await state.update_data(phone_number=phone)

    if not await is_api_available():
        logger.warning("API недоступне при отриманні контакту")
        await message.answer(
            "⚠️ Сервер недоступний. Спробуйте пізніше.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="🔁 Спробувати ще раз")]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return

    try:
        user = await get_user_by_phone(phone)
    except Exception as e:
        logger.error(f"[REGISTRATION] Помилка при виклику get_user_by_phone: {e}")
        user = None

    if user:
        logger.info(f"[REGISTRATION] Користувач знайдений: {user}")
        await message.answer(
            f"Вас розпізнано як {user.get('first_name')}!",
            reply_markup=main_menu()
        )
        return

    logger.info("[REGISTRATION] Користувача не знайдено — починаємо реєстрацію")
    await message.answer("Введіть ваше ім’я:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Registration.first_name)

# --- First name ---
@router.message(Registration.first_name)
async def get_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip())
    await message.answer("Тепер введіть ваше прізвище:")
    await state.set_state(Registration.last_name)

# --- Last name ---
@router.message(Registration.last_name)
async def get_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text.strip())

    email_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="пропустити")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Якщо бажаєте, введіть email або натисніть 'пропустити':", reply_markup=email_keyboard)
    await state.set_state(Registration.email)

# --- Email or skip ---
@router.message(Registration.email, F.text.lower() == "пропустити")
async def skip_email(message: Message, state: FSMContext):
    await state.update_data(email=None)
    await finish_registration(message, state)

@router.message(Registration.email)
async def get_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text.strip())
    await finish_registration(message, state)

# --- Final step ---
async def finish_registration(message: Message, state: FSMContext):
    data = await state.get_data()

    if not await is_api_available():
        logger.warning("[REGISTRATION] API недоступне при завершенні реєстрації")
        await message.answer("⚠️ Сервер недоступний. Спробуйте пізніше.")
        return

    phone_number = data.get("phone_number")  # 🔹 ЗБЕРІГАЄМО НОМЕР

    try:
        await create_user(
            telegram_id=message.from_user.id,
            phone_number=phone_number,
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data.get("email")
        )
        logger.info(f"[REGISTRATION] Користувача створено: telegram_id={message.from_user.id}")
    except ClientConnectorError:
        logger.exception("[REGISTRATION] API недоступне при створенні користувача.")
        await message.answer("❌ API недоступне. Спробуйте пізніше.")
        return
    except Exception as e:
        logger.exception(f"[REGISTRATION] Помилка при створенні користувача: {e}")
        await message.answer("❌ Сталася помилка під час реєстрації. Спробуйте пізніше.")
        return

    await message.answer(
        f"✅ Реєстрація завершена!\n"
        f"👤 {data['first_name']} {data['last_name']}\n"
        f"📞 {phone_number}\n"
        f"✉️ {data.get('email') or 'не вказано'}",
        parse_mode="Markdown"
    )
    await message.answer("Оберіть опцію з меню нижче:", reply_markup=main_menu())

    await state.clear()
    await state.update_data(phone_number=phone_number)  # 🔹 ПОВЕРТАЄМО НОМЕР У FSM
