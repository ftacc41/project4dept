-- Cleans and standardizes the raw events table
with source as (
    select * from {{ source('raw', 'events') }}
),

renamed as (
    select
        cast(event_id as string)                            as event_id,
        cast(customer_id as string)                         as customer_id,
        lower(trim(event_type))                             as event_type,
        lower(trim(channel))                                as channel,
        timestamp(event_timestamp)                          as event_at,
        date(event_timestamp)                               as event_date,
        cast(session_duration_seconds as int64)             as session_duration_seconds,
        cast(pages_viewed as int64)                         as pages_viewed,
        cast(clicked_ad as bool)                            as clicked_ad,
        lower(trim(campaign_id))                            as campaign_id
    from source
    where event_id is not null
      and customer_id is not null
)

select * from renamed
