from aiogram import Router, F, types
from aiogram.types import LabeledPrice
from config import PAYMENT_TOKEN
from models import ProdAction
import database as db
from handlers import user
#Создаем логгер
from config import init_logging
init_logging()
import logging
logger = logging.getLogger(__name__)
#----------------------------
router = Router()

@router.pre_checkout_query()
async def process_pre_checkout(query: types.PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def success_pay(message: types.Message):
    # Данные платежа
    payload = message.successful_payment.invoice_payload
    product = await db.get_product(payload)
    
    # Можно попробовать удалить сообщение об успешной оплате (сервисное), 
    # но Telegram не всегда дает это сделать сразу. 
    # Поэтому просто шлем файл.
    
    await message.answer(f"✅ Оплата принята! Благодарим за покупку <b>{product.name}</b>.", parse_mode="HTML")
    
    # Отправляем файл
    if product.file_id:
        await message.answer_document(
            document=product.file_id,
            caption="Ваш документ готов к скачиванию"
        )
    else:
        await message.answer("Ошибка: файл не найден в базе. Обратитесь в поддержку.")
    await user.show_main_menu(message)


@router.callback_query(ProdAction.filter(F.action == "pay"))
async def handle_buy(callback: types.CallbackQuery, callback_data: ProdAction):
    p_id = callback_data.id
    logger.info(f"Пользователь id={callback.from_user.id} запустил оплату товара: {p_id}")
    
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение перед инвойсом: {e}")

    product = await db.get_product(p_id)
    name = product.name
    price = product.price

    prices = [LabeledPrice(label=name, amount=int(float(price) * 100))]

    await callback.message.answer_invoice(
        title=name,
        description=f"Покупка {name}",
        payload=str(p_id),
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=prices,
        start_parameter="pay"
    )
    await callback.answer()