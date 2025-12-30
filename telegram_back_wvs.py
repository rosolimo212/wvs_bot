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

def make_log_event(
                user_id,
                event_type='',
                parameters={}
                ):
    log_str = [user_id,event_type,parameters]
    logging_df = pd.DataFrame([log_str], columns=['user_id', 'event_type', 'parameters'])
    logging_df['parameters'] = logging_df['parameters'].astype(str)
    dl.insert_data(logging_df, 'tl', 'wvs_events', 'config_wvs.yaml', section='logging')


@dp.message_handler(commands='start', state='*')
async def show_main_menu(message: types.Message, state: FSMContext):
    await Form.waiting_for_option.set()
    user_id = message.from_user.id
    user_name = message.from_user.username
    make_log_event(user_id, event_type='main_menu', parameters=[])

    markup = make_answer_buttons([
                                    qv_data['dialogs']['option1_message'], 
                                    qv_data['dialogs']['option2_message'], 
                                    qv_data['dialogs']['option3_message'],
                                    qv_data['dialogs']['option4_message'],
                                ])
    await message.answer(qv_data['dialogs']['hello_message'])
    await message.answer(qv_data['dialogs']['choice_message'], reply_markup=markup)

    await Form.waiting_for_option.set()  # Устанавливаем состояние ожидания опции


@dp.message_handler(state=Form.waiting_for_option)
async def process_option(message: types.Message, state: FSMContext):
    if message.text.lower() == qv_data['dialogs']['option1_message'].lower():
        await state.update_data(option_flag='main')
        result = await option1_proc(message, state)
    elif message.text.lower() == qv_data['dialogs']['option2_message'].lower():
        await state.update_data(option_flag='secondary')
        result = await option2_proc(message, state)
    elif message.text.lower() == qv_data['dialogs']['option3_message'].lower():
        result = await option3_proc(message)
    elif message.text.lower() == qv_data['dialogs']['option4_message'].lower():
        result = await option4_proc(message)
    elif message.text.lower() == "Ok".lower():
        result = await show_main_menu(message, state)
    else:
        await message.answer(qv_data['dialogs']['error_message'], reply_markup=ok_markup)


@dp.message_handler(lambda message: message.text.lower() == "Ok", state=Form.waiting_for_option)
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await show_main_menu(message)


async def show_index(user_id):
    with open('count_ind.sql', 'r') as f:
        query= f.read()
    query = query.format(user_id=user_id)
    results_df = dl.get_data(query, 'config_wvs.yaml', section='logging')
    rv = results_df['rv'].values[0]
    sv = results_df['sv'].values[0]

    return qv_data['dialogs']['index_str'].format(
                rv=rv, 
                sv=sv
                )

async def show_nearest_country(user_id):
    with open('find_country.sql', 'r') as f:
        query= f.read()
    query = query.format(user_id=user_id)
    results_df = dl.get_data(query, 'config_wvs.yaml', section='logging')

    rv = results_df['rv'].values[0]
    sv = results_df['sv'].values[0]
    country_code = results_df['country_code'].values[0]
    country_rv = results_df['country_rv'].values[0]
    country_sv = results_df['country_sv'].values[0]

    return qv_data['dialogs']['nearest_country_str'].format(
                rv=rv, 
                sv=sv, 
                country_code=country_code, 
                country_rv=country_rv, 
                country_sv=country_sv
                ), sv, rv

import matplotlib.pyplot as plt
def plot_clusters_with_annotations(
    df,
    annotate_list,
    annotate_on='country_code',
    x='country_rv',
    y='country_sv',
    hue_candidates=('label', 'cluster', 'labels', 'group'),
    figsize=(12,8),
    point_size=80,
    cmap_small='tab10',
    user_point=None,
    user_label='You',
    user_marker_size=300,
    user_color='red',
    user_marker='o',
    label_fontsize=9,
    label_fontweight='bold',
    label_bbox_fc='white',
    label_bbox_alpha=0.35,    # None -> bbox отключён
    label_boxstyle='round,pad=0.2'
):
    # --- выбрать колонку для hue ---
    hue_col = None
    for c in hue_candidates:
        if c in df.columns:
            hue_col = c
            break
    if hue_col is None:
        raise ValueError(f"Не найдена колонка для hue. Проверяйте: {hue_candidates}")

    # --- выбрать строки для подписи ---
    if annotate_on == 'index':
        rows_to_annotate = df.loc[df.index.intersection(annotate_list)]
    else:
        if annotate_on not in df.columns:
            raise ValueError(f"Колонки '{annotate_on}' нет в df")
        rows_to_annotate = df[df[annotate_on].isin(annotate_list)]

    if rows_to_annotate.empty:
        raise ValueError("Ни одна строка не соответствует списку annotate_list")

    # --- подготовка палитры ---
    df = df.copy()
    df[hue_col] = df[hue_col].astype('category')
    n_colors = len(df[hue_col].cat.categories)
    palette = sns.color_palette(cmap_small if n_colors <= 10 else "husl", n_colors=n_colors)

    plt.figure(figsize=figsize)
    ax = sns.scatterplot(
        data=df, x=x, y=y, hue=hue_col,
        palette=palette, s=point_size, edgecolor='k', alpha=0.9
    )

    # bbox словарь (или None)
    def make_bbox():
        if label_bbox_alpha is None:
            return None
        return dict(boxstyle=label_boxstyle, fc=label_bbox_fc, ec='none', alpha=label_bbox_alpha)

    bbox_dict = make_bbox()

    # Calculate 4 pixels offset in data coordinates
    fig = ax.figure
    # Force a draw to ensure transforms are set up correctly
    fig.canvas.draw()
    # Get the axes bbox in display coordinates (pixels)
    ax_bbox = ax.get_window_extent()
    # Get y-axis range in data coordinates
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min
    # Get axes height in pixels
    ax_height_pixels = ax_bbox.height
    # Convert 4 pixels to data coordinates
    y_offset_data = (4 / ax_height_pixels) * y_range

    texts = []
    for _, r in rows_to_annotate.iterrows():
        # безопасно берем значение для подписи
        tx = r[annotate_on] if annotate_on != 'index' else r.name
        # Add 4 pixels offset in y direction
        t = ax.text(r[x], r[y] + y_offset_data, str(tx),
                    fontsize=label_fontsize, fontweight=label_fontweight,
                    ha='left', va='bottom', color='black',
                    bbox=bbox_dict)
        texts.append(t)

    # --- обработать user_point ---
    def extract_user_coords(up):
        if up is None:
            return None
        # tuple/list like (x,y)
        if isinstance(up, (list, tuple)) and len(up) == 2:
            return float(up[0]), float(up[1])
        # dict-like
        if isinstance(up, dict):
            ux = up.get(x, up.get('x', None))
            uy = up.get(y, up.get('y', None))
            if ux is None or uy is None:
                raise ValueError("В dict user_point ожидаются ключи '{}' и '{}' или 'x'/'y'".format(x, y))
            return float(ux), float(uy)
        # pandas Series (row) или DataFrame (берём первую строку)
        if isinstance(up, pd.Series):
            if x in up.index and y in up.index:
                return float(up[x]), float(up[y])
            # fallback: попытка по 'x'/'y'
            if 'x' in up.index and 'y' in up.index:
                return float(up['x']), float(up['y'])
            raise ValueError("Series не содержит колонок '{}' и '{}'".format(x, y))
        if isinstance(up, pd.DataFrame):
            row = up.iloc[0]
            return extract_user_coords(row)
        raise ValueError("user_point должен быть tuple/list (x,y) или dict илиpandas.Series/DataFrame")

    if user_point is not None:
        ux_uy = extract_user_coords(user_point)
        ux, uy = ux_uy

        # Draw vertical dashed line at x = user_point[0]
        ax.axvline(ux, color=user_color, linestyle='--', linewidth=1.5, zorder=200, label=user_label)
        # Draw horizontal dashed line at y = user_point[1]
        ax.axhline(uy, color=user_color, linestyle='--', linewidth=1.5, zorder=200)

    # --- скорректировать подписи (если есть adjustText и есть подписи) ---
    if texts:
        try:
            from adjustText import adjust_text
            adjust_text(texts,
                        only_move={'points':'y','texts':'y'},
                        arrowprops=dict(arrowstyle='-', color='gray', lw=0.5),
                        ax=ax)
        except Exception:
            # если adjustText не установлен или упал — пропускаем
            pass

    ax.set_title(f"Положение относительно других стран", fontsize=14)
    ax.set_xlabel("Традиционные/Секулярно-рациональные ценности")
    ax.set_ylabel("Ценности выживания/ Самовыражения")
    
    # Show legend only if user_point is provided (to show user label)
    if user_point is not None:
        ax.legend(bbox_to_anchor=(1.02,1), loc='upper left')
    
    plt.tight_layout()
    plt.show()

    return ax


def show_country_plot(user_sv, user_rv):
    print("Зашли в show_country_plot")
    df = dl.get_data(
                """
                select country_code, country_rv, country_sv
                from tl.country_data
                where country_code != 'EGY'
                """
                , 
                'config_wvs.yaml', 
                section='logging'
        )
    df['country_rv'] = df['country_rv'].fillna(user_rv).astype(float)
    df['country_sv'] = df['country_sv'].fillna(user_sv).astype(float)

    ax = plot_clusters_with_annotations(
        df, 
        ['RUS','USA', 'UZB', 'GTM', 'AND', 'PAK', 'KOR', 'DEU', 'JPN', 'MDV', 'ARG', 'CAN'], 
        annotate_on='country_code',
        user_point=(user_sv, user_rv), 
        user_label='Вы', 
        label_bbox_alpha=0.2,
        x='country_sv',
        y='country_rv',
                                )
    ax.figure.savefig('geo.png')



async def show_position(user_id):
    with open('count_pos.sql', 'r') as f:
        query= f.read()
    query = query.format(user_id=user_id)
    results_df = dl.get_data(query, 'config_wvs.yaml', section='logging')

    rv = results_df['rv'].values[0]
    sv = results_df['sv'].values[0]
    rv_rank = int(np.round(results_df['rv_rank'].values[0], 2) * 100)
    sv_rank = int(np.round(results_df['sv_rank'].values[0], 2) * 100)


    return qv_data['dialogs']['position_str'].format(
                rv=rv, 
                sv=sv, 
                rv_rank=rv_rank, 
                sv_rank=sv_rank
                )


async def option1_proc(message, state: FSMContext):
    print("Это мы зашли в option1_proc")
    user_id = message.from_user.id
    user_name = message.from_user.username
    make_log_event(user_id, event_type='main_questionary', parameters=[])
    await state.update_data(option_flag='main')
    await Form.waiting_for_answer.set()

    num_questions_ready = await get_next_question(str(user_id), table_name='tl.user_answers')
    print("В option1_proc прочитали номер последнего вопроса", str(num_questions_ready))
    num_questions_rest = len(qv_data['main_questions']) - num_questions_ready
    time = np.floor(num_questions_rest * 0.35)
    print('num_questions_rest', num_questions_rest)
    if num_questions_rest > 0:
        await message.answer(
                                qv_data['dialogs']['user_data_message'].format(
                                                        user_name=user_name,
                                                        num = num_questions_rest,
                                                        time = time,
                                                        ),
                                reply_markup=ok_markup
                            )
        variants_from_qv = qv_data['main_questions'][num_questions_ready]['variants']
        variants_to_dialog = []
        for v in variants_from_qv:
            variants_to_dialog.append(v)
        variants_to_dialog.append('Вернуться позже')
        print('len', len(variants_to_dialog))
        qv_markup = make_answer_buttons(variants_to_dialog)
        print(variants_to_dialog)
        await message.answer(qv_data['main_questions'][num_questions_ready]['text'], reply_markup=qv_markup)
        print("Задан вопрос ", qv_data['main_questions'][num_questions_ready]['text'])
        
    else:
        await message.answer("Вы заполнили анкету целиком! Всё хорошо", reply_markup=ok_markup)
        make_log_event(user_id, event_type='questions_finished', parameters=[])
        results_str = await show_index(user_id)
        await message.answer(results_str, reply_markup=ok_markup)
        await Form.waiting_for_option.set()


async def option2_proc(message, state: FSMContext):
    user_name = message.from_user.username
    user_id = message.from_user.id
    make_log_event(user_id, event_type='secondary_questionary', parameters=[])

    await state.update_data(option_flag='secondary')
    await Form.waiting_for_answer.set()

    num_questions_ready = await get_next_question(str(user_id), table_name='tl.user_reviews')
    print("В option2_proc прочитали номер последнего вопроса", str(num_questions_ready))
    num_questions_rest = len(qv_data['secondary_questions']) - num_questions_ready
    time = np.floor(num_questions_rest * 0.35)
    print('num_questions_rest', num_questions_rest)

    if num_questions_rest > 0:
        await message.answer(
                                qv_data['dialogs']['second_questionary_message'].format(
                                                        user_name=user_name,
                                                        num = num_questions_rest,
                                                        time = time,
                                                        ),
                                reply_markup=ok_markup
                            )
        variants_from_qv = qv_data['secondary_questions'][num_questions_ready]['variants']
        variants_to_dialog = []
        for v in variants_from_qv:
            variants_to_dialog.append(v)
        variants_to_dialog.append('Вернуться позже')
        print('len', len(variants_to_dialog))
        qv_markup = make_answer_buttons(variants_to_dialog)
        print(variants_to_dialog)
        await message.answer(qv_data['secondary_questions'][num_questions_ready]['text'], reply_markup=qv_markup)
        print("Задан вопрос ", qv_data['secondary_questions'][num_questions_ready]['text'])
        
    else:
        await message.answer("Вы заполнили анкету целиком! Всё хорошо", reply_markup=ok_markup)
        make_log_event(user_id, event_type='secondary_questions_finished', parameters=[])
        await Form.waiting_for_option.set()

    


async def option3_proc(message):
    user_name = message.from_user.username
    user_id = message.from_user.id
    try:
        nearest_country_str, sv, rv = await show_nearest_country(user_id)
        make_log_event(user_id, event_type='find_country', parameters=[{'answer': nearest_country_str}])
        await message.answer(nearest_country_str, reply_markup=ok_markup)

        show_country_plot(sv, rv)
        with open('geo.png', 'rb') as photo:
            await message.answer_photo(photo)
    except Exception as e:
        print(str(e))
        await message.answer("Для начала нужно заполнить основную анкету", reply_markup=ok_markup)
        make_log_event(user_id, event_type='find_country', parameters=[{'answer': 'No data'}])


async def option4_proc(message):
    user_name = message.from_user.username
    user_id = message.from_user.id
    try:
        user_position_str = await show_position(user_id)
        make_log_event(user_id, event_type='find_position', parameters=[{'answer': user_position_str}])
        await message.answer(user_position_str, reply_markup=ok_markup)
    except Exception as e:
        await message.answer("Для начала нужно заполнить основную анкету", reply_markup=ok_markup)
        make_log_event(user_id, event_type='find_position', parameters=[{'answer': 'No data'}])

async def get_next_question(user_id, table_name='tl.user_answers'):
    print("Зашли в get_next_question")
    try:
        last_answered_question_df = dl.get_data(f"""
                            select max(qv_number) as num
                            from {table_name}
                            where user_id = '{user_id}'
                            limit 1
                            """.format(
                                        user_id=user_id,
                                        table_name=table_name
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
    # Get the questionnaire type from state (per-user storage)
    state_data = await state.get_data()
    option_flag = state_data.get('option_flag', 'main')  # Default to 'main' if not set
    print("option_flag", option_flag)
    last_answer = str(message.text)
    print("В make_qv прошлый ответ", str(last_answer))
    user_id = message.from_user.id

    if option_flag == 'main':
        table_name = 'tl.user_answers'
        questions_key = 'main_questions'
        table_insert = 'user_answers'
    elif option_flag == 'secondary':
        table_name = 'tl.user_reviews'
        questions_key = 'secondary_questions'
        table_insert = 'user_reviews'
    else:
        # Fallback to main if flag is invalid
        table_name = 'tl.user_answers'
        questions_key = 'main_questions'
        table_insert = 'user_answers'

    last_question_index = await get_next_question(user_id, table_name=table_name)
    print("В make_qv номер последнего вопроса", str(last_question_index))
    last_question = qv_data[questions_key][last_question_index]

    df_to_sql = pd.DataFrame([
                                str(message.from_user.id),
                                str(message.from_user.username),
                                last_question['id'],
                                int(last_question['num']),
                                last_question['text'],
                                last_answer,
                                ]).T
    df_to_sql.columns = ['user_id', 'user_name', 'qv_id', 'qv_number', 'qv_text', 'answer_text']
    dl.insert_data(df_to_sql, 'tl', table_insert, 'config_wvs.yaml', section='logging')
    make_log_event(user_id, event_type='record_answer', parameters=[{'qv_number': int(last_question['num'])}])

    try:
        next_question_index = await get_next_question(user_id, table_name=table_name)
        print("В make_qv номер следующего вопроса", str(next_question_index))
        current_question = qv_data[questions_key][next_question_index]

        variants_from_qv = current_question['variants']
        variants_to_dialog = []
        for v in variants_from_qv:
            variants_to_dialog.append(v)
        variants_to_dialog.append('Вернуться позже')
        print('len', len(variants_to_dialog))
        qv_markup = make_answer_buttons(variants_to_dialog)
        await message.answer(current_question['text'], reply_markup=qv_markup)
        print("Задан вопрос ", current_question['text'])
    except:
        await message.answer("Вы заполнили анкету целиком! Всё хорошо", reply_markup=ok_markup)
        if option_flag == 'main':
            results_str = await show_index(user_id)
            await message.answer(results_str, reply_markup=ok_markup)
        make_log_event(user_id, event_type='questions_finished', parameters=[])
        await state.finish()
        await Form.waiting_for_option.set()

@dp.message_handler(lambda message: message.text.lower() == 'вернуться позже', state=Form.waiting_for_answer)
async def back_to_main_menu_qv(message: types.Message, state: FSMContext):
    await show_main_menu(message, state)
 
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
