import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
import requests
import hashlib
from datetime import datetime

API_TOKEN = "7059190222:AAEcrqvPUd2TVXCrk9YewKkE23EpQmeHvkc"
BITRIX24_WEBHOOK_URL = "https://b24-n6ip93.bitrix24.kz/rest/1/af6asaygshr5l8c2/lists.element.add"
LIST_ID = '25'  # Идентификатор списка
TITLE_FIELD_CODE = 'NAME'  # Код поля для названия (Title)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())
user_data = {}

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Анкета"]
    keyboard.add(*buttons)
    await message.answer("Выберите раздел:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "Анкета")
async def start_survey(message: types.Message):
    await message.answer("Введите ваше ФИО:")
    user_data[message.from_user.id] = {'step': 'fio'}

@dp.message_handler(lambda message: user_data.get(message.from_user.id, {}).get('step') == 'fio')
async def process_fio(message: types.Message):
    user_data[message.from_user.id]['fio'] = message.text
    user_data[message.from_user.id]['step'] = 'phone'
    await message.answer("Введите ваш номер телефона:")

@dp.message_handler(lambda message: user_data.get(message.from_user.id, {}).get('step') == 'phone')
async def process_phone(message: types.Message):
    user_data[message.from_user.id]['phone'] = message.text
    user_data[message.from_user.id]['step'] = 'email'
    await message.answer("Введите вашу почту:")

@dp.message_handler(lambda message: user_data.get(message.from_user.id, {}).get('step') == 'email')
async def process_email(message: types.Message):
    user_data[message.from_user.id]['email'] = message.text
    user_data[message.from_user.id]['step'] = 'address'
    await message.answer("Введите ваш адрес проживания:")

@dp.message_handler(lambda message: user_data.get(message.from_user.id, {}).get('step') == 'address')
async def process_address(message: types.Message):
    user_data[message.from_user.id]['address'] = message.text

    await message.answer("Спасибо! Ваши данные отправлены.")
    await send_data_to_bitrix(user_data[message.from_user.id])

    # Очищаем данные после отправки
    del user_data[message.from_user.id]

async def send_data_to_bitrix(data):
    # Создаем уникальный ELEMENT_CODE, например, хешируем комбинацию данных пользователя и текущей даты
    element_code = hashlib.sha256(f"{data['fio']}_{datetime.now()}".encode()).hexdigest()

    payload = {
        'IBLOCK_TYPE_ID': 'lists',
        'IBLOCK_ID': LIST_ID,
        'ELEMENT_CODE': element_code,
        'fields': {
            'NAME': data['fio'],  # Здесь указывается название (Title)
            'PROPERTY_107': data['phone'],
            'PROPERTY_109': data['email'],
            'PROPERTY_111': data['address']  # Убедитесь, что 'ADDRESS' соответствует идентификатору поля в вашем списке
        }
    }

    response = requests.post(BITRIX24_WEBHOOK_URL, json=payload)
    if response.status_code == 200:
        logging.info("Data successfully sent to Bitrix24")
    elif response.status_code == 400 and "ERROR_ELEMENT_ALREADY_EXISTS" in response.text:
        logging.warning("Element already exists in Bitrix24. Consider updating instead of creating.")
    else:
        logging.error(f"Failed to send data to Bitrix24: {response.status_code} - {response.text}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
