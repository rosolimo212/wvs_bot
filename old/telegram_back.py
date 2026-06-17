# coding: utf-8
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

import numpy as np
import pandas as pd

import os
current_dir = os.path.abspath(os.getcwd())
parent_dir = os.path.dirname(current_dir)

import data_load as dl
import epics as chst

import sys
sys.path.append(current_dir)

telegram_settings = dl.read_yaml_config('config.yaml', section='telgram_test_bot')
telegram_api_token = telegram_settings['token']
admin_chat_id = 249792088

postres_settings = dl.read_yaml_config('config.yaml', section='logging')


hello_message = """Привет! Этот бот поможет тебе узнать детали того, как ты играешь турниры! 
"""
choice_message = """Выберете вариант из предложенных: 
"""
option1_message = """Посмотреть вероятности взятий конкретного турнира"""
option2_message = """Посмотреть таблицу"""
option3_message = """Запланировать календарь"""

team_request_message = """
Для начала, пожалуйста, введи ID своей команды. 
Его можно узнать тут: https://rating.chgk.info/teams
"""
team_request_sucsess_message = """
Команда {team_name} успешно найдена!
"""
tournament_request_message = """Отлично! 
Теперь введи ID турнира. 
Его можно узнать тут: https://rating.chgk.info/tournaments
"""
tournament_request_sucsess_message = """
Турнир {tourn_name} в базе существует!
"""
before_proc_message = """Отлично! 
Теперь мы попробуем забрать данные с турнирного сайта и всё посчитать.
Это занимает какое-то время, обычно 5-10 секунд
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

# Определяем состояния
class Form(StatesGroup):
    # ожидание ввода команды
    waiting_for_team = State()  
    # ожидание ввода турнира
    waiting_for_tourn = State()
    # ожидание выбора опции в главном меню
    waiting_for_option = State()  

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
                                ])
    await message.answer(hello_message)
    await message.answer(choice_message, reply_markup=markup)

    await Form.waiting_for_option.set()  # Устанавливаем состояние ожидания опции

@dp.message_handler(state=Form.waiting_for_option)
async def process_option(message: types.Message, state: FSMContext):
    markup = make_answer_buttons([
    'Ok',
                        ])
    if message.text.lower() == option1_message.lower():
        result = await current_tourn_stat(state, message)
    elif message.text.lower() == option2_message.lower():
        result = await option2_proc(message)
    elif message.text.lower() == option3_message.lower():
        result = await option3_proc(message)
    elif message.text.lower() == "Ok".lower():
        result = await show_main_menu(message, state)
    else:
        await message.answer(error_message, reply_markup=markup)

@dp.message_handler(lambda message: message.text.lower() == "Ok", state=Form.waiting_for_option)
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await show_main_menu(message)

async def current_tourn_stat(state, message):
     await Form.waiting_for_team.set()
     await message.answer(team_request_message, reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=Form.waiting_for_team)
async def get_team(message, state): 
    team_id = message.text  
    await state.update_data(team_id=team_id)

    try:
        team_name = chst.get_team_name(team_id)
        await message.answer(
                                team_request_sucsess_message.format(team_name=team_name), 
                                reply_markup=types.ReplyKeyboardRemove()
                            )
        
        await Form.waiting_for_tourn.set()
        await message.answer(tournament_request_message)
    except Exception as e:
        print(str(e))
        await message.answer(error_message)

@dp.message_handler(state=Form.waiting_for_tourn)
async def get_tourn(message, state): 
    tourn_id = message.text  
    await state.update_data(tourn_id=tourn_id)

    try:
        tourn_name = chst.get_tournament_name(tourn_id)
        await message.answer(
                                tournament_request_sucsess_message.format(tourn_name=tourn_name), 
                                reply_markup=types.ReplyKeyboardRemove()
                            )
        await message.answer(before_proc_message)
        await Form.waiting_for_option.set()
        await make_concl(message, state)

    except Exception as e:
        print(str(e))
        await message.answer(error_message)

async def option2_proc(message):
    markup = make_answer_buttons([
    'Ok',
                        ])
    await message.answer("Эта функция появится позже", reply_markup=markup)

async def option3_proc(message):
    markup = make_answer_buttons([
    'Ok',
                        ])
    await message.answer("Эта функция появится позже", reply_markup=markup)

async def make_concl(message, state):
    markup = make_answer_buttons([
        'Ok',
                            ])

    threshold = 0.3
    user_data = await state.get_data() 
    tourn_id = int(user_data.get("tourn_id")) 
    team_id = int(user_data.get("team_id"))

    try:
        tourn_df, question_df, players_df = chst.get_tourn_result(tourn_id)
        await message.answer("Результаты турнира в базе найдены")

        try:
            question_df = question_df.merge(tourn_df, 'left', on=['tourn_id', 'team_id'])
            qv_df = chst.tourn_stat(question_df)
            qv_stat = chst.diff_stat(qv_df)
            await message.answer("Расплюсовка турнира загружена", reply_markup=markup)

            try:
                res_df = qv_stat[
                                (qv_stat['team_id'] == team_id) &
                                (qv_stat['from_expected'] > threshold)
                                ].sort_values(by='from_expected', ascending=False)
            except Exception as e:
                print(str(e))
                await message.answer("Кажется, команда не играла выбранный вами турнир", reply_markup=markup)

            if len(res_df) == 0:
                await message.answer("Кажется, команда не играла выбранный вами турнир", reply_markup=markup)
            else:
                res_df['difficulty'] = np.round(res_df['difficulty'], 2)
                res_df['from_expected'] = np.round(res_df['from_expected'], 2)
                epics_df = res_df[
                                    res_df['qv_result'] == 1
                                ][[
                                    'team_name', 
                                    'question_num', 'difficulty', 'from_expected'
                                ]].set_index('team_name')
                
                prod_df = res_df[
                                    res_df['qv_result'] == 0
                                ][[
                                    'team_name', 
                                    'question_num', 'difficulty', 'from_expected'
                                ]].set_index('team_name')

                res_str, pdod_str, epic_str = chst.make_strs(res_df, epics_df, prod_df)
                await message.answer(res_str)
                await message.answer(pdod_str)
                await message.answer(epic_str, reply_markup=markup)

        except Exception as e:
            print(str(e))
            await message.answer("Кажется, расплюсовки у турнира ещё нет", reply_markup=markup)
    except Exception as e:
        print(str(e))
        await message.answer("Кажется, с турниром есть какая-то ошибка", reply_markup=markup)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)