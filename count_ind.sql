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
                        FROM $$^[+-]?[0-9]+$$
                        ) as answer_num
    FROM tl.user_answers
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
country_stats as
(
    select 
        country_code,
        round(avg(rv), 2) as country_rv,
        round(avg(sv), 2) as country_sv,
        1 as j
    from country_raw
    group by 1
),
stat_dist as
(
    select 
        us.user_id,
        us.user_name,
        us.rv,
        us.sv,
        cs.country_code,
        cs.country_rv,
        cs.country_sv,
        abs(us.rv - cs.country_rv) as rv_diff,
        abs(us.sv - cs.country_sv) as sv_diff,
        abs(us.rv - cs.country_rv) + abs(us.sv - cs.country_sv) as diff_sum,
        row_number() over (
                            partition by us.user_id 
                            order by 
                                abs(us.rv - cs.country_rv) +
                                abs(us.sv - cs.country_sv)
                            ) as country_rank
    from user_stat us
    left outer join country_stats cs on
        (us.j = cs.j)
)

select user_id, user_name, rv, sv, country_code, country_rv, country_sv
from stat_dist
where country_rank = 1

limit 1