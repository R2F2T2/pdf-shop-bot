from enum import Enum
from aiogram.filters.callback_data import CallbackData
from dataclasses import dataclass
from typing import Optional

@dataclass
class Product:
    id: int
    category_id: int
    name: str
    description: str
    price: float
    file_id: str

@dataclass
class Category:
    id: int
    name: str

class DBResult(Enum):
    DONE = 'done'
    NOT_FOUND = 'not_found'
    DUPLICATE = 'duplicate'
    ERROR = 'error'
    EMPTY = 'empty'

    
class CategoryClick(CallbackData, prefix="catalog"):
    category_id: int

class CategoryAddClick(CallbackData, prefix="add"):
    category_id: int
    
class ProdClick(CallbackData, prefix="p"):
    id: int

class ProdAction(CallbackData, prefix="prod"):
    action: str      # "view", "confirm_delete", "delete"
    prop: str = 'default'
    id: int          
    cat_id: int  