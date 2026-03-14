from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder,InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest # Импортируем исключение
from config import ADMIN_IDS
import database as db
#Создаем логгер
from config import init_logging
init_logging()
import logging
logger = logging.getLogger(__name__)
#----------------------------
router = Router()



@router.message(Command("start"))
async def cmd_start(message: types.Message):
    logger.info(f"Вход пользователя: {message.from_user.full_name} id: {message.from_user.id}")
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
        logger.info("Вывод меню администратора")        
        builder.row(InlineKeyboardButton(text="📝 Список (Редактировать)", callback_data="show_categories"))
        text = "👋 Приветсвую, администратор!"
    else: #Меню для юзера
        logger.info("Вывод меню покупателя")
        builder.row(InlineKeyboardButton(text="📚 Посмотреть каталог", callback_data="show_categories"))    
        text = "👋 Приветствую Вас в магазине учебных пособий!\nНажмите кнопку ниже, чтобы выбрать продукт:"

    kb = builder.as_markup()

    if isinstance(event, types.CallbackQuery):
        try:
            # Пытаемся отредактировать
            await event.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отредактировать предыдущее сообщение бота: {e}")
            pass
    else:
        # Если ввели /start — шлем новое
        await event.answer(text, reply_markup=kb)

