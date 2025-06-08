from datetime import datetime
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from loguru import logger

from telegram_bot.keyboards.menu import main_menu
from telegram_bot.services.car_service import (
    add_car_phone,
    get_user_cars,
    update_car_by_id,
    delete_car_by_id
)

router = Router()


# Стани FSM
class AddCarState(StatesGroup):
    brand = State()
    model = State()
    year = State()
    license_plate = State()


class UpdateCarState(StatesGroup):
    brand = State()
    model = State()
    year = State()
    selected_plate = State()


# Кнопки
def back_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )


def cars_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Список авто")],
            [KeyboardButton(text="🚘 Додати авто")],
            [KeyboardButton(text="✏️ Змінити авто")],
            [KeyboardButton(text="🗑 Видалити авто")],
            [KeyboardButton(text="⬅️ Назад до меню")]
        ],
        resize_keyboard=True
    )


def validate_license_plate(plate: str) -> bool:
    return (
        len(plate) == 8 and
        plate[:2].isalpha() and
        plate[2:6].isdigit() and
        plate[6:].isalpha()
    )


# Меню авто
@router.message(F.text == "🚘 Мої авто")
async def open_cars_menu(message: Message, state: FSMContext):
    await state.update_data(last_menu="main")
    await message.answer("Оберіть дію з автомобілями:", reply_markup=cars_menu_keyboard())


# 📋 Список авто
@router.message(F.text == "📋 Список авто")
async def list_user_cars(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")
    if not phone:
        await message.answer("⚠️ Не вдалося визначити номер телефону.")
        return
    try:
        cars = await get_user_cars(phone)
        if not cars:
            await message.answer("📭 У вас немає зареєстрованих авто.")
            return
        text = "🚘 Ваші авто:\n\n"
        for i, car in enumerate(cars, 1):
            text += (
                f"{i}. {car['brand']} {car['model']} {car['year']}\n"
                f"   Номер: {car['license_plate']}\n\n"
            )
        await message.answer(text)
    except Exception as e:
        logger.error(f"[CAR] list_user_cars error: {e}")
        await message.answer("❌ Помилка при завантаженні авто.")


# 🚘 Додати авто
@router.message(F.text == "🚘 Додати авто")
async def start_add_car(message: Message, state: FSMContext):
    await message.answer("Введіть марку авто:", reply_markup=back_kb())
    await state.set_state(AddCarState.brand)


@router.message(AddCarState.brand)
async def get_brand(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        data = await state.get_data()
        phone = data.get("phone_number")
        await state.clear()
        if phone:
            await state.update_data(phone_number=phone)
        await message.answer("↩️ Повертаємось до меню авто:", reply_markup=cars_menu_keyboard())
        return
    brand = message.text.strip()
    if len(brand) < 2:
        await message.answer("❌ Назва занадто коротка.", reply_markup=back_kb())
        return
    await state.update_data(brand=brand)
    await message.answer("Введіть модель авто:", reply_markup=back_kb())
    await state.set_state(AddCarState.model)


@router.message(AddCarState.model)
async def get_model(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        data = await state.get_data()
        phone = data.get("phone_number")
        await state.clear()
        if phone:
            await state.update_data(phone_number=phone)
        await message.answer("↩️ Повертаємось до меню авто:", reply_markup=cars_menu_keyboard())
        return
    model = message.text.strip()
    if len(model) < 1:
        await message.answer("❌ Назва занадто коротка.", reply_markup=back_kb())
        return
    await state.update_data(model=model)
    await message.answer("Введіть рік випуску:", reply_markup=back_kb())
    await state.set_state(AddCarState.year)


@router.message(AddCarState.year)
async def get_year(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        data = await state.get_data()
        phone = data.get("phone_number")
        await state.clear()
        if phone:
            await state.update_data(phone_number=phone)
        await message.answer("↩️ Повертаємось до меню авто:", reply_markup=cars_menu_keyboard())
        return
    year = message.text.strip()
    if not year.isdigit() or not (1900 <= int(year) <= datetime.now().year + 1):
        await message.answer("❌ Невірний рік.", reply_markup=back_kb())
        return
    await state.update_data(year=int(year))
    await message.answer("Введіть номер авто (АА1234ВК):", reply_markup=back_kb())
    await state.set_state(AddCarState.license_plate)


@router.message(AddCarState.license_plate)
async def get_plate(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        data = await state.get_data()
        phone = data.get("phone_number")
        await state.clear()
        if phone:
            await state.update_data(phone_number=phone)
        await message.answer("↩️ Повертаємось до меню авто:", reply_markup=cars_menu_keyboard())
        return
    plate = message.text.strip().upper().replace("і", "І")
    if not validate_license_plate(plate):
        await message.answer("❌ Невірний формат.", reply_markup=back_kb())
        return
    data = await state.get_data()
    phone = data.get("phone_number")
    if not phone:
        await message.answer("⚠️ Немає номера телефону.")
        return
    try:
        result = await add_car_phone(phone, {
            "brand": data["brand"],
            "model": data["model"],
            "year": data["year"],
            "license_plate": plate
        })
        if result == "duplicate":
            await message.answer("⚠️ Авто вже існує.")
        elif result:
            await message.answer(f"✅ Авто додано: {plate}")
        else:
            await message.answer("❌ Не вдалося додати авто.")
    except Exception as e:
        logger.error(f"[CAR] Add error: {e}")
        await message.answer("❌ Помилка при додаванні.")
    await state.clear()
    await state.update_data(phone_number=phone)
    await message.answer("Оберіть подальшу дію:", reply_markup=cars_menu_keyboard())


# ✏️ Змінити авто
@router.message(F.text == "✏️ Змінити авто")
async def start_update_car(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")
    if not phone:
        await message.answer("⚠️ Немає телефону.")
        return
    try:
        cars = await get_user_cars(phone)
        if not cars:
            await message.answer("📭 Авто не знайдено.")
            return
        for car in cars:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✏️ Змінити", callback_data=f"edit:{car['license_plate']}")
            ]])
            await message.answer(
                f"{car['brand']} {car['model']} {car['year']}\nНомер: {car['license_plate']}",
                reply_markup=kb
            )
    except Exception as e:
        logger.error(f"[CAR] update list error: {e}")
        await message.answer("❌ Помилка при завантаженні.")


@router.callback_query(F.data.startswith("edit:"))
async def select_car_for_update(callback: CallbackQuery, state: FSMContext):
    plate = callback.data.split(":")[1]
    await state.update_data(selected_plate=plate)
    await state.set_state(UpdateCarState.brand)
    await callback.message.answer("Введіть нову марку авто:", reply_markup=back_kb())
    await callback.answer()


@router.message(UpdateCarState.brand)
async def update_brand(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        data = await state.get_data()
        phone = data.get("phone_number")
        await state.clear()
        if phone:
            await state.update_data(phone_number=phone)
        await message.answer("↩️ Повертаємось до меню авто:", reply_markup=cars_menu_keyboard())
        return
    brand = message.text.strip()
    if len(brand) < 2:
        await message.answer("❌ Занадто коротка марка.", reply_markup=back_kb())
        return
    await state.update_data(brand=brand)
    await message.answer("Введіть нову модель авто:", reply_markup=back_kb())
    await state.set_state(UpdateCarState.model)


@router.message(UpdateCarState.model)
async def update_model(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        data = await state.get_data()
        phone = data.get("phone_number")
        await state.clear()
        if phone:
            await state.update_data(phone_number=phone)
        await message.answer("↩️ Повертаємось до меню авто:", reply_markup=cars_menu_keyboard())
        return
    model = message.text.strip()
    if len(model) < 1:
        await message.answer("❌ Занадто коротка модель.", reply_markup=back_kb())
        return
    await state.update_data(model=model)
    await message.answer("Введіть новий рік:", reply_markup=back_kb())
    await state.set_state(UpdateCarState.year)


@router.message(UpdateCarState.year)
async def update_year(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        data = await state.get_data()
        phone = data.get("phone_number")
        await state.clear()
        if phone:
            await state.update_data(phone_number=phone)
        await message.answer("↩️ Повертаємось до меню авто:", reply_markup=cars_menu_keyboard())
        return
    year = message.text.strip()
    if not year.isdigit() or not (1900 <= int(year) <= datetime.now().year + 1):
        await message.answer("❌ Введіть коректний рік.", reply_markup=back_kb())
        return

    data = await state.get_data()
    phone = data.get("phone_number")
    plate = data.get("selected_plate")

    if not phone or not plate:
        await message.answer("⚠️ Дані втрачені.")
        await state.clear()
        return

    try:
        result = await update_car_by_id(phone, plate, {
            "brand": data["brand"],
            "model": data["model"],
            "year": int(year)
        })
        if result:
            await message.answer("✅ Авто оновлено.")
        else:
            await message.answer("❌ Не вдалося оновити авто.")
    except Exception as e:
        logger.error(f"[CAR] update error: {e}")
        await message.answer("❌ Помилка при оновленні.")
    await state.clear()
    await state.update_data(phone_number=phone)
    await message.answer("Оберіть подальшу дію:", reply_markup=cars_menu_keyboard())


# 🗑 Видалення авто
@router.message(F.text == "🗑 Видалити авто")
async def start_delete_car(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")
    if not phone:
        await message.answer("⚠️ Немає телефону.")
        return
    try:
        cars = await get_user_cars(phone)
        if not cars:
            await message.answer("📭 Авто не знайдено.")
            return
        for car in cars:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🗑 Видалити", callback_data=f"delete:{car['license_plate']}")
            ]])
            await message.answer(
                f"{car['brand']} {car['model']} {car['year']}\nНомер: {car['license_plate']}",
                reply_markup=kb
            )
    except Exception as e:
        logger.error(f"[CAR] delete error: {e}")
        await message.answer("❌ Помилка при видаленні.")


@router.callback_query(F.data.startswith("delete:"))
async def delete_car(callback: CallbackQuery, state: FSMContext):
    plate = callback.data.split(":")[1]
    data = await state.get_data()
    phone = data.get("phone_number")
    if not phone:
        await callback.answer("⚠️ Немає телефону.")
        return
    try:
        result = await delete_car_by_id(phone, plate)
        if result:
            await callback.message.edit_text("✅ Авто успішно видалено.")
        else:
            await callback.message.edit_text("❌ Не вдалося видалити авто.")
    except Exception as e:
        logger.error(f"[CAR] delete_car error: {e}")
        await callback.message.edit_text("❌ Помилка при видаленні.")
    await callback.answer()


# Назад до меню
@router.message(F.text == "⬅️ Назад до меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    await message.answer("⬅️ Ви повернулись до головного меню", reply_markup=main_menu())
