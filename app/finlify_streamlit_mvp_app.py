from __future__ import annotations

from pathlib import Path
from typing import Optional

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
FORECAST_FILE = BASE_DIR / "data/visualization/investment/asset_forecast_for_streamlit.csv"

DECISION_COLORS = {
    "BUY": "#16a34a",
    "HOLD": "#f59e0b",
    "WATCH": "#eab308",
    "AVOID": "#dc2626",
}
DATE_CANDIDATE_COLUMNS = ["date", "Date", "trade_date", "snapshot_date", "as_of_date"]


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


@st.cache_data
def load_forecasts() -> pd.DataFrame:
    if not FORECAST_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(FORECAST_FILE)

    if "forecast_date" in df.columns:
        df["forecast_date"] = pd.to_datetime(df["forecast_date"], errors="coerce")
    if "last_actual_date" in df.columns:
        df["last_actual_date"] = pd.to_datetime(df["last_actual_date"], errors="coerce")
    if "horizon" in df.columns:
        df["horizon"] = pd.to_numeric(df["horizon"], errors="coerce")

    for col in ["forecast_price", "lower_ci", "upper_ci", "forecast_ret_1d", "last_actual_close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def apply_global_ui_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1.3rem;
        }
        h1 {
            margin-bottom: 0.1rem !important;
        }
        h3 {
            margin-top: 0.75rem !important;
            margin-bottom: 0.4rem !important;
        }
        thead tr th {
            font-size: 15px !important;
        }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 0.65rem;
            padding: 0.5rem 0.65rem;
            background: rgba(148, 163, 184, 0.08);
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.82rem;
            font-weight: 600;
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
        }
        section[data-testid="stSidebar"] label {
            font-weight: 600;
        }
        .finlify-note {
            border-left: 3px solid #94a3b8;
            padding: 0.55rem 0.75rem;
            border-radius: 0.4rem;
            background: rgba(148, 163, 184, 0.08);
            margin: 0.25rem 0 0.7rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_most_recent_data_date(*dfs: pd.DataFrame) -> str:
    latest_date = None

    for df in dfs:
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue

        for col in DATE_CANDIDATE_COLUMNS:
            if col not in df.columns:
                continue

            parsed_dates = pd.to_datetime(df[col], errors="coerce")
            if parsed_dates.notna().any():
                col_max = parsed_dates.max()
                if pd.notna(col_max) and (latest_date is None or col_max > latest_date):
                    latest_date = col_max

    if latest_date is None:
        return "Not available"
    return latest_date.strftime("%Y-%m-%d")


def render_page_header(title: str, subtitle: Optional[str] = None) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.caption(f"Data as of: {most_recent_data_date}")


def get_decision_color(decision: str) -> str:
    return DECISION_COLORS.get(str(decision).upper(), "#64748b")


def render_decision_badge(decision: str) -> None:
    decision_upper = str(decision).upper()
    color = get_decision_color(decision_upper)
    text_color = "#0f172a" if decision_upper == "WATCH" else "white"

    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:0.46rem 0.95rem;
            border-radius:999px;
            background-color:{color};
            color:{text_color};
            font-weight:700;
            font-size:0.92rem;
            box-shadow:0 2px 6px rgba(2, 6, 23, 0.18);">
            {decision_upper}
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


def format_metric_score(value) -> str:
    numeric_value = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric_value):
        return "-"
    return format_score(numeric_value)


def decision_style(val):
    v = str(val).upper()
    color = DECISION_COLORS.get(v)
    if not color:
        return ""

    text_color = "black" if v == "WATCH" else "white"
    return f"background-color: {color}; color: {text_color};"


def render_kpi_row(metrics: list[tuple[str, str]]) -> None:
    if not metrics:
        return

    cols = st.columns(len(metrics))
    for idx, (label, value) in enumerate(metrics):
        cols[idx].metric(label, value)


def render_table(df: pd.DataFrame, highlight_decision: bool = False) -> None:
    table_content = df
    if highlight_decision:
        decision_col = None
        if "Investment Decision" in df.columns:
            decision_col = "Investment Decision"
        elif "decision" in df.columns:
            decision_col = "decision"

        if decision_col:
            table_content = df.style.map(decision_style, subset=[decision_col])

    max_rows = 20 if len(df) > 12 else 12
    st.dataframe(
        table_content,
        use_container_width=True,
        hide_index=True,
        height=dataframe_height(df, max_rows=max_rows),
    )


def render_empty_state(message: str) -> None:
    st.markdown(
        f'<div class="finlify-note">{message}</div>',
        unsafe_allow_html=True,
    )


def apply_chart_layout(fig, horizontal_legend: bool = False) -> None:
    base_layout = {
        "margin": dict(t=12, b=12, l=8, r=8),
        "legend_title_text": "",
    }
    if horizontal_legend:
        base_layout["legend"] = dict(
            orientation="h",
            yanchor="bottom",
            y=-0.28,
            xanchor="center",
            x=0.5,
        )
    fig.update_layout(**base_layout)
    if hasattr(fig.layout, "xaxis"):
        fig.update_layout(xaxis_title=None)
    if hasattr(fig.layout, "yaxis"):
        fig.update_layout(yaxis_title=None)


def render_page_explainer(page_type: str) -> None:
    expander_title = "How to read this page" if page_type == "market" else "What this page shows"
    with st.expander(expander_title, expanded=False):
        st.markdown(
            """
            - **Composite Score** combines trend and momentum signals after a risk penalty.
            - **Trend Score** reflects longer-term direction and consistency.
            - **Momentum Score** captures recent acceleration in price action.
            - **Risk Penalty** reduces conviction when volatility or downside risk is elevated.
            - **BUY / HOLD / WATCH / AVOID** summarize the current investment stance.
            """
        )


def render_top_opportunities(df: pd.DataFrame) -> None:
    if df.empty:
        render_empty_state("No ranked opportunities available.")
        return

    top_df = df.copy()
    if "rank" in top_df.columns:
        top_df = top_df.sort_values("rank", ascending=True)
    elif "composite_score" in top_df.columns:
        top_df = top_df.sort_values("composite_score", ascending=False)

    top_df = top_df.head(3)
    cols = st.columns(3)
    for idx, (_, row) in enumerate(top_df.iterrows()):
        with cols[idx]:
            ticker = str(row.get("ticker", "-"))
            st.markdown(f"**{ticker}**")
            render_decision_badge(str(row.get("decision", "-")))
            st.caption(f"Composite Score: {format_metric_score(row.get('composite_score'))}")
            if "asset_type" in top_df.columns:
                st.caption(f"Asset Type: {row.get('asset_type', '-')}")


def render_decision_snapshot(asset: pd.Series, universe_size: int) -> None:
    trend = pd.to_numeric(asset.get("trend_score"), errors="coerce")
    momentum = pd.to_numeric(asset.get("momentum_score"), errors="coerce")
    risk = pd.to_numeric(asset.get("risk_penalty"), errors="coerce")
    rank = pd.to_numeric(asset.get("rank"), errors="coerce")
    decision = str(asset.get("decision", "-")).upper()

    notes = [f"Current stance is **{decision}** based on the latest score profile."]

    if pd.notna(trend) and pd.notna(momentum):
        if trend > momentum:
            notes.append("Trend strength is currently stronger than momentum.")
        elif momentum > trend:
            notes.append("Momentum is currently stronger than trend strength.")
        else:
            notes.append("Trend and momentum are currently balanced.")

    if pd.notna(risk) and pd.notna(trend) and pd.notna(momentum):
        if risk >= (trend + momentum) * 0.5:
            notes.append("Risk penalty is relatively high versus positive components.")
        else:
            notes.append("Risk penalty is moderate relative to trend and momentum.")

    if pd.notna(rank) and universe_size > 0:
        top_cutoff = max(1, int(universe_size * 0.2))
        if rank <= top_cutoff:
            notes.append("This asset currently ranks in the upper tier of the screened universe.")
        elif rank <= max(1, int(universe_size * 0.5)):
            notes.append("This asset currently ranks in the middle tier of the screened universe.")
        else:
            notes.append("This asset currently ranks in the lower half of the screened universe.")

    st.markdown("\n".join([f"- {line}" for line in notes]))


rankings_df = load_rankings()
prices_df = load_prices()
forecasts_df = load_forecasts()
most_recent_data_date = get_most_recent_data_date(rankings_df, prices_df)
apply_global_ui_style()

st.sidebar.title("Finlify MVP")
st.sidebar.caption("Investment Decision Support MVP")
page = st.sidebar.radio(
    "Navigation",
    ["Market Overview", "Asset Detail", "Watchlist Compare"],
)

if rankings_df.empty:
    st.warning("No ranking data found. Please add data/top_ranked_assets.csv")
    st.stop()

all_tickers = sorted(rankings_df["ticker"].dropna().astype(str).unique().tolist())
selected_ticker = st.sidebar.selectbox("Ticker", all_tickers)
if not selected_ticker:
    render_empty_state("No ticker selected. Please choose a ticker from the sidebar.")
    st.stop()

if page == "Market Overview":
    render_page_header(
        "Finlify Market Overview",
        "Decision-support MVP built from ranking outputs",
    )
    render_page_explainer("market")

    buy_ratio = (
        (rankings_df["decision"].astype(str).str.upper() == "BUY").sum() / len(rankings_df)
        if "decision" in rankings_df.columns and len(rankings_df) > 0
        else 0
    )

    avg_score = (
        pd.to_numeric(rankings_df["composite_score"], errors="coerce").dropna().mean()
        if "composite_score" in rankings_df.columns
        else None
    )
    buy_count = (
        int((rankings_df["decision"].astype(str).str.upper() == "BUY").sum())
        if "decision" in rankings_df.columns
        else 0
    )

    render_kpi_row(
        [
            ("Assets Covered", str(len(rankings_df))),
            ("Average Score", format_metric_score(avg_score)),
            ("Buy Signals", str(buy_count)),
            ("Buy Signal Ratio", f"{buy_ratio:.1%}"),
        ]
    )

    st.subheader("Top Opportunities")
    render_top_opportunities(rankings_df)

    with st.container():
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
                color_discrete_map=DECISION_COLORS,
                category_orders={"decision": ["BUY", "HOLD", "WATCH", "AVOID"]},
            )
            apply_chart_layout(fig, horizontal_legend=True)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Ranked Opportunities")

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
            "risk_penalty": "Risk Penalty",
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
            "Risk Penalty",
            "Investment Decision",
        ]
        if col in display_df.columns
    ]

    ranked_table = display_df[display_cols].sort_values("Rank").head(20)
    render_table(ranked_table, highlight_decision=True)

    st.markdown(
        """
        **Scoring Logic**

        Composite Score = Trend Score + Momentum Score − Risk Penalty

        • **Trend Score**: measures long-term directional strength  
        • **Momentum Score**: captures recent acceleration in price  
        • **Risk Penalty**: reduces conviction when volatility and downside risk rise  

        Investment decisions are mapped from Composite Score thresholds.
        """
    )

elif page == "Asset Detail":
    render_page_header(f"Asset Detail: {selected_ticker}")
    render_page_explainer("asset")

    asset_row = rankings_df[
        rankings_df["ticker"].astype(str).str.upper() == selected_ticker.upper()
    ].copy()

    price_row = pd.DataFrame()
    if not prices_df.empty and "ticker" in prices_df.columns:
        price_row = prices_df[
            prices_df["ticker"].astype(str).str.upper() == selected_ticker.upper()
        ].copy()

    forecast_row = pd.DataFrame()
    if not forecasts_df.empty:
        selected_source_ticker = str(asset_row.iloc[0].get("source_ticker", "")).upper() if not asset_row.empty else ""
        if selected_source_ticker and "source_ticker" in forecasts_df.columns:
            forecast_row = forecasts_df[
                forecasts_df["source_ticker"].astype(str).str.upper() == selected_source_ticker
            ].copy()
        elif "ticker" in forecasts_df.columns:
            forecast_row = forecasts_df[
                forecasts_df["ticker"].astype(str).str.upper() == selected_ticker.upper()
            ].copy()

    if asset_row.empty:
        render_empty_state("Ticker not found in ranking data.")
        st.stop()

    asset = asset_row.iloc[0]

    st.subheader("Score Summary")
    render_kpi_row(
        [
            ("Composite Score", format_metric_score(asset.get("composite_score"))),
            ("Trend Score", format_metric_score(asset.get("trend_score"))),
            ("Momentum Score", format_metric_score(asset.get("momentum_score"))),
            ("Risk Penalty", format_metric_score(asset.get("risk_penalty"))),
        ]
    )

    st.markdown("**Current Decision**")
    render_decision_badge(str(asset.get("decision", "")))

    st.subheader("Decision Snapshot")
    render_decision_snapshot(asset, len(rankings_df))

    with st.container():
        st.subheader("Price History")

        filter_col1, filter_col2, filter_col3 = st.columns([1.35, 1.2, 1.45])

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

        with filter_col3:
            if hasattr(st, "toggle"):
                show_forecast = st.toggle("Show Forecast", value=False, key="asset_show_forecast")
            else:
                show_forecast = st.checkbox("Show Forecast", value=False, key="asset_show_forecast")
            forecast_horizon = st.radio(
                "Forecast Horizon",
                ["30D (1M)", "60D (3M)", "90D (4M)"],
                horizontal=True,
                key="asset_forecast_horizon",
                disabled=not show_forecast,
            )
            st.caption(
                "Forecasts are trend-based statistical projections for decision support. "
                "The shaded band represents a volatility-based uncertainty range, "
                "not a guaranteed price prediction."
            )

        if not price_row.empty and {"date", "close"}.issubset(price_row.columns):
            price_row = price_row.sort_values("date").copy()

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
            )
            fig_price.update_traces(
                name="Historical Price",
                hovertemplate="%{x}<br>Historical Price: %{y:.2f}<extra></extra>",
            )
            apply_chart_layout(fig_price)
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

            if show_forecast:
                forecast_available = {"forecast_date", "forecast_price", "horizon"}.issubset(forecast_row.columns)
                if forecast_available:
                    horizon_map_forecast = {"30D (1M)": 30, "60D (3M)": 60, "90D (4M)": 90}
                    horizon_limit = horizon_map_forecast.get(forecast_horizon, 90)
                    forecast_plot = forecast_row.copy()
                    forecast_plot = forecast_plot[
                        forecast_plot["horizon"].notna() & (forecast_plot["horizon"] <= horizon_limit)
                    ].copy()
                    forecast_plot = forecast_plot.dropna(subset=["forecast_date", "forecast_price"])
                    forecast_plot = forecast_plot.sort_values("forecast_date")
                    forecast_plot = forecast_plot[
                        forecast_plot["forecast_date"] > latest_date
                    ].drop_duplicates(subset=["forecast_date"], keep="last")

                    if not forecast_plot.empty:
                        fig_price.add_vline(
                            x=latest_date,
                            line_dash="dot",
                            line_color="#64748b",
                            line_width=1,
                            annotation_text="Forecast Start",
                            annotation_position="top left",
                        )

                        ci_plot = forecast_plot.dropna(subset=["lower_ci", "upper_ci"]).copy()
                        if not ci_plot.empty:
                            fig_price.add_scatter(
                                x=ci_plot["forecast_date"],
                                y=ci_plot["lower_ci"],
                                mode="lines",
                                line=dict(color="rgba(249, 115, 22, 0.35)", width=1, dash="dot"),
                                name="Lower Band",
                                hovertemplate="%{x}<br>Lower Band: %{y:.2f}<extra></extra>",
                            )
                            fig_price.add_scatter(
                                x=ci_plot["forecast_date"],
                                y=ci_plot["upper_ci"],
                                mode="lines",
                                line=dict(color="rgba(249, 115, 22, 0.35)", width=1, dash="dot"),
                                fill="tonexty",
                                fillcolor="rgba(249, 115, 22, 0.16)",
                                name="Upper Band",
                                hovertemplate="%{x}<br>Upper Band: %{y:.2f}<extra></extra>",
                            )

                        fig_price.add_scatter(
                            x=forecast_plot["forecast_date"],
                            y=forecast_plot["forecast_price"],
                            mode="lines",
                            name="Forecast Price",
                            line=dict(color="#f97316", dash="dash", width=2),
                            hovertemplate="%{x}<br>Forecast Price: %{y:.2f}<extra></extra>",
                        )
                    else:
                        st.caption("Forecast data is unavailable for this asset and horizon; showing history only.")
                else:
                    st.caption("Forecast file is missing or incomplete; showing history only.")

            st.plotly_chart(fig_price, use_container_width=True)

        else:
            render_empty_state("No price history found for this ticker.")

elif page == "Watchlist Compare":
    render_page_header("Watchlist Compare")

    selected = st.multiselect(
        "Select up to 5 tickers",
        all_tickers,
        default=all_tickers[:4],
        max_selections=5,
    )

    if not selected:
        render_empty_state("Select at least one ticker to compare the watchlist.")
        st.stop()

    compare_df = rankings_df[rankings_df["ticker"].isin(selected)].copy()

    if "composite_score" in compare_df.columns:
        score_numeric = pd.to_numeric(compare_df["composite_score"], errors="coerce")
    else:
        score_numeric = pd.Series(dtype="float64")
    highest_ticker = "-"
    lowest_ticker = "-"
    avg_watchlist_score = "-"
    if score_numeric.notna().any():
        highest_ticker = str(compare_df.loc[score_numeric.idxmax(), "ticker"])
        lowest_ticker = str(compare_df.loc[score_numeric.idxmin(), "ticker"])
        avg_watchlist_score = format_metric_score(score_numeric.mean())
    buy_signals = (
        int((compare_df["decision"].astype(str).str.upper() == "BUY").sum())
        if "decision" in compare_df.columns
        else 0
    )

    st.subheader("Watchlist Highlights")
    render_kpi_row(
        [
            ("Highest Score", highest_ticker),
            ("Lowest Score", lowest_ticker),
            ("Buy Signals", str(buy_signals)),
            ("Avg Composite Score", avg_watchlist_score),
        ]
    )

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
            "risk_penalty": "Risk Penalty",
            "decision": "Investment Decision",
        }
    )

    score_sort_col = (
        "_composite_score_sort" if "_composite_score_sort" in compare_display.columns else "Composite Score"
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
            "Risk Penalty",
            "Investment Decision",
        ]
        if col in compare_display.columns
    ]

    st.subheader("Watchlist Summary")
    watchlist_table = compare_display.sort_values(score_sort_col, ascending=False)[display_cols]
    render_table(watchlist_table, highlight_decision=True)

    st.subheader("Composite Score Comparison")

    score_table_cols = [
        col
        for col in [
            "Ticker",
            "Composite Score",
            "Trend Score",
            "Momentum Score",
            "Risk Penalty",
            "Investment Decision",
        ]
        if col in compare_display.columns
    ]

    score_compare_df = compare_display.sort_values(score_sort_col, ascending=False)[score_table_cols]
    render_table(score_compare_df)

    with st.container():
        st.subheader("Watchlist Price Comparison")

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

            apply_chart_layout(fig_price_multi)
            fig_price_multi.update_traces(hovertemplate="%{x}<br>%{y:.2f}")

            st.plotly_chart(fig_price_multi, use_container_width=True)

        else:
            render_empty_state("No price history available for watchlist comparison.")
