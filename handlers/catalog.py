from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder,InlineKeyboardButton 
from aiogram.filters.callback_data import CallbackData
from aiogram.types import LabeledPrice
import database as db
import os

router = Router()
#raw_id = os.getenv("ADMIN_ID")
#ADMIN_ID = int(raw_id)
raw_ids = os.getenv("ADMIN_IDS", "")
#print(f"DEBUG: ADMIN_ID is {raw_ids}") # Это покажет, что прочиталось
# Читаем строку "123,456", делим по запятой и превращаем каждый элемент в int
ADMIN_IDS = [int(admin_id) for admin_id in raw_ids.split(",") if admin_id]
#Класс который описывает схему кнопки
class ProdClick(CallbackData, prefix="p"):
    id: int

#Возвращает каталог
@router.callback_query(F.data == "show_catalog")
async def process_show_catalog(callback: types.CallbackQuery):
    print("Выводим каталог")
    # 1. Получаем все книги из базы
    products = await db.get_products()
    
    if not products:
        await callback.answer("Книг пока нет в продаже.", show_alert=True)
        return

    # 2. Строим клавиатуру со списком книг
    builder = InlineKeyboardBuilder()
    for p in products:
        # Используем наш класс ProdClick или просто строку с ID
        builder.row(InlineKeyboardButton(
            text=f"📖 {p['name']} — {p['price']}₽", 
            callback_data=ProdClick(id=p['id']).pack() # Тот самый класс из прошлого шага
        ))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))

    # 3. Редактируем старое сообщение (меню обновляется "на месте")
    await callback.message.edit_text(
        "📚 Доступные учебные пособия (PDF):",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(ProdClick.filter())
async def handle_book_click(callback: types.CallbackQuery, callback_data: ProdClick):    
    await show_product_card(callback,callback_data.id)    
    await callback.answer()


async def show_product_card(event: types.Message | types.CallbackQuery, product_id: int):
    # Достаем свежие данные из БД
    book = await db.get_product(product_id)
    if not book:
        if isinstance(event, types.CallbackQuery):
            return await event.answer("Товар не найден!")
        return await event.answer("Товар не найден!")

    user_id = event.from_user.id
    kb = InlineKeyboardBuilder()

    if user_id in ADMIN_IDS:
        # Кнопки для админа
        kb.row(InlineKeyboardButton(text="📝 Изменить название", callback_data=f"edit_name_{book['id']}"))
        kb.row(InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"edit_price_{book['id']}"))
        kb.row(InlineKeyboardButton(text="📄 Изменить описание", callback_data=f"edit_description_{book['id']}"))
        kb.row(InlineKeyboardButton(text="🗑 Удалить книгу", callback_data=f"del_{book['id']}"))
        kb.row(InlineKeyboardButton(text=f"💳 Тестовая покупка {book['price']}₽", callback_data=f"buy_{book['id']}"))
        text = (f"⚙️ **Управление книгой:** {book['name']}\n"
                f"💰 Цена: {book['price']}₽\n"
                f"📝 Описание: {book['description']}")
    else:
        # Кнопки для юзера
        kb.row(InlineKeyboardButton(text=f"💳 Купить за {book['price']}₽", callback_data=f"buy_{book['id']}"))
        text = f"📘 **Книга:** {book['name']}\n\n{book['description']}"

    kb.row(InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data="show_catalog"))

    # Если это сообщение (после ввода текста), шлем новое. Если кнопка — редактируем.
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    else:
        await event.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
