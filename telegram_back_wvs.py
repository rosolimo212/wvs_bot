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
exit_markup = make_answer_buttons([
    'Вернуться позже',
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
    print("Это мы зашли в option1_proc")
    user_id = message.from_user.id
    user_name = message.from_user.username
    await Form.waiting_for_answer.set()

    num_questions_ready = await get_next_question(str(user_id))
    print("В option1_proc прочитали номер последнего вопроса", str(num_questions_ready))
    num_questions_rest = len(qv_data['questions']) - num_questions_ready
    time = np.floor(num_questions_rest * 0.75)
    print('num_questions_rest', num_questions_rest)
    if num_questions_rest > 0:
        await message.answer(
                                user_data_message.format(
                                                        user_name=user_name,
                                                        num = num_questions_rest,
                                                        time = time,
                                                        ),
                                reply_markup=ok_markup
                            )
        await message.answer(qv_data['questions'][num_questions_ready]['text'], reply_markup=exit_markup)
        print("Задан вопрос ", qv_data['questions'][num_questions_ready]['text'])
    else:
        await message.answer("Вы заполнили анкету целиком! Всё хорошо", reply_markup=ok_markup)
        await Form.waiting_for_option.set()


async def option2_proc(message):
    await message.answer("Эта функция появится позже", reply_markup=ok_markup)


async def option3_proc(message):
    await message.answer("Эта функция появится позже", reply_markup=ok_markup)


async def option4_proc(message):
    await message.answer("Эта функция появится позже", reply_markup=ok_markup)


async def get_next_question(user_id):
    print("Зашли в get_next_question")
    try:
        last_answered_question_df = dl.get_data("""
                            select max(qv_number) as num
                            from tl.user_answers
                            where user_id = '{user_id}'
                            limit 1
                            """.format(
                                        user_id=user_id
                                        ), 'config_wvs.yaml')
        last_answered_question_df['num'] = last_answered_question_df['num'].fillna(0)
        print("В get_next_question датафрейм целиком", last_answered_question_df)
        last_answered_question_num = int(last_answered_question_df['num'].values[0])
        print("В get_next_question целевое число", last_answered_question_num)
    except Exception as e:
        print("В get_next_question началось исключение")
        print(str(e))
        last_answered_question_num = 0
   
    return last_answered_question_num


@dp.message_handler(lambda message: message.text.lower() != 'вернуться позже', state=Form.waiting_for_answer)
async def make_qv(message: types.Message, state: FSMContext):
    print("Это мы зашли в make_qv")
    last_answer = str(message.text)
    print("В make_qv прошлый ответ", str(last_answer))
    user_id = message.from_user.id

    last_question_index = await get_next_question(user_id)
    print("В make_qv номер последнего вопроса", str(last_question_index))
    last_question = qv_data['questions'][last_question_index]

    df_to_sql = pd.DataFrame([
                                str(message.from_user.id),
                                str(message.from_user.username),
                                last_question['id'],
                                last_question['num'],
                                last_question['text'],
                                last_answer,
                                ]).T
    df_to_sql.columns = ['user_id', 'user_name', 'qv_id', 'qv_number', 'qv_text', 'answer_text']
    dl.insert_data(df_to_sql, 'tl', 'user_answers', 'config_wvs.yaml', section='logging')

    try:
        next_question_index = await get_next_question(user_id)
        print("В make_qv номер следующего вопроса", str(next_question_index))
        current_question = qv_data['questions'][next_question_index]
        await message.answer(current_question['text'], reply_markup=exit_markup)
        print("Задан вопрос ", current_question['text'])
    except:
        await message.answer("Вы заполнили анкету целиком! Всё хорошо", reply_markup=ok_markup)
        await state.finish()
        await Form.waiting_for_option.set()

@dp.message_handler(lambda message: message.text.lower() == 'вернуться позже', state=Form.waiting_for_answer)
async def back_to_main_menu_qv(message: types.Message, state: FSMContext):
    await show_main_menu(message, state)
 
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
