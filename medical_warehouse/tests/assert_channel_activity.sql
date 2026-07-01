-- Test to ensure channels have recent activity (within last 90 days)
{{ config(
    tags = ["data_quality"]
) }}

select *
from {{ ref('dim_channels') }}
where last_post_date < current_date - interval '90 days'
