import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from config import BOT_TOKEN
from handlers import user, admin, catalog, add_category, edit_category, add_product, payments
load_dotenv()
import database as db
# Создаем логгер
from config import init_logging
init_logging()
import logging
logger = logging.getLogger(__name__) 

async def main():    
    logger.info("Запуск бота...")
    await db.db_start()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Подключаем роутеры
    dp.include_routers(user.router, admin.router, catalog.router, add_category.router, edit_category.router, add_product.router, payments.router)

    await dp.start_polling(bot)
    logger.info("Бот запущен!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Бот остановлен!")
