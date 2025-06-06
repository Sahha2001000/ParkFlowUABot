from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from loguru import logger


def main_menu():
    logger.debug("Формування клавіатури головного меню")
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚘 Мої авто")],
            [KeyboardButton(text="📍 Перевірити доступні місця")],
            [KeyboardButton(text="ℹ️ Статус бронювання")],
            [KeyboardButton(text="💳 Картки")],
            [KeyboardButton(text="⚙️ Налаштування")]
        ],
        resize_keyboard=True
    )


def settings_menu():
    logger.debug("Формування клавіатури меню налаштувань")
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Отримати інформацію про себе")],
            [KeyboardButton(text="✏️ Змінити ім'я")],
            [KeyboardButton(text="📧 Змінити email")],
            [KeyboardButton(text="❌ Видалити мій профіль")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )


retry_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔁 Спробувати ще раз")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

error_retry_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔁 Повторити спробу")],
        [KeyboardButton(text="⬅️ Назад до меню")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

contact_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📞 Надати номер телефону", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)
def car_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Додати авто")],
            [KeyboardButton(text="📋 Переглянути мої авто")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )


def generate_keyboard(items):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=item)] for item in items],
        resize_keyboard=True
    )

back_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅️ Назад")]],
    resize_keyboard=True
)
def card_menu():
    logger.debug("Формування меню керування картками")
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Додати картку")],
            [KeyboardButton(text="📋 Мої картки")],
            [KeyboardButton(text="❌ Видалити картку")],
            [KeyboardButton(text="⬅️ Назад до меню")]
        ],
        resize_keyboard=True
    )