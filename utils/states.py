from aiogram.fsm.state import State, StatesGroup

class AddCategory(StatesGroup):
    name = State()

class EditCategory(StatesGroup):
    new_name = State()

class AddProduct(StatesGroup):
    category_id = State()
    name = State()
    description = State()
    price = State()
    file_id = State()
    confirm = State()

class EditProduct(StatesGroup):
    waiting_for_value = State()