import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import requests

# Bitrix24 URL
BITRIX24_USER_GET_URL = 'https://b24-n6ip93.bitrix24.kz/rest/1/af6asaygshr5l8c2/user.get.json'

# API token for Telegram bot
API_TOKEN = "7059190222:AAEcrqvPUd2TVXCrk9YewKkE23EpQmeHvkc"
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Define states
class SearchStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_full_name = State()
    waiting_for_phone_number = State()

# Function to get all users from Bitrix24
def get_all_users():
    response = requests.post(BITRIX24_USER_GET_URL, json={})
    if response.status_code == 200:
        return response.json().get('result', [])
    else:
        print(f"Error fetching users: {response.status_code} - {response.text}")
        return []

# Function to find user by username
def find_user_by_username(username):
    users = get_all_users()
    for user in users:
        if user.get('UF_USR_1721130322852') == f"@{username}":
            return user
    return None

# Function to find user by full name
def find_user_by_full_name(full_name):
    users = get_all_users()
    for user in users:
        if f"{user.get('LAST_NAME', '')} {user.get('NAME', '')}".strip() == full_name:
            return user
    return None

# Function to find user by phone number
def find_user_by_phone(phone_number):
    users = get_all_users()
    for user in users:
        if user.get('PERSONAL_MOBILE') == phone_number:
            return user
    return None

# Create inline keyboard for search options
def create_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton(text="Telegram(@username)", callback_data="option_1"),
        InlineKeyboardButton(text="Фамилия Имя", callback_data="option_2"),
        InlineKeyboardButton(text="Номер телефона", callback_data="option_3"),
        InlineKeyboardButton(text="Отменить поиск", callback_data="option_4"),
    ]
    keyboard.add(*buttons)
    return keyboard

@dp.message_handler(commands=["getprofile"])
async def ask_profile(message: types.Message):
    keyboard = create_inline_keyboard()
    await message.answer("Выберите вид поиска:", reply_markup=keyboard)

@dp.callback_query_handler(text="option_1")
async def handle_option_1(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Введите @username сотрудника:")
    await SearchStates.waiting_for_username.set()

@dp.callback_query_handler(text="option_2")
async def handle_option_2(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Введите Фамилию и Имя сотрудника:")
    await SearchStates.waiting_for_full_name.set()

@dp.callback_query_handler(text="option_3")
async def handle_option_3(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Введите сотовый номер сотрудника:")
    await SearchStates.waiting_for_phone_number.set()

@dp.callback_query_handler(text="option_4")
async def handle_option_4(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "Поиск отменен.")
    await FSMContext.finish()

@dp.message_handler(state=SearchStates.waiting_for_username)
async def process_username(message: types.Message, state: FSMContext):
    username = message.text.strip('@')
    user = find_user_by_username(username)
    if user:
        await message.answer(f"User found: {user}")
    else:
        await message.answer("User not found")
    await state.finish()

@dp.message_handler(state=SearchStates.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    user = find_user_by_full_name(full_name)
    if user:
        await message.answer(f"User found: {user}")
    else:
        await message.answer("User not found")
    await state.finish()

@dp.message_handler(state=SearchStates.waiting_for_phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    phone_number = message.text.strip()
    user = find_user_by_phone(phone_number)
    if user:
        await message.answer(f"User found: {user}")
    else:
        await message.answer("User not found")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
