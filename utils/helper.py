from models import DBResult
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from typing import Any
from models import Product
import database as db
#Создаем логгер
from config import init_logging
init_logging()
import logging
logger = logging.getLogger(__name__)

def handle_db_result( result: Any | DBResult)-> str | bool:

    if isinstance(result, DBResult):
        match result:
            case DBResult.NOT_FOUND: return "❌ Объект не найден в базе данных."
            case DBResult.DUPLICATE: return "⚠️ Такая запись уже существует (дубликат)\nВведите другое значение:"
            case DBResult.ERROR:     return "🆘 Произошла системная ошибка базы данных."
            case DBResult.EMPTY:     return "📂 Раздел пока пуст."
            case _:                  return "❓ Неизвестный статус базы данных."    

    return True # Все прошло успешно

def get_add_product_text(data: dict, next_step: str) -> str:
    # Собираем то, что уже введено
    category_id = data.get('category_name', '...')
    name = data.get('name', '...')
    desc = data.get('description', '...')
    price = data.get('price', '...')
    
    text = (
        f"<b>🛒 Добавление товара</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"📂 Категория: {category_id}\n"
        f"🏷 Название: {name}\n"
        f"📝 Описание: {desc}\n"
        f"💰 Цена: {price}\n"
        f"━━━━━━━━━━━━━━\n"
        f"➡️ <b>{next_step}</b>"
    )
    return text

def get_string_data(prod: Product) -> str:
    """Возвращет строку с полями объекта"""
    # Обрезаем описание и добавляем троеточие, если оно длинное
    desc = prod.description
    short_desc = (desc[:17] + '...') if len(desc) > 20 else desc
    
    # Сокращаем длинный file_id (оставляем начало и конец)
    f_id = prod.file_id
    short_id = f"{f_id[:6]}...{f_id[-4:]}" if len(f_id) > 10 else f_id
    
    return f"{prod.category_id} | {prod.name} | {short_desc} | Цена: {prod.price} | ID: {short_id}"


async def update_bot_interface(message: types.Message, state: FSMContext, new_text: str, reply_markup=None):
    data = await state.get_data()
    msg_id = data.get("last_msg_id")
    
    # 1. Удаляем сообщение пользователя, чтобы чат был чистым
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение: {e}")

    # 2. Редактируем сообщение бота
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg_id,
            text=new_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in e.message:
            # Если текст тот же — просто ничего не делаем, цель достигнута
            logger.warning(e)
            return
        
        # Если же ошибка другая (сообщение удалено и т.д.), шлем новое
        logger.warning(f"Редактирование не удалось ({e.message}), отправляем новое.")
        sent = await message.answer(new_text, reply_markup=reply_markup, parse_mode="HTML")
        await state.update_data(last_msg_id=sent.message_id)
    except Exception as e:
        logger.error(f"Критическая ошибка интерфейса: {e}")
