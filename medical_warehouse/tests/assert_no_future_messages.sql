-- Test to ensure no messages have future dates
{{ config(
    tags = ["data_quality"]
) }}

select *
from {{ ref('stg_telegram_messages') }}
where message_date > current_timestamp
