from __future__ import annotations

"""
Build visualization-layer CSV exports for Power BI / Power Query consumption.
"""

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_HISTORICAL_INPUT = Path("data/mart/investment/factor_features.parquet")
DEFAULT_RANKING_INPUT = Path("data/mart/investment/top_ranked_assets.parquet")
DEFAULT_PRICE_HISTORY_OUTPUT = Path("data/visualization/investment/price_history_for_pbi.csv")
DEFAULT_LATEST_RANKING_OUTPUT = Path("data/visualization/investment/latest_ranking_for_pbi.csv")

PRICE_HISTORY_COLS = [
    "date",
    "ticker",
    "source_ticker",
    "asset_type",
    "close",
    "ma_20",
    "ma_50",
    "ma_200",
    "source",
]

LATEST_RANKING_COLS = [
    "ticker",
    "source_ticker",
    "asset_type",
    "date",
    "rank_overall",
    "rank_within_asset_type",
    "trend_score",
    "momentum_score",
    "risk_penalty",
    "composite_score",
    "decision",
    "decision_reason",
    "source",
    "decision_order",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build visualization CSV exports from mart outputs.")
    parser.add_argument(
        "--historical-input-parquet",
        type=Path,
        default=DEFAULT_HISTORICAL_INPUT,
        help="Historical mart parquet for price history export.",
    )
    parser.add_argument(
        "--ranking-input-parquet",
        type=Path,
        default=DEFAULT_RANKING_INPUT,
        help="Latest ranking mart parquet for ranking export.",
    )
    parser.add_argument(
        "--price-history-output-csv",
        type=Path,
        default=DEFAULT_PRICE_HISTORY_OUTPUT,
        help="Output CSV path for Power BI price history.",
    )
    parser.add_argument(
        "--latest-ranking-output-csv",
        type=Path,
        default=DEFAULT_LATEST_RANKING_OUTPUT,
        help="Output CSV path for Power BI latest ranking.",
    )
    return parser.parse_args()


def validate_price_history_input_schema(df: pd.DataFrame) -> None:
    # MA columns can be filled if absent, but core identity/price fields must exist.
    required_core = {"date", "ticker", "source_ticker", "asset_type", "close", "source"}
    missing = sorted(required_core - set(df.columns))
    if missing:
        raise ValueError(f"Historical input missing required columns: {missing}")


def validate_price_history_export_schema(df: pd.DataFrame) -> None:
    missing = sorted(set(PRICE_HISTORY_COLS) - set(df.columns))
    if missing:
        raise ValueError(f"Price history export missing required columns: {missing}")


def validate_latest_ranking_input_schema(df: pd.DataFrame) -> None:
    required = {
        "ticker",
        "source_ticker",
        "asset_type",
        "date",
        "rank_overall",
        "rank_within_asset_type",
        "trend_score",
        "momentum_score",
        "risk_penalty",
        "composite_score",
        "decision",
        "decision_reason",
        "source",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Ranking input missing required columns: {missing}")


def validate_latest_ranking_export_schema(df: pd.DataFrame) -> None:
    missing = sorted(set(LATEST_RANKING_COLS) - set(df.columns))
    if missing:
        raise ValueError(f"Latest ranking export missing required columns: {missing}")


def build_price_history_export(historical_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a chart-friendly historical dataset from mart features.
    """
    validate_price_history_input_schema(historical_df)
    out = historical_df.copy()

    # Keep export stable even if moving-average fields are absent in upstream input.
    for col in ["ma_20", "ma_50", "ma_200"]:
        if col not in out.columns:
            out[col] = pd.NA

    out = out[PRICE_HISTORY_COLS].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date
    out = out.sort_values(["ticker", "source_ticker", "date"], kind="mergesort").reset_index(drop=True)
    validate_price_history_export_schema(out)
    return out


def build_latest_ranking_export(ranking_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a presentation-ready latest ranking table for KPI cards and tabular visuals.
    """
    validate_latest_ranking_input_schema(ranking_df)
    out = ranking_df.copy()

    # decision_order exists for deterministic BI sorting and conditional formatting.
    decision_map = {"BUY": 4, "HOLD": 3, "WATCH": 2, "AVOID": 1}
    out["decision_order"] = out["decision"].map(decision_map).fillna(0).astype(int)

    out = out[LATEST_RANKING_COLS].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date
    out = out.sort_values(["rank_overall", "ticker"], kind="mergesort").reset_index(drop=True)
    validate_latest_ranking_export_schema(out)
    return out


def main() -> None:
    # Visualization layer is additive after mart; it reshapes outputs for BI tools only.
    args = parse_args()
    if not args.historical_input_parquet.exists():
        raise FileNotFoundError(f"Historical input parquet not found: {args.historical_input_parquet}")
    if not args.ranking_input_parquet.exists():
        raise FileNotFoundError(f"Ranking input parquet not found: {args.ranking_input_parquet}")

    historical_df = pd.read_parquet(args.historical_input_parquet)
    ranking_df = pd.read_parquet(args.ranking_input_parquet)

    price_history_export = build_price_history_export(historical_df)
    latest_ranking_export = build_latest_ranking_export(ranking_df)

    args.price_history_output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.latest_ranking_output_csv.parent.mkdir(parents=True, exist_ok=True)

    price_history_export.to_csv(args.price_history_output_csv, index=False)
    latest_ranking_export.to_csv(args.latest_ranking_output_csv, index=False)

    print(f"Price history CSV written: {args.price_history_output_csv} (rows={len(price_history_export):,})")
    print(f"Latest ranking CSV written: {args.latest_ranking_output_csv} (rows={len(latest_ranking_export):,})")


if __name__ == "__main__":
    main()

