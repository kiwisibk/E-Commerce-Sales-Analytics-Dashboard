# E-Commerce Sales & Customer Insights Dashboard

An enterprise-grade modular data analysis pipeline and interactive [Streamlit](https://streamlit.io/) dashboard designed to analyze Brazilian e-commerce performance, customer distributions, and fulfillment trends based on the [Olist Brazilian E-Commerce public dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

---

## 🌟 Key Features

- **Automated Kaggle Ingestion (`src/fetch_data.py`)**:
  - Secure and dynamic cross-platform path resolution using Python's `pathlib`.
  - Automatic download and archive extraction of `olistbr/brazilian-ecommerce` via the Kaggle API.
  - File existence verification preventing redundant downloads.
  - Offline demo sample generator (`--generate-sample`) for instant evaluation without API credentials.
- **High-Performance Data Engineering (`src/data_processing.py`)**:
  - Joins order header attributes (`olist_orders_dataset.csv`), item financials (`olist_order_items_dataset.csv`), and customer geolocation (`olist_customers_dataset.csv`).
  - Order-level aggregation of revenue, shipping freight, and unit item counts.
  - Temporal feature extraction (year, month, quarter, day of week) and Brazilian state normalization.
  - Optimized data loading with Streamlit caching (`@st.cache_data`).
- **Interactive Executive Dashboard (`app.py`)**:
  - **Dynamic Sidebar Controls**: Filter by year, purchase month, custom calendar date range, order status, and Brazilian states (UF).
  - **Tab 1: Sales Performance & Time Series**:
    - Executive KPI Cards: Total Revenue (*Gesamtumsatz*), Order Count (*Anzahl Bestellungen*), Average Order Value (AOV), Total Items Sold, and Units per Order.
    - Interactive dual-axis Plotly time series chart showing sales revenue and order volume trends with toggleable granularity (Monthly, Weekly, Daily).
  - **Tab 2: Geographic Insights**:
    - Ranked Plotly horizontal bar chart of top Brazilian states with revenue, percentage market share, and average basket sizes.
    - Ranked breakdown of top municipal cities by revenue.
  - **Tab 3: Raw Dataset Explorer**:
    - Embedded inside a collapsible `st.expander` container as required.
    - Interactive `st.dataframe()` with search capabilities across Order IDs, Customer IDs, and Cities.
    - One-click CSV export of filtered analytical records.

---

## 🏗️ Project Architecture

```text
E-Commerce-Sales-Analytics-Dashboard/
│
├── .gitignore                      # Git ignore rules for virtual environments, caches, and raw CSVs
├── LICENSE                         # Repository license
├── README.md                       # Comprehensive project documentation
├── requirements.txt                # Python project dependencies
├── app.py                          # Streamlit dashboard entry point
│
├── data/                           # Data storage folder
│   ├── .gitkeep                    # Directory tracking placeholder
│   ├── olist_orders_dataset.csv
│   ├── olist_order_items_dataset.csv
│   └── olist_customers_dataset.csv
│
└── src/                            # Modular Python backend package
    ├── __init__.py                 # Package initializer
    ├── fetch_data.py               # Kaggle API automated ingestion routine
    └── data_processing.py          # Data cleaning, aggregation, merging, and caching
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites & Virtual Environment

Ensure Python 3.10+ is installed on your system.

```bash
# Clone the repository
git clone https://github.com/kiwisibk/E-Commerce-Sales-Analytics-Dashboard.git
cd E-Commerce-Sales-Analytics-Dashboard

# Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install project dependencies
pip install -r requirements.txt
```

### 2. Kaggle API Configuration & Data Ingestion

#### Option A: Download Official Dataset from Kaggle

1. Download your API credentials token (`kaggle.json`) from your Kaggle account settings:
   - Go to [kaggle.com/settings](https://www.kaggle.com/settings) -> **API** -> **Create New Token**.
   - Move `kaggle.json` to `~/.kaggle/kaggle.json` (on Windows: `C:\Users\<Username>\.kaggle\kaggle.json`).
   - *Alternatively, set environment variables `KAGGLE_USERNAME` and `KAGGLE_KEY`.*
2. Execute the ingestion script:

```bash
python src/fetch_data.py
```

#### Option B: Offline Demo / Instant Sample Data

If you want to test the dashboard immediately without Kaggle credentials:

```bash
python src/fetch_data.py --generate-sample
```

### 3. Launching the Streamlit Dashboard

Run the Streamlit application:

```bash
streamlit run app.py
```

The application will launch in your default web browser at `http://localhost:8501`.

---

## 📊 Analytical Data Model

The pipeline aggregates and normalizes three relational datasets into a single analytical dataframe:

| Raw Dataset | Key Join Field | Attributes Extracted |
| :--- | :--- | :--- |
| `olist_orders_dataset.csv` | `order_id`, `customer_id` | `order_status`, `order_purchase_timestamp`, `order_delivered_customer_date` |
| `olist_order_items_dataset.csv` | `order_id` | Aggregated `total_revenue` (`sum(price)`), `total_freight`, `items_count` |
| `olist_customers_dataset.csv` | `customer_id` | `customer_city`, `customer_state` (UF), `state_name` |

---

## 🛠️ Technology Stack

- **UI & Dashboarding**: [Streamlit](https://streamlit.io/)
- **Data Manipulation**: [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
- **Interactive Visualizations**: [Plotly](https://plotly.com/python/)
- **Data Ingestion**: [Kaggle Python API](https://github.com/Kaggle/kaggle-api)
- **Filesystem Management**: Standard Library `pathlib`

---

## 📄 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.
