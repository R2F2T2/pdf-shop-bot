from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder,InlineKeyboardButton 
from aiogram.exceptions import TelegramBadRequest
from utils.states import EditCategory
from utils.filters import IsAdmin
from utils.helper import handle_db_result, get_add_product_text, update_bot_interface
from handlers import catalog
from models import CategoryAddClick, DBResult, Category, Product, CategoryAction
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
add_text_message = "Добавление категории"


# 2. Хендлер для обработки нажатия на кнопку "добавить категорию"
@router.callback_query(CategoryAction.filter(F.action == "edit"))
async def start_edit_category(callback: types.CallbackQuery, callback_data: CategoryAction, state: FSMContext):
    logger.info("start_edit_category")
    await callback.answer()   
    data = await state.get_data()
    #Если повторно нажимаем ввести котегорию - ничего не делаем
    if data == None:
        return
    instr_msg = await callback.message.answer("Введите новое название категории:")
    await state.update_data(
        cat_msg_id=callback.message.message_id,
        instr_msg_id=instr_msg.message_id,
        edit_cat_id=callback_data.id
        )

    logger.info(f"Запущена процедура переименование категории!")    
    # Переходим к следующему состоянию
    await state.set_state(EditCategory.new_name)

# 3. Хендлер для ввода названия категории(текстом)
@router.message(EditCategory.new_name)
async def edit_category_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db_result = await db.update_category(data['edit_cat_id'], message.text)        
    if handle_db_result(db_result)!=True:        
        await message.delete() #Удалеям сообщение пользователя
        #Изменяем инструкцию   
        try:
            new_text = handle_db_result(db_result)
            await message.bot.edit_message_text(
                                            new_text, 
                                            chat_id=message.chat.id, 
                                            message_id=data.get("instr_msg_id"))
        except TelegramBadRequest as e:
            if "message is not modified" in e.message.lower():
                # Игнорируем, если текст тот же самый — это не страшно
                pass
            else:
                await message.answer(new_text)
        return
    await state.update_data(name=message.text)
    try:
        await message.delete() #Удалеям свое сообщение
        await message.bot.delete_message(message.chat.id, data.get("instr_msg_id"))#Удаляем инструкцию
    except Exception as e:
        logger.warning(f"Не удалоcь удалить сообщения")    
    logger.debug(f"Введена новая категория: {message.text}")
    await catalog.process_show_categories_feat(message, data["cat_msg_id"])
    await state.clear()