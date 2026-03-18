-- Cleans and standardizes the raw churn labels table
with source as (
    select * from {{ source('raw', 'churn_labels') }}
),

renamed as (
    select
        cast(customer_id as string)                         as customer_id,
        cast(is_churned as bool)                            as is_churned,
        cast(churn_probability as float64)                  as churn_probability,
        date(last_activity_date)                            as last_activity_date,
        cast(days_since_last_order as int64)                as days_since_last_order
    from source
    where customer_id is not null
)

select * from renamed
