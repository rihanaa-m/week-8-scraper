-- Channel dimension table with aggregated statistics

with channel_stats as (
    select
        channel_name,
        -- First and last post dates
        min(message_date) as first_post_date,
        max(message_date) as last_post_date,
        -- Total posts
        count(*) as total_posts,
        -- Average views
        avg(views) as avg_views,
        -- Total views
        sum(views) as total_views,
        -- Total forwards
        sum(forwards) as total_forwards,
        -- Messages with media
        sum(case when has_media then 1 else 0 end) as messages_with_media
    from {{ ref('stg_telegram_messages') }}
    group by channel_name
),

with_surrogate_key as (
    select
        -- Generate surrogate key using hash
        row_number() over (order by channel_name) as channel_key,
        channel_name,
        first_post_date,
        last_post_date,
        total_posts,
        avg_views,
        total_views,
        total_forwards,
        messages_with_media,
        -- Calculate media percentage
        case 
            when total_posts > 0 
            then (messages_with_media::float / total_posts::float) * 100 
            else 0 
        end as media_percentage
    from channel_stats
)

select * from with_surrogate_key
