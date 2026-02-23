from aiogram.fsm.state import State, StatesGroup

class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    file_id = State()

class EditProduct(StatesGroup):
    waiting_for_value = State()