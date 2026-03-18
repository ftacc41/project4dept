-- Cleans and standardizes the raw orders table
with source as (
    select * from {{ source('raw', 'orders') }}
),

renamed as (
    select
        cast(order_id as string)                            as order_id,
        cast(customer_id as string)                         as customer_id,
        cast(order_amount as float64)                       as order_amount,
        lower(trim(status))                                 as status,
        lower(trim(product_category))                       as product_category,
        timestamp(order_date)                               as ordered_at,
        date(order_date)                                    as order_date
    from source
    where order_id is not null
      and customer_id is not null
      and order_amount > 0
)

select * from renamed
