import asyncio
from config import BOT_TOKEN
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
load_dotenv()
import database as db
from handlers import admin, catalog, user, payments
#Создаем логгер
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
    dp.include_routers(admin.router, user.router, payments.router, catalog.router)

    await dp.start_polling(bot)
    logger.info("Бот запущен!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Бот остановлен!")
