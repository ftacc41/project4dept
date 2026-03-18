-- Campaign performance: impressions, clicks, conversions, and revenue attributed per campaign
with events as (
    select * from {{ ref('stg_events') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
    where status = 'completed'
),

-- Attribute orders to the last campaign the customer clicked before ordering
last_click as (
    select
        e.customer_id,
        e.campaign_id,
        e.event_at,
        row_number() over (
            partition by e.customer_id
            order by e.event_at desc
        ) as rn
    from events e
    where e.clicked_ad = true
      and e.campaign_id is not null
),

attributed_orders as (
    select
        o.order_id,
        o.customer_id,
        o.order_amount,
        o.order_date,
        lc.campaign_id
    from orders o
    left join last_click lc
        on o.customer_id = lc.customer_id
        and lc.rn = 1
),

event_stats as (
    select
        campaign_id,
        channel,
        count(event_id)                                     as total_impressions,
        countif(clicked_ad)                                 as total_clicks,
        round(countif(clicked_ad) / count(event_id) * 100, 2) as ctr_pct,
        count(distinct customer_id)                         as unique_users_reached
    from events
    where campaign_id is not null
    group by campaign_id, channel
),

revenue_stats as (
    select
        campaign_id,
        count(order_id)                                     as attributed_orders,
        round(sum(order_amount), 2)                         as attributed_revenue,
        round(avg(order_amount), 2)                         as avg_order_value
    from attributed_orders
    where campaign_id is not null
    group by campaign_id
)

select
    es.campaign_id,
    es.channel,
    es.total_impressions,
    es.total_clicks,
    es.ctr_pct,
    es.unique_users_reached,
    coalesce(rs.attributed_orders, 0)                       as attributed_orders,
    coalesce(rs.attributed_revenue, 0.0)                    as attributed_revenue,
    coalesce(rs.avg_order_value, 0.0)                       as avg_order_value,
    -- Conversion rate = orders / clicks
    round(
        safe_divide(coalesce(rs.attributed_orders, 0), es.total_clicks) * 100,
    2)                                                      as conversion_rate_pct,
    current_timestamp()                                     as updated_at
from event_stats es
left join revenue_stats rs using (campaign_id)
order by attributed_revenue desc
