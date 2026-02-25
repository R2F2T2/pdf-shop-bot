from aiogram import Router, F, types
from aiogram.types import LabeledPrice
from config import PAYMENT_TOKEN
import database as db

router = Router()

@router.pre_checkout_query()
async def process_pre_checkout(query: types.PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def success_pay(message: types.Message):
    p_id = message.successful_payment.invoice_payload
    product = await db.get_product(p_id)
    file_id = product['file_id']
    await message.answer(f"✅ Спасибо за покупку! Вот ваш файл:")
    await message.answer_document(file_id)

@router.callback_query(F.data.startswith("buy_"))
async def handle_buy(callback: types.CallbackQuery):
    p_id = callback.data.split("_")[1]
    product = await db.get_product(p_id)
    name = product['name']
    price = product['price']

    prices = [LabeledPrice(label=product['name'], amount=int(price* 100))]

    print(f'Запускаем платежку {p_id}')
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