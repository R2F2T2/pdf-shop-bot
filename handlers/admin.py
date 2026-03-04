from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from utils.states import EditProduct
from utils.filters import IsAdmin
from utils.helper import handle_db_result
from handlers import catalog
from models import ProdAction, CategoryClick, PCategory
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
    callback: types.CallbackQuery, callback_data: ProdAction, state: FSMContext
):
    # 1. Сохраняем ID карточки товара (в которой нажали кнопку)
    # И ID инструкции, которую мы сейчас отправим
    instruction = await callback.message.answer(
        f"📝 Введите новое значение для {callback_data.prop}:"
    )

    await state.update_data(
        edit_id=callback_data.id,
        edit_prop=callback_data.prop,
        edit_cat=callback_data.cat,
        card_msg_id=callback.message.message_id,  # ID старой карточки
        instr_msg_id=instruction.message_id,  # ID текста "Введите..."
    )

    await state.set_state(EditProduct.waiting_for_value)
    await callback.answer()


@router.message(EditProduct.waiting_for_value)
async def process_edit_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_id = data["edit_id"]
    prop = data["edit_prop"]
    
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

    # 2. Обновляем в БД
    result = await db.update_product_field(p_id, prop, message.text)

    # 3. Если всё успешно (handle_db_result вернул True)
    if await handle_db_result(result, message):
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
@router.callback_query(ProdAction.filter((F.action == "del") & (F.prop == "conf")))
async def confirm_delete(callback: types.CallbackQuery, callback_data: ProdAction):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=ProdAction(
                action="del", prop="force", id=callback_data.id, cat=callback_data.cat
            ).pack(),
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=CategoryClick(category=callback_data.cat).pack(),
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

    result = await db.delete_product(callback_data.id)
    if not await handle_db_result(result, callback.message):
        await callback.answer()  # Убираем "часики"
        return
    await catalog.send_catalog_view(callback.message, callback_data.cat)
