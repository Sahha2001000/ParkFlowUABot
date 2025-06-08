from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import pytz

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, any_state
from loguru import logger

from telegram_bot.keyboards.menu import main_menu
from telegram_bot.services.booking_service import (
    get_all_cities,
    get_parkings_by_city,
    get_available_spots,
    get_user_cars,
    get_spot_by_id,
    book_spot,
    get_user_bookings
)
from telegram_bot.services.card_service import get_user_cards

router = Router()

STATUS_LABELS = {
    "paid": "✅ Оплачено",
    "pending": "🕒 Очікує оплату",
    "rejected": "❌ Відхилено",
}

class SpotState(StatesGroup):
    select_city = State()
    select_parking = State()
    select_spot = State()
    select_car = State()
    select_card = State()
    select_duration = State()
    confirm_booking = State()

async def push_state(state: FSMContext, new_state: State):
    data = await state.get_data()
    history = data.get("state_history", [])
    current = await state.get_state()
    if current:
        history.append(current)
    await state.update_data(state_history=history)
    await state.set_state(new_state)

def build_keyboard_from_list(options: list[str]) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=o)] for o in options]
    rows.append([KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="🏠 Головне меню")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

@router.message(F.text == "🏠 Головне меню", any_state)
async def handle_main_menu_any(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")
    await state.clear()
    if phone:
        await state.update_data(phone_number=phone)
    await message.answer("⬅️ Ви повернулись до головного меню", reply_markup=main_menu())

async def handle_navigation_buttons(message: Message, state: FSMContext):
    data = await state.get_data()
    history = data.get("state_history", [])
    phone = data.get("phone_number")

    if message.text == "🏠 Головне меню":
        await state.clear()
        if phone:
            await state.update_data(phone_number=phone)
        return await message.answer("⬅️ Ви повернулись до головного меню", reply_markup=main_menu())

    if message.text == "⬅️ Назад":
        if not history:
            await state.clear()
            if phone:
                await state.update_data(phone_number=phone)
            return await message.answer("⬅️ Ви повернулись до головного меню", reply_markup=main_menu())

        prev_state = history.pop()
        await state.set_state(prev_state)
        await state.update_data(state_history=history)

        # Правильна маршрутизація назад
        match prev_state:
            case SpotState.select_city.state:
                return await start_checking(message, state)
            case SpotState.select_parking.state:
                return await select_city(message, state)
            case SpotState.select_spot.state:
                return await select_parking(message, state)
            case SpotState.select_car.state:
                return await select_spot(message, state)
            case SpotState.select_card.state:
                return await select_car(message, state)
            case SpotState.select_duration.state:
                return await select_card(message, state)
            case SpotState.confirm_booking.state:
                return await select_duration(message, state)

        return await message.answer("⬅️ Повернулись до попереднього кроку.")


@router.message(F.text == "📍 Перевірити доступні місця")
async def start_checking(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")
    if not phone:
        return await message.answer("⚠️ Поділіться номером або введіть /start.")

    await state.clear()
    await state.update_data(phone_number=phone)

    try:
        cities = await get_all_cities()
    except Exception as e:
        logger.exception("[BOT] get_all_cities failed")
        return await message.answer("⚠️ Сервер недоступний.")

    if not cities:
        return await message.answer("Немає доступних міст.")

    await push_state(state, SpotState.select_city)
    await state.update_data(cities=cities)
    await message.answer("Оберіть місто:", reply_markup=build_keyboard_from_list(
        [f"{c['id']}: {c['name']}" for c in cities]
    ))

@router.message(SpotState.select_city)
async def select_city(message: Message, state: FSMContext):
    if message.text in ["⬅️ Назад", "🏠 Головне меню"]:
        return await handle_navigation_buttons(message, state)

    data = await state.get_data()
    cities = data.get("cities", [])
    city = next((c for c in cities if f"{c['id']}: {c['name']}" == message.text.strip()), None)
    if not city:
        return await message.answer("Місто не знайдено.")

    try:
        parkings = await get_parkings_by_city(city["id"])
    except Exception:
        logger.exception("[BOT] get_parkings_by_city failed")
        return await message.answer("⚠️ Не вдалося отримати паркінги.")

    if not parkings:
        return await message.answer("Немає паркінгів.")

    await push_state(state, SpotState.select_parking)
    await state.update_data(parkings=parkings)
    await message.answer("Оберіть паркінг:", reply_markup=build_keyboard_from_list(
        [f"{p['id']}: {p['name']}" for p in parkings]
    ))

@router.message(SpotState.select_parking)
async def select_parking(message: Message, state: FSMContext):
    if message.text in ["⬅️ Назад", "🏠 Головне меню"]:
        return await handle_navigation_buttons(message, state)

    data = await state.get_data()
    parkings = data.get("parkings", [])
    parking = next((p for p in parkings if f"{p['id']}: {p['name']}" == message.text.strip()), None)
    if not parking:
        return await message.answer("Паркінг не знайдено.")

    try:
        spots = await get_available_spots(parking["id"])
    except Exception:
        logger.exception("[BOT] get_available_spots failed")
        return await message.answer("⚠️ Не вдалося отримати місця.")

    if not spots:
        return await message.answer("Немає вільних місць.")

    await push_state(state, SpotState.select_spot)
    await state.update_data(selected_parking=parking, spots=spots)
    await message.answer("Оберіть місце:", reply_markup=build_keyboard_from_list([
        f"{s['id']}: Місце №{s['number']}) {s['hourly_rate']} ціна за годину" for s in spots
    ]))

@router.message(SpotState.select_spot)
async def select_spot(message: Message, state: FSMContext):
    if message.text in ["⬅️ Назад", "🏠 Головне меню"]:
        return await handle_navigation_buttons(message, state)

    data = await state.get_data()
    spot = next((s for s in data.get("spots", []) if f"{s['id']}: Місце №{s['number']}) {s['hourly_rate']} ціна за годину" == message.text.strip()), None)
    if not spot:
        return await message.answer("Місце не знайдено.")

    try:
        cars = await get_user_cars(data["phone_number"])
    except Exception:
        logger.exception("[BOT] get_user_cars failed")
        return await message.answer("⚠️ Не вдалося отримати авто.")

    if not cars:
        return await message.answer("❌ У вас немає зареєстрованих авто.")

    await push_state(state, SpotState.select_car)
    await state.update_data(selected_spot=spot, cars=cars)
    await message.answer("Оберіть авто:", reply_markup=build_keyboard_from_list([
        f"{c['id']}: {c['brand']} {c['model']}: {c['license_plate']}" for c in cars
    ]))

@router.message(SpotState.select_car)
async def select_car(message: Message, state: FSMContext):
    if message.text in ["⬅️ Назад", "🏠 Головне меню"]:
        return await handle_navigation_buttons(message, state)

    data = await state.get_data()
    car = next((c for c in data.get("cars", []) if f"{c['id']}: {c['brand']} {c['model']}: {c['license_plate']}" == message.text.strip()), None)
    if not car:
        return await message.answer("Авто не знайдено.")

    try:
        cards = await get_user_cards(data["phone_number"])
    except Exception:
        logger.exception("[BOT] get_user_cards failed")
        return await message.answer("⚠️ Не вдалося отримати картки.")

    if not cards:
        return await message.answer("❌ У вас немає збережених карток.")

    await push_state(state, SpotState.select_card)
    await state.update_data(selected_car=car, cards=cards)
    await message.answer("Оберіть картку:", reply_markup=build_keyboard_from_list([
        f"{c['id']}: {c['number']}" for c in cards
    ]))

@router.message(SpotState.select_card)
async def select_card(message: Message, state: FSMContext):
    if message.text in ["⬅️ Назад", "🏠 Головне меню"]:
        return await handle_navigation_buttons(message, state)

    data = await state.get_data()
    selected = next((c for c in data.get("cards", []) if f"{c['id']}: {c['number']}" == message.text.strip()), None)
    if not selected:
        return await message.answer("❌ Картку не знайдено.")

    await push_state(state, SpotState.select_duration)
    await state.update_data(selected_card=selected)

    durations = [f"{i} годин" for i in range(1, 25)]
    await message.answer("Оберіть тривалість бронювання:", reply_markup=build_keyboard_from_list(durations))

@router.message(SpotState.select_duration)
async def select_duration(message: Message, state: FSMContext):
    if message.text in ["⬅️ Назад", "🏠 Головне меню"]:
        return await handle_navigation_buttons(message, state)

    try:
        duration_hours = int(message.text.split()[0])
    except Exception:
        return await message.answer("❌ Некоректний формат тривалості. Введіть число, напр. `2 години`")

    data = await state.get_data()
    spot = data.get("selected_spot")
    card = data.get("selected_card")
    car = data.get("selected_car")
    parking = data.get("selected_parking")

    if not spot or not card or not car or not parking:
        return await message.answer("⚠️ Дані для бронювання неповні. Спробуйте почати з початку.", reply_markup=main_menu())

    # Отримуємо ціну за годину з місця
    hourly_rate = spot.get("hourly_rate")
    if hourly_rate is None:
        return await message.answer("❌ Не вдалося отримати ціну за годину для обраного місця.")

    total_price = duration_hours * hourly_rate
    kyiv_tz = pytz.timezone("Europe/Kyiv")
    occupied_from = datetime.now(kyiv_tz)

    await push_state(state, SpotState.confirm_booking)
    await state.update_data(
        duration_hours=duration_hours,
        total_price=total_price,
        occupied_from=occupied_from.isoformat()
    )

    card_masked = f"{card['number'][:4]} **** **** {card['number'][-4:]}"
    await message.answer(
        f"📍 Паркінг: {parking['name']}\n"
        f"🅿️ Місце №{spot['number']}\n"
        f"🚗 Авто: {car['brand']} {car['model']} {car['license_plate']}\n"
        f"💳 Картка: {card_masked}\n"
        f"⏳ Тривалість: {duration_hours} год\n"
        f"💰 До сплати: {total_price} грн\n\n"
        f"✅ Підтвердити бронювання?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Так"), KeyboardButton(text="❌ Ні")],
                [KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="🏠 Головне меню")],
            ],
            resize_keyboard=True,
        ),
    )


@router.message(SpotState.confirm_booking)
async def confirm_booking(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Ні":
        await state.clear()
        return await message.answer("❌ Бронювання скасовано.", reply_markup=main_menu())
    if text in ["⬅️ Назад", "🏠 Головне меню"]:
        return await handle_navigation_buttons(message, state)
    if text != "✅ Так":
        return await message.answer("❗ Оберіть: ✅ Так або ❌ Ні")

    data = await state.get_data()
    try:
        occupied_from = datetime.fromisoformat(data["occupied_from"])
    except Exception:
        occupied_from = datetime.now(pytz.timezone("Europe/Kyiv"))

    result = await book_spot(
        spot_id=data["selected_spot"]["id"],
        car_id=data["selected_car"]["id"],
        phone_number=data["phone_number"],
        card_id=data["selected_card"]["id"],
        duration_hours=data["duration_hours"],
        occupied_from=occupied_from.isoformat(),
    )

    if not result:
        return await message.answer("❌ Помилка під час бронювання.")

    occupied_until = occupied_from + timedelta(hours=data["duration_hours"])
    await message.answer(
        f"✅ Бронювання створено!\n"
        f"🅿️ Місце №{data['selected_spot']['number']}\n"
        f"🚗 Авто: {data['selected_car']['brand']} {data['selected_car']['license_plate']}\n"
        f"💰 Сума: {result['total_price']} грн\n"
        f"🕓 З: {occupied_from.strftime('%d.%m.%Y %H:%M')}\n"
        f"🕓 По: {occupied_until.strftime('%d.%m.%Y %H:%M')}\n"
        f"📄 ID: {result['id']}\n"
        f"📅 Створено: {datetime.fromisoformat(result['created_at']).strftime('%d.%m.%Y %H:%M')}",
        reply_markup=main_menu()
    )
    await state.clear()
    await state.update_data(phone_number=data["phone_number"])

BOOKINGS_PER_PAGE = 5

async def format_booking(b, spot_cache: dict):
    try:
        spot_id = b.get("spot_id")
        if spot_id not in spot_cache:
            spot_cache[spot_id] = await get_spot_by_id(spot_id)
        spot = spot_cache[spot_id]
        if not spot:
            return f"❌ Некоректне бронювання ID {b.get('id')}"

        occupied_from = parsedate_to_datetime(spot['occupied_from']).astimezone(pytz.timezone("Europe/Kyiv"))
        occupied_until = parsedate_to_datetime(spot['occupied_until']).astimezone(pytz.timezone("Europe/Kyiv"))
        card = b.get("card", {})
        car = b.get("car", {})

        return (
            f"📄 ID: {b.get('id')}\n"
            f"🅿️ Місце №{spot.get('number', '?')}\n"
            f"🚗 Авто: {car.get('brand', '')} {car.get('license_plate', '')}\n"
            f"💳 Картка: ****{card.get('number', '')[-4:]}\n"
            f"⏳ {b.get('duration_hours')} год\n"
            f"🕓 З: {occupied_from.strftime('%d.%m.%Y %H:%M')}\n"
            f"🕓 По: {occupied_until.strftime('%d.%m.%Y %H:%M')}\n"
            f"💰 Сума: {b.get('total_price')} грн\n"
            f"{STATUS_LABELS.get(b.get('status'), '❔ Статус?')}"
        )
    except Exception as e:
        logger.exception("format_booking error")
        return f"❌ Помилка бронювання ID {b.get('id')}"

def build_bookings_keyboard(page: int, total_pages: int) -> ReplyKeyboardMarkup:
    buttons = []
    nav = []

    if page > 1:
        nav.append(KeyboardButton(text="⬅️ Попередня"))
    if page < total_pages:
        nav.append(KeyboardButton(text="➡️ Наступна"))

    if nav:
        buttons.append(nav)

    buttons.append([KeyboardButton(text="🏠 Головне меню")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
@router.message(F.text == "ℹ️ Статус бронювання")
async def handle_booking_status(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")
    if not phone:
        return await message.answer("⚠️ Поділіться номером або введіть /start")
    bookings = await get_user_bookings(phone)
    if not bookings:
        return await message.answer("❌ У вас немає бронювань.", reply_markup=main_menu())
    bookings.sort(key=lambda b: b["created_at"], reverse=True)
    await state.update_data(bookings=bookings, booking_page=1)
    await show_booking_page(message, bookings, 1)

@router.message(F.text.in_(["⬅️ Попередня", "➡️ Наступна"]))
async def handle_booking_pagination(message: Message, state: FSMContext):
    data = await state.get_data()
    bookings = data.get("bookings", [])
    page = data.get("booking_page", 1)
    total_pages = (len(bookings) + BOOKINGS_PER_PAGE - 1) // BOOKINGS_PER_PAGE
    if message.text == "⬅️ Попередня" and page > 1:
        page -= 1
    elif message.text == "➡️ Наступна" and page < total_pages:
        page += 1
    await state.update_data(booking_page=page)
    await show_booking_page(message, bookings, page)

async def show_booking_page(message: Message, bookings: list, page: int):
    start = (page - 1) * BOOKINGS_PER_PAGE
    end = start + BOOKINGS_PER_PAGE
    chunk = bookings[start:end]
    total_pages = (len(bookings) + BOOKINGS_PER_PAGE - 1) // BOOKINGS_PER_PAGE
    spot_cache = {}
    text = "\n\n".join([await format_booking(b, spot_cache) for b in chunk])
    await message.answer(
        f"📄 Сторінка {page}/{total_pages}\n\n{text}",
        reply_markup=build_bookings_keyboard(page, total_pages),
    )
