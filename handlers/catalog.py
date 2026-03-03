from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder,InlineKeyboardButton 
from aiogram.filters.callback_data import CallbackData
from aiogram.types import LabeledPrice
from aiogram.exceptions import TelegramBadRequest
from config import ADMIN_IDS
import database as db
from models import PCategory, CategoryAddClick, ProdClick, ProdAction
from utils.helper import handle_db_result   
#Создаем логгер
from config import init_logging
init_logging()
import logging
logger = logging.getLogger(__name__)
#----------------------------
router = Router()

@router.callback_query(F.data == "show_categories")
async def process_show_category(callback: types.CallbackQuery):
    logger.info("Выводим меню категории")
 
    # 2. Строим клавиатуру со списком книг
    builder = InlineKeyboardBuilder()
    for cat in PCategory:
    # Используем наш класс ProdClick или просто строку с ID
        builder.row(InlineKeyboardButton(
            text=cat.value, 
            callback_data=CategoryAddClick(category=cat).pack()
        ))       
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    try:
        # 3. Редактируем старое сообщение (меню обновляется "на месте")
        await callback.message.edit_text(
            "Выберите категорию",
            reply_markup=builder.as_markup()
        )
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать предыдущее сообщение бота: {e}")
        await callback.message.answer(
            "Выберите категорию",
            reply_markup=builder.as_markup()
        )
    await callback.answer()

#Возвращает каталог
@router.callback_query(CategoryAddClick.filter())
async def process_show_catalog(callback: types.CallbackQuery, callback_data: CategoryAddClick):
    logger.debug("Пользователь выбрал категорию")
    await send_catalog_view(callback.message, callback_data.category)    
    await callback.answer()

async def send_catalog_view(message: types.Message, category: PCategory):
    """Возвращает каталог выбранной категории"""
    products = await db.get_all_products(category)
    if not await handle_db_result(products, message):
        return    
    
    # 2. Строим клавиатуру со списком книг
    builder = InlineKeyboardBuilder()
    for p in products:
        # Используем наш класс ProdClick или просто строку с ID
        builder.row(InlineKeyboardButton(
            text=f"📖 {p['name']} — {p['price']}₽", 
            callback_data=ProdClick(id=p['id']).pack() # Тот самый класс из прошлого шага
        ))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="show_categories"))

    # 3. Редактируем старое сообщение (меню обновляется "на месте")
    try:
        await message.edit_text(
            "📚 Доступные учебные пособия (PDF):",
            reply_markup=builder.as_markup()
        )
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать предыдущее сообщение бота: {e}")
        await message.answer(
            "📚 Доступные учебные пособия (PDF):",
            reply_markup=builder.as_markup()
        )


@router.callback_query(ProdClick.filter())
async def handle_book_click(callback: types.CallbackQuery, callback_data: ProdClick):    
    await show_product_card(callback,callback_data.id)    
    await callback.answer()


async def show_product_card(event: types.Message | types.CallbackQuery, product_id: int):
    # Достаем свежие данные из БД
    book = await db.get_product(product_id)
    # 2. Определяем, куда слать ответ (в callback или в новое сообщение)
    target_msg = event if isinstance(event, types.Message) else event.message
    # 3. Проверка через хелпер
    # Если вернет False — хелпер сам ответит "Объект не найден" или "Ошибка"
    if not await handle_db_result(book, target_msg):
        if isinstance(event, types.CallbackQuery):
            await event.answer()
        return 
        
    user_id = event.from_user.id
    raw_cat = book['category']
    enum_cat = PCategory[raw_cat]
    logger.info(f"Выводим карточку продукта id={product_id}")
    kb = InlineKeyboardBuilder()
    if user_id in ADMIN_IDS:
        # Кнопки для админа
        kb.row(InlineKeyboardButton(text="📝 Изменить название", 
                                    callback_data= ProdAction(action="edit", prop="name", id=book['id'], cat=enum_cat).pack()))
        kb.row(InlineKeyboardButton(text="💰 Изменить цену", 
                                    callback_data= ProdAction(action="edit", prop="price", id=book['id'], cat=enum_cat).pack()))
        kb.row(InlineKeyboardButton(text="📄 Изменить описание", 
                                    callback_data= ProdAction(action="edit", prop="description",id=book['id'], cat=enum_cat).pack()))
        kb.row(InlineKeyboardButton(text="🗑 Удалить книгу", 
                                    callback_data= ProdAction(action="del", prop="conf",id=book['id'], cat=enum_cat).pack()))
        kb.row(InlineKeyboardButton(text=f"💳 Тестовая покупка {book['price']}₽", 
                                    callback_data= ProdAction(action="pay", id=book['id'], cat=enum_cat).pack()))
        text = (f"⚙️ **Управление книгой:** {book['name']}\n"
                f"💰 Цена: {book['price']}₽\n"
                f"📝 Описание: {book['description']}")
    else:
        # Кнопки для юзера
        kb.row(InlineKeyboardButton(text=f"💳 Купить за {book['price']}₽", callback_data=ProdAction(action="pay", id=book['id'], cat=enum_cat).pack()))
        text = f"📘 **Книга:** {book['name']}\n\n{book['description']}"

    kb.row(InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data=CategoryAddClick(category=enum_cat).pack()))

    # Если это сообщение (после ввода текста), шлем новое. Если кнопка — редактируем.
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    else:
        await event.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
