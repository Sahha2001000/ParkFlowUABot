from aiogram import Router, F, types
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from loguru import logger

from telegram_bot.keyboards.menu import main_menu, card_menu
from telegram_bot.services.card_service import (
    add_card,
    get_user_cards,
    delete_card_by_id,
    update_card_by_id
)

router = Router()


class AddCardState(StatesGroup):
    number = State()
    exp_date = State()
    cvv = State()


class UpdateCardState(StatesGroup):
    number = State()
    exp_date = State()
    cvv = State()


def back_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )


@router.message(F.text == "💳 Картки")
async def open_card_menu(message: Message, state: FSMContext):
    logger.info(f"[CARD] Користувач {message.from_user.id} відкрив меню карток")
    await message.answer("Оберіть дію з картками:", reply_markup=card_menu())


@router.message(F.text == "➕ Додати картку")
async def start_add_card(message: Message, state: FSMContext):
    logger.info(f"[CARD] Додавання картки — старт від {message.from_user.id}")
    await message.answer("Введіть номер картки (16 цифр):", reply_markup=back_kb())
    await state.set_state(AddCardState.number)


@router.message(AddCardState.number)
async def get_card_number(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        logger.info(f"[CARD] {message.from_user.id} повернувся назад з номера")
        await return_to_menu(state, message)
        return

    number = message.text.strip().replace(" ", "")
    if not (number.isdigit() and len(number) == 16):
        await message.answer("❌ Номер має бути з 16 цифр:", reply_markup=back_kb())
        return

    logger.debug(f"[CARD] Отримано номер від {message.from_user.id}: {number}")
    await state.update_data(number=number)
    await message.answer("Введіть термін дії (MM/YY):", reply_markup=back_kb())
    await state.set_state(AddCardState.exp_date)


@router.message(AddCardState.exp_date)
async def get_exp_date(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        logger.info(f"[CARD] {message.from_user.id} повернувся назад з дати")
        await return_to_menu(state, message)
        return

    exp = message.text.strip()
    if len(exp) != 5 or exp[2] != "/" or not (exp[:2].isdigit() and exp[3:].isdigit()):
        await message.answer("❌ Формат має бути MM/YY:", reply_markup=back_kb())
        return

    logger.debug(f"[CARD] Отримано термін дії від {message.from_user.id}: {exp}")
    await state.update_data(exp_date=exp)
    await message.answer("Введіть CVV (3 цифри):", reply_markup=back_kb())
    await state.set_state(AddCardState.cvv)


@router.message(AddCardState.cvv)
async def get_cvv(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        logger.info(f"[CARD] {message.from_user.id} повернувся назад з CVV")
        await return_to_menu(state, message)
        return

    cvv = message.text.strip()
    if not (cvv.isdigit() and len(cvv) == 3):
        await message.answer("❌ CVV має бути з 3 цифр:", reply_markup=back_kb())
        return

    await state.update_data(cvv=cvv)
    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        logger.error(f"[CARD] Немає номера телефону в state у {message.from_user.id}")
        await message.answer("⚠️ Номер телефону не знайдено.")
        return

    logger.info(f"[CARD] Спроба додати картку для {phone}")
    try:
        result = await add_card(phone, {
            "number": data["number"],
            "exp_date": data["exp_date"],
            "cvv": data["cvv"]
        })
        if result == "duplicate":
            await message.answer("⚠️ Така картка вже існує.")
        elif result:
            await message.answer("✅ Картку додано успішно.")
        else:
            await message.answer("❌ Не вдалося додати картку.")
    except Exception as e:
        logger.exception(f"[CARD] Помилка додавання картки: {e}")
        await message.answer("❌ Сталася помилка.")

    await state.clear()
    await state.update_data(phone_number=phone)
    await message.answer("Оберіть подальші дії:", reply_markup=card_menu())


@router.message(F.text == "📋 Мої картки")
async def list_cards(message: Message, state: FSMContext):
    phone = (await state.get_data()).get("phone_number")
    logger.info(f"[CARD] {message.from_user.id} запитав список карток")

    if not phone:
        await message.answer("⚠️ Номер телефону не знайдено.")
        return

    cards = await get_user_cards(phone)
    if not cards:
        await message.answer("📭 У вас немає збережених карток.")
        return

    response = "💳 Ваші картки:\n\n"
    for i, card in enumerate(cards, 1):
        masked = f"{card['number'][:4]} **** **** {card['number'][-4:]}"
        response += f"{i}. {masked} — {card['exp_date']}\n"

    await message.answer(response)


@router.message(F.text == "❌ Видалити картку")
async def show_cards_for_deletion(message: Message, state: FSMContext):
    phone = (await state.get_data()).get("phone_number")
    logger.info(f"[CARD] {message.from_user.id} хоче видалити картку")

    if not phone:
        await message.answer("⚠️ Номер телефону не знайдено.")
        return

    cards = await get_user_cards(phone)
    if not cards:
        await message.answer("📭 У вас немає карток.")
        return

    for card in cards:
        card_id = card["id"]
        masked = f"{card['number'][:4]} **** **** {card['number'][-4:]}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"delete_card:{card_id}")]
        ])
        await message.answer(f"💳 {masked} — {card['exp_date']}", reply_markup=kb)


@router.callback_query(F.data.startswith("delete_card:"))
async def handle_card_deletion(callback: CallbackQuery, state: FSMContext):
    card_id = int(callback.data.split(":")[1])
    logger.info(f"[CARD] Видалення картки ID {card_id}")
    success = await delete_card_by_id(card_id)
    if success:
        await callback.message.edit_text("✅ Картку видалено.")
    else:
        await callback.message.edit_text("❌ Не вдалося видалити картку.")
    await callback.answer()


@router.message(F.text == "✏️ Змінити картку")
async def show_cards_for_update(message: Message, state: FSMContext):
    phone = (await state.get_data()).get("phone_number")
    logger.info(f"[CARD] {message.from_user.id} хоче змінити картку")

    if not phone:
        await message.answer("⚠️ Номер телефону не знайдено.")
        return

    cards = await get_user_cards(phone)
    if not cards:
        await message.answer("📭 У вас немає карток.")
        return

    for card in cards:
        card_id = card["id"]
        masked = f"{card['number'][:4]} **** **** {card['number'][-4:]}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Змінити", callback_data=f"edit_card:{card_id}")]
        ])
        await message.answer(f"💳 {masked} — {card['exp_date']}", reply_markup=kb)


@router.callback_query(F.data.startswith("edit_card:"))
async def start_update_card(callback: CallbackQuery, state: FSMContext):
    card_id = int(callback.data.split(":")[1])
    logger.info(f"[CARD] Користувач {callback.from_user.id} вибрав картку ID {card_id} для редагування")
    await state.update_data(card_id=card_id)
    await state.set_state(UpdateCardState.number)
    await callback.message.answer("Введіть новий номер картки:", reply_markup=back_kb())
    await callback.answer()


@router.message(UpdateCardState.number)
async def update_number(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await return_to_menu(state, message)
        return

    number = message.text.strip().replace(" ", "")
    if not (number.isdigit() and len(number) == 16):
        await message.answer("❌ Введіть 16 цифр:", reply_markup=back_kb())
        return

    logger.debug(f"[CARD] Новий номер: {number}")
    await state.update_data(number=number)
    await message.answer("Введіть новий термін дії (MM/YY):", reply_markup=back_kb())
    await state.set_state(UpdateCardState.exp_date)


@router.message(UpdateCardState.exp_date)
async def update_exp_date(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await return_to_menu(state, message)
        return

    exp = message.text.strip()
    if len(exp) != 5 or exp[2] != "/" or not (exp[:2].isdigit() and exp[3:].isdigit()):
        await message.answer("❌ Формат має бути MM/YY:", reply_markup=back_kb())
        return

    logger.debug(f"[CARD] Нова дата: {exp}")
    await state.update_data(exp_date=exp)
    await message.answer("Введіть новий CVV:", reply_markup=back_kb())
    await state.set_state(UpdateCardState.cvv)


@router.message(UpdateCardState.cvv)
async def update_cvv(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await return_to_menu(state, message)
        return

    cvv = message.text.strip()
    if not (cvv.isdigit() and len(cvv) == 3):
        await message.answer("❌ CVV має бути з 3 цифр:", reply_markup=back_kb())
        return

    await state.update_data(cvv=cvv)
    data = await state.get_data()
    phone = data.get("phone_number")
    card_id = data.get("card_id")

    logger.info(f"[CARD] Спроба оновлення картки {card_id} для {phone}")
    try:
        result = await update_card_by_id(card_id, {
            "number": data["number"],
            "exp_date": data["exp_date"],
            "cvv": data["cvv"]
        })
        if result:
            await message.answer("✅ Картку оновлено успішно.")
        else:
            await message.answer("❌ Не вдалося оновити картку.")
    except Exception as e:
        logger.error(f"[CARD] Помилка при оновленні картки: {e}")
        await message.answer("❌ Сталася помилка при оновленні.")

    await state.clear()
    await state.update_data(phone_number=phone)
    await message.answer("Оберіть подальші дії:", reply_markup=card_menu())


@router.message(F.text == "⬅️ Назад до меню")
async def return_main(message: Message, state: FSMContext):
    logger.info(f"[CARD] {message.from_user.id} повернувся до головного меню")
    await message.answer("⬅️ Ви повернулись до головного меню", reply_markup=main_menu())


async def return_to_menu(state: FSMContext, message: Message):
    phone = (await state.get_data()).get("phone_number")
    await state.clear()
    if phone:
        await state.update_data(phone_number=phone)
    logger.debug(f"[CARD] Повернення до меню карток для {message.from_user.id}")
    await message.answer("↩️ Повертаємось до меню карток:", reply_markup=card_menu())
