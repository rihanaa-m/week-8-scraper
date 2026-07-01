-- Generate a comprehensive date dimension table
-- This will be populated with dates from the data range in the messages

with date_range as (
    select 
        min(message_date) as min_date,
        max(message_date) as max_date
    from {{ ref('stg_telegram_messages') }}
),

generate_series as (
    select 
        generate_series(
            (select min_date from date_range),
            (select max_date from date_range),
            interval '1 day'
        )::date as full_date
),

date_attributes as (
    select
        full_date,
        -- Surrogate key in YYYYMMDD format
        to_char(full_date, 'YYYYMMDD')::int as date_key,
        -- Day attributes
        extract(isodow from full_date) as day_of_week,
        to_char(full_date, 'Day') as day_name,
        -- Week attributes
        extract(week from full_date) as week_of_year,
        -- Month attributes
        extract(month from full_date) as month,
        to_char(full_date, 'Month') as month_name,
        -- Quarter attributes
        extract(quarter from full_date) as quarter,
        -- Year attributes
        extract(year from full_date) as year,
        -- Weekend flag
        extract(isodow from full_date) in (6, 7) as is_weekend
    from generate_series
)

select * from date_attributes
