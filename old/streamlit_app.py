# coding: utf-8
"""
Streamlit equivalent of telegram_back_wvs.py — WVS values questionnaire app.
"""
import json
import os

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
import streamlit.components.v1 as components

# Load data_load and config from wvs_bot directory
_current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(_current_dir)

import data_load as dl

# Load questions and dialogs
with open(os.path.join(_current_dir, "questions.json"), "r", encoding="utf-8") as f:
    qv_data = json.load(f)

st.set_page_config(page_title="Ценности WVS", layout="wide")

CONFIG_FILE = "config_wvs.yaml"


def make_log_event(user_id, event_type="", parameters=None):
    """Log event to tl.wvs_events. parameters: dict or list, will be stored as JSON string."""
    if parameters is None:
        parameters = {}
    try:
        params_str = json.dumps(parameters, ensure_ascii=False) if parameters else "{}"
        logging_df = pd.DataFrame(
            [[str(user_id), event_type, params_str]],
            columns=["user_id", "event_type", "parameters"],
        )
        dl.insert_data(logging_df, "tl", "wvs_events", CONFIG_FILE, section="logging")
    except Exception as e:
        st.warning(f"Логирование не удалось: {e}")


def _autofocus_script():
    """Inject JS to focus the first text input in main content (not sidebar)."""
    components.html(
        """
        <script>
        (function() {
            const timer = setInterval(function() {
                const main = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
                if (main) {
                    const inputs = main.querySelectorAll('input[type="text"]');
                    for (let i = 0; i < inputs.length; i++) {
                        const inp = inputs[i];
                        if (inp && !inp.closest('[data-testid="stSidebar"]')) {
                            inp.focus();
                            clearInterval(timer);
                            return;
                        }
                    }
                }
            }, 100);
            setTimeout(() => clearInterval(timer), 3000);
        })();
        </script>
        """,
        height=0,
    )


def get_next_question(user_id: str, table_name: str = "tl.user_answers") -> int:
    """Get index of next question to answer (0-based)."""
    try:
        query = f"""
            SELECT COALESCE(MAX(qv_number), 0)::int AS num
            FROM {table_name}
            WHERE user_id = '{user_id}'
        """
        df = dl.get_data(query, CONFIG_FILE, section="logging")
        if df is None or df.empty:
            return 0
        return int(df["num"].values[0])
    except Exception:
        return 0


def show_index(user_id: str) -> str:
    """Get user's rv/sv index string."""
    with open(os.path.join(_current_dir, "count_ind.sql"), "r") as f:
        query = f.read()
    # count_ind has "where user_id != '212619715'" - replace with user filter
    query = query.replace("where user_id != '212619715'", f"where user_id = '{user_id}'")
    results_df = dl.get_data(query, CONFIG_FILE, section="logging")
    if results_df is None or results_df.empty:
        return "Нет данных. Заполните основную анкету."
    rv = results_df["rv"].values[0]
    sv = results_df["sv"].values[0]
    return qv_data["dialogs"]["index_str"].format(rv=rv, sv=sv)


def show_nearest_country(user_id: str):
    """Get nearest country by values."""
    with open(os.path.join(_current_dir, "find_country.sql"), "r") as f:
        query = f.read().format(user_id=user_id)
    results_df = dl.get_data(query, CONFIG_FILE, section="logging")
    if results_df is None or results_df.empty:
        return None, None, None
    rv = results_df["rv"].values[0]
    sv = results_df["sv"].values[0]
    country_code = results_df["country_code"].values[0]
    country_rv = results_df["country_rv"].values[0]
    country_sv = results_df["country_sv"].values[0]
    res_str = qv_data["dialogs"]["nearest_country_str"].format(
        rv=rv, sv=sv, country_code=country_code,
        country_rv=country_rv, country_sv=country_sv
    )
    return res_str, sv, rv


def show_position(user_id: str, query_file: str, res_str: str) -> str:
    """Get user position string from SQL query."""
    with open(os.path.join(_current_dir, query_file), "r") as f:
        query = f.read().format(user_id=user_id)
    results_df = dl.get_data(query, CONFIG_FILE, section="logging")
    if results_df is None or results_df.empty:
        return None
    rv = results_df["rv"].values[0]
    sv = results_df["sv"].values[0]
    rv_rank = int(np.round(results_df["rv_rank"].values[0], 2) * 100)
    sv_rank = int(np.round(results_df["sv_rank"].values[0], 2) * 100)
    return res_str.format(rv=rv, sv=sv, rv_rank=rv_rank, sv_rank=sv_rank)


def plot_clusters_streamlit(
    df, annotate_list, user_point=None, user_label="Вы",
    annotate_on="country_code", x="country_sv", y="country_rv",
    hue_candidates=("label", "cluster", "labels", "group"),
):
    """Generate country cluster plot for Streamlit (returns fig)."""
    hue_col = None
    for c in hue_candidates:
        if c in df.columns:
            hue_col = c
            break
    if hue_col is None:
        hue_col = "cluster" if "cluster" in df.columns else df.columns[0]

    df = df.copy()
    df[hue_col] = df[hue_col].astype("category")
    n_colors = len(df[hue_col].cat.categories)
    palette = sns.color_palette("tab10" if n_colors <= 10 else "husl", n_colors=n_colors)

    rows_to_annotate = (
        df[df[annotate_on].isin(annotate_list)]
        if annotate_on in df.columns and annotate_list
        else df.head(0)
    )

    fig, ax = plt.subplots(figsize=(12, 8))
    sns.scatterplot(data=df, x=x, y=y, hue=hue_col, palette=palette, s=80, edgecolor="k", alpha=0.9, ax=ax)

    bbox_dict = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.35)
    if not rows_to_annotate.empty:
        for _, r in rows_to_annotate.iterrows():
            tx = r[annotate_on] if annotate_on != "index" else r.name
            ax.text(r[x], r[y] + 0.02, str(tx), fontsize=9, fontweight="bold", ha="left", va="bottom", bbox=bbox_dict)

    if user_point is not None:
        ux, uy = float(user_point[0]), float(user_point[1])
        ax.axvline(ux, color="red", linestyle="--", linewidth=1.5, zorder=200, label=user_label)
        ax.axhline(uy, color="red", linestyle="--", linewidth=1.5, zorder=200)

    ax.set_title("Положение относительно других стран", fontsize=14)
    ax.set_xlabel("Традиционные/Секулярно-рациональные ценности")
    ax.set_ylabel("Ценности выживания/Самовыражения")
    if user_point is not None:
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    return fig


def show_country_plot(user_sv, user_rv):
    """Load country data and create plot."""
    df = dl.get_data(
        """
        SELECT country_code, country_rv, country_sv, cluster
        FROM tl.country_data
        WHERE country_code != 'EGY'
        """,
        CONFIG_FILE,
        section="logging",
    )
    if df is None or df.empty:
        return None
    df["country_rv"] = df["country_rv"].fillna(user_rv).astype(float)
    df["country_sv"] = df["country_sv"].fillna(user_sv).astype(float)

    return plot_clusters_streamlit(
        df,
        ["RUS", "USA", "UZB", "GTM", "AND", "PAK", "IRN", "ARM", "KOR", "DEU", "JPN", "MDV", "ARG", "CAN"],
        annotate_on="country_code",
        user_point=(user_sv, user_rv),
        user_label="Вы",
        x="country_sv",
        y="country_rv",
    )


# --- Session state init ---
if "user_id" not in st.session_state:
    st.session_state.user_id = "streamlit_user"
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "reviews" not in st.session_state:
    st.session_state.reviews = {}


# --- Sidebar: user ID ---
with st.sidebar:
    st.header("Настройки")
    user_id = st.text_input("User ID (для БД)", value=st.session_state.user_id, key="user_id_input")
    st.session_state.user_id = user_id


# --- Main UI ---
st.title("Ценности WVS")
st.write(qv_data["dialogs"]["hello_message"])
st.write(qv_data["dialogs"]["choice_message"])

option = st.radio(
    "Выберите действие",
    [
        qv_data["dialogs"]["option1_message"],
        qv_data["dialogs"]["option2_message"],
        qv_data["dialogs"]["option3_message"],
        qv_data["dialogs"]["option4_message"],
    ],
    label_visibility="collapsed",
)

st.divider()

if option == qv_data["dialogs"]["option1_message"]:
    if st.session_state.get("return_later"):
        st.session_state.return_later = False
        st.info("Вы вернулись в главное меню. Выберите действие выше.")
    else:
        st.subheader("Основная анкета")
        if f"log_main_{user_id}" not in st.session_state:
            make_log_event(user_id, event_type="main_questionary", parameters={})
            st.session_state[f"log_main_{user_id}"] = True
        num_ready = get_next_question(user_id, "tl.user_answers")
        num_rest = len(qv_data["main_questions"]) - num_ready
        time_est = int(np.floor(num_rest * 0.35))

        if num_rest > 0:
            st.info(f"Осталось {num_rest} вопросов, ~{time_est} мин.")
            q = qv_data["main_questions"][num_ready]
            st.write(f"**Вопрос {int(q['num'])}:** {q['text']}")

            CUSTOM_OPTION = "✏️ Ввести свой ответ"
            options = q["variants"] + [CUSTOM_OPTION] + ["Вернуться позже"]

            selected = st.radio("Выберите ответ", options, key=f"main_q_{num_ready}", label_visibility="collapsed")

            custom_answer = ""
            if selected == CUSTOM_OPTION:
                custom_answer = st.text_input(
                    "Введите свой ответ",
                    key=f"main_custom_{num_ready}",
                    placeholder="Введите ответ...",
                    label_visibility="collapsed",
                )
                _autofocus_script()

            col1, col2 = st.columns([1, 4])
            with col1:
                submit = st.button("Ответить", key=f"main_btn_{num_ready}")
            with col2:
                if st.button("Вернуться позже", key=f"main_back_{num_ready}"):
                    st.session_state.return_later = True
                    st.rerun()

            if submit:
                if selected == "Вернуться позже":
                    st.session_state.return_later = True
                    st.rerun()
                elif selected == CUSTOM_OPTION:
                    if custom_answer and custom_answer.strip():
                        answer = custom_answer.strip()
                    else:
                        st.warning("Введите свой ответ")
                        answer = None
                else:
                    answer = selected

                if answer:
                    df_to_sql = pd.DataFrame([[
                        user_id, user_id, q["id"], int(q["num"]), q["text"], answer
                    ]], columns=["user_id", "user_name", "qv_id", "qv_number", "qv_text", "answer_text"])
                    try:
                        dl.insert_data(df_to_sql, "tl", "user_answers", CONFIG_FILE, section="logging")
                        make_log_event(user_id, event_type="record_answer", parameters={"qv_number": int(q["num"])})
                        st.success("Ответ сохранён!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка сохранения: {e}")
        else:
            make_log_event(user_id, event_type="questions_finished", parameters={})
            st.success("Вы заполнили основную анкету!")
            try:
                st.markdown(show_index(user_id))
            except Exception as e:
                st.error(f"Ошибка: {e}")

elif option == qv_data["dialogs"]["option2_message"]:
    if st.session_state.get("return_later"):
        st.session_state.return_later = False
        st.info("Вы вернулись в главное меню. Выберите действие выше.")
    else:
        st.subheader("Дополнительная анкета")
        if f"log_sec_{user_id}" not in st.session_state:
            make_log_event(user_id, event_type="secondary_questionary", parameters={})
            st.session_state[f"log_sec_{user_id}"] = True
        num_ready = get_next_question(user_id, "tl.user_reviews")
        num_rest = len(qv_data["secondary_questions"]) - num_ready
        time_est = int(np.floor(num_rest * 0.35))

        if num_rest > 0:
            st.info(f"Осталось {num_rest} вопросов, ~{time_est} мин.")
            q = qv_data["secondary_questions"][num_ready]
            st.write(f"**Вопрос {int(q['num'])}:** {q['text']}")

            CUSTOM_OPTION = "✏️ Ввести свой ответ"
            options = q["variants"] + [CUSTOM_OPTION] + ["Вернуться позже"]

            selected = st.radio("Выберите ответ", options, key=f"sec_q_{num_ready}", label_visibility="collapsed")

            custom_answer = ""
            if selected == CUSTOM_OPTION:
                custom_answer = st.text_input(
                    "Введите свой ответ",
                    key=f"sec_custom_{num_ready}",
                    placeholder="Введите ответ...",
                    label_visibility="collapsed",
                )
                _autofocus_script()

            col1, col2 = st.columns([1, 4])
            with col1:
                submit = st.button("Ответить", key=f"sec_btn_{num_ready}")
            with col2:
                if st.button("Вернуться позже", key=f"sec_back_{num_ready}"):
                    st.session_state.return_later = True
                    st.rerun()

            if submit:
                if selected == "Вернуться позже":
                    st.session_state.return_later = True
                    st.rerun()
                elif selected == CUSTOM_OPTION:
                    if custom_answer and custom_answer.strip():
                        answer = custom_answer.strip()
                    else:
                        st.warning("Введите свой ответ")
                        answer = None
                else:
                    answer = selected

                if answer:
                    df_to_sql = pd.DataFrame([[
                        user_id, user_id, q["id"], int(q["num"]), q["text"], answer
                    ]], columns=["user_id", "user_name", "qv_id", "qv_number", "qv_text", "answer_text"])
                    try:
                        dl.insert_data(df_to_sql, "tl", "user_reviews", CONFIG_FILE, section="logging")
                        make_log_event(user_id, event_type="record_answer", parameters={"qv_number": int(q["num"])})
                        st.success("Ответ сохранён!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка сохранения: {e}")
        else:
            make_log_event(user_id, event_type="secondary_questions_finished", parameters={})
            st.success("Вы заполнили дополнительную анкету!")

elif option == qv_data["dialogs"]["option3_message"]:
    st.subheader("Найти страну, близкую по ценностям")
    try:
        result = show_nearest_country(user_id)
        if result[0] is not None:
            res_str, sv, rv = result
            make_log_event(user_id, event_type="find_country", parameters={"answer": res_str[:100]})
            st.markdown(res_str)
            fig = show_country_plot(sv, rv)
            if fig is not None:
                st.pyplot(fig)
        else:
            make_log_event(user_id, event_type="find_country", parameters={"answer": "No data"})
            st.warning("Для начала нужно заполнить основную анкету")
    except Exception as e:
        make_log_event(user_id, event_type="find_country", parameters={"answer": str(e)})
        st.error(f"Для начала нужно заполнить основную анкету. Ошибка: {e}")

elif option == qv_data["dialogs"]["option4_message"]:
    st.subheader("Понять своё место в социуме")
    try:
        pos_str = show_position(user_id, "count_pos.sql", qv_data["dialogs"]["global_position_str"])
        if pos_str:
            make_log_event(user_id, event_type="find_position", parameters={"answer": pos_str[:100]})
            st.markdown(pos_str)
            try:
                age_str = show_position(user_id, "age_strat.sql", qv_data["dialogs"]["age_position_str"])
                if age_str:
                    st.markdown(age_str)
                gender_str = show_position(user_id, "gender_age_strat.sql", qv_data["dialogs"]["gender_age_position_str"])
                if gender_str:
                    st.markdown(gender_str)
            except Exception:
                make_log_event(user_id, event_type="find_position", parameters={"answer": "No secondary data"})
                st.info("Если вы заполните дополнительную анкету, мы сможем точнее определить ваше место")
        else:
            make_log_event(user_id, event_type="find_position", parameters={"answer": "No data"})
            st.warning("Для начала нужно заполнить основную анкету")
    except Exception as e:
        make_log_event(user_id, event_type="find_position", parameters={"answer": str(e)})
        st.error(f"Для начала нужно заполнить основную анкету. Ошибка: {e}")
