"""
Streamlit Application: E-Commerce Sales & Customer Insights Dashboard.

This is the main dashboard entry point. It loads, merges, and caches Brazilian
E-Commerce dataset records, provides dynamic time and regional filtering in the sidebar,
and visualizes KPIs, time series trends, geographic performance, and raw data tables.
"""

from datetime import datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Import backend modules
from src.data_processing import (
    BRAZILIAN_STATES,
    check_data_files_exist,
    filter_data,
    generate_sample_dataset,
    get_data_dir,
    load_and_merge_data,
)
from src.fetch_data import fetch_kaggle_dataset

# ==============================================================================
# Page Configuration & Global Theming
# ==============================================================================
st.set_page_config(
    page_title="E-Commerce Sales & Customer Insights",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom CSS styling for modern executive UI
st.markdown(
    """
    <style>
    /* Metric card custom styling */
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"]:hover {
        border-color: #ced4da;
        box-shadow: 0 4px 6px rgba(0,0,0,0.08);
        transition: all 0.2s ease-in-out;
    }
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.05rem;
        font-weight: 600;
        padding: 0.5rem 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_currency_brl(value: float) -> str:
    """
    Format a numeric float as Brazilian Real currency (R$).

    Args:
        value (float): Value to format.

    Returns:
        str: Formatted currency string.
    """
    return f"R$ {value:,.2f}"


def format_large_number(value: int) -> str:
    """
    Format large integers with thousand separators.

    Args:
        value (int): Integer value.

    Returns:
        str: Formatted number string.
    """
    return f"{value:,}"


def render_missing_data_banner(data_dir: Path, missing_files: list[str]) -> None:
    """
    Render a clean guided setup banner when dataset CSV files are missing.

    Args:
        data_dir (Path): Target data directory path.
        missing_files (list[str]): List of missing file names.
    """
    st.warning("⚠️ **Dataset Not Detected Locally**")
    st.info(
        f"The dashboard requires the Brazilian E-Commerce dataset files in `{data_dir}`.\n\n"
        f"**Missing file(s):** {', '.join(f'`{f}`' for f in missing_files)}\n\n"
        "You can download the official dataset from Kaggle or generate sample data instantly below:"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Download Dataset via Kaggle API", use_container_width=True):
            with st.spinner("Downloading and extracting dataset from Kaggle..."):
                success = fetch_kaggle_dataset(data_dir=data_dir)
                if success:
                    st.success("Dataset successfully downloaded! Refreshing...")
                    st.rerun()
                else:
                    st.error(
                        "Kaggle download failed. Please verify that your Kaggle API key "
                        "is configured at `~/.kaggle/kaggle.json` or via environment variables."
                    )
    with col2:
        if st.button("✨ Generate Instant Sample Demo Data", use_container_width=True):
            with st.spinner("Generating realistic synthetic Olist dataset..."):
                generate_sample_dataset(data_dir=data_dir, num_orders=3000)
                st.success("Sample data generated successfully! Refreshing...")
                st.rerun()


def main() -> None:
    """
    Main execution pipeline for the Streamlit dashboard.
    """
    data_dir = get_data_dir()
    all_files_exist, missing_files = check_data_files_exist(data_dir)

    # If dataset files do not exist, present guided ingestion options
    if not all_files_exist:
        st.title("🛒 E-Commerce Sales & Customer Insights Dashboard")
        st.markdown(
            "An end-to-end analytical dashboard built on the Olist Brazilian E-Commerce public dataset."
        )
        st.divider()
        render_missing_data_banner(data_dir, missing_files)
        return

    # Load and cache merged data
    with st.spinner("Loading and merging analytical datasets..."):
        try:
            df = load_and_merge_data(str(data_dir))
        except Exception as err:
            st.error(f"Error while loading dataset: {err}")
            return

    # ==============================================================================
    # Sidebar: Dynamic Time and Attribute Filters
    # ==============================================================================
    st.sidebar.image(
        "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/svgs/solid/chart-line.svg",
        width=40,
    )
    st.sidebar.title("Dashboard Controls")
    st.sidebar.markdown("Use the filters below to dynamically slice the dataset.")

    # Time Filter 1: Available Years
    available_years = sorted(df["order_year"].unique().tolist())
    selected_years = st.sidebar.multiselect(
        "📅 Select Year(s)",
        options=available_years,
        default=available_years,
        help="Filter orders by the year of purchase.",
    )

    # Time Filter 2: Available Months (1 to 12)
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    available_months = sorted(df["order_month"].unique().tolist())
    selected_months = st.sidebar.multiselect(
        "🗓️ Select Month(s)",
        options=available_months,
        default=available_months,
        format_func=lambda m: f"{m:02d} - {month_names.get(m, m)}",
        help="Filter orders by purchase month.",
    )

    # Time Filter 3: Exact Date Range Slider
    min_date = df["order_purchase_timestamp"].min().date()
    max_date = df["order_purchase_timestamp"].max().date()
    selected_date_range = st.sidebar.date_input(
        "⏱️ Custom Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Refine data selection within specific calendar dates.",
    )

    st.sidebar.divider()

    # Attribute Filter: Order Status
    available_statuses = sorted(df["order_status"].unique().tolist())
    selected_statuses = st.sidebar.multiselect(
        "📦 Order Status",
        options=available_statuses,
        default=available_statuses,
        help="Filter by fulfillment status (e.g., delivered, shipped, canceled).",
    )

    # Attribute Filter: Customer State
    available_states = sorted(df["customer_state"].unique().tolist())
    selected_states = st.sidebar.multiselect(
        "📍 Customer State (UF)",
        options=available_states,
        default=available_states,
        format_func=lambda s: f"{s} - {BRAZILIAN_STATES.get(s, s)}",
        help="Filter orders by customer state location.",
    )

    # Apply all user filters
    date_tuple = selected_date_range if isinstance(selected_date_range, tuple) and len(selected_date_range) == 2 else None
    filtered_df = filter_data(
        df=df,
        selected_years=selected_years,
        selected_months=selected_months,
        selected_states=selected_states,
        selected_statuses=selected_statuses,
        date_range=date_tuple,
    )

    # Provide sidebar data overview
    st.sidebar.caption(
        f"Showing **{format_large_number(len(filtered_df))}** of **{format_large_number(len(df))}** orders."
    )

    # ==============================================================================
    # Main Header
    # ==============================================================================
    st.title("🛒 E-Commerce Sales & Customer Insights")
    st.markdown(
        "An enterprise analytics dashboard delivering sales trends, fulfillment metrics, "
        "and customer geolocation performance for Brazilian e-commerce operations."
    )

    # Check if filtered dataset has records
    if filtered_df.empty:
        st.warning("No records match the selected filter criteria. Please adjust your filters in the sidebar.")
        return

    # ==============================================================================
    # Tabs Layout
    # ==============================================================================
    tab_kpi, tab_geo, tab_raw = st.tabs([
        "📈 Sales Performance & Time Series",
        "🗺️ Geographic Insights",
        "📋 Raw Dataset Explorer",
    ])

    # ------------------------------------------------------------------------------
    # TAB 1: KPIs & Plotly Time Series
    # ------------------------------------------------------------------------------
    with tab_kpi:
        st.subheader("Executive Sales KPIs")

        # Compute core KPI metrics
        total_revenue = filtered_df["total_revenue"].sum()
        total_orders = filtered_df["order_id"].nunique()
        total_items = filtered_df["items_count"].sum()
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
        avg_items_per_order = total_items / total_orders if total_orders > 0 else 0.0

        # Render KPI Metric Cards
        col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
        with col_kpi1:
            st.metric(
                label="Total Revenue",
                value=format_currency_brl(total_revenue),
                help="Sum of item prices across all filtered orders.",
            )
        with col_kpi2:
            st.metric(
                label="Total Orders",
                value=format_large_number(total_orders),
                help="Count of unique purchase orders placed.",
            )
        with col_kpi3:
            st.metric(
                label="Average Order Value (AOV)",
                value=format_currency_brl(avg_order_value),
                help="Average sales revenue generated per order.",
            )
        with col_kpi4:
            st.metric(
                label="Total Items Sold",
                value=format_large_number(int(total_items)),
                help="Total unit quantity of products ordered.",
            )
        with col_kpi5:
            st.metric(
                label="Avg Items / Order",
                value=f"{avg_items_per_order:.2f}",
                help="Average number of products contained in an order.",
            )

        st.divider()

        # Time Series Aggregation Controls
        st.subheader("Revenue Trend Over Time")
        col_ctrl1, col_ctrl2 = st.columns([2, 4])
        with col_ctrl1:
            time_granularity = st.radio(
                "Time Aggregation Level:",
                options=["Monthly", "Weekly", "Daily"],
                horizontal=True,
                index=0,
                help="Select grouping interval for the time series visualization.",
            )

        # Aggregate time series data based on user selection
        df_ts = filtered_df.copy()
        if time_granularity == "Monthly":
            df_ts["period"] = df_ts["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
            hover_fmt = "%B %Y"
        elif time_granularity == "Weekly":
            df_ts["period"] = df_ts["order_purchase_timestamp"].dt.to_period("W").dt.start_time
            hover_fmt = "Week of %Y-%m-%d"
        else:
            df_ts["period"] = df_ts["order_date"]
            hover_fmt = "%Y-%m-%d"

        trend_df = (
            df_ts.groupby("period")
            .agg(
                period_revenue=("total_revenue", "sum"),
                period_orders=("order_id", "nunique"),
            )
            .reset_index()
            .sort_values("period")
        )

        # Build Interactive Plotly Time Series Chart
        fig_trend = go.Figure()

        # Add Revenue Area / Line Trace
        fig_trend.add_trace(
            go.Scatter(
                x=trend_df["period"],
                y=trend_df["period_revenue"],
                name="Revenue (R$)",
                mode="lines+markers",
                line=dict(color="#1f77b4", width=3),
                fill="tozeroy",
                fillcolor="rgba(31, 119, 180, 0.12)",
                hovertemplate="<b>Date:</b> %{x|" + hover_fmt + "}<br><b>Revenue:</b> R$ %{y:,.2f}<extra></extra>",
            )
        )

        # Add Order Volume on secondary Y-axis
        fig_trend.add_trace(
            go.Bar(
                x=trend_df["period"],
                y=trend_df["period_orders"],
                name="Order Volume",
                yaxis="y2",
                opacity=0.35,
                marker=dict(color="#2ca02c"),
                hovertemplate="<b>Date:</b> %{x|" + hover_fmt + "}<br><b>Orders:</b> %{y:,}<extra></extra>",
            )
        )

        fig_trend.update_layout(
            title=f"E-Commerce Revenue & Order Volume ({time_granularity})",
            xaxis=dict(title="Purchase Date", showgrid=True, gridcolor="#f0f0f0"),
            yaxis=dict(
                title="Revenue (R$)",
                tickprefix="R$ ",
                showgrid=True,
                gridcolor="#f0f0f0",
            ),
            yaxis2=dict(
                title="Order Count",
                overlaying="y",
                side="right",
                showgrid=False,
            ),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=60, b=40),
            height=450,
        )

        st.plotly_chart(fig_trend, use_container_width=True)

    # ------------------------------------------------------------------------------
    # TAB 2: Geografie (Top States & Spatial Analysis)
    # ------------------------------------------------------------------------------
    with tab_geo:
        st.subheader("Regional Performance Across Brazilian States")

        # Aggregate metrics by customer state
        state_agg = (
            filtered_df.groupby(["customer_state", "state_name"])
            .agg(
                state_revenue=("total_revenue", "sum"),
                state_orders=("order_id", "nunique"),
                state_avg_order_value=("total_revenue", "mean"),
            )
            .reset_index()
        )

        # Calculate revenue market share percentage
        total_market_rev = state_agg["state_revenue"].sum()
        state_agg["revenue_share_pct"] = (state_agg["state_revenue"] / total_market_rev) * 100
        state_agg = state_agg.sort_values("state_revenue", ascending=False).reset_index(drop=True)

        col_geo_ctrl, col_geo_info = st.columns([2, 4])
        with col_geo_ctrl:
            top_n_states = st.slider(
                "Number of Top States to Display:",
                min_value=5,
                max_value=len(state_agg),
                value=min(10, len(state_agg)),
                step=1,
                help="Limit the state ranking view to the highest performing regions.",
            )

        top_states_df = state_agg.head(top_n_states).sort_values("state_revenue", ascending=True)

        # Plotly Horizontal Bar Chart: Revenue by Top States
        fig_state_bar = px.bar(
            top_states_df,
            x="state_revenue",
            y="customer_state",
            orientation="h",
            text="state_revenue",
            color="state_revenue",
            color_continuous_scale="Viridis",
            custom_data=["state_name", "state_orders", "revenue_share_pct", "state_avg_order_value"],
            labels={
                "state_revenue": "Total Revenue (R$)",
                "customer_state": "State Code",
            },
            title=f"Top {top_n_states} Brazilian States by Total Revenue",
        )

        fig_state_bar.update_traces(
            texttemplate="R$ %{x:,.0f}",
            textposition="outside",
            hovertemplate=(
                "<b>State:</b> %{customdata[0]} (%{y})<br>"
                "<b>Revenue:</b> R$ %{x:,.2f}<br>"
                "<b>Share of Total:</b> %{customdata[2]:.2f}%<br>"
                "<b>Order Count:</b> %{customdata[1]:,}<br>"
                "<b>Average Order Value:</b> R$ %{customdata[3]:,.2f}<extra></extra>"
            ),
        )

        fig_state_bar.update_layout(
            height=450,
            margin=dict(l=40, r=60, t=60, b=40),
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickprefix="R$ "),
            coloraxis_showscale=False,
        )

        st.plotly_chart(fig_state_bar, use_container_width=True)

        # Secondary Geographic Breakdown: Top Cities within the Filtered Data
        st.subheader("Top Performing Cities by Revenue")
        city_agg = (
            filtered_df.groupby(["customer_city", "customer_state"])
            .agg(
                city_revenue=("total_revenue", "sum"),
                city_orders=("order_id", "nunique"),
            )
            .reset_index()
            .sort_values("city_revenue", ascending=False)
            .head(10)
        )
        city_agg["city_label"] = city_agg["customer_city"] + " (" + city_agg["customer_state"] + ")"

        fig_city_bar = px.bar(
            city_agg,
            x="city_label",
            y="city_revenue",
            color="city_revenue",
            color_continuous_scale="Blues",
            labels={"city_label": "City", "city_revenue": "Revenue (R$)"},
            title="Top 10 Cities by Revenue",
        )
        fig_city_bar.update_traces(
            hovertemplate="<b>City:</b> %{x}<br><b>Revenue:</b> R$ %{y:,.2f}<extra></extra>"
        )
        fig_city_bar.update_layout(
            xaxis_tickangle=-30,
            height=380,
            coloraxis_showscale=False,
            margin=dict(l=40, r=40, t=60, b=40),
        )
        st.plotly_chart(fig_city_bar, use_container_width=True)

    # ------------------------------------------------------------------------------
    # TAB 3: Rohdaten (Raw Data & Export)
    # ------------------------------------------------------------------------------
    with tab_raw:
        st.subheader("Underlying Order Level Data")
        st.markdown(
            "Inspect the fully merged analytical records combining orders, items, and customer locations."
        )

        # Raw data table inside an expander as strictly specified
        with st.expander("🔍 Explore Raw Merged Orders Dataset", expanded=True):
            col_search, col_rows = st.columns([3, 1])
            with col_search:
                search_query = st.text_input(
                    "Search within dataset (Customer ID, City, or Order ID):",
                    placeholder="e.g., São Paulo or cust_0001...",
                )
            with col_rows:
                max_display_rows = st.selectbox(
                    "Display Rows Limit:",
                    options=[50, 100, 250, 500, 1000, "All"],
                    index=1,
                )

            # Apply search text filtering if entered
            display_df = filtered_df
            if search_query:
                q = search_query.strip().lower()
                display_df = display_df[
                    display_df["order_id"].str.lower().str.contains(q, na=False)
                    | display_df["customer_id"].str.lower().str.contains(q, na=False)
                    | display_df["customer_city"].str.lower().str.contains(q, na=False)
                    | display_df["customer_state"].str.lower().str.contains(q, na=False)
                ]

            # Slice rows according to selector
            if max_display_rows != "All":
                display_df = display_df.head(int(max_display_rows))

            # Select and format columns for clean tabular presentation
            columns_to_show = [
                "order_id",
                "order_status",
                "order_purchase_timestamp",
                "total_revenue",
                "total_freight",
                "total_order_value",
                "items_count",
                "customer_city",
                "customer_state",
                "state_name",
            ]

            # Interactive dataframe view
            st.dataframe(
                display_df[columns_to_show],
                use_container_width=True,
                column_config={
                    "total_revenue": st.column_config.NumberColumn(
                        "Revenue", format="R$ %.2f"
                    ),
                    "total_freight": st.column_config.NumberColumn(
                        "Freight", format="R$ %.2f"
                    ),
                    "total_order_value": st.column_config.NumberColumn(
                        "Total Value", format="R$ %.2f"
                    ),
                    "items_count": st.column_config.NumberColumn(
                        "Items", format="%d"
                    ),
                    "order_purchase_timestamp": st.column_config.DatetimeColumn(
                        "Purchase Timestamp", format="YYYY-MM-DD HH:mm:ss"
                    ),
                },
            )

            # CSV Download Button for filtered dataset
            csv_data = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Filtered Data as CSV",
                data=csv_data,
                file_name=f"ecommerce_sales_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                help="Export the currently filtered view of the dataset to a local CSV file.",
            )


if __name__ == "__main__":
    main()
