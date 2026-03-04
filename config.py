import os
from dotenv import load_dotenv
import logging
import sys
import colorlog

load_dotenv() # Загружает переменные из .env в окружение

BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]


def init_logging():
    # 1. Создаем форматтер
    log_formatter = logging.Formatter(
        fmt="%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s:%(lineno)d - %(message)s"
    )

    # 2. Настраиваем обработчик для файла
    file_handler = logging.FileHandler("bot_logs.log", encoding="utf-8")
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)  # В файл пишем всё

    # Создаем цветной форматтер для консоли
    color_formatter = colorlog.ColoredFormatter(
        fmt="%(log_color)s%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(color_formatter) # Ставим цветной форматтер
    console_handler.setLevel(logging.DEBUG)        # Теперь DEBUG будет виден


    # 4. Применяем глобальную конфигурацию
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler]
    )
    
    return logging.getLogger(__name__)
