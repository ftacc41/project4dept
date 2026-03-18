"""
Synthetic marketing data generator for the analytics pipeline.

Generates customers, events, orders, and churn labels with realistic fields
that feed into the BigQuery raw layer → dbt staging → dbt marts.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import uuid


def generate_synthetic_data(
    num_customers: int = 1000,
    num_events: int = 50000,
    output_dir: str = "/tmp/airflow_data",
) -> dict:
    """
    Generate synthetic marketing data and write CSVs to output_dir.
    Returns a dict with paths to each generated file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    np.random.seed(42)

    print(f"Generating {num_customers} customers and {num_events} events...")

    # ===== CUSTOMERS =====
    customer_ids = np.arange(1, num_customers + 1)
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Avery"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]

    customers_df = pd.DataFrame({
        "customer_id": customer_ids,
        "name": [
            f"{np.random.choice(first_names)} {np.random.choice(last_names)}"
            for _ in customer_ids
        ],
        "email": [f"customer_{i}@example.com" for i in customer_ids],
        "age": np.random.randint(18, 70, size=num_customers),
        "segment": np.random.choice(
            ["enterprise", "smb", "consumer", "startup"],
            size=num_customers,
            p=[0.15, 0.35, 0.35, 0.15],
        ),
        "region": np.random.choice(["US", "EU", "APAC", "LATAM"], size=num_customers),
        "acquisition_cost": np.round(np.random.uniform(10, 500, size=num_customers), 2),
        "signup_date": [
            (datetime.now() - timedelta(days=int(np.random.randint(0, 730)))).date()
            for _ in customer_ids
        ],
    })

    customers_csv = Path(output_dir) / "customers.csv"
    customers_df.to_csv(customers_csv, index=False)
    print(f"  ✓ {len(customers_df)} customers → {customers_csv}")

    # ===== EVENTS =====
    channels = ["organic", "paid_search", "social", "email", "referral"]
    event_types = ["page_view", "click", "add_to_cart", "purchase", "wishlist", "review"]
    event_weights = [0.4, 0.3, 0.15, 0.1, 0.03, 0.02]
    campaign_ids = [f"camp_{i:04d}" for i in range(1, 51)]  # 50 campaigns
    base_date = datetime.now() - timedelta(days=90)

    events_data = []
    for i in range(num_events):
        event_type = np.random.choice(event_types, p=event_weights)
        clicked = event_type in ["click", "purchase"]
        events_data.append({
            "event_id": f"evt_{i:08d}",
            "customer_id": int(np.random.choice(customer_ids)),
            "event_type": event_type,
            "event_timestamp": base_date + timedelta(
                days=int(np.random.randint(0, 90)),
                hours=int(np.random.randint(0, 24)),
                minutes=int(np.random.randint(0, 60)),
            ),
            "channel": np.random.choice(channels),
            "session_duration_seconds": int(np.random.randint(5, 1800)),
            "pages_viewed": int(np.random.randint(1, 20)),
            "clicked_ad": clicked,
            "campaign_id": np.random.choice(campaign_ids) if clicked else None,
        })

    events_df = pd.DataFrame(events_data)
    events_csv = Path(output_dir) / "events.csv"
    events_df.to_csv(events_csv, index=False)
    print(f"  ✓ {len(events_df)} events → {events_csv}")

    # ===== ORDERS =====
    purchase_events = events_df[events_df["event_type"] == "purchase"].copy()
    categories = ["electronics", "clothing", "home", "beauty", "sports", "food"]

    orders_df = pd.DataFrame({
        "order_id": np.arange(1, len(purchase_events) + 1),
        "customer_id": purchase_events["customer_id"].values,
        "order_date": purchase_events["event_timestamp"].values,
        "order_amount": np.round(np.random.lognormal(5, 1, size=len(purchase_events)), 2),
        "product_category": np.random.choice(categories, size=len(purchase_events)),
        "status": np.random.choice(
            ["completed", "pending", "cancelled", "refunded"],
            size=len(purchase_events),
            p=[0.80, 0.10, 0.06, 0.04],
        ),
    })

    orders_csv = Path(output_dir) / "orders.csv"
    orders_df.to_csv(orders_csv, index=False)
    print(f"  ✓ {len(orders_df)} orders → {orders_csv}")

    # ===== CHURN LABELS =====
    cutoff_date = datetime.now() - timedelta(days=30)
    latest_purchase = (
        events_df[events_df["event_type"] == "purchase"]
        .groupby("customer_id")["event_timestamp"]
        .max()
    )

    churn_labels = []
    for cust_id in customer_ids:
        if cust_id in latest_purchase.index:
            last_activity = latest_purchase[cust_id]
            is_churned = last_activity < cutoff_date
            days_since = (datetime.now() - last_activity).days
        else:
            last_activity = datetime.now() - timedelta(days=int(np.random.randint(60, 365)))
            is_churned = True
            days_since = (datetime.now() - last_activity).days

        churn_labels.append({
            "customer_id": cust_id,
            "is_churned": bool(is_churned),
            "churn_probability": round(float(np.random.beta(2, 5) if not is_churned else np.random.beta(5, 2)), 4),
            "last_activity_date": last_activity.date(),
            "days_since_last_order": days_since,
        })

    churn_df = pd.DataFrame(churn_labels)
    churn_csv = Path(output_dir) / "churn_labels.csv"
    churn_df.to_csv(churn_csv, index=False)
    print(f"  ✓ {len(churn_df)} churn labels → {churn_csv}")

    print("\n✅ Data generation complete!")
    return {
        "customers_csv": str(customers_csv),
        "events_csv": str(events_csv),
        "orders_csv": str(orders_csv),
        "churn_csv": str(churn_csv),
    }


if __name__ == "__main__":
    generate_synthetic_data()
