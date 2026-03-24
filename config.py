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
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, LOG_LEVEL, logging.INFO)

    log_formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s:%(lineno)d - %(message)s"
    )

    file_handler = logging.FileHandler("bot_logs.log", encoding="utf-8")
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)  # можно INFO если хочешь меньше

    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(color_formatter)
    console_handler.setLevel(level)

    logging.basicConfig(
        level=level,
        handlers=[file_handler, console_handler]
    )

    # Душим лишний шум
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    return logging.getLogger(__name__)
