
import aiosqlite
from typing import List
from typing import Optional
from models import DBResult, Category, Product, Category
DB_PATH = 'bot_database.db'
#Создаем логгер
from config import init_logging
init_logging()
import logging
from utils.helper import get_string_data
logger = logging.getLogger(__name__)

async def db_start():
    async with aiosqlite.connect(DB_PATH) as db:
        logger.info("Создание таблиц")
        # Таблица пользователей (уже была)
        await db.execute("CREATE TABLE IF NOT EXISTS users(user_id PRIMARY KEY)")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        """)

        # Таблица товаров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,  -- Внешний ключ (FK)
                name TEXT,
                description TEXT,
                price REAL,
                file_id TEXT,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                UNIQUE(category_id, name)
            )
        """)
        await db.commit()

async def get_categories() -> list[Category]|DBResult:
    logger.info(f"Запрос категорий")
    categories = []
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM categories ORDER BY name") as cursor:
                rows = await cursor.fetchall()
                if len(rows) == 0:
                    logger.warning(f"Таблица категорий пуста!")
                    return DBResult.EMPTY
                else:                
                    for row in rows:
                        category = Category(**dict(row))
                        categories.append(category)  
                    logger.info(f"Запрос категории выполнен.")                       
                    return categories
    except Exception as e:
        logger.error(f'Ошибка при запросе всех продуктов: {e}') # Вот это покажет причину
        return DBResult.ERROR

async def get_category(c_id: int) -> Category | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM categories WHERE id = ?", (c_id,)) as cursor:
            row = await cursor.fetchone()
            return Category(**dict(row)) if row else None

async def get_all_products(category: Category) -> list[Product]|DBResult:
    logger.info(f"Запрос продуктов категории: {category.name}")
    products = []

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM products WHERE category_id = ? ORDER BY name", (category.id,)) as cursor:                
                rows = await cursor.fetchall()
                if len(rows) == 0:
                    logger.warning(f"Продуктов в категории {category.name} в базе нет!")
                    return DBResult.EMPTY
                else:                
                    products = [Product(**dict(row)) for row in rows]
                    logger.info(f"Запрос продуктов категории {category.name} выполнен.")                       
                    return products
    except Exception as e:
        logger.error(f'Ошибка при запросе всех продуктов: {e}') # Вот это покажет причину
        return DBResult.ERROR

async def get_product(p_id) -> Product|DBResult:
    logger.info(f"Запрос продукта id: {p_id}")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row 
            async with db.execute("SELECT * FROM products WHERE id = ?", (p_id,)) as cursor:                
                row = await cursor.fetchone()                
                if row:
                    logger.info(f"Запрос продукта {p_id} выполнен")
                    # Распаковываем словарь в аргументы класса
                    return Product(**dict(row))
                return DBResult.NOT_FOUND         
    except Exception as e:
        logger.error(f'Ошибка при запросе продукта id = {p_id} : {e}')
        return DBResult.ERROR

async def add_product(product: Product) -> int|DBResult:
    logger.info("Добавляем новый продукт")
    # Проверка: если пришла строка, пробуем превратить её в Enum
            
    # Если это не Enum и не строка, которую мы смогли превратить в Enum
    if isinstance(product, Product):    
        str_data = get_string_data(product)
        logger.info("Запись в базу: " + product.name)
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "INSERT INTO products (category_id, name, description, price, file_id) VALUES (?, ?, ?, ?, ?)",
                    (
                        product.category_id, # В базу всегда пишем техническое имя (PLANS/TASKS)
                        product.name,
                        product.description,
                        product.price, 
                        product.file_id
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
    else:
        return DBResult.ERROR

async def add_category(cat_name: str) -> int|DBResult:
    logger.info("Добавляем новую категорию")
 
    logger.info("Запись в базу категории: " + cat_name)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO categories (name) VALUES (?)", (cat_name, ))
            await db.commit()
            logger.info("Введена новая категория:" + cat_name)
            return cursor.lastrowid            
    except aiosqlite.IntegrityError:
        logger.warning("Попытка записи дубликата:" + cat_name )
        return DBResult.DUPLICATE
    except Exception as e:
        logger.error(f'Ошибка записи: {e}')
        return DBResult.ERROR


async def delete_product(p_id: int) -> int|DBResult:
    """Удаляем из базы данных и возвращаем категорию"""
    logger.info(f'Удаляем: {p_id}')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Используем RETURNING для получения значения категории
            cursor = await db.execute(
                "DELETE FROM products WHERE id = ? RETURNING category_id",
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

async def update_product(p: Product) -> DBResult:
    """Редактирует продукт по ip"""
    logger.info(f'Редактируем продукт id = {p}')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                '''
                UPDATE products 
                SET 
                    category_id = ?,
                    name = ?,
                    description = ?,
                    price = ?                
                WHERE id = ?
                ''', 
                (p.category_id, p.name, p.description, p.price, p.id)
            )            
            await db.commit()
            if cursor.rowcount == 0:
                logger.warning(f"Ошибка удаления продукта id={p.id}. Товара нет в базе.!")
                return DBResult.NOT_FOUND
            return "DONE"
    except aiosqlite.IntegrityError:
        return DBResult.DUPLICATE
    except Exception as e:
        logger.warning(f"Ошибка удаления продукта id={p.id}. {e}")
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


async def update_product_field(product_id: int, field_name: str, new_value) -> DBResult:
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
    
async def check_duplicate_name(category_id: int, product_name: str) -> DBResult:
    # Используем COUNT, чтобы база сама посчитала количество
    query = "SELECT COUNT(*) FROM products WHERE category_id = ? AND name = ?"
    logger.info("Проверяем дубликаты...")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(query, (category_id, product_name,)) as cursor:
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


