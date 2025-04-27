# coding: utf-8
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

import numpy as np
import pandas as pd

import json

import os
current_dir = os.path.abspath(os.getcwd())
parent_dir = os.path.dirname(current_dir)

import data_load as dl

import sys
sys.path.append(current_dir)

telegram_settings = dl.read_yaml_config('config_wvs.yaml', section='telgram_test_bot')
telegram_api_token = telegram_settings['token']
admin_chat_id = 249792088

postres_settings = dl.read_yaml_config('config_wvs.yaml', section='logging')

# Загрузка JSON из файла
with open('questions.json', 'r', encoding='utf-8') as file:
    qv_data = json.load(file)

hello_message = """Привет! Этот бот поможет тебе разобраться в ценностях и сравнить свои ценности с ценностями других людей
"""
choice_message = """Выберете вариант из предложенных: 
"""
option1_message = """Заполнить основную анкету"""
option2_message = """Заполнить дополнительную анкету"""
option3_message = """Найти страну, близкую вам по ценностям"""
option4_message = """Понять своё место в социуме"""
user_data_message = """
Заполняем основную анкету. 
Мы будет сохранять ответы для пользователя с именем {user_name} в Telegram.
Вам осталось заполнить {num} вопросов, это займёт около {time} минут. 
Вы можете закончить заполнение анкеты и продолжить его в любой момент.  
Приступаем?
"""
finish_message = """'ОК' возвращает вас в главное меню
"""
error_message = """Что-то пошло не так. Возможно, ошибка на нашей стороне. А возможно, вы ввели что-то неожиданное
Попробуйте начать сначала, выбрав команду /start
"""
# about buttons
def make_answer_buttons(buttons_lst):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for button in buttons_lst:
        item = types.KeyboardButton(button)
        markup.add(item)
    
    return markup 

ok_markup = make_answer_buttons([
    'Ok',
                        ])
start_markup = make_answer_buttons([
    'Давайте!',
                        ])

# Определяем состояния
class Form(StatesGroup):
    # ожидание ввода команды
    waiting_for_option = State()  
    # ожидание ввода турнира
    waiting_for_user_data = State()
    # ожидание выбора опции в главном меню
    waiting_for_answer = State()  

# Инициализация бота и диспетчера
bot = Bot(token=telegram_api_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

@dp.message_handler(commands='start', state='*')
async def show_main_menu(message: types.Message, state: FSMContext):
    await Form.waiting_for_option.set()

    markup = make_answer_buttons([
                                    option1_message, 
                                    option2_message, 
                                    option3_message,
                                    option4_message,
                                ])
    await message.answer(hello_message)
    await message.answer(choice_message, reply_markup=markup)

    await Form.waiting_for_option.set()  # Устанавливаем состояние ожидания опции

@dp.message_handler(state=Form.waiting_for_option)
async def process_option(message: types.Message, state: FSMContext):
    if message.text.lower() == option1_message.lower():
        result = await option1_proc(message)
    elif message.text.lower() == option2_message.lower():
        result = await option2_proc(message)
    elif message.text.lower() == option3_message.lower():
        result = await option3_proc(message)
    elif message.text.lower() == option4_message.lower():
        result = await option4_proc(message)
    elif message.text.lower() == "Ok".lower():
        result = await show_main_menu(message, state)
    else:
        await message.answer(error_message, reply_markup=ok_markup)

@dp.message_handler(lambda message: message.text.lower() == "Ok", state=Form.waiting_for_option)
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await show_main_menu(message)

async def option1_proc(message):
    user_id = message.from_user.id
    user_name = message.from_user.username
    num_questions_ready = await get_next_question(str(user_id))
    num_questions_rest = len(qv_data['questions']) - num_questions_ready
    # await message.answer(str(num_questions_ready))
    # await message.answer(str(num_questions_rest))

    time = np.floor(num_questions_rest * 0.75)
    await message.answer(
                            user_data_message.format(
                                                    user_name=user_name,
                                                    num = num_questions_rest,
                                                    time = time,
                                                    ), 
                            reply_markup=start_markup
                        )
    await Form.waiting_for_answer.set()

async def option2_proc(message):
    await message.answer("Эта функция появится позже", reply_markup=ok_markup)

async def option3_proc(message):
    await message.answer("Эта функция появится позже", reply_markup=ok_markup)

async def option4_proc(message):
    await message.answer("Эта функция появится позже", reply_markup=ok_markup)


async def get_next_question(user_id):
    try:
        last_answered_question_df = dl.get_data("""
                            select max(qv_number) as num
                            from tl.user_answers
                            where user_id = '{user_id}'
                            limit 1
                            """.format(
                                        user_id=user_id
                                        ), 'config_wvs.yaml')
        last_answered_question_num = int(last_answered_question_df['num'].values[0])
    except Exception as e:
        print(str(e))
        last_answered_question_num = 0
   
    print('answered_questions', last_answered_question_num)
    return last_answered_question_num

@dp.message_handler(lambda message: message.text.lower() != 'Давайте!', state=Form.waiting_for_answer)
async def make_qv(message: types.Message, state: FSMContext):
    last_answer = str(message.text)
    await message.answer(last_answer)

    user_id = message.from_user.id
    last_answered_question_num = await get_next_question(user_id)
    last_question = qv_data['questions'][last_answered_question_num]
    current_question = qv_data['questions'][last_answered_question_num+1]

    print('last_answered_question_num', last_answered_question_num)
    await message.answer('Самый свежий вопрос в базе ' + str(last_answered_question_num))

    df_to_sql = pd.DataFrame([
                                str(message.from_user.id),
                                str(message.from_user.username),
                                current_question['id'],
                                current_question['num'],
                                current_question['text'],
                                last_answer,
                                ]).T
    df_to_sql.columns = ['user_id', 'user_name', 'qv_id', 'qv_number', 'qv_text', 'answer_text']
    if last_answer != 'Давайте!':
        dl.insert_data(df_to_sql, 'tl', 'user_answers', 'config_wvs.yaml', section='logging')
    
    await message.answer('В БД пойдёт такое: \n' + str(df_to_sql))

    await message.answer(current_question['text'], reply_markup=types.ReplyKeyboardRemove())
 
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
