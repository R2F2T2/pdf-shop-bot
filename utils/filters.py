from aiogram import types
from aiogram.filters import BaseFilter
import os

# Подгружаем ID админов (те же, что вы парсили в начале)
raw_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(admin_id) for admin_id in raw_ids.split(",") if admin_id]

class IsAdmin(BaseFilter):
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        return event.from_user.id in ADMIN_IDS