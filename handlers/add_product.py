from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder,InlineKeyboardButton 
from aiogram.exceptions import TelegramBadRequest
from utils.states import AddProduct
from utils.filters import IsAdmin
from utils.helper import handle_db_result, get_add_product_text, update_bot_interface
from handlers import catalog
from models import PCategory,  CategoryAddClick, DBResult
import database as db
#Создаем логгер
from config import init_logging
init_logging()
import logging
logger = logging.getLogger(__name__)
#----------------------------

router = Router()
#Все функции из этого файла доступны только админам
router.message.filter(IsAdmin()) 
router.callback_query.filter(IsAdmin())
add_text_message = "Добавление товара"

# 1. Хендлер для вывода кнопок категорий
@router.callback_query(F.data == 'prod_add')
async def start_add(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback.from_user.id} начал добавление продукта")
    await callback.answer()
    #стираем предыдущее
    #await callback.message.delete()
    builder = InlineKeyboardBuilder()
    for cat in PCategory:
        builder.row(InlineKeyboardButton(
            text=cat.value, 
            # Важно: здесь мы передаем callback_data
            callback_data=CategoryAddClick(category=cat).pack()
        ))  
    try:
        sent_message = await callback.message.edit_text(
            "Выберите категорию:",
            reply_markup=builder.as_markup()
        )
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать предыдущее сообщение бота: {e}")
        sent_message = await callback.message.answer(
            "Выберите категорию:",
            reply_markup=builder.as_markup()
        )
    # Сохраняем ID сообщения, которое будем редактировать всё время
    await state.update_data(last_msg_id=sent_message.message_id)
    await state.set_state(AddProduct.category)

# 2. Хендлер для обработки нажатия на кнопку категории
@router.callback_query(AddProduct.category, CategoryAddClick.filter())
async def category_chosen(callback: types.CallbackQuery, callback_data: CategoryAddClick, state: FSMContext):
    await callback.answer()   
    # Сохраняем категорию из callback_data (то, что было в кнопке)
    await state.update_data(category=callback_data.category)
    data = await state.get_data()
    new_text = get_add_product_text(data, "Введите название:")
    # Редактируем старое сообщение
    try:
        await callback.message.edit_text(new_text, parse_mode="HTML") 
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать предыдущее сообщение бота: {e}")
        await callback.message.answer(new_text) 
    logger.debug(f"Введена категория: {callback_data.category.value}")    
    # Переходим к следующему состоянию
    await state.set_state(AddProduct.name)

# 3. Хендлер для ввода названия (текстом)
@router.message(AddProduct.name)
async def add_name(message: types.Message, state: FSMContext):        
    data = await state.get_data()
    if await db.check_duplicate_name(data.get('category'), message.text) == DBResult.DUPLICATE:
        new_text = get_add_product_text(data, "Товар с таким названием уже есть в базе\n" \
                                        "Введите другое имя:")        
        return await update_bot_interface(message, state, new_text)
    await state.update_data(name=message.text)
    data = await state.get_data()
    new_text = get_add_product_text(data, "Введите описание:")
    await update_bot_interface(message, state, new_text)
    logger.debug(f"Введено название: {message.text}")
    await state.set_state(AddProduct.description)

# 4. Хендлер для ввода описания (текстом)
@router.message(AddProduct.description)
async def add_description(message: types.Message, state: FSMContext):
    desc = message.text
    await state.update_data(description=desc)
    short_desc = (desc[:17] + '...') if len(desc) > 20 else desc
    data = await state.get_data()
    new_text = get_add_product_text(data, "Введите цену:")
    await update_bot_interface(message, state, new_text)
    logger.debug(f"Введено описание: {short_desc}")
    await state.set_state(AddProduct.price)

# 5. Хендлер для ввода цены (текстом)
@router.message(AddProduct.price)
async def add_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not message.text.isdigit():
        new_text = get_add_product_text(data, "Неверный формат!\nВведите цену в рублях:")
        return await update_bot_interface(message, state, new_text)
    await state.update_data(price=message.text)    
    data = await state.get_data()
    new_text = get_add_product_text(data, "Пришлите PDF файл:")
    await update_bot_interface(message, state, new_text)  
    logger.debug(f"Введена цена: {message.text}")
    await state.set_state(AddProduct.file_id)

# 6. Хендлер для приняти файла
@router.message(AddProduct.file_id)
async def add_file(message: types.Message, state: FSMContext):
    #Если в сообщении нет файла 
    if not message.document:
        data = await state.get_data()# Нужно для формирования сообщения
        new_text = get_add_product_text(data, "Ваше сообщение не содержит файл!\nПришлите файл:")
        logger.warning("Пользователь прислал сообщение без файла.")
        return await update_bot_interface(message, state, new_text) 

    tg_id = message.document.file_id
    await state.update_data(file_id=tg_id)
    data = await state.get_data()
    old_msg_id = data.get("last_msg_id")
    preview_text = get_add_product_text(data, "Все верно?Сохраняем?")
    #  Удаляем файл пользователя и СТАРОЕ сообщение бота (интерфейс)
    await message.delete()
    try:
        await message.bot.delete_message(message.chat.id, old_msg_id)
    except Exception:
        pass

    # Создаем кнопки подтверждения
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Сохранить", callback_data="confirm_add")
    kb.button(text="❌ Отмена", callback_data="cancel_add")
    kb.adjust(1) # Кнопки друг под другом

    # Отправляем НОВОЕ сообщение с кнопками
    new_msg = await message.answer(preview_text, reply_markup=kb.as_markup(), parse_mode="HTML")
    
    # Обновляем ID сообщения в стейте для красоты
    await state.update_data(last_msg_id=new_msg.message_id)
    await state.set_state(AddProduct.confirm)

# 7. Хендлер нажатия кнопки "Сохранить"
@router.callback_query(F.data == "confirm_add")
async def process_confirm(callback: types.CallbackQuery, state: FSMContext):
    logger.debug("Пользователь нажал кнопку Сохранить")
    await callback.answer()
    data = await state.get_data()
    new_db_id = await db.add_product(data)
    message = callback.message
    if  await handle_db_result(new_db_id, callback.message):
        # Всплывашка сверху
        await callback.answer("✅ Товар успешно добавлен!", show_alert=False)
        # Удаляем сообщение с кнопками
        #await callback.message.delete()
        await catalog.show_product_card(callback, new_db_id)
    else:
        await callback.answer("❌ Произошла ошибка при сохранении в базу.\nВозвращамеся в каталог.", show_alert=True)
        await catalog.send_catalog_view(message, data.get('category'))
    await state.clear()

# 7. Хендлер нажатия кнопки "отмена" (текстом)
@router.callback_query(F.data == "cancel_add")
async def process_cancel(callback: types.CallbackQuery, state: FSMContext):
    logger.debug("Пользователь нажал кнопку Отмена")
    await callback.answer()
    message = callback.message
    data = await state.get_data()
    await catalog.send_catalog_view(message, data.get('category'))
    await state.clear()
