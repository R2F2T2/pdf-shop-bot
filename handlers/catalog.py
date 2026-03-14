from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder,InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from config import ADMIN_IDS
import database as db
from models import Product, Category, CategoryClick, ProdClick, ProdAction, DBResult
from utils.helper import handle_db_result   
#Создаем логгер
from config import init_logging
init_logging()
import logging
logger = logging.getLogger(__name__)
#----------------------------
router = Router()

#TODO удалить
async def process_show_category(callback: types.CallbackQuery):
    logger.info("Выводим меню категории")
    db_result = await db.get_categories()
    builder = InlineKeyboardBuilder()
    if isinstance(db_result, list):
        # Строим клавиатуру со списком книг                 
        for cat in db_result:            
        # Используем наш класс ProdClick или просто строку с ID
            builder.row(InlineKeyboardButton(
                text=cat.name,
                callback_data=CategoryClick(category_id=cat.id).pack()
            ))       
        msg_text = "Выберете категорию:"
    else:
        msg_text = handle_db_result(db_result)
        
    #builder.row(InlineKeyboardButton(text="➕ Добавить категорию", callback_data="cat_add"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
        
    try:
        # 3. Редактируем старое сообщение (меню обновляется "на месте")
        await callback.message.edit_text(
            msg_text,
            reply_markup=builder.as_markup()
        )
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать предыдущее сообщение бота: {e}")
        await callback.message.answer(
            "Выберите категорию",
            reply_markup=builder.as_markup()
        )
    await callback.answer()

@router.callback_query(F.data == "show_categories")
async def process_show_categories_feat(
        event: types.Message | types.CallbackQuery,
        edit_msg_id: int = None
    ):
    logger.info("Выводим меню категории")
    db_result = await db.get_categories()
    builder = InlineKeyboardBuilder()
    user_id = event.from_user.id
    # Определяем, куда слать ответ (в callback или в новое сообщение)
    chat_id = event.chat.id if isinstance(event, types.Message) else event.message.chat.id
    if isinstance(db_result, list):
        # Строим клавиатуру со списком категорий                 
        for cat in db_result:            
        # Используем наш класс ProdClick или просто строку с ID
            builder.row(InlineKeyboardButton(
                text=cat.name,
                callback_data=CategoryClick(category_id=cat.id).pack()
            ))       
        msg_text = "Выберете категорию:"
    else:
        msg_text = handle_db_result(db_result)

    if user_id in ADMIN_IDS: #Если администратор    
        builder.row(InlineKeyboardButton(text="➕ Добавить категорию", callback_data="cat_add"))

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))

    try:
        if edit_msg_id:
            # Редактируем конкретное сообщение по ID
            await event.bot.edit_message_text(
                chat_id=chat_id,
                message_id=edit_msg_id,
                text=msg_text,
                reply_markup=builder.as_markup()
            )
        elif isinstance(event, types.CallbackQuery):
            # Если это нажатие кнопки "назад" из меню products — редактируем текущее сообщение кнопки
            await event.message.edit_text(
                text=msg_text,
                reply_markup=builder.as_markup()
            )
        else:
            # Если это просто текстовое сообщение — отправляем новое
            await event.answer(
                text=msg_text,
                reply_markup=builder.as_markup()
            )
    except TelegramBadRequest as e:
        if "message is not modified" not in e.message:
            logger.error(f"Ошибка при обновлении меню: {e}")

#Возвращает каталог
@router.callback_query(CategoryClick.filter())
async def process_show_catalog(callback: types.CallbackQuery, callback_data: CategoryClick):
    await send_catalog_view(callback, callback_data.category_id)    
    await callback.answer()

async def send_catalog_view(callback: types.CallbackQuery, category_id: int):
    """Возвращает каталог выбранной категории"""
    user_id = callback.from_user.id
    db_result = await db.get_category(category_id)
    result = handle_db_result(db_result)
    if isinstance(db_result, Category):
        category = db_result
        logger.debug("Пользователь выбрал категорию: " + category.name)
    else:
        msg_text = result
        
    builder = InlineKeyboardBuilder()
    db_result = await db.get_all_products(category)
    if isinstance(db_result, list):
        # Строим клавиатуру со списком книг
        for p in db_result:
            # Используем наш класс ProdClick или просто строку с ID
            builder.row(InlineKeyboardButton(
                text=f"📖 {p.name} — {p.price}₽", 
                callback_data=ProdClick(id=p.id).pack() # Тот самый класс из прошлого шага
            ))
        msg_text = f"📚 Доступные учебные пособия категории {category.name} (PDF):"
    else:
        msg_text = handle_db_result(db_result)
    
    if user_id in ADMIN_IDS:
        builder.row(InlineKeyboardButton(
            text="➕ Добавить продукт", 
            callback_data=ProdAction(
                action="add", 
                id=0,           # товара еще нет, ставим 0
                cat_id=category_id
                ).pack()
            ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="show_categories"))
    # 3. Редактируем старое сообщение (меню обновляется "на месте")
    try:
        await callback.message.edit_text(
            msg_text,
            reply_markup=builder.as_markup()
        )
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать предыдущее сообщение бота: {e}")
        await callback.message.answer(
            msg_text,
            reply_markup=builder.as_markup()
        )


@router.callback_query(ProdClick.filter())
async def handle_book_click(callback: types.CallbackQuery, callback_data: ProdClick):    
    await show_product_card(callback, callback_data.id)    
    await callback.answer()

async def show_product_card(
        event: types.Message | types.CallbackQuery, 
        product_id: int,
        edit_msg_id: int = None
        ):
    # Достаем свежие данные из БД
    db_result = await db.get_product(product_id)
    # 2. Определяем, куда слать ответ (в callback или в новое сообщение)
    target_msg = event if isinstance(event, types.Message) else event.message
    # 3. Проверка через хелпер
    # Если вернет False — хелпер сам ответит "Объект не найден" или "Ошибка"
    user_id = event.from_user.id
    kb = InlineKeyboardBuilder()
    if isinstance(db_result, Product):
        book = db_result
        if user_id in ADMIN_IDS:
            logger.warning(f"Выводится карточка продукта id={product_id} от имени администратора")
            # Кнопки для админа
            kb.row(InlineKeyboardButton(text="📝 Изменить название", 
                                        callback_data= ProdAction(action="edit", prop="name", id=book.id, cat_id=book.category_id).pack()))
            kb.row(InlineKeyboardButton(text="💰 Изменить цену", 
                                        callback_data= ProdAction(action="edit", prop="price", id=book.id, cat_id=book.category_id).pack()))
            kb.row(InlineKeyboardButton(text="📄 Изменить описание", 
                                        callback_data= ProdAction(action="edit", prop="description",id=book.id, cat_id=book.category_id).pack()))
            kb.row(InlineKeyboardButton(text="🗑 Удалить книгу", 
                                        callback_data= ProdAction(action="del", prop="conf",id=book.id, cat_id=book.category_id).pack()))
            kb.row(InlineKeyboardButton(text=f"💳 Тестовая покупка {book.price}₽", 
                                        callback_data= ProdAction(action="pay", id=book.id, cat_id=book.category_id).pack()))
            text = (f"⚙️ **Управление книгой:** {book.name}\n"
                    f"💰 Цена: {book.price}₽\n"
                    f"📝 Описание: {book.description}")
        else:
            logger.info(f"Выводим карточку продукта id={product_id} от имени обычноого пользователя")
            # Кнопки для юзера
            kb.row(InlineKeyboardButton(text=f"💳 Купить за {book.price}₽", callback_data=ProdAction(action="pay", id=book.id, cat_id=book.category_id).pack()))
            text = f"📘 **Книга:** {book.name}\n\n{book.description}"
        #Общая кнопука назад    
        kb.row(InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data=CategoryClick(category_id=book.category_id).pack()))
    else:
        text = handle_db_result(db_result)
        # Если возникла неожиданная ошибка предлагаем вернуться в меню выбора категории
        kb.row(InlineKeyboardButton(text="⬅️ Категории", callback_data="show_categories"))
        # Логика отправки/редактирования:
    if edit_msg_id:
        # Если явно указали ID для редактирования
        await event.bot.edit_message_text(
            chat_id=target_msg.chat.id,
            message_id=edit_msg_id,
            text=text,
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    # Если это сообщение (после ввода текста), шлем новое. Если кнопка — редактируем.
    elif isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    else:
        await event.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
