-- запрос для того, чтобы получить wvs-баллы
-- которые можно сравнить с широкой выборкой
WITH 
base as 
(
    SELECT 
            *,
            -- номер - в первых 10 символах
            -- нам нужны числа 
            -- но они могут быть отрицательные
            substring(
                        ltrim(left(answer_text, 10)) 
                        FROM $$^[+-]?[0-results_str9]+$$
                        ) as answer_num
    FROM tl.user_answers
    where user_id = '{user_id}'
),
prep_val as
(
    select 
        *,
        CASE
            -- опция "не знаю" должна быть у каждого вопроса
            WHEN answer_text = 'Не знаю' 
            THEN -1
            -- пока у нас только один вопрос, который требует обобщений
            WHEN 
                (qv_id = 'Q17') and
                -- простой поиск по корню
                (answer_text not like '%ослуш%')
            THEN 2
            WHEN
                (qv_id = 'Q17') and
                (answer_text like '%ослуш%')
            THEN 1
            WHEN
                -- остальных берём число 
                (qv_id != 'Q17') and
                (answer_num IS NOT NULL)
            THEN answer_num::int
            ELSE -1
        END AS answer_value,
        -- главный конструктив - группировка вопросов по категориям
        case 
            when 
                qv_id in 
                (
                'Q17', 'Q8', 'Q11', 'Q30', 'Q29', 'Q33', 'Q152'
                )
                then 'rv'
            when 
                qv_id in 
                (
                'Q173', 'Q45', 'Q69', 'Q6', 'Q27', 'Q70', 'Q65'
                )
                then 'sv'
            else 'na'
        end as val_type
    from base
),
user_val as
(
    select user_id, user_name, val_type, sum(answer_value) as value
    from prep_val
    group by 1, 2, 3
),
user_stat as 
(
    select 
        rv.user_id,
        rv.user_name, 
        rv.value as rv,
        sv.value as sv,
        1 as j
    from user_val rv
    -- не самый изящный, но быстрый способо сделать pivot средствами sql
    left outer join user_val sv on
        (rv.user_id = sv.user_id)
    where 
            rv.val_type = 'rv' 
        and sv.val_type = 'sv'
),
user_meta_raw as
(
    select *
    from tl.user_reviews
    where user_id = '{user_id}'
),
user_meta as
(
    select 
            us.*,
            ag.answer_text::int as birth_date,
            -- разница в годах между датой рождения и текущей датой
            extract(year from current_date)::int - ag.answer_text::int as age,
            gen.answer_text as gender
    from user_stat us
    left outer join user_meta_raw ag on
        (us.user_id = ag.user_id)
    left outer join user_meta_raw gen on
        (us.user_id = gen.user_id)
    where ag.qv_id='S01'
    and gen.qv_id='S03'
),
gen_sample_raw as
(
    select 
        "D_INTERVIEW", "B_COUNTRY_ALPHA" as country_code,
        cs.name as country_name,
        "Q173" + "Q45" + "Q69" + "Q6" + "Q27" + "Q70" + "Q65" as rv,
        "Q17" + "Q8" + "Q11" + "Q30" + "Q29" + "Q33" + "Q152" as sv,
        "Q262" as age,
        case
            when "Q260" = 1 then 'Мужчина'
            when "Q260" = 2 then 'Женщина'
            else 'Предпочитаю не отвечать'
        end as gender
    from tl.gen_sample gs
    left outer join tl.country_data cs on
        (gs."B_COUNTRY_ALPHA" = cs.country_code)
),
sample_ranks as
(
    select 
        um.rv as rv,
        um.sv as sv,
        gs.rv as gen_rv,
        gs.sv as gen_sv,
        percent_rank() over (order by gs.rv) as rv_rank,
        percent_rank() over (order by gs.sv) as sv_rank,
        gs.*
    from user_meta um
    left outer join gen_sample_raw gs on
        (um.age = gs.age) and (um.gender = gs.gender)
    where gs.country_code = 'RUS'
)

select 
        distinct
        rv,
        sv,
        gen_rv,
        gen_sv,
        rv_rank,
        sv_rank
from sample_ranks
where rv = gen_rv and sv = gen_sv

limit 1



