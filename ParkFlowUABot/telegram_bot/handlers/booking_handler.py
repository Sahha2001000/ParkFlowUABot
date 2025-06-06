# booking_handler.py
from datetime import datetime, timedelta
import pytz

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from loguru import logger

# Константи статусів
STATUS_LABELS = {
    "paid": "✅ Оплачено",
    "pending": "🕒 Очікує оплату",
    "rejected": "❌ Відхилено"
}

BOOKINGS_PER_PAGE = 5

from telegram_bot.keyboards.menu import main_menu, generate_keyboard
from telegram_bot.services.parking_service import (
    get_all_cities,
    get_parkings_by_city,
    get_available_spots,
    get_user_cars,
    book_spot,
    get_spot_by_id
)
from telegram_bot.services.card_service import get_user_cards
from telegram_bot.services.booking_service import get_user_bookings

router = Router()

class SpotState(StatesGroup):
    select_city = State()
    select_parking = State()
    select_spot = State()
    select_car = State()
    select_card = State()
    select_duration = State()

@router.message(F.text == "📍 Перевірити доступні місця")
async def start_checking(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")
    if not phone:
        await message.answer("⚠️ Поділіться номером або введіть /start.")
        return
    await state.clear()
    await state.update_data(phone_number=phone)
    try:
        cities = await get_all_cities()
    except Exception as e:
        logger.error(f"[BOT] get_all_cities failed: {e}")
        return await message.answer("⚠️ Сервер недоступний.")
    if not cities:
        return await message.answer("Немає доступних міст.")
    await state.set_state(SpotState.select_city)
    await state.update_data(cities=cities)
    await message.answer("Оберіть місто:", reply_markup=generate_keyboard([f"{c['id']}: {c['name']}" for c in cities]))

@router.message(SpotState.select_city)
async def select_city(message: Message, state: FSMContext):
    data = await state.get_data()
    cities = data.get("cities", [])
    city = next((c for c in cities if f"{c['id']}: {c['name']}" == message.text), None)
    if not city:
        return await message.answer("Місто не знайдено.")
    try:
        parkings = await get_parkings_by_city(city["id"])
    except Exception as e:
        logger.error(f"[BOT] get_parkings_by_city failed: {e}")
        return await message.answer("⚠️ Не вдалося отримати паркінги.")
    if not parkings:
        return await message.answer("Немає паркінгів.")
    await state.set_state(SpotState.select_parking)
    await state.update_data(parkings=parkings)
    await message.answer("Оберіть паркінг:", reply_markup=generate_keyboard([f"{p['id']}: {p['name']}" for p in parkings]))

@router.message(SpotState.select_parking)
async def select_parking(message: Message, state: FSMContext):
    data = await state.get_data()
    parkings = data.get("parkings", [])
    parking = next((p for p in parkings if f"{p['id']}: {p['name']}" == message.text), None)
    if not parking:
        return await message.answer("Паркінг не знайдено.")
    try:
        spots = await get_available_spots(parking["id"])
    except Exception as e:
        logger.error(f"[BOT] get_available_spots failed: {e}")
        return await message.answer("⚠️ Не вдалося отримати місця.")
    if not spots:
        return await message.answer("Немає вільних місць.")
    await state.set_state(SpotState.select_spot)
    await state.update_data(selected_parking=parking, spots=spots)
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f"{s['id']}: Місце №{s.get('number', '-')})")] for s in spots] +
                 [[KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="🏠 Головне меню")]],
        resize_keyboard=True
    )
    await message.answer("Оберіть місце:", reply_markup=markup)

@router.message(SpotState.select_spot)
async def select_spot(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    if text in ["⬅️ Назад", "🏠 Головне меню"]:
        await state.set_state(SpotState.select_city if text == "⬅️ Назад" else None)
        return await message.answer("⬅️ Повернулись до меню", reply_markup=main_menu())
    spot = next((s for s in data.get("spots", []) if f"{s['id']}: Місце №{s.get('number', '-')})" == text), None)
    if not spot:
        return await message.answer("Місце не знайдено.")
    try:
        cars = await get_user_cars(data["phone_number"])
    except Exception as e:
        logger.error(f"[BOT] get_user_cars failed: {e}")
        return await message.answer("⚠️ Не вдалося отримати авто.")
    if not cars:
        return await message.answer("❌ У вас немає зареєстрованих авто.")
    await state.set_state(SpotState.select_car)
    await state.update_data(selected_spot=spot, cars=cars)
    await message.answer("Оберіть авто:", reply_markup=generate_keyboard([f"{c['id']}: {c['brand']} {c['license_plate']}" for c in cars]))

@router.message(SpotState.select_car)
async def select_car(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    car = next((c for c in data.get("cars", []) if f"{c['id']}: {c['brand']} {c['license_plate']}" == text), None)
    if not car:
        return await message.answer("Авто не знайдено.")
    try:
        cards = await get_user_cards(data["phone_number"])
    except Exception as e:
        logger.error(f"[BOT] get_user_cards failed: {e}")
        return await message.answer("⚠️ Не вдалося отримати картки.")
    if not cards:
        return await message.answer("❌ У вас немає збережених карток.")
    await state.set_state(SpotState.select_card)
    await state.update_data(selected_car=car, cards=cards)
    await message.answer("Оберіть картку:", reply_markup=generate_keyboard([f"{c['id']}: {c['number']}" for c in cards]))

@router.message(SpotState.select_card)
async def select_card(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    card = next((c for c in data.get("cards", []) if f"{c['id']}: {c['number']}" == text), None)
    if not card:
        return await message.answer("Картку не знайдено.")
    await state.set_state(SpotState.select_duration)
    await state.update_data(selected_card=card)
    await message.answer("Оберіть тривалість бронювання:", reply_markup=generate_keyboard([f"{i} годин" for i in range(1, 25)]))

@router.message(SpotState.select_duration)
async def select_duration(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        duration_hours = int(message.text.split()[0])
    except:
        return await message.answer("Некоректна тривалість.")
    phone = data["phone_number"]
    spot = data["selected_spot"]
    car = data["selected_car"]
    card = data["selected_card"]
    kyiv_tz = pytz.timezone("Europe/Kyiv")
    try:
        occupied_from_str = spot["occupied_from"]
        occupied_from = datetime.strptime(occupied_from_str, "%a, %d %b %Y %H:%M:%S %Z").astimezone(kyiv_tz)
    except Exception:
        occupied_from = datetime.now(kyiv_tz)
    booking = await book_spot(
        spot_id=spot["id"],
        car_id=car["id"],
        phone_number=phone,
        card_id=card["id"],
        duration_hours=duration_hours,
        occupied_from=occupied_from.isoformat()
    )
    if booking:
        await message.answer(
            f"✅ Місце №{spot.get('number', '-')} заброньовано.\n"
            f"🚗 Авто: {car['brand']} {car.get('model', '')} {car['license_plate']}\n"
            f"💳 Картка: ****{card['number'][-4:]}\n"
            f"⏳ Тривалість: {duration_hours} год\n"
            f"🧾 Бронювання ID: {booking['id']}\n"
            f"💰 Сума: {booking['total_price']} грн\n"
            f"🗓 Зайнято з: {occupied_from.strftime('%d.%m.%Y %H:%M')}\n"
            f"🗓 До: {(occupied_from + timedelta(hours=duration_hours)).strftime('%d.%m.%Y %H:%M')}\n"
            f"📅 Створено: {datetime.fromisoformat(booking['created_at']).strftime('%d.%m.%Y %H:%M')}\n"
            f"📆 Оплата: {datetime.fromisoformat(booking['paid_at']).strftime('%d.%m.%Y %H:%M') if booking.get('paid_at') else '—'}\n"
            f"{STATUS_LABELS.get(booking['status'].lower(), '❔ Невідомий статус')}",
            reply_markup=main_menu()
        )
    else:
        await message.answer("❌ Не вдалося створити бронювання.", reply_markup=main_menu())
    await state.clear()
    await state.update_data(phone_number=phone)


STATUS_LABELS = {
    "paid": "✅ Оплачено",
    "pending": "🕒 Очікує оплату",
    "rejected": "❌ Відхилено"
}

BOOKINGS_PER_PAGE = 5

from datetime import datetime

def format_date_for_display(raw: str) -> str:
    if not raw:
        return "—"
    try:
        # Пробуємо різні формати
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%a, %d %b %Y %H:%M:%S %Z"):
            try:
                dt = datetime.strptime(raw.strip(), fmt)
                break
            except:
                continue
        else:
            return "—"
        # Додаємо +3 години (UTC → Europe/Kyiv)
        dt_kyiv = dt + timedelta(hours=3)
        return dt_kyiv.strftime("%d.%m.%Y %H:%M")
    except:
        return "—"



@router.message(F.text == "ℹ️ Статус бронювання")
async def show_booking_status(message: Message, state: FSMContext):
    # Get phone from state or request it
    data = await state.get_data()
    phone = data.get("phone_number")

    if not phone:
        await message.answer("⚠️ Будь ласка, поділіться номером телефону або введіть /start.")
        return

    try:
        # Fetch user bookings
        bookings = await get_user_bookings(phone)
        logger.info(f"[BOT] Отримано бронювань: {len(bookings)} для {phone}")

        if not bookings:
            await message.answer("📭 У вас немає активних бронювань.")
            return

        # Clear previous booking data but keep phone
        await state.clear()
        await state.update_data(
            phone_number=phone,
            bookings=bookings,
            bookings_page=0
        )

        # Show first page
        await send_booking_page(message, state, 0)

    except Exception as e:
        logger.error(f"[BOT] Помилка отримання бронювань: {e}")
        await message.answer("⚠️ Сталася помилка при отриманні бронювань. Спробуйте пізніше.")


@router.message(F.text.in_(["⬅️ Попередні", "➡️ Наступні"]))
async def paginate_bookings(message: Message, state: FSMContext):
    # Verify we have required data
    data = await state.get_data()
    phone = data.get("phone_number")
    bookings = data.get("bookings", [])
    current_page = data.get("bookings_page", 0)

    if not phone:
        await message.answer("⚠️ Сесія оновилась. Введіть /start.")
        return

    if not bookings:
        await message.answer("⚠️ Дані про бронювання втрачені. Спробуйте знову.")
        return

    # Calculate new page
    max_page = (len(bookings) - 1) // BOOKINGS_PER_PAGE

    if message.text == "⬅️ Попередні":
        new_page = max(current_page - 1, 0)
    else:
        new_page = min(current_page + 1, max_page)

    # Update state and show page
    await state.update_data(
        bookings_page=new_page,
        phone_number=phone  # Always preserve phone
    )
    await send_booking_page(message, state, new_page)


async def send_booking_page(message: Message, state: FSMContext, page: int):
    data = await state.get_data()
    phone = data.get("phone_number")
    bookings = data.get("bookings", [])

    # Validate data
    if not phone or not bookings:
        await message.answer("⚠️ Дані про бронювання втрачені. Спробуйте знову.")
        return

    try:
        # Get related data
        cars = await get_user_cars(phone) or []
        cards = await get_user_cards(phone) or []

        # Paginate bookings
        start_idx = page * BOOKINGS_PER_PAGE
        page_bookings = bookings[start_idx: start_idx + BOOKINGS_PER_PAGE]

        # Prepare messages
        messages = []
        for booking in page_bookings:
            try:
                car = next((c for c in cars if c["id"] == booking["car_id"]), {})
                card = next((c for c in cards if c["id"] == booking["card_id"]), {})
                spot = await get_spot_by_id(booking["spot_id"]) or {}
            except Exception as e:
                logger.warning(f"[BOT] Не вдалося отримати дані для бронювання {booking['id']}: {e}")
                continue

            status = booking.get("status", "").lower()
            status_label = STATUS_LABELS.get(status, "❔ Невідомий статус")

            created_date = format_date_for_display(booking.get("created_at", ""))
            paid_date = format_date_for_display(booking.get("paid_at", ""))
            occupied_from = format_date_for_display(spot.get("occupied_from", ""))
            occupied_until = format_date_for_display(spot.get("occupied_until", ""))

            card_number = card.get('number', '0000000000000000')
            card_masked = f"{card_number[:4]} **** **** {card_number[-4:]}" if card_number else "—"

            msg = (
                f"📍 Місце №{spot.get('number', '-')}\n"
                f"🚗 Авто: {car.get('brand', '-')} {car.get('model', '-')} {car.get('license_plate', '???')}\n"
                f"💳 Картка: {card_masked}\n"
                f"⏳ Тривалість: {booking['duration_hours']} год\n"
                f"💰 Сума: {booking['total_price']} грн\n"
                f"🆔 Бронювання ID: {booking['id']}\n"
                f"🗓 Зайнято з: {occupied_from}\n"
                f"🗓 До: {occupied_until}\n"
                f"📅 Створено: {created_date}\n"
                f"📆 Оплата: {paid_date}\n"
                f"{status_label}"
            )

            messages.append(msg)

        # Send messages if any
        if messages:
            await message.answer("\n\n".join(messages))
        else:
            await message.answer("⚠️ Не вдалося показати бронювання.")

        # Prepare navigation buttons
        max_page = (len(bookings) - 1) // BOOKINGS_PER_PAGE
        buttons = []

        if page > 0:
            buttons.append(KeyboardButton(text="⬅️ Попередні"))
        if page < max_page:
            buttons.append(KeyboardButton(text="➡️ Наступні"))

        buttons.append(KeyboardButton(text="🏠 Головне меню"))

        # Send navigation
        await message.answer(
            "Оберіть дію:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[buttons],
                resize_keyboard=True
            )
        )

    except Exception as e:
        logger.error(f"[BOT] Помилка показу сторінки: {e}")
        await message.answer("⚠️ Сталася помилка. Спробуйте пізніше.")

@router.message(F.text == "🏠 Головне меню")
async def go_to_main_menu(message: Message, state: FSMContext):
    # Clear all data except phone if exists
    data = await state.get_data()
    phone = data.get("phone_number")

    await state.clear()
    if phone:
        await state.update_data(phone_number=phone)

    await message.answer(
        "⬅️ Ви повернулись до головного меню",
        reply_markup=main_menu()
    )