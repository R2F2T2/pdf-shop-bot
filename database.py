
import aiosqlite

DB_PATH = 'bot_database.db'

async def db_start():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей (уже была)
        await db.execute("CREATE TABLE IF NOT EXISTS users(user_id PRIMARY KEY)")
        # Новая таблица для товаров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                price REAL,
                file_id TEXT
            )
        """)
        await db.commit()

async def get_products():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM products") as cursor:
                print('ДБ извлечение продуктов')
                rows = await cursor.fetchall()
                print(f'Извлечено строк: {len(rows)}')
                
                result = [dict(row) for row in rows]
                print('ДБ Загрузка завершена успешно')
                return result
    except Exception as e:
        print(f'ОШИБКА В DATABASE.PY: {e}') # Вот это покажет причину
        return []

async def get_product(p_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row 
        async with db.execute("SELECT * FROM products WHERE id = ?", (p_id,)) as cursor:
            print('БД: Запрос получен...')
            row = await cursor.fetchone()                
            if row:
                return dict(row)
            return None         


async def add_product(product):
    """Принимает поля и сохраняет в БД"""
    print(f'БД: Запись данных: {product['name']} | Цена: {product['price']} | ID файла: {product['file_id']}')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO products (name, description, price, file_id) VALUES (?, ?, ?, ?)",
                (product['name'], product['description'], product['price'], product['file_id'])
            )
            await db.commit()
            new_id = cursor.lastrowid
            print('БД: Запись прошла успешно')
            return new_id
    except Exception as e:
        print(f'БД: Ошибка записи в базу: {e}')
        return None


async def add_product_ft(p_name, p_description, p_price, p_file_id):
    """Принимает поля и сохраняет в БД"""
    print(f'БД: Запись данных: {p_name}, {p_description}, {p_price}, {p_file_id} ')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO products (name, description, price, file_id) VALUES (?, ?, ?, ?)",
                (p_name, p_description, p_price, p_file_id)
            )
            await db.commit()
            print('БД: Запись прошла успешно')
    except Exception as e:
        print(f'БД: Ошибка записи в базу: {e}')

async def delete_product(p_id: int):
    """Удаляем из базы данных"""
    print(f'Удаляем: {p_id}')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE from products WHERE id = ?",
                (p_id,)
            )
            await db.commit()
            return True
    except Exception as e:
        db.rollback()
        print(f'БД: Ошибка удаления: {e}')
        return False

async def update_product(p_id, p_name, p_description, p_price):
    """Редактирует продукт по ip"""
    print(f'DB: Редактируем продукт id = {p_id}')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                '''
                UPDATE products 
                SET name = ?,
                    description = ?,
                    price = ?                
                WHERE id = ?
                ''', 
                (p_name, p_description, p_price, p_id)
            )            
            await db.commit()
    except Exception as e:
        db.rollback()
        print(f'БД: Ошибка редактирования: {e}')

async def delete_all_product():
    """Удаляем все из базы данных (С обнулением счетчика id) """
    print('БД: Удаляем все записи')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE from products")
            await db.execute("DELETE FROM sqlite_sequence WHERE name='products'")
            await db.commit()
            print('БД: Удаление завершено')
    except Exception as e:
        db.rollback()
        print(f'БД: Ошибка удаления: {e}')


async def update_product_field(product_id: int, field_name: str, new_value):
    query = f"UPDATE products SET {field_name} = ? WHERE id = ?"
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(query, (new_value, product_id))
            await db.commit()
            if cursor.rowcount == 0:
                return "not_found"
            return "success"
    except aiosqlite.IntegrityError:
        # Сработает, если нарушена уникальность (UNIQUE) поля name
        return "duplicate"
    
async def check_duplicate_name(product_name):
    # Используем COUNT, чтобы база сама посчитала количество
    query = "SELECT COUNT(*) FROM products WHERE name = ?"
    print("Проверяем дубликаты...")
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(query, (product_name,)) as cursor:
                # Извлекаем результат (это будет кортеж, например (1,))
                result = await cursor.fetchone()
                count = result[0]
                
                if count > 0:
                    print(f"БД: Обнаружены дубликаты! {count} шт.")
                    return True
                else:
                    print(f"БД: Дубликатов не найдено.")
                    return False
    except Exception as e:
        print(f'БД: Ошибка проверки дубликата: {e}')
        return False


