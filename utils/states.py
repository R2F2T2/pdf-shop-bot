from aiogram.fsm.state import State, StatesGroup

class AddProduct(StatesGroup):
    category = State()
    name = State()
    description = State()
    price = State()
    file_id = State()
    confirm = State()

class EditProduct(StatesGroup):
    waiting_for_value = State()