"""
Synthetic GA4-like event data generator for marketing analytics pipeline.

Generates realistic customer events (page views, clicks, purchases, etc.)
with timestamps, user IDs, and event properties for pipeline testing.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json


def generate_synthetic_data(
    num_customers: int = 1000,
    num_events: int = 50000,
    output_dir: str = "/tmp/airflow_data",
) -> dict:
    """
    Generate synthetic GA4-like events and customer data.
    
    Args:
        num_customers: Number of unique customers to generate
        num_events: Number of events to generate
        output_dir: Directory to save CSV files
        
    Returns:
        Dictionary with paths to generated files
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    print(f"Generating {num_customers} customers and {num_events} events...")
    
    # ===== CUSTOMERS =====
    customer_ids = np.arange(1, num_customers + 1)
    
    # Customer acquisition dates (last 2 years)
    acquisition_dates = [
        (datetime.now() - timedelta(days=np.random.randint(0, 730))).date()
        for _ in customer_ids
    ]
    
    # Regional distribution
    regions = np.random.choice(['US', 'EU', 'APAC', 'LATAM'], size=num_customers)
    
    # Customer segments (based on some logic)
    segments = np.random.choice(['Premium', 'Standard', 'Basic'], size=num_customers, p=[0.2, 0.5, 0.3])
    
    customers_df = pd.DataFrame({
        'customer_id': customer_ids,
        'acquisition_date': acquisition_dates,
        'region': regions,
        'segment': segments,
        'created_at': datetime.now(),
    })
    
    customers_csv = Path(output_dir) / "customers.csv"
    customers_df.to_csv(customers_csv, index=False)
    print(f"✓ Generated {len(customers_df)} customers → {customers_csv}")
    
    # ===== EVENTS =====
    event_types = ['page_view', 'click', 'add_to_cart', 'purchase', 'wishlist', 'review']
    event_weights = [0.4, 0.3, 0.15, 0.1, 0.03, 0.02]
    
    # Generate events over last 90 days
    base_date = datetime.now() - timedelta(days=90)
    
    events_data = []
    for _ in range(num_events):
        customer_id = np.random.choice(customer_ids)
        event_type = np.random.choice(event_types, p=event_weights)
        
        # Event timestamp
        event_date = base_date + timedelta(
            days=np.random.randint(0, 90),
            hours=np.random.randint(0, 24),
            minutes=np.random.randint(0, 60),
        )
        
        # Event properties
        event_value = 0
        if event_type == 'purchase':
            event_value = round(np.random.lognormal(5, 1), 2)
        elif event_type == 'add_to_cart':
            event_value = round(np.random.uniform(20, 500), 2)
        
        events_data.append({
            'event_id': f"evt_{_:08d}",
            'customer_id': customer_id,
            'event_type': event_type,
            'event_timestamp': event_date,
            'event_value': event_value,
            'page_url': f"https://example.com/page_{np.random.randint(1, 100)}",
            'device_type': np.random.choice(['mobile', 'desktop', 'tablet'], p=[0.5, 0.35, 0.15]),
            'country': np.random.choice(['US', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP', 'BR'], p=[0.3, 0.15, 0.1, 0.1, 0.08, 0.07, 0.1, 0.1]),
            'created_at': datetime.now(),
        })
    
    events_df = pd.DataFrame(events_data)
    events_csv = Path(output_dir) / "events.csv"
    events_df.to_csv(events_csv, index=False)
    print(f"✓ Generated {len(events_df)} events → {events_csv}")
    
    # ===== ORDERS =====
    # Create orders from purchase events
    purchase_events = events_df[events_df['event_type'] == 'purchase'].copy()
    
    order_ids = np.arange(1, len(purchase_events) + 1)
    orders_df = pd.DataFrame({
        'order_id': order_ids,
        'customer_id': purchase_events['customer_id'].values,
        'order_date': purchase_events['event_timestamp'].values,
        'order_amount': purchase_events['event_value'].values,
        'source': np.random.choice(['organic', 'paid_search', 'social', 'direct'], size=len(purchase_events)),
        'status': np.random.choice(['completed', 'pending', 'cancelled'], size=len(purchase_events), p=[0.85, 0.1, 0.05]),
        'created_at': datetime.now(),
    })
    
    orders_csv = Path(output_dir) / "orders.csv"
    orders_df.to_csv(orders_csv, index=False)
    print(f"✓ Generated {len(orders_df)} orders → {orders_csv}")
    
    # ===== CHURN LABELS (for ML training) =====
    # Label: customer has not purchased in last 30 days = churned
    cutoff_date = datetime.now() - timedelta(days=30)
    
    latest_purchase = events_df[events_df['event_type'] == 'purchase'].groupby('customer_id')['event_timestamp'].max()
    
    churn_labels = []
    for cust_id in customer_ids:
        if cust_id in latest_purchase.index:
            is_churned = latest_purchase[cust_id] < cutoff_date
        else:
            is_churned = True  # No purchase ever = churned
        
        churn_labels.append({
            'customer_id': cust_id,
            'is_churned': int(is_churned),
            'label_date': datetime.now().date(),
        })
    
    churn_df = pd.DataFrame(churn_labels)
    churn_csv = Path(output_dir) / "churn_labels.csv"
    churn_df.to_csv(churn_csv, index=False)
    print(f"✓ Generated {len(churn_df)} churn labels → {churn_csv}")
    
    print("\n✅ Data generation complete!")
    print(f"   Files saved to: {output_dir}")
    
    return {
        'customers_csv': str(customers_csv),
        'events_csv': str(events_csv),
        'orders_csv': str(orders_csv),
        'churn_csv': str(churn_csv),
    }


if __name__ == "__main__":
    generate_synthetic_data()
