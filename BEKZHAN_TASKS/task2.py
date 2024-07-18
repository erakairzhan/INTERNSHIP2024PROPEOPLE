import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import requests
import datetime

API_TOKEN = "7059190222:AAEcrqvPUd2TVXCrk9YewKkE23EpQmeHvkc"
BITRIX24_WEBHOOK_URL = "https://b24-n6ip93.bitrix24.kz/rest/1/af6asaygshr5l8c2/calendar.event.add"
BITRIX24_EVENTS_URL = "https://b24-n6ip93.bitrix24.kz/rest/1/af6asaygshr5l8c2/calendar.event.get"

# Замените на ID секций переговорных комнат
ROOMS = {
    "BCC 9 этаж": "calendar_13_47",
    "BCC 10 этаж": "calendar_11_43",
    "BCC 11 этаж": "calendar_15_51"
}

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

class BookingStates(StatesGroup):
    waiting_for_room = State()
    waiting_for_date = State()
    waiting_for_time = State()

def create_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton(text="🎢 Заявки", callback_data="option_1"),
        InlineKeyboardButton(text="🗓 Бронь переговорки", callback_data="option_2"),
        InlineKeyboardButton(text="🌑 Dream Coins", callback_data="option_3"),
        InlineKeyboardButton(text="📚 Библиотека", callback_data="option_4"),
        InlineKeyboardButton(text="✨ BFE Плюшки", callback_data="option_5"),
        InlineKeyboardButton(text="❓ Задать вопрос", callback_data="option_6")
    ]
    keyboard.add(*buttons)
    return keyboard

def create_inline_keyboard_rooms():
    keyboard = InlineKeyboardMarkup(row_width=1)
    buttons = [InlineKeyboardButton(text=name, callback_data=name) for name in ROOMS.keys()]
    buttons.append(InlineKeyboardButton(text="Назад", callback_data="back_to_main"))
    keyboard.add(*buttons)
    return keyboard

def create_inline_keyboard_dates():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="Сегодня", callback_data="today"),
        InlineKeyboardButton(text="Завтра", callback_data="tomorrow"),
        InlineKeyboardButton(text="Назад", callback_data="back_to_rooms")
    )
    return keyboard

def create_inline_keyboard_times(available_times):
    keyboard = InlineKeyboardMarkup(row_width=3)
    for time in available_times:
        keyboard.insert(InlineKeyboardButton(text=time, callback_data=time))
    keyboard.add(InlineKeyboardButton(text="Назад", callback_data="back_to_dates"))
    return keyboard

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    keyboard = create_inline_keyboard()
    await message.answer("<b>Салем!</b>\nМы собрали полезные для тебя услуги, пользуйся!", reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query_handler(text="option_2")
async def handle_option_2(callback_query: types.CallbackQuery):
    keyboard = create_inline_keyboard_rooms()
    await bot.send_message(callback_query.from_user.id, "Выберите переговорную комнату:", reply_markup=keyboard)
    await BookingStates.waiting_for_room.set()
    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(state=BookingStates.waiting_for_room)
async def handle_room_selection(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "back_to_main":
        await send_welcome(callback_query.message)
        await state.finish()
        await bot.answer_callback_query(callback_query.id)
        return
    
    await state.update_data(room=callback_query.data)
    keyboard = create_inline_keyboard_dates()
    await bot.send_message(callback_query.from_user.id, "Выберите день для бронирования:", reply_markup=keyboard)
    await BookingStates.waiting_for_date.set()
    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(state=BookingStates.waiting_for_date)
async def process_date(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "back_to_rooms":
        keyboard = create_inline_keyboard_rooms()
        await bot.send_message(callback_query.from_user.id, "Выберите переговорную комнату:", reply_markup=keyboard)
        await BookingStates.waiting_for_room.set()
        await bot.answer_callback_query(callback_query.id)
        return

    await state.update_data(date=callback_query.data)
    data = await state.get_data()
    room = data.get('room')
    print(room)
    date_choice = data.get('date')

    date = datetime.date.today() if date_choice == 'today' else datetime.date.today() + datetime.timedelta(days=1)
    start_time = datetime.datetime.combine(date, datetime.time(0, 0))
    end_time = datetime.datetime.combine(date, datetime.time(23, 59))

    event_data = {
        'type': 'user',
        'ownerId': '1',
        'from': start_time.strftime('%Y-%m-%d %H:%M:%S'),
        'to': end_time.strftime('%Y-%m-%d %H:%M:%S'),
        'section': ROOMS[room]
    }

    response = requests.post(BITRIX24_EVENTS_URL, json=event_data)

    if response.status_code == 200:
        events = response.json().get('result', [])
        busy_times = [event['DATE_FROM'][11:16] for event in events]
        available_times = [f"{hour}:00" for hour in range(10, 19) if f"{hour}:00" not in busy_times]
        keyboard = create_inline_keyboard_times(available_times)
        await bot.send_message(callback_query.from_user.id, "Выберите время для бронирования:", reply_markup=keyboard)
        await BookingStates.waiting_for_time.set()
    else:
        logging.error(f"Ошибка при получении событий: {response.status_code} - {response.text}")
        await bot.send_message(callback_query.from_user.id, "Ошибка при получении событий, попробуйте позже.")

    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(state=BookingStates.waiting_for_time)
async def process_time(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "back_to_dates":
        keyboard = create_inline_keyboard_dates()
        await bot.send_message(callback_query.from_user.id, "Выберите день для бронирования:", reply_markup=keyboard)
        await BookingStates.waiting_for_date.set()
        await bot.answer_callback_query(callback_query.id)
        return

    data = await state.get_data()
    room = data.get('room')
    date_choice = data.get('date')
    time = callback_query.data

    date = datetime.date.today() if date_choice == 'today' else datetime.date.today() + datetime.timedelta(days=1)
    start_time = datetime.datetime.combine(date, datetime.datetime.strptime(time, '%H:%M').time())
    end_time = start_time + datetime.timedelta(hours=1)  # Событие на 1 час

    event_data = {
        'type': 'user',
        'ownerId': '1',
        'name': f"Бронирование переговорки {room}",
        'from': start_time.strftime('%Y-%m-%d %H:%M:%S'),
        'to': end_time.strftime('%Y-%m-%d %H:%M:%S'),
        'section': "7",
        'location': ROOMS[room],
        'resource': room  # Имя ресурса (название переговорной комнаты)
    }

    response = requests.post(BITRIX24_WEBHOOK_URL, json=event_data)

    if response.status_code == 200:
        await bot.send_message(callback_query.from_user.id, "Бронирование успешно завершено!")
    else:
        logging.error(f"Ошибка при бронировании: {response.status_code} - {response.text}")
        await bot.send_message(callback_query.from_user.id, "Ошибка при бронировании, попробуйте позже.")

    await state.finish()
    await bot.answer_callback_query(callback_query.id)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)