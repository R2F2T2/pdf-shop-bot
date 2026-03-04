
import aiosqlite
from models import DBResult, PCategory
DB_PATH = 'bot_database.db'
#Создаем логгер
from config import init_logging
init_logging()
import logging
from utils.helper import get_string_data
logger = logging.getLogger(__name__)

async def db_start():
    async with aiosqlite.connect(DB_PATH) as db:
        logger.info("Создание таблицы")
        # Таблица пользователей (уже была)
        await db.execute("CREATE TABLE IF NOT EXISTS users(user_id PRIMARY KEY)")
        # Новая таблица для товаров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category text,
                name TEXT,
                description TEXT,
                price REAL,
                file_id TEXT,
                UNIQUE(category, name)
            )
        """)
        await db.commit()

async def get_all_products(category: PCategory):
    logger.info(f"Запрос продуктов категории: {category.value}")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM products WHERE category = ? ORDER BY name", (category.name,)) as cursor:
                rows = await cursor.fetchall()
                if len(rows) == 0:
                    logger.warning(f"Продуктов в категории {category.value} в базе нет!")
                    return DBResult.EMPTY
                else:                
                    result = [dict(row) for row in rows] 
                    logger.info(f"Запрос продуктов категории {category.value} выполнен.")                       
                    return result
    except Exception as e:
        logger.error(f'Ошибка при запросе всех продуктов: {e}') # Вот это покажет причину
        return DBResult.ERROR

async def get_product(p_id):
    logger.info(f"Запрос продукта id: {p_id}")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row 
            async with db.execute("SELECT * FROM products WHERE id = ?", (p_id,)) as cursor:                
                row = await cursor.fetchone()                
                if row:
                    logger.info(f"Запрос продукта {p_id} выполнен")
                    return dict(row)
                return DBResult.NOT_FOUND         
    except Exception as e:
        logger.error(f'Ошибка при запросе продукта id = {p_id} : {e}')
        return DBResult.ERROR

async def add_product(product_data: dict):
    logger.info("Добавляем новый продукт")
    """
    Принимает словарь с данными товара. 
    Ожидает, что в product_data['category'] лежит объект PCategory (Enum).
    """
    category = product_data.get('category')

    # Проверка: если пришла строка, пробуем превратить её в Enum
    if isinstance(category, str):
        try:
            category = PCategory[category]
        except KeyError:
            logger.warning(f"Неверная категория {category}")
            return DBResult.ERROR
            
    # Если это не Enum и не строка, которую мы смогли превратить в Enum
    if not isinstance(category, PCategory):
        logger.warning(f"Поле category должно быть объектом Enum Category")
        return DBResult.ERROR
    
    str_data = get_string_data(product_data)
    logger.info("Запись в базу: " + str_data)

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO products (category, name, description, price, file_id) VALUES (?, ?, ?, ?, ?)",
                (
                    category.name, # В базу всегда пишем техническое имя (PLANS/TASKS)
                    product_data['name'],
                    product_data['description'],
                    product_data['price'], 
                    product_data['file_id']
                )
            )
            await db.commit()
            logger.info("Введена новая запись:" + str_data)
            return cursor.lastrowid
            
    except aiosqlite.IntegrityError:
        logger.warning("Попытка записи дубликата")
        return DBResult.DUPLICATE
    except Exception as e:
        logger.error(f'Ошибка записи: {e}')
        return DBResult.ERROR


#TODO убрать принты (пока не используется)
async def add_product_ft(p_category: PCategory, p_name, p_description, p_price, p_file_id):
    """Принимает поля и сохраняет в БД"""
    print(f'БД: Запись данных: {p_category.name}, {p_name}, {p_description}, {p_price}, {p_file_id} ')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO products (category, name, description, price, file_id) VALUES (?, ?, ?, ?, ?)",
                (p_category.name, p_name, p_description, p_price, p_file_id)
            )
            await db.commit()        
            print('БД: Запись прошла успешно')
            return  cursor.lastrowid
    except aiosqlite.IntegrityError:
        return DBResult.DUPLICATE
    except Exception as e:
        print(f'БД: Ошибка добавления в базу: {e}')
        return DBResult.ERROR

async def delete_product(p_id: int):
    """Удаляем из базы данных и возвращаем категорию"""
    logger.info(f'Удаляем: {p_id}')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Используем RETURNING для получения значения категории
            cursor = await db.execute(
                "DELETE FROM products WHERE id = ? RETURNING category",
                (p_id,)
            )
            # Извлекаем результат (одну строку)
            row = await cursor.fetchone()
            await db.commit() # Не забываем зафиксировать изменения

            if row:
                logger.info(f"удаление продукта id={p_id} выполнено успешно")
                return row[0] 
            else:
                logger.warning(f"удаление продукта id={p_id} не удалось. Его нет в базе")
                return DBResult.NOT_FOUND
                
    except Exception as e:
        logger.error(f'Ошибка удаления продукта id={p_id} : {e}')
        return DBResult.ERROR

async def update_product(p_id, p_category: PCategory, p_name, p_description, p_price):
    """Редактирует продукт по ip"""
    logger.info(f'Редактируем продукт id = {p_id}')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                '''
                UPDATE products 
                SET 
                    category = ?,
                    name = ?,
                    description = ?,
                    price = ?                
                WHERE id = ?
                ''', 
                (p_category.name, p_name, p_description, p_price, p_id)
            )            
            await db.commit()
            if cursor.rowcount == 0:
                logger.warning(f"Ошибка удаления продукта id={p_id}. Товара нет в базе.!")
                return DBResult.NOT_FOUND
            return "DONE"
    except aiosqlite.IntegrityError:
        return DBResult.DUPLICATE
    except Exception as e:
        logger.warning(f"Ошибка удаления продукта id={p_id}. {e}")
        return DBResult.ERROR

async def delete_all_product():
    """Удаляем все из базы данных (С обнулением счетчика id) """
    logger.info('БД: Удаляем все записи')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE from products")
            await db.execute("DELETE FROM sqlite_sequence WHERE name='products'")
            await db.commit()
            logger.info("Все запииса базы удалены!")
            return DBResult.DONE
    except Exception as e:
        db.rollback()
        logger.info(f"Ошибка удаления всех записей! {e}")
        return DBResult.ERROR


async def update_product_field(product_id: int, field_name: str, new_value):
    logger.info(f"Редактирование свойства {field_name} у продукта id = {product_id}")
    query = f"UPDATE products SET {field_name} = ? WHERE id = ?"
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(query, (new_value, product_id))
            await db.commit()
            if cursor.rowcount == 0:
                logger.warning(f"Редактирование свойства у продукта неуспешно! Продукт id = {product_id} в базе не обзаружен")
                return "NOT_FOUND"
    except aiosqlite.IntegrityError:
        return "DUPLICATE"
    except Exception as e:
        db.rollback()
        logger.error(f'Ошибка редактирования свойства: {e}')
        return "ERROR"
    
async def check_duplicate_name(category: PCategory, product_name):
    # Используем COUNT, чтобы база сама посчитала количество
    query = "SELECT COUNT(*) FROM products WHERE category = ? AND name = ?"
    logger.info("Проверяем дубликаты...")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(query, (category.name, product_name,)) as cursor:
                # Извлекаем результат (это будет кортеж, например (1,))
                result = await cursor.fetchone()
                count = result[0]
                
                if count > 0:
                    logger.warning(f"Обнаружены дубликаты! {count} шт.")
                    return DBResult.DUPLICATE
                else:
                    logger.info(f"Дубликатов не найдено.")
                    return DBResult.NOT_FOUND
    except Exception as e:
        logger.error(f'Ошибка проверки дубликата: {e}')
        return DBResult.ERROR


