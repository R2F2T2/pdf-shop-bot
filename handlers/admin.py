import os
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder,InlineKeyboardButton 
from utils.states import AddProduct, EditProduct
from utils.filters import IsAdmin
from handlers import catalog
import database as db

router = Router()
#Все функции из этого файла доступны только админам
router.message.filter(IsAdmin()) 
router.callback_query.filter(IsAdmin())

@router.callback_query(F.data == 'prod_add')
async def start_add(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer() # Убираем часики
    
    # Удаляем меню, чтобы оно не болталось сверху
    await callback.message.delete() 
    
    # Шлем НОВОЕ сообщение
    await callback.message.answer("📝 Введите название товара:")
    await state.set_state(AddProduct.name)

@router.message(AddProduct.name)
async def add_name(message: types.Message, state: FSMContext):
    if await db.check_duplicate_name(message.text):
        return await message.answer("Товар с таким названием уже есть в базе\n" \
        "Введите другое имя:")
    await state.update_data(name=message.text)
    await message.answer("Введите описание товара")
    await state.set_state(AddProduct.description)

@router.message(AddProduct.description)
async def add_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите цену в рублях:")
    await state.set_state(AddProduct.price)

@router.message(AddProduct.price)
async def add_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Нужно число!")
    await state.update_data(price=int(message.text))
    await message.answer("Пришлите PDF файл:")
    await state.set_state(AddProduct.file_id)

@router.message(AddProduct.file_id, F.document)
async def add_file(message: types.Message, state: FSMContext):
    tg_id = message.document.file_id
    await state.update_data(file_id=tg_id)
    data = await state.get_data()
    print(f'DEBUG: Данные для записи: {data}')
    new_db_id = await db.add_product(data)
    if new_db_id:
        await message.answer(f'✅ Товар {data['name']} добавлен!')
        await catalog.show_product_card(message, new_db_id)
    else:
        await message.answer("❌ Произошла ошибка при сохранении в базу. \n"
        "Возвращамеся в каталог.")
        await catalog.process_show_catalog()
    await state.clear()

@router.callback_query(F.data.startswith("edit_"))
async def edit_book(callback: types.CallbackQuery, state: FSMContext):
    print("Пробуем отредактировать товар")
    # Разбираем callback_data: edit_name_123 -> ['edit', 'name', '123']
    parts = callback.data.split("_")
    prop = parts[1]
    p_id = parts[2]

    # Словарь для красивых текстов
    prompts = {
        'name': "Введите новое название товара:",
        'price': "Введите новую цену товара (только цифры):",
        'description': "Введите новое описание товара:"
    }

    # Сохраняем данные в память FSM
    await state.update_data(edit_id=p_id, edit_prop=prop)
    
    # Переключаем бота в режим ожидания текста
    await state.set_state(EditProduct.waiting_for_value)
    
    await callback.message.answer(prompts.get(prop, "Введите новое значение:"))
    await callback.answer()

@router.message(EditProduct.waiting_for_value)
async def process_edit_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_id, prop = data['edit_id'], data['edit_prop']
    
    # Вызываем метод и смотрим на результат
    result = await db.update_product_field(p_id, prop, message.text)
    
    if result == "duplicate":
        return await message.answer("❌ Ошибка: Товар с таким названием уже существует!\nВведите другое название!")
    
    if result == "not_found":
        await state.clear()
        return await message.answer("❌ Ошибка: Товар не найден в базе.")

    await state.clear()
    await message.answer(f"✅ Успешно! Поле '{prop}' изменено на: {message.text}")
    await catalog.show_product_card(message, p_id)

# 1. Сначала спрашиваем подтверждение
@router.callback_query(F.data.startswith("del_"))
async def confirm_delete(callback: types.CallbackQuery):
    p_id = callback.data.split("_")[1]
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"force_del_{p_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"show_product_card({p_id})") # Наша кнопка отмены
    )
    await callback.message.edit_text("⚠️ Вы уверены, что хотите удалить этот товар?", reply_markup=kb.as_markup())

# 2. Само удаление
@router.callback_query(F.data.startswith("force_del_"))
async def delete_book_action(callback: types.CallbackQuery):
    p_id = int(callback.data.split("_")[2])
    
    deleted = await db.delete_product(p_id)
    
    if deleted:
        await callback.answer("🗑 Товар удален", show_alert=True)
    else:
        await callback.answer("❌ Ошибка: товар не найден", show_alert=True)
    
 
    await catalog.process_show_catalog(callback)


