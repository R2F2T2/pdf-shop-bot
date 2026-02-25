from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder,InlineKeyboardButton
from aiogram.types import LabeledPrice, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramBadRequest # Импортируем исключение
import database as db
import os

router = Router()
#raw_id = os.getenv("ADMIN_ID")
#ADMIN_ID = int(raw_id)
raw_ids = os.getenv("ADMIN_IDS", "")
print(f"DEBUG: ADMIN_ID is {raw_ids}") # Это покажет, что прочиталось
# Читаем строку "123,456", делим по запятой и превращаем каждый элемент в int
ADMIN_IDS = [int(admin_id) for admin_id in raw_ids.split(",") if admin_id]
# Команда СТАРТ
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await show_main_menu(message)

# Кнопка НАЗАД (callback_data="main_menu")
@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await show_main_menu(callback)
    await callback.answer() # Убираем "часики"

async def show_main_menu(event: types.Message | types.CallbackQuery):
    user_id = event.from_user.id
    builder = InlineKeyboardBuilder()

    if user_id in ADMIN_IDS: #Меню для админа
        builder.row(InlineKeyboardButton(text="➕ Добавить продукт", callback_data="prod_add"))
        builder.row(InlineKeyboardButton(text="📝 Список (Редактировать)", callback_data="show_catalog"))
        text = "👋 Приветсвую, администратор!"
    else: #Меню для юзера
        builder.row(InlineKeyboardButton(text="📚 Посмотреть каталог", callback_data="show_catalog"))    
        text = "👋 Приветствую Вас в магазине учебных пособий!\nНажмите кнопку ниже, чтобы выбрать продукт:"

    kb = builder.as_markup()

    if isinstance(event, types.CallbackQuery):
        try:
            # Пытаемся отредактировать
            await event.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            # Если текст и кнопки совпали — просто игнорируем ошибку
            pass
    else:
        # Если ввели /start — шлем новое
        await event.answer(text, reply_markup=kb)

