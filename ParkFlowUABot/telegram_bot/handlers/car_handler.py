from datetime import datetime

import self
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from loguru import logger

from telegram_bot.keyboards.menu import main_menu
from telegram_bot.services.api_service import is_api_available
from telegram_bot.services.car_service import (
    add_car_phone,
    get_user_cars,
    update_car_by_id,
    delete_car_by_id
)

router = Router()


class AddCarState(StatesGroup):
    brand = State()
    model = State()
    year = State()
    license_plate = State()


class UpdateCarState(StatesGroup):
    select_car = State()
    new_brand = State()
    new_model = State()
    new_year = State()


def cars_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚘 Додати авто")],
            [KeyboardButton(text="📋 Список авто")],
            [KeyboardButton(text="✏️ Змінити авто")],
            [KeyboardButton(text="🗑 Видалити авто")],
            [KeyboardButton(text="⬅️ Назад до меню")]
        ],
        resize_keyboard=True
    )


@router.message(F.text == "🚘 Мої авто")
async def open_cars_menu(message: Message, state: FSMContext):
    logger.info(f"[CAR] User {message.from_user.id} opened cars menu")
    await state.update_data(last_menu="main")
    await message.answer("Оберіть дію з автомобілями:", reply_markup=cars_menu_keyboard())


@router.message(F.text == "🚘 Додати авто")
async def start_add_car(message: Message, state: FSMContext):
    logger.info(f"[CAR] User {message.from_user.id} started adding car")
    await message.answer("Введіть марку авто:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddCarState.brand)


@router.message(AddCarState.brand)
async def get_car_brand(message: Message, state: FSMContext):
    brand = message.text.strip()
    if len(brand) < 2:
        await message.answer("❌ Назва марки занадто коротка. Введіть ще раз:")
        return

    await state.update_data(brand=brand)
    await message.answer("Введіть модель авто:")
    await state.set_state(AddCarState.model)


@router.message(AddCarState.model)
async def get_car_model(message: Message, state: FSMContext):
    model = message.text.strip()
    if len(model) < 1:
        await message.answer("❌ Назва моделі занадто коротка. Введіть ще раз:")
        return

    await state.update_data(model=model)
    await message.answer("Введіть рік випуску авто (наприклад, 2010):")
    await state.set_state(AddCarState.year)


@router.message(AddCarState.year)
async def get_car_year(message: Message, state: FSMContext):
    year = message.text.strip()
    if not year.isdigit() or not (1900 <= int(year) <= datetime.now().year + 1):
        await message.answer(f"❌ Введіть коректний рік (1900-{datetime.now().year + 1}):")
        return

    await state.update_data(year=int(year))
    await message.answer("Введіть державний номер авто (формат: АА1234ВК):")
    await state.set_state(AddCarState.license_plate)


@router.message(AddCarState.license_plate)
async def get_car_license_plate(message: Message, state: FSMContext):
    license_plate = message.text.strip().upper().replace("і", "І")
    if not self.validate_license_plate(license_plate):
        await message.answer("❌ Невірний формат номеру. Введіть у форматі АА1234ВК:")
        return

    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        await message.answer("⚠️ Помилка ідентифікації. Спробуйте знову.")
        return

    try:
        result = await add_car_phone(phone, {
            "brand": data["brand"],
            "model": data["model"],
            "year": data["year"],
            "license_plate": license_plate
        })

        if result == "duplicate":
            await message.answer("⚠️ Авто з таким номером вже існує.")
        elif result:
            await message.answer(
                "✅ Авто успішно додано:\n"
                f"Марка: {data['brand']}\n"
                f"Модель: {data['model']}\n"
                f"Рік: {data['year']}\n"
                f"Номер: {license_plate}"
            )
        else:
            await message.answer("❌ Не вдалося додати авто. Спробуйте пізніше.")
    except Exception as e:
        logger.error(f"[CAR] Помилка додавання авто: {e}")
        await message.answer("❌ Сталася помилка. Спробуйте пізніше.")

    await state.clear()
    await state.update_data(phone_number=phone)
    await message.answer("Оберіть подальші дії:", reply_markup=cars_menu_keyboard())


def validate_license_plate(plate: str) -> bool:
    return (
            len(plate) == 8 and
            plate[:2].isalpha() and
            plate[2:6].isdigit() and
            plate[6:].isalpha()
    )


@router.message(F.text == "📋 Список авто")
async def list_user_cars(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        await message.answer("⚠️ Помилка ідентифікації. Спробуйте знову.")
        return

    try:
        cars = await get_user_cars(phone)
        if not cars:
            await message.answer("📭 У вас немає зареєстрованих авто.")
            return

        response = "🚘 Ваші автомобілі:\n\n"
        for i, car in enumerate(cars, 1):
            response += (
                f"{i}. {car['brand']} {car['model']} {car['year']}\n"
                f"   Номер: {car['license_plate']}\n\n"
            )
        await message.answer(response)
    except Exception as e:
        logger.error(f"[CAR] Помилка отримання списку авто: {e}")
        await message.answer("❌ Не вдалося завантажити список авто.")


@router.message(F.text == "🗑 Видалити авто")
async def start_delete_car(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        await message.answer("⚠️ Помилка ідентифікації. Спробуйте знову.")
        return

    try:
        cars = await get_user_cars(phone)
        if not cars:
            await message.answer("📭 У вас немає авто для видалення.")
            return

        for car in cars:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🗑 Видалити",
                    callback_data=f"delete_car:{car['license_plate']}"
                )]
            ])
            await message.answer(
                f"{car['brand']} {car['model']} {car['year']}\n"
                f"Номер: {car['license_plate']}",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"[CAR] Помилка отримання авто для видалення: {e}")
        await message.answer("❌ Не вдалося завантажити список авто.")


@router.callback_query(F.data.startswith("delete_car:"))
async def handle_car_deletion(callback: CallbackQuery, state: FSMContext):
    license_plate = callback.data.split(":")[1]
    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        await callback.answer("⚠️ Помилка ідентифікації.")
        return

    try:
        success = await delete_car_by_id(phone, license_plate)
        if success:
            await callback.message.edit_text("✅ Авто успішно видалено.")
        else:
            await callback.message.edit_text("❌ Не вдалося видалити авто.")
    except Exception as e:
        logger.error(f"[CAR] Помилка видалення авто: {e}")
        await callback.message.edit_text("❌ Сталася помилка при видаленні.")

    await callback.answer()


@router.message(F.text == "✏️ Змінити авто")
async def start_update_car(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        await message.answer("⚠️ Помилка ідентифікації. Спробуйте знову.")
        return

    try:
        cars = await get_user_cars(phone)
        if not cars:
            await message.answer("📭 У вас немає авто для зміни.")
            return

        for car in cars:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="✏️ Змінити",
                    callback_data=f"update_car:{car['license_plate']}"
                )]
            ])
            await message.answer(
                f"{car['brand']} {car['model']} {car['year']}\n"
                f"Номер: {car['license_plate']}",
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"[CAR] Помилка отримання авто для зміни: {e}")
        await message.answer("❌ Не вдалося завантажити список авто.")


@router.callback_query(F.data.startswith("update_car:"))
async def handle_car_update_selection(callback: CallbackQuery, state: FSMContext):
    license_plate = callback.data.split(":")[1]
    await state.update_data(selected_car_plate=license_plate)
    await state.set_state(UpdateCarState.new_brand)
    await callback.message.answer("Введіть нову марку авто:")
    await callback.answer()


@router.message(UpdateCarState.new_brand)
async def get_updated_brand(message: Message, state: FSMContext):
    brand = message.text.strip()
    if len(brand) < 2:
        await message.answer("❌ Назва марки занадто коротка. Введіть ще раз:")
        return

    await state.update_data(new_brand=brand)
    await message.answer("Введіть нову модель авто:")
    await state.set_state(UpdateCarState.new_model)


@router.message(UpdateCarState.new_model)
async def get_updated_model(message: Message, state: FSMContext):
    model = message.text.strip()
    if len(model) < 1:
        await message.answer("❌ Назва моделі занадто коротка. Введіть ще раз:")
        return

    await state.update_data(new_model=model)
    await message.answer("Введіть новий рік випуску авто:")
    await state.set_state(UpdateCarState.new_year)


@router.message(UpdateCarState.new_year)
async def finish_car_update(message: Message, state: FSMContext):
    year = message.text.strip()
    if not year.isdigit() or not (1900 <= int(year) <= datetime.now().year + 1):
        await message.answer(f"❌ Введіть коректний рік (1900-{datetime.now().year + 1}):")
        return

    data = await state.get_data()
    phone = data.get("phone_number")
    license_plate = data.get("selected_car_plate")

    if not phone or not license_plate:
        await message.answer("⚠️ Помилка ідентифікації. Спробуйте знову.")
        await state.clear()
        return

    try:
        success = await update_car_by_id(phone, license_plate, {
            "brand": data["new_brand"],
            "model": data["new_model"],
            "year": int(year)
        })

        if success:
            await message.answer("✅ Дані авто успішно оновлено!")
        else:
            await message.answer("❌ Не вдалося оновити дані авто.")
    except Exception as e:
        logger.error(f"[CAR] Помилка оновлення авто: {e}")
        await message.answer("❌ Сталася помилка при оновленні.")

    await state.clear()
    await state.update_data(phone_number=phone)
    await message.answer("Оберіть подальші дії:", reply_markup=cars_menu_keyboard())


@router.message(F.text == "⬅️ Назад до меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.update_data(last_menu="main")
    await message.answer("⬅️ Ви повернулись до головного меню", reply_markup=main_menu())