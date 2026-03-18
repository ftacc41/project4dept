-- Cleans and standardizes the raw customers table
with source as (
    select * from {{ source('raw', 'customers') }}
),

renamed as (
    select
        cast(customer_id as string)                         as customer_id,
        lower(trim(email))                                  as email,
        lower(trim(name))                                   as name,
        lower(trim(segment))                                as segment,
        lower(trim(region))                                 as region,
        cast(age as int64)                                  as age,
        cast(acquisition_cost as float64)                   as acquisition_cost,
        date(signup_date)                                   as signup_date
    from source
    where customer_id is not null
)

select * from renamed
