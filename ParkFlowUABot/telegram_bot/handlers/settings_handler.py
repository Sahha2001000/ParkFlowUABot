from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from telegram_bot.services.user_service import get_user_by_phone, delete_user_by_phone, update_user_by_phone
from telegram_bot.services.api_service import is_api_available
from telegram_bot.keyboards.menu import main_menu, settings_menu

router = Router()


class EditState(StatesGroup):
    new_full_name = State()
    new_email = State()


async def get_last_menu_markup(state: FSMContext):
    data = await state.get_data()
    menu = data.get("last_menu")
    if menu == "settings":
        return settings_menu()
    elif menu == "main":
        return main_menu()
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔁 Спробувати ще раз")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def get_valid_phone_or_notify(message: Message, state: FSMContext) -> str | None:
    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        await message.answer("❗ Не вдалося отримати номер телефону. Спробуйте /start.")
        return None

    if not await is_api_available():
        markup = await get_last_menu_markup(state)
        await message.answer("⚠️ Сервер тимчасово недоступний. Спробуйте пізніше.", reply_markup=markup)
        return None

    return phone


@router.message(F.text == "⚙️ Налаштування")
async def open_settings(message: Message, state: FSMContext):
    logger.info(f"[SETTINGS] Користувач {message.from_user.id} відкрив меню Налаштування")
    await state.update_data(last_menu="settings")
    await message.answer("Оберіть дію в меню налаштувань:", reply_markup=settings_menu())


@router.message(F.text == "⬅️ Назад")
async def go_back(message: Message, state: FSMContext):
    logger.info(f"[SETTINGS] Користувач {message.from_user.id} повернувся до головного меню")
    await state.update_data(last_menu="main")
    await message.answer("Повернення в головне меню:", reply_markup=main_menu())


@router.message(F.text == "👤 Отримати інформацію про себе")
async def get_user_info(message: Message, state: FSMContext):
    logger.info(f"[SETTINGS] Користувач {message.from_user.id} запитав інформацію про себе")
    phone = await get_valid_phone_or_notify(message, state)
    if not phone:
        return

    user = await get_user_by_phone(phone)
    markup = await get_last_menu_markup(state)
    if user:
        await message.answer(
            f"👤 *Ваш профіль:*\n"
            f"Ім'я: {user.get('first_name', '')} {user.get('last_name', '')}\n"
            f"Телефон: {user.get('phone_number', '')}\n"
            f"Email: {user.get('email') or 'не вказано'}",
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        await message.answer("❌ Користувача не знайдено.", reply_markup=markup)


@router.message(F.text == "✏️ Змінити ім'я")
async def change_name_prompt(message: Message, state: FSMContext):
    logger.info(f"[SETTINGS] Користувач {message.from_user.id} змінює ім’я")
    await message.answer("Введіть нові ім’я та прізвище через пробіл:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EditState.new_full_name)


@router.message(EditState.new_full_name)
async def update_full_name(message: Message, state: FSMContext):
    input_text = message.text.strip()
    parts = input_text.split(maxsplit=1)
    phone = await get_valid_phone_or_notify(message, state)
    markup = await get_last_menu_markup(state)

    if not phone:
        await state.clear()
        return

    if len(parts) != 2:
        await message.answer("❗ Введіть і ім’я, і прізвище через пробіл (наприклад: Іван Петренко).")
        return

    first_name, last_name = parts
    success = await update_user_by_phone(phone, {"first_name": first_name, "last_name": last_name})
    if success:
        await message.answer("✅ Ім’я та прізвище оновлено.", reply_markup=markup)
    else:
        await message.answer("❌ Не вдалося оновити. Спробуйте пізніше.", reply_markup=markup)

    await state.clear()
    await state.update_data(phone_number=phone, last_menu="settings")


@router.message(F.text == "📧 Змінити email")
async def change_email_prompt(message: Message, state: FSMContext):
    logger.info(f"[SETTINGS] Користувач {message.from_user.id} змінює email")
    await message.answer("Введіть новий email:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EditState.new_email)


@router.message(EditState.new_email)
async def update_email(message: Message, state: FSMContext):
    email = message.text.strip()
    data = await state.get_data()
    phone = await get_valid_phone_or_notify(message, state)
    markup = await get_last_menu_markup(state)

    if not phone:
        await state.clear()
        return

    if "@" not in email or "." not in email:
        await message.answer("❗ Невірний формат email. Спробуйте ще раз.")
        return

    success = await update_user_by_phone(phone, {"email": email})
    if success:
        await message.answer("✅ Email оновлено.", reply_markup=markup)
    else:
        await message.answer("❌ Не вдалося оновити email. Спробуйте пізніше.", reply_markup=markup)

    await state.clear()
    await state.update_data(phone_number=phone, last_menu="settings")


@router.message(F.text == "❌ Видалити мій профіль")
async def delete_profile(message: Message, state: FSMContext):
    logger.info(f"[SETTINGS] Користувач {message.from_user.id} ініціював видалення профілю")
    await state.update_data(last_menu="settings")
    confirm_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Так, видалити")],
            [KeyboardButton(text="❌ Ні, скасувати")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("❗ Ви впевнені, що хочете видалити свій профіль?", reply_markup=confirm_keyboard)


@router.message(F.text == "✅ Так, видалити")
async def confirm_delete(message: Message, state: FSMContext):
    logger.info(f"[SETTINGS] Користувач {message.from_user.id} підтвердив видалення профілю")
    phone = await get_valid_phone_or_notify(message, state)
    markup = await get_last_menu_markup(state)

    if not phone:
        return

    success = await delete_user_by_phone(phone)
    if success:
        await message.answer("✅ Ваш профіль успішно видалено. Для повторної реєстрації введіть /start.", reply_markup=main_menu())
        await state.clear()
    else:
        await message.answer("❌ Не вдалося видалити профіль. Спробуйте пізніше.", reply_markup=markup)


@router.message(F.text == "❌ Ні, скасувати")
async def cancel_delete(message: Message, state: FSMContext):
    logger.info(f"[SETTINGS] Користувач {message.from_user.id} скасував видалення профілю")
    await message.answer("Скасовано.", reply_markup=settings_menu())


@router.message(F.text == "🔁 Спробувати ще раз")
async def retry_action(message: Message, state: FSMContext):
    logger.info(f"[ERROR_HANDLER] Користувач {message.from_user.id} натиснув '🔁 Спробувати ще раз'")
    markup = await get_last_menu_markup(state)
    await message.answer("🔁 Повторіть дію або виберіть інше меню.", reply_markup=markup)


@router.message()
async def fallback_handler(message: Message, state: FSMContext):
    logger.warning(f"[ERROR_HANDLER] Невідоме повідомлення від {message.from_user.id}: '{message.text}'")
    markup = await get_last_menu_markup(state)
    await message.answer("⛔ Невідома команда. Виберіть пункт із меню або введіть /start.", reply_markup=markup)
