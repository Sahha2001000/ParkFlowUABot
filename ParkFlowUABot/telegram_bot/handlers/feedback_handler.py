from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime

from loguru import logger

from telegram_bot.services.feedback_service import send_feedback, get_all_feedbacks
from telegram_bot.services.user_service import get_user_by_phone, get_user_by_id
from telegram_bot.keyboards.menu import main_menu

router = Router()

class FeedbackStates(StatesGroup):
    typing_feedback = State()
    confirming = State()
    viewing_feedbacks = State()

FEEDBACKS_PER_PAGE = 5

# 📋 Меню
def feedback_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✍️ Надіслати відгук")],
            [KeyboardButton(text="📖 Всі відгуки")],
            [KeyboardButton(text="🏠 Головне меню")]
        ],
        resize_keyboard=True
    )

def feedback_pagination_keyboard(page: int, total_pages: int) -> ReplyKeyboardMarkup:
    buttons = []

    nav = []
    if page > 1:
        nav.append(KeyboardButton(text="⬅️ Назад"))
    if page < total_pages:
        nav.append(KeyboardButton(text="➡️ Вперед"))
    if nav:
        buttons.append(nav)

    buttons.append([KeyboardButton(text="📋 Меню відгуків")])
    buttons.append([KeyboardButton(text="🏠 Головне меню")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@router.message(F.text == "📣 Відгуки")
async def feedback_menu(message: Message, state: FSMContext):
    await state.set_state(None)
    await message.answer("Меню відгуків:", reply_markup=feedback_menu_keyboard())

@router.message(F.text == "✍️ Надіслати відгук")
async def prompt_feedback(message: Message, state: FSMContext):
    await state.set_state(FeedbackStates.typing_feedback)
    await message.answer("📝 Напишіть свій відгук:", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    ))

@router.message(FeedbackStates.typing_feedback)
async def save_draft(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        return await feedback_menu(message, state)

    await state.update_data(draft=message.text.strip())
    await state.set_state(FeedbackStates.confirming)
    await message.answer(
        f"📄 Ваш відгук:\n\n{message.text.strip()}\n\n"
        "Натисніть 📤 Відправити або ⬅️ Назад для редагування.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📤 Відправити")],
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
    )

@router.message(FeedbackStates.confirming)
async def send_final_feedback(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.set_state(FeedbackStates.typing_feedback)
        return await message.answer("✍️ Введіть новий текст відгуку:")

    if message.text != "📤 Відправити":
        return await message.answer("❗ Натисніть 📤 Відправити або ⬅️ Назад.")

    data = await state.get_data()
    phone = data.get("phone_number")
    feedback_text = data.get("draft", "").strip()

    if not phone:
        await state.clear()
        return await message.answer("⚠️ Телефон не знайдено. Спробуйте /start.", reply_markup=main_menu())

    user = await get_user_by_phone(phone)
    if not user:
        await state.clear()
        return await message.answer("❌ Користувача не знайдено.", reply_markup=main_menu())

    user_id = user["id"]
    await send_feedback(user_id=user_id, text=feedback_text)

    await message.answer("✅ Ваш відгук надіслано. Дякуємо!", reply_markup=feedback_menu_keyboard())
    await state.clear()
    await state.update_data(phone_number=phone)  # повертаємо телефон у контекст

@router.message(F.text == "📖 Всі відгуки")
async def view_all_feedbacks(message: Message, state: FSMContext):
    feedbacks = await get_all_feedbacks()
    if not feedbacks:
        return await message.answer("😔 Ще немає жодного відгуку.")

    await state.set_state(FeedbackStates.viewing_feedbacks)
    await state.update_data(feedback_page=1)
    await send_feedback_page(message, feedbacks, page=1)

@router.message(F.text.in_(["⬅️ Назад", "➡️ Вперед"]))
async def paginate_feedbacks(message: Message, state: FSMContext):
    feedbacks = await get_all_feedbacks()
    if not feedbacks:
        return await message.answer("😔 Відгуки відсутні.")

    data = await state.get_data()
    page = data.get("feedback_page", 1)
    total_pages = (len(feedbacks) + FEEDBACKS_PER_PAGE - 1) // FEEDBACKS_PER_PAGE

    if message.text == "⬅️ Назад" and page > 1:
        page -= 1
    elif message.text == "➡️ Вперед" and page < total_pages:
        page += 1

    await state.update_data(feedback_page=page)
    await send_feedback_page(message, feedbacks, page)

async def send_feedback_page(message: Message, feedbacks: list, page: int):
    total_pages = (len(feedbacks) + FEEDBACKS_PER_PAGE - 1) // FEEDBACKS_PER_PAGE
    start = (page - 1) * FEEDBACKS_PER_PAGE
    end = start + FEEDBACKS_PER_PAGE
    chunk = feedbacks[::-1][start:end]

    lines = []

    for fb in chunk:
        user = await get_user_by_id(fb["user_id"])
        if user:
            full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        else:
            full_name = "Видалений акаунт"

        created_at = fb.get("timestamp") or fb.get("created_at") or "—"
        try:
            created_at = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
        except Exception:
            pass

        lines.append(
            f"👤 {full_name} (ID: {fb['user_id']})\n"
            f"🕓 {created_at}\n"
            f"💬 {fb['text']}"
        )

    await message.answer(
        f"📝 Відгуки (сторінка {page}/{total_pages}):\n\n" + "\n\n".join(lines),
        reply_markup=feedback_pagination_keyboard(page, total_pages)
    )

@router.message(F.text == "📋 Меню відгуків")
async def back_to_feedback_menu(message: Message, state: FSMContext):
    await state.set_state(None)
    await message.answer("Меню відгуків:", reply_markup=feedback_menu_keyboard())

@router.message(F.text == "🏠 Головне меню")
async def to_main(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone_number")
    await state.clear()
    if phone:
        await state.update_data(phone_number=phone)
    await message.answer("⬅️ Ви повернулись до головного меню", reply_markup=main_menu())
