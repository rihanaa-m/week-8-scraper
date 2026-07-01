-- Fact table for messages with foreign keys to dimensions

with messages as (
    select
        message_id,
        channel_name,
        message_date,
        message_text,
        message_length,
        has_media,
        image_path,
        views,
        forwards
    from {{ ref('stg_telegram_messages') }}
),

with_channel_key as (
    select
        m.*,
        c.channel_key
    from messages m
    left join {{ ref('dim_channels') }} c
        on m.channel_name = c.channel_name
),

with_date_key as (
    select
        m.*,
        d.date_key
    from with_channel_key m
    left join {{ ref('dim_dates') }} d
        on date(m.message_date) = d.full_date
)

select
    message_id,
    channel_key,
    date_key,
    message_text,
    message_length,
    views as view_count,
    forwards as forward_count,
    has_media as has_image_flag,
    image_path
from with_date_key
