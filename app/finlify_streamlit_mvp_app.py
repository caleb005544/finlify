from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Finlify MVP",
    page_icon="📈",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent.parent
MART_DIR = BASE_DIR / "data/mart"
RANKING_FILE = MART_DIR / "investment/top_ranked_assets.csv"
PRICE_FILE = BASE_DIR / "data/visualization/investment/price_history_for_pbi.csv"


@st.cache_data
def load_rankings() -> pd.DataFrame:
    if not RANKING_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(RANKING_FILE)

    if "rank_overall" in df.columns:
        df = df.rename(columns={"rank_overall": "rank"})

    return df


@st.cache_data
def load_prices() -> pd.DataFrame:
    if not PRICE_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(PRICE_FILE)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])

    return df


def get_decision_color(decision: str) -> str:
    color_map = {
        "BUY": "#16a34a",
        "HOLD": "#f59e0b",
        "WATCH": "#eab308",
        "AVOID": "#dc2626",
    }
    return color_map.get(str(decision).upper(), "#64748b")


def render_decision_badge(decision: str) -> None:
    color = get_decision_color(decision)
    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:0.35rem 0.8rem;
            border-radius:999px;
            background-color:{color};
            color:white;
            font-weight:600;">
            {decision}
        </div>
        """,
        unsafe_allow_html=True,
    )


def dataframe_height(df: pd.DataFrame, max_rows: int = 12) -> int:
    row_count = min(len(df), max_rows)
    return 45 + row_count * 35


def format_score(value):
    if pd.isna(value):
        return ""
    return f"{value:.2f}".rstrip("0").rstrip(".")


rankings_df = load_rankings()
prices_df = load_prices()

st.sidebar.title("Finlify MVP")
page = st.sidebar.radio(
    "Navigation",
    ["Market Overview", "Asset Detail", "Watchlist Compare"],
)

if rankings_df.empty:
    st.warning("No ranking data found. Please add data/top_ranked_assets.csv")
    st.stop()

all_tickers = sorted(rankings_df["ticker"].dropna().astype(str).unique().tolist())
selected_ticker = st.sidebar.selectbox("Ticker", all_tickers)

if page == "Market Overview":
    st.title("Finlify Market Overview")
    st.caption("Decision-support MVP built from ranking outputs")

    buy_ratio = (
        (rankings_df["decision"].astype(str).str.upper() == "BUY").sum() / len(rankings_df)
        if "decision" in rankings_df.columns and len(rankings_df) > 0
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Assets Covered", len(rankings_df))
    c2.metric(
        "Average Score",
        round(rankings_df["composite_score"].dropna().mean(), 2)
        if "composite_score" in rankings_df.columns
        else "-",
    )
    c3.metric(
        "BUY Count",
        int((rankings_df["decision"].astype(str).str.upper() == "BUY").sum())
        if "decision" in rankings_df.columns
        else 0,
    )
    c4.metric("BUY Ratio", f"{buy_ratio:.1%}")

    st.markdown(
        """
        **Scoring Logic**

        Composite Score = Trend Score + Momentum Score − Risk Score

        • **Trend Score**: measures long-term directional strength  
        • **Momentum Score**: captures recent acceleration in price  
        • **Risk Score**: penalizes volatility and downside risk  

        Investment Decision is derived from Composite Score thresholds.
        """
    )

    st.markdown(
        """
        <style>
        thead tr th {
            font-size: 16px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.9, 1])

    with left:
        st.subheader("Top Ranked Assets")

        display_df = rankings_df.copy()

        if "composite_score" in display_df.columns:
            display_df["composite_score"] = display_df["composite_score"].map(format_score)
        if "trend_score" in display_df.columns:
            display_df["trend_score"] = display_df["trend_score"].map(format_score)
        if "momentum_score" in display_df.columns:
            display_df["momentum_score"] = display_df["momentum_score"].map(format_score)
        if "risk_penalty" in display_df.columns:
            display_df["risk_penalty"] = display_df["risk_penalty"].map(format_score)

        display_df = display_df.rename(
            columns={
                "rank": "Rank",
                "ticker": "Ticker",
                "asset_type": "Asset Type",
                "composite_score": "Composite Score",
                "trend_score": "Trend Score",
                "momentum_score": "Momentum Score",
                "risk_penalty": "Risk Score",
                "decision": "Investment Decision",
            }
        )

        display_cols = [
            col
            for col in [
                "Rank",
                "Ticker",
                "Asset Type",
                "Composite Score",
                "Trend Score",
                "Momentum Score",
                "Risk Score",
                "Investment Decision",
            ]
            if col in display_df.columns
        ]

        def decision_color(val):
            v = str(val).upper()
            if v == "BUY":
                return "background-color: #16a34a; color: white;"
            if v == "HOLD":
                return "background-color: #f59e0b; color: white;"
            if v == "WATCH":
                return "background-color: #eab308; color: black;"
            if v == "AVOID":
                return "background-color: #dc2626; color: white;"
            return ""

        ranked_table = display_df[display_cols].sort_values("Rank").head(20)

        styled_df = ranked_table.style.map(
            decision_color,
            subset=["Investment Decision"] if "Investment Decision" in display_df.columns else [],
        )

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            height=dataframe_height(ranked_table, max_rows=20),
        )

    with right:
        st.subheader("Decision Distribution")
        if "decision" in rankings_df.columns:
            decision_counts = (
                rankings_df["decision"]
                .astype(str)
                .str.upper()
                .value_counts()
                .rename_axis("decision")
                .reset_index(name="count")
            )

            fig = px.pie(
                decision_counts,
                names="decision",
                values="count",
                hole=0.35,
                color="decision",
                color_discrete_map={
                    "BUY": "#16a34a",
                    "HOLD": "#f59e0b",
                    "WATCH": "#eab308",
                    "AVOID": "#dc2626",
                },
            )
            st.plotly_chart(fig, use_container_width=True)

elif page == "Asset Detail":
    st.title(f"Asset Detail: {selected_ticker}")

    asset_row = rankings_df[
        rankings_df["ticker"].astype(str).str.upper() == selected_ticker.upper()
    ].copy()

    price_row = pd.DataFrame()
    if not prices_df.empty and "ticker" in prices_df.columns:
        price_row = prices_df[
            prices_df["ticker"].astype(str).str.upper() == selected_ticker.upper()
        ].copy()

    if asset_row.empty:
        st.error("Ticker not found in ranking data.")
        st.stop()

    asset = asset_row.iloc[0]

    # Top summary
    st.subheader("Asset Detail")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Composite Score", round(float(asset["composite_score"]), 2))
    c2.metric("Trend Score", round(float(asset["trend_score"]), 2))
    c3.metric("Momentum Score", round(float(asset["momentum_score"]), 2))
    c4.metric("Risk Penalty", round(float(asset["risk_penalty"]), 2))

    st.markdown("**Decision**")
    render_decision_badge(str(asset["decision"]))

    st.subheader("Price History")

    filter_col1, filter_col2 = st.columns([1.6, 1.4])

    with filter_col1:
        horizon = st.radio(
            "Time Horizon",
            ["All Time", "3Y", "1Y", "6M", "3M", "1M"],
            horizontal=True,
        )

    with filter_col2:
        ma_options = st.multiselect(
            "Moving Averages",
            ["MA20", "MA50", "MA200"],
            default=[],
        )

    if not price_row.empty and {"date", "close"}.issubset(price_row.columns):
        price_row = price_row.sort_values("date").copy()

        # Time horizon filter
        latest_date = price_row["date"].max()
        horizon_map = {
            "3Y": pd.DateOffset(years=3),
            "1Y": pd.DateOffset(years=1),
            "6M": pd.DateOffset(months=6),
            "3M": pd.DateOffset(months=3),
            "1M": pd.DateOffset(months=1),
        }

        if horizon in horizon_map:
            start_date = latest_date - horizon_map[horizon]
            price_row = price_row[price_row["date"] >= start_date].copy()

        # Moving averages
        if "MA20" in ma_options:
            price_row["MA20"] = price_row["close"].rolling(20).mean()
        if "MA50" in ma_options:
            price_row["MA50"] = price_row["close"].rolling(50).mean()
        if "MA200" in ma_options:
            price_row["MA200"] = price_row["close"].rolling(200).mean()

        fig_price = px.line(
            price_row,
            x="date",
            y="close",
            title=f"{selected_ticker} Close Price",
        )
        fig_price.update_layout(
            xaxis_title=None,
            yaxis_title=None,
        )
        if "MA20" in price_row.columns:
            fig_price.add_scatter(
                x=price_row["date"],
                y=price_row["MA20"],
                mode="lines",
                name="MA20",
            )

        if "MA50" in price_row.columns:
            fig_price.add_scatter(
                x=price_row["date"],
                y=price_row["MA50"],
                mode="lines",
                name="MA50",
            )

        if "MA200" in price_row.columns:
            fig_price.add_scatter(
                x=price_row["date"],
                y=price_row["MA200"],
                mode="lines",
                name="MA200",
            )

        st.plotly_chart(fig_price, use_container_width=True)

    else:
        st.info("No price history found for this ticker.")

elif page == "Watchlist Compare":
    st.title("Watchlist Compare")

    selected = st.multiselect(
        "Select up to 5 tickers",
        all_tickers,
        default=all_tickers[:4],
        max_selections=5,
    )

    if not selected:
        st.info("Select at least one ticker.")
        st.stop()

    compare_df = rankings_df[rankings_df["ticker"].isin(selected)].copy()

    st.subheader("Watchlist Summary")

    compare_display = compare_df.copy()

    if "composite_score" in compare_display.columns:
        compare_display["_composite_score_sort"] = compare_display["composite_score"]
        compare_display["composite_score"] = compare_display["composite_score"].map(format_score)
    if "trend_score" in compare_display.columns:
        compare_display["trend_score"] = compare_display["trend_score"].map(format_score)
    if "momentum_score" in compare_display.columns:
        compare_display["momentum_score"] = compare_display["momentum_score"].map(format_score)
    if "risk_penalty" in compare_display.columns:
        compare_display["risk_penalty"] = compare_display["risk_penalty"].map(format_score)

    compare_display = compare_display.rename(
        columns={
            "rank": "Rank",
            "ticker": "Ticker",
            "asset_type": "Asset Type",
            "composite_score": "Composite Score",
            "trend_score": "Trend Score",
            "momentum_score": "Momentum Score",
            "risk_penalty": "Risk Score",
            "decision": "Investment Decision",
        }
    )

    display_cols = [
        col
        for col in [
            "Rank",
            "Ticker",
            "Asset Type",
            "Composite Score",
            "Trend Score",
            "Momentum Score",
            "Risk Score",
            "Investment Decision",
        ]
        if col in compare_display.columns
    ]
    
    def decision_color(val):
        v = str(val).upper()
        if v == "BUY":
            return "background-color: #16a34a; color: white;"
        if v == "HOLD":
            return "background-color: #f59e0b; color: white;"
        if v == "WATCH":
            return "background-color: #eab308; color: black;"
        if v == "AVOID":
            return "background-color: #dc2626; color: white;"
        return ""

    score_sort_col = (
        "_composite_score_sort" if "_composite_score_sort" in compare_display.columns else "Composite Score"
    )
    watchlist_table = compare_display.sort_values(score_sort_col, ascending=False)[display_cols]

    styled_compare = watchlist_table.style.map(
        decision_color,
        subset=["Investment Decision"] if "Investment Decision" in compare_display.columns else [],
    )

    st.dataframe(
        styled_compare,
        use_container_width=True,
        hide_index=True,
        height=dataframe_height(watchlist_table),
    )

    st.subheader("Composite Score Comparison")

    score_table_cols = [
        col
        for col in [
            "Ticker",
            "Composite Score",
            "Trend Score",
            "Momentum Score",
            "Risk Score",
            "Investment Decision",
        ]
        if col in compare_display.columns
    ]

    score_compare_df = compare_display.sort_values(score_sort_col, ascending=False)[score_table_cols]

    st.dataframe(
        score_compare_df,
        use_container_width=True,
        hide_index=True,
        height=dataframe_height(score_compare_df),
    )

    st.subheader("Compare Price History")

    horizon = st.radio(
        "Time Horizon",
        ["All Time", "3Y", "1Y", "6M", "3M", "1M"],
        horizontal=True,
        key="watchlist_horizon",
    )

    chart_mode = st.radio(
        "Chart Mode",
        ["Normalized Return", "Price Level"],
        horizontal=True,
        key="watchlist_chart_mode",
    )

    if not prices_df.empty and {"date", "ticker", "close"}.issubset(prices_df.columns):
        ticker_order = (
            compare_display.sort_values(score_sort_col, ascending=False)["Ticker"].tolist()
            if "Ticker" in compare_display.columns
            else selected
        )
        compare_prices = prices_df[prices_df["ticker"].isin(selected)].copy()
        compare_prices["date"] = pd.to_datetime(compare_prices["date"])
        compare_prices = compare_prices.sort_values(["ticker", "date"])

        latest_date = compare_prices["date"].max()
        horizon_map = {
            "3Y": pd.DateOffset(years=3),
            "1Y": pd.DateOffset(years=1),
            "6M": pd.DateOffset(months=6),
            "3M": pd.DateOffset(months=3),
            "1M": pd.DateOffset(months=1),
        }

        if horizon in horizon_map:
            start_date = latest_date - horizon_map[horizon]
            compare_prices = compare_prices[compare_prices["date"] >= start_date].copy()

        if chart_mode == "Normalized Return":
            compare_prices["base_close"] = compare_prices.groupby("ticker")["close"].transform("first")
            compare_prices = compare_prices[
                compare_prices["base_close"].notna() & (compare_prices["base_close"] != 0)
            ].copy()
            compare_prices["normalized_return"] = (
                compare_prices["close"] / compare_prices["base_close"]
            ) * 100

            fig_price_multi = px.line(
                compare_prices,
                x="date",
                y="normalized_return",
                color="ticker",
                category_orders={"ticker": ticker_order},
            )
        else:
            fig_price_multi = px.line(
                compare_prices,
                x="date",
                y="close",
                color="ticker",
                category_orders={"ticker": ticker_order},
            )

        fig_price_multi.update_layout(
            xaxis_title=None,
            yaxis_title=None,
        )

        fig_price_multi.update_traces(
            hovertemplate="%{x}<br>%{y:.2f}"
        )

        st.plotly_chart(fig_price_multi, use_container_width=True)

    else:
        st.info("No price history available for watchlist comparison.")
