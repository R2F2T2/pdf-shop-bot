from enum import Enum
from aiogram.filters.callback_data import CallbackData

class DBResult(Enum):
    DONE = 'done'
    NOT_FOUND = 'not_found'
    DUPLICATE = 'duplicate'
    ERROR = 'error'
    EMPTY = 'empty'

class PCategory(Enum):
    psyho = 'Психология'
    neuro = 'Неврология'

class CategoryClick(CallbackData, prefix="catalog"):
    category: PCategory

class CategoryAddClick(CallbackData, prefix="catalog"):
    category: PCategory
    
class ProdClick(CallbackData, prefix="p"):
    id: int

class ProdAction(CallbackData, prefix="prod"):
    action: str      # "view", "confirm_delete", "delete"
    prop: str = 'default'
    id: int          
    cat: PCategory 