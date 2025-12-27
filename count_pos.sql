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
    left outer join user_val sv on
        (rv.user_id = sv.user_id)
    where 
            rv.val_type = 'rv' 
        and sv.val_type = 'sv'
),
country_raw as
(
    select 
        "D_INTERVIEW", "B_COUNTRY_ALPHA" as country_code,
        "Q173" + "Q45" + "Q69" + "Q6" + "Q27" + "Q70" + "Q65" as rv,
        "Q17" + "Q8" + "Q11" + "Q30" + "Q29" + "Q33" + "Q152" as sv,
        1 as j
    from tl.gen_sample
),
country_ranks as
(
    select 
        *,
        percent_rank() over (order by rv) as rv_rank,
        percent_rank() over (order by sv) as sv_rank
    from country_raw
    where country_code = 'RUS'
)

select 
        distinct 
        us.*,
        cr.rv_rank,
        cr.sv_rank
from user_stat us
left outer join country_ranks cr on
    (us.rv = cr.rv) and (us.sv = cr.sv)


limit 1