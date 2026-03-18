-- Customer lifetime value: total revenue, order counts, and avg order value per customer
with orders as (
    select * from {{ ref('stg_orders') }}
    where status = 'completed'
),

customers as (
    select * from {{ ref('stg_customers') }}
),

churn as (
    select * from {{ ref('stg_churn_labels') }}
),

order_stats as (
    select
        customer_id,
        count(order_id)                                     as total_orders,
        sum(order_amount)                                   as total_revenue,
        avg(order_amount)                                   as avg_order_value,
        min(order_date)                                     as first_order_date,
        max(order_date)                                     as last_order_date,
        date_diff(max(order_date), min(order_date), day)    as customer_lifespan_days
    from orders
    group by customer_id
)

select
    c.customer_id,
    c.name,
    c.email,
    c.segment,
    c.region,
    c.age,
    c.acquisition_cost,
    c.signup_date,
    coalesce(o.total_orders, 0)                             as total_orders,
    coalesce(o.total_revenue, 0.0)                          as total_revenue,
    coalesce(o.avg_order_value, 0.0)                        as avg_order_value,
    o.first_order_date,
    o.last_order_date,
    coalesce(o.customer_lifespan_days, 0)                   as customer_lifespan_days,
    -- Simple LTV = revenue - acquisition cost
    coalesce(o.total_revenue, 0.0) - c.acquisition_cost     as net_ltv,
    ch.churn_probability,
    ch.is_churned,
    current_timestamp()                                      as updated_at
from customers c
left join order_stats o using (customer_id)
left join churn ch using (customer_id)
