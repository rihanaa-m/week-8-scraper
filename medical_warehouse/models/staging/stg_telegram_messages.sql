with source as (
    select * from {{ source('raw', 'telegram_messages') }}
),

renamed as (
    select
        message_id,
        channel_name,
        -- Parse and standardize date
        message_date,
        -- Clean text data
        coalesce(message_text, '') as message_text,
        -- Standardize boolean fields
        coalesce(has_media, false) as has_media,
        -- Clean image path
        image_path,
        -- Ensure numeric fields have defaults
        coalesce(views, 0) as views,
        coalesce(forwards, 0) as forwards,
        -- Add calculated fields
        length(coalesce(message_text, '')) as message_length,
        -- Add record metadata
        loaded_at
    from source
),

filtered as (
    select
        *
    from renamed
    where message_date is not null
)

select * from filtered
