import asyncio
from config import BOT_TOKEN
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
load_dotenv()
import database as db
from handlers import admin, catalog, user, payments

async def main():
    await db.db_start()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_routers(admin.router, user.router, payments.router, catalog.router)

    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
