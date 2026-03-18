-- Churn summary by segment and region, with revenue at risk
with ltv as (
    select * from {{ ref('mart_customer_ltv') }}
)

select
    segment,
    region,
    count(customer_id)                                          as total_customers,
    countif(is_churned)                                         as churned_customers,
    count(customer_id) - countif(is_churned)                    as active_customers,
    round(countif(is_churned) / count(customer_id) * 100, 2)   as churn_rate_pct,
    round(avg(churn_probability), 4)                            as avg_churn_probability,
    -- High-risk = churn_probability > 0.7
    countif(churn_probability > 0.7 and not is_churned)         as high_risk_customers,
    round(sum(case when not is_churned then total_revenue else 0 end), 2)   as active_revenue,
    -- Revenue at risk = revenue from high-risk customers
    round(sum(case when churn_probability > 0.7 and not is_churned then total_revenue else 0 end), 2) as revenue_at_risk,
    current_timestamp()                                         as updated_at
from ltv
group by segment, region
order by churn_rate_pct desc
