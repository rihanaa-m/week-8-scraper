-- Test to ensure messages have meaningful text content
{{ config(
    tags = ["data_quality"]
) }}

select *
from {{ ref('stg_telegram_messages') }}
where message_length = 0 and not has_media
