from aiogram import Router, F, types
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from loguru import logger

from telegram_bot.keyboards.menu import main_menu, card_menu
from telegram_bot.services.card_service import (
    add_card,
    get_user_cards,
    delete_card_by_id,
)

router = Router()


class AddCardState(StatesGroup):
    number = State()
    exp_date = State()
    cvv = State()


@router.message(F.text == "💳 Картки")
async def open_card_menu(message: Message, state: FSMContext):
    logger.info(f"[CARD] Користувач {message.from_user.id} відкрив меню карток")
    await message.answer("Оберіть дію з картками:", reply_markup=card_menu())


@router.message(F.text == "➕ Додати картку")
async def start_add_card(message: Message, state: FSMContext):
    await message.answer("Введіть номер картки (16 цифр):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddCardState.number)


@router.message(AddCardState.number)
async def get_card_number(message: Message, state: FSMContext):
    number = message.text.strip().replace(" ", "")
    if not (number.isdigit() and len(number) == 16):
        await message.answer("❌ Некоректний номер. Введіть 16 цифр:")
        return

    await state.update_data(number=number)
    await message.answer("Введіть термін дії (MM/YY):")
    await state.set_state(AddCardState.exp_date)


@router.message(AddCardState.exp_date)
async def get_exp_date(message: Message, state: FSMContext):
    exp = message.text.strip()
    if len(exp) != 5 or exp[2] != "/" or not (exp[:2].isdigit() and exp[3:].isdigit()):
        await message.answer("❌ Невірний формат. Введіть у форматі MM/YY:")
        return

    await state.update_data(exp_date=exp)
    await message.answer("Введіть CVV (3 цифри):")
    await state.set_state(AddCardState.cvv)


@router.message(AddCardState.cvv)
async def get_cvv(message: Message, state: FSMContext):
    cvv = message.text.strip()
    if not (cvv.isdigit() and len(cvv) == 3):
        await message.answer("❌ Введіть коректний CVV (3 цифри):")
        return

    await state.update_data(cvv=cvv)
    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        logger.error("[CARD] Відсутній номер телефону в FSM")
        return await message.answer("⚠️ Номер телефону не знайдено. Повторіть /start")

    card_data = {
        "number": data["number"],
        "exp_date": data["exp_date"],
        "cvv": data["cvv"]
    }

    try:
        result = await add_card(phone, card_data)
        if result == "duplicate":
            await message.answer("⚠️ Така картка вже існує.")
        elif result:
            await message.answer("✅ Картка додана успішно.")
        else:
            await message.answer("❌ Не вдалося додати картку. Спробуйте пізніше.")
    except Exception as e:
        logger.exception(f"[CARD] Помилка при додаванні картки: {e}")
        await message.answer("❌ Сталася помилка. Спробуйте пізніше.")

    await state.clear()
    await state.update_data(phone_number=phone)
    await message.answer("Оберіть подальші дії:", reply_markup=card_menu())


@router.message(F.text == "📋 Мої картки")
async def list_cards(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        await message.answer("⚠️ Номер телефону не знайдено.")
        return

    cards = await get_user_cards(phone)
    if not cards:
        await message.answer("❌ У вас немає збережених карток.")
        return

    text = "💳 Ваші картки:\n\n"
    for i, card in enumerate(cards, 1):
        text += f"{i}. {card['number'][:4]} **** **** {card['number'][-4:]} — {card['exp_date']}\n"

    await message.answer(text)


@router.message(F.text == "❌ Видалити картку")
async def show_cards_for_deletion(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        await message.answer("⚠️ Номер телефону не знайдено. Повторіть /start")
        return

    cards = await get_user_cards(phone)
    if not cards:
        await message.answer("❌ У вас немає збережених карток.")
        return

    for card in cards:
        card_id = card["id"]
        number = card["number"]
        masked = f"{number[:4]} **** **** {number[-4:]}"
        text = f"💳 {masked} — {card['exp_date']}"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"delete_card:{card_id}")]
        ])

        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("delete_card:"))
async def handle_card_deletion(callback: types.CallbackQuery, state: FSMContext):
    card_id = int(callback.data.split(":")[1])
    success = await delete_card_by_id(card_id)

    if success:
        await callback.message.edit_text("✅ Картку видалено.")
    else:
        await callback.message.edit_text("❌ Не вдалося видалити картку.")

    await callback.answer()


@router.message(F.text == "⬅️ Назад до меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    await message.answer("⬅️ Ви повернулись до головного меню", reply_markup=main_menu())
