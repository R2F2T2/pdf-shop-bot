from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from utils.states import EditProduct
from utils.filters import IsAdmin
from utils.helper import handle_db_result
from handlers import catalog
from models import ProdAction, CategoryClick, Category, DBResult, PROPS_RU
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


@router.callback_query(ProdAction.filter(F.action == "edit"))
async def start_edit_field(
    callback: types.CallbackQuery, callback_data: ProdAction, state: FSMContext):
    data = await state.get_data()
    old_inst_id = data.get("instr_msg_id")
    old_prop = data.get("edit_prop")
    readable_prop = PROPS_RU.get(callback_data.prop, callback_data.prop)
    text = f'<b>"{readable_prop}"</b>\nВведите новое значение:'
    # Если в стейте уже висит ID старой инструкции
    if old_inst_id:
        if old_prop != callback_data.prop: #Если свойство не совпадает пытаемя редактировать другое совойство
            try:                
                instruction = await callback.bot.edit_message_text(
                                chat_id=callback.message.chat.id,
                                message_id=old_inst_id,
                                text=text,
                                parse_mode="HTML")   
                new_instr_id = old_inst_id
            except Exception as e:
                # Если сообщение удалено или возникла ошибка — шлем новое
                logger.error(f"Не могу отредактировать сообщение: {e}")
                instruction = await callback.message.answer(text, parse_mode="HTML")
                new_instr_id = instruction.message_id
        else:
            await callback.answer()
            return
    #Если инструкций не было, выдаем новое
    else: 
        # Если это первое нажатие кнопки «Изменить»
        instruction = await callback.message.answer(text, parse_mode="HTML")
        new_instr_id = instruction.message_id

    await state.update_data(
        edit_id=callback_data.id,
        edit_prop=callback_data.prop,
        edit_cat=callback_data.cat_id,
        card_msg_id=callback.message.message_id,  # ID старой карточки
        instr_msg_id=new_instr_id,  # ID текста "Введите..."
    )

    await state.set_state(EditProduct.waiting_for_value)
    await callback.answer()


@router.message(EditProduct.waiting_for_value)
async def process_edit_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_id = data["edit_id"]
    prop = data["edit_prop"]
    cat_id = data["edit_cat"]
    
    # 1. Проверяем цену
    if prop == "price":
        if message.text.isdigit():
            if int(message.text)<100:
                await message.delete()
                return await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=data["instr_msg_id"],
                    text="Цена должна быть не менее 100р!\nВведите цену:")            
        else:
            await message.delete()
            return await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=data["instr_msg_id"],
                    text="Цена должна быть числом!\nВведите цену:")         
    if prop == "name" and await db.check_duplicate_name(cat_id, message.text) == DBResult.DUPLICATE:
        cat = await db.get_category(p_id)
        if isinstance(cat, Category):
            cat: Category = cat
        else:
            return
        return await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=data["instr_msg_id"],
            text=f"В категории {cat.name} уже есть объект с названием {message.text}!\nВведите другое название:")   
    # 2. Обновляем в БД
    result = await db.update_product_field(p_id, prop, message.text)

    # 3. Если всё успешно (handle_db_result вернул True)
    if handle_db_result(result) == True:
        # --- БЛОК ОЧИСТКИ ---
        try:
            # Удаляем сообщение админа (новый текст)
            await message.delete()
            # Удаляем инструкцию "Введите..."
            await message.bot.delete_message(message.chat.id, data["instr_msg_id"])            
            #  ОБНОВЛЯЕМ старую карточку свежими данными
            await catalog.show_product_card(
                event=message, 
                product_id=data['edit_id'], 
                edit_msg_id=data["card_msg_id"] # Указываем, что именно редактировать
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении интерфейса: {e}")
    await state.clear()

# 1. Сначала спрашиваем подтверждение
@router.callback_query(ProdAction.filter((F.action == "del") and (F.prop == "conf")))
async def confirm_delete(callback: types.CallbackQuery, callback_data: ProdAction):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=ProdAction(
                action="del", prop="force", id=callback_data.id, cat_id=callback_data.cat_id
            ).pack(),
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=CategoryClick(category_id=callback_data.cat_id).pack(),
        ),
    )
    try:
        await callback.message.edit_text(
            "⚠️ Вы уверены, что хотите удалить этот товар?", reply_markup=kb.as_markup()
        )
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отредактировать предыдущее сообщение бота: {e}")
        await callback.message.answer(
            "⚠️ Вы уверены, что хотите удалить этот товар?", reply_markup=kb.as_markup()
        )


# 2. Само удаление
@router.callback_query(ProdAction.filter((F.action == "del") & (F.prop == "force")))
async def delete_book_action(callback: types.CallbackQuery, callback_data: ProdAction):
    await callback.answer()  # Убираем "часики"
    result = await db.delete_product(callback_data.id)
    if handle_db_result(result) != True:
        return
    await catalog.send_catalog_view(callback.message, callback_data.cat_id)
