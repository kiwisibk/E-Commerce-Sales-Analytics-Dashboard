"""
Data processing and feature engineering module for the E-Commerce Analytics Dashboard.

Provides robust functions to load, clean, aggregate, and merge Brazilian E-Commerce
datasets (Orders, Order Items, Customers) with Streamlit caching support.
"""

from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Tuple, List, Optional
import numpy as np
import pandas as pd
try:
    import streamlit as st
    cache_decorator = st.cache_data
except ImportError:
    # Graceful fallback decorator if streamlit is not yet installed in current Python env
    def cache_decorator(*args, **kwargs):
        def inner(func):
            return func
        return inner

# Configure module-level logging
logger = logging.getLogger(__name__)

# Expected file names as specified in the project requirements
ORDERS_FILENAME = "olist_orders_dataset.csv"
ITEMS_FILENAME = "olist_order_items_dataset.csv"
CUSTOMERS_FILENAME = "olist_customers_dataset.csv"

# Mapping of Brazilian 2-letter state abbreviations to full state names
BRAZILIAN_STATES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}


def get_data_dir() -> Path:
    """
    Dynamically resolve the project data directory relative to this source file.

    Returns:
        Path: Absolute pathlib.Path to the data/ folder.
    """
    project_root = Path(__file__).resolve().parent.parent
    return project_root / "data"


def check_data_files_exist(data_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Check if the three primary CSV files required for merging exist.

    Args:
        data_dir (Path, optional): Directory containing dataset files. Defaults to project 'data/'.

    Returns:
        Tuple[bool, List[str]]: (True if all exist, list of missing file names).
    """
    if data_dir is None:
        data_dir = get_data_dir()

    required_files = [ORDERS_FILENAME, ITEMS_FILENAME, CUSTOMERS_FILENAME]
    missing = [fname for fname in required_files if not (data_dir / fname).is_file()]

    return (len(missing) == 0, missing)


@cache_decorator(show_spinner=True)
def load_and_merge_data(data_dir_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load raw CSV datasets, perform data cleaning and feature engineering,
    and merge into a unified analytical DataFrame at the order level.

    Merged data combines:
    - Order status and purchase timestamps (olist_orders_dataset)
    - Revenue, freight, and item counts aggregated per order (olist_order_items_dataset)
    - Customer location (city, state, full state name) (olist_customers_dataset)

    Args:
        data_dir_path (str, optional): String representation of the data directory path.
                                      Using str allows clean Streamlit cache hashing.

    Returns:
        pd.DataFrame: Cleaned and merged analytical dataset.
    """
    data_dir = Path(data_dir_path) if data_dir_path else get_data_dir()

    # Verify existence of input files
    all_exist, missing = check_data_files_exist(data_dir)
    if not all_exist:
        raise FileNotFoundError(
            f"Missing required dataset file(s) in {data_dir}: {', '.join(missing)}. "
            "Please run 'python src/fetch_data.py' first."
        )

    # 1. Load Orders Dataset
    orders_path = data_dir / ORDERS_FILENAME
    df_orders = pd.read_csv(
        orders_path,
        usecols=[
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    )

    # Convert timestamps to datetime format
    df_orders["order_purchase_timestamp"] = pd.to_datetime(
        df_orders["order_purchase_timestamp"], errors="coerce"
    )
    df_orders["order_delivered_customer_date"] = pd.to_datetime(
        df_orders["order_delivered_customer_date"], errors="coerce"
    )
    df_orders["order_estimated_delivery_date"] = pd.to_datetime(
        df_orders["order_estimated_delivery_date"], errors="coerce"
    )

    # Drop orders where the purchase timestamp is invalid
    df_orders = df_orders.dropna(subset=["order_purchase_timestamp"])

    # 2. Load Order Items Dataset and aggregate per order
    items_path = data_dir / ITEMS_FILENAME
    df_items = pd.read_csv(
        items_path,
        usecols=["order_id", "order_item_id", "price", "freight_value"],
    )

    # Group by order_id to calculate total revenue, freight, and item count per order
    order_items_agg = (
        df_items.groupby("order_id")
        .agg(
            total_revenue=("price", "sum"),
            total_freight=("freight_value", "sum"),
            items_count=("order_item_id", "count"),
            avg_item_price=("price", "mean"),
        )
        .reset_index()
    )

    # Calculate total order value including freight
    order_items_agg["total_order_value"] = (
        order_items_agg["total_revenue"] + order_items_agg["total_freight"]
    )

    # 3. Load Customers Dataset
    customers_path = data_dir / CUSTOMERS_FILENAME
    df_customers = pd.read_csv(
        customers_path,
        usecols=["customer_id", "customer_city", "customer_state", "customer_zip_code_prefix"],
    )

    # Clean text columns: standardize state codes to uppercase and titles for cities
    df_customers["customer_state"] = df_customers["customer_state"].astype(str).str.strip().str.upper()
    df_customers["customer_city"] = df_customers["customer_city"].astype(str).str.strip().str.title()
    df_customers["state_name"] = df_customers["customer_state"].map(BRAZILIAN_STATES).fillna(df_customers["customer_state"])

    # 4. Merge datasets
    # Merge orders with aggregated item values
    merged = pd.merge(df_orders, order_items_agg, on="order_id", how="inner")

    # Merge with customer location information
    merged = pd.merge(merged, df_customers, on="customer_id", how="inner")

    # 5. Temporal Feature Engineering
    merged["order_year"] = merged["order_purchase_timestamp"].dt.year
    merged["order_month"] = merged["order_purchase_timestamp"].dt.month
    merged["order_month_name"] = merged["order_purchase_timestamp"].dt.strftime("%b")
    merged["order_year_month"] = merged["order_purchase_timestamp"].dt.to_period("M").astype(str)
    merged["order_date"] = merged["order_purchase_timestamp"].dt.floor("d")
    merged["day_of_week"] = merged["order_purchase_timestamp"].dt.day_name()
    merged["quarter"] = merged["order_purchase_timestamp"].dt.to_period("Q").astype(str)

    # Sort chronologically by default
    merged = merged.sort_values("order_purchase_timestamp", ascending=True).reset_index(drop=True)

    logger.info("Successfully merged and processed %d orders.", len(merged))
    return merged


def filter_data(
    df: pd.DataFrame,
    selected_years: Optional[List[int]] = None,
    selected_months: Optional[List[int]] = None,
    selected_states: Optional[List[str]] = None,
    selected_statuses: Optional[List[str]] = None,
    date_range: Optional[Tuple[datetime, datetime]] = None,
) -> pd.DataFrame:
    """
    Apply multi-dimensional filters to the analytical DataFrame.

    Args:
        df (pd.DataFrame): Analytical DataFrame.
        selected_years (List[int], optional): Selected years.
        selected_months (List[int], optional): Selected month numbers (1-12).
        selected_states (List[str], optional): Selected state codes.
        selected_statuses (List[str], optional): Selected order statuses.
        date_range (Tuple[datetime, datetime], optional): Start and end date range.

    Returns:
        pd.DataFrame: Filtered DataFrame.
    """
    filtered = df.copy()

    # Filter by date range if provided
    if date_range and len(date_range) == 2 and date_range[0] and date_range[1]:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        filtered = filtered[
            (filtered["order_purchase_timestamp"] >= start_date)
            & (filtered["order_purchase_timestamp"] <= end_date)
        ]

    # Filter by years
    if selected_years:
        filtered = filtered[filtered["order_year"].isin(selected_years)]

    # Filter by months
    if selected_months:
        filtered = filtered[filtered["order_month"].isin(selected_months)]

    # Filter by state codes
    if selected_states:
        filtered = filtered[filtered["customer_state"].isin(selected_states)]

    # Filter by order status
    if selected_statuses:
        filtered = filtered[filtered["order_status"].isin(selected_statuses)]

    return filtered


def generate_sample_dataset(data_dir: Optional[Path] = None, num_orders: int = 2500) -> None:
    """
    Generate realistic synthetic sample CSV files matching the Olist schema.
    This enables immediate out-of-the-box execution and testing even when
    Kaggle API credentials have not been configured yet.

    Args:
        data_dir (Path, optional): Destination directory. Defaults to project 'data/'.
        num_orders (int): Number of synthetic orders to generate.
    """
    if data_dir is None:
        data_dir = get_data_dir()

    data_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(42)

    # 1. Generate Customers
    states_pool = list(BRAZILIAN_STATES.keys())
    state_weights = [
        0.42 if s == "SP" else (0.13 if s == "RJ" else (0.11 if s == "MG" else 0.02))
        for s in states_pool
    ]
    # Normalize weights
    total_w = sum(state_weights)
    state_weights = [w / total_w for w in state_weights]

    cities_by_state = {
        "SP": ["São Paulo", "Campinas", "Santos", "Ribeirão Preto", "São Bernardo do Campo"],
        "RJ": ["Rio de Janeiro", "Niterói", "Petrópolis", "Nova Iguaçu", "Duque de Caxias"],
        "MG": ["Belo Horizonte", "Uberlândia", "Contagem", "Juiz de Fora", "Betim"],
        "RS": ["Porto Alegre", "Caxias do Sul", "Canoas", "Pelotas"],
        "PR": ["Curitiba", "Londrina", "Maringá", "Ponta Grossa"],
        "SC": ["Florianópolis", "Joinville", "Blumenau", "Chapecó"],
        "BA": ["Salvador", "Feira de Santana", "Vitória da Conquista"],
    }

    num_customers = int(num_orders * 0.85)
    customer_ids = [f"cust_{i:06d}" for i in range(1, num_customers + 1)]
    assigned_states = np.random.choice(states_pool, size=num_customers, p=state_weights)
    assigned_cities = [
        np.random.choice(cities_by_state.get(st_code, [f"{st_code} City"]))
        for st_code in assigned_states
    ]
    zip_codes = np.random.randint(10000, 99999, size=num_customers)

    df_customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "customer_unique_id": [f"uniq_{i:06d}" for i in range(1, num_customers + 1)],
            "customer_zip_code_prefix": zip_codes,
            "customer_city": assigned_cities,
            "customer_state": assigned_states,
        }
    )

    # 2. Generate Orders
    order_ids = [f"ord_{i:06d}" for i in range(1, num_orders + 1)]
    order_customers = np.random.choice(customer_ids, size=num_orders)

    # Generate dates across 2017 and 2018 (matching the peak Olist timeframe)
    start_date = datetime(2017, 1, 1)
    end_date = datetime(2018, 8, 31)
    total_seconds = int((end_date - start_date).total_seconds())

    random_seconds = np.random.randint(0, total_seconds, size=num_orders)
    purchase_dates = [start_date + timedelta(seconds=int(s)) for s in random_seconds]

    statuses = ["delivered", "shipped", "canceled", "invoiced"]
    status_weights = [0.96, 0.02, 0.01, 0.01]
    order_statuses = np.random.choice(statuses, size=num_orders, p=status_weights)

    df_orders = pd.DataFrame(
        {
            "order_id": order_ids,
            "customer_id": order_customers,
            "order_status": order_statuses,
            "order_purchase_timestamp": [d.strftime("%Y-%m-%d %H:%M:%S") for d in purchase_dates],
            "order_approved_at": [(d + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S") for d in purchase_dates],
            "order_delivered_carrier_date": [(d + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S") for d in purchase_dates],
            "order_delivered_customer_date": [(d + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S") for d in purchase_dates],
            "order_estimated_delivery_date": [(d + timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S") for d in purchase_dates],
        }
    )

    # 3. Generate Order Items
    items_records = []
    product_ids = [f"prod_{i:04d}" for i in range(1, 150)]
    seller_ids = [f"sell_{i:04d}" for i in range(1, 50)]

    for o_id in order_ids:
        # Number of items per order (most have 1 item, some have 2-4 items)
        n_items = np.random.choice([1, 2, 3, 4], p=[0.82, 0.12, 0.04, 0.02])
        for item_idx in range(1, n_items + 1):
            price = round(float(np.random.exponential(scale=90.0) + 12.0), 2)
            freight = round(float(np.random.uniform(10.0, 35.0)), 2)
            items_records.append(
                {
                    "order_id": o_id,
                    "order_item_id": item_idx,
                    "product_id": np.random.choice(product_ids),
                    "seller_id": np.random.choice(seller_ids),
                    "shipping_limit_date": datetime(2018, 1, 1).strftime("%Y-%m-%d %H:%M:%S"),
                    "price": price,
                    "freight_value": freight,
                }
            )

    df_items = pd.DataFrame(items_records)

    # Save CSV files to target directory
    df_customers.to_csv(data_dir / CUSTOMERS_FILENAME, index=False)
    df_orders.to_csv(data_dir / ORDERS_FILENAME, index=False)
    df_items.to_csv(data_dir / ITEMS_FILENAME, index=False)

    logger.info("Sample CSV files generated successfully at: %s", data_dir)
