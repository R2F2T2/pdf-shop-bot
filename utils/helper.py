from models import DBResult
async def handle_db_result(result, message, success_handler=None):
    """
    Универсальный обработчик ответов от БД.
    :param result: То, что вернула функция БД (dict или DBResult)
    :param message: Объект сообщения aiogram для ответа юзеру
    :param success_handler: Функция, которая выполнится, если данные получены
    """
    # 1. Проверяем, не ошибка ли это из нашего Enum
    if isinstance(result, DBResult):
        if result == DBResult.NOT_FOUND:
            await message.answer("❌ Объект не найден в базе данных.")
        elif result == DBResult.DUPLICATE:
            await message.answer("⚠️ Такая запись уже существует (дубликат).")
        elif result == DBResult.ERROR:
            await message.answer("🆘 Произошла системная ошибка базы данных.")
        elif result == DBResult.EMPTY:
            await message.answer("Раздел пуст")
        return False  # Сигнализируем, что была проблема
    
    # 2. Если это не DBResult, значит это наши данные (словарь или ID)
    if success_handler:
        await success_handler(result)
    return True # Все прошло успешно

def get_add_product_text(data: dict, next_step: str) -> str:
    # Собираем то, что уже введено
    category = data.get('category')
    name = data.get('name', '...')
    desc = data.get('description', '...')
    price = data.get('price', '...')
    
    text = (
        f"<b>🛒 Добавление товара</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"📂 Категория: {category.value if category else '...'}\n"
        f"🏷 Название: {name}\n"
        f"📝 Описание: {desc}\n"
        f"💰 Цена: {price}\n"
        f"━━━━━━━━━━━━━━\n"
        f"➡️ <b>{next_step}</b>"
    )
    return text

def get_string_data(prod) -> str:
    """Возвращет строку с полями объекта"""
    # Обрезаем описание и добавляем троеточие, если оно длинное
    desc = prod.get('description', '')
    short_desc = (desc[:17] + '...') if len(desc) > 20 else desc
    
    # Сокращаем длинный file_id (оставляем начало и конец)
    f_id = str(prod.get('file_id', ''))
    short_id = f"{f_id[:6]}...{f_id[-4:]}" if len(f_id) > 10 else f_id
    
    # Категория (если это Enum, берем .value)
    cat = prod.get('category')
    cat_val = cat.value if hasattr(cat, 'value') else cat

    return f"{cat_val} | {prod['name']} | {short_desc} | Цена: {prod['price']} | ID: {short_id}"
