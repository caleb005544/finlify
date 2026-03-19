from __future__ import annotations

"""
Build a lightweight signal snapshot CSV for heatmaps and dashboards.
"""

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_PARQUET = Path("data/mart/investment/top_ranked_assets.parquet")
DEFAULT_OUTPUT_CSV = Path("data/visualization/investment/signal_heatmap_snapshot.csv")

SIGNAL_HEATMAP_COLS = [
    "ticker",
    "asset_type",
    "decision",
    "confidence",
    "regime",
    "risk_level",
    "horizon_days",
    "composite_score",
    "rank_overall",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build signal heatmap snapshot CSV from ranked assets output.")
    parser.add_argument(
        "--input-parquet",
        type=Path,
        default=DEFAULT_INPUT_PARQUET,
        help="Input ranked assets parquet path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help="Output CSV path for signal heatmap snapshot.",
    )
    return parser.parse_args()


def validate_input_schema(df: pd.DataFrame) -> None:
    missing = sorted(set(SIGNAL_HEATMAP_COLS) - set(df.columns))
    if missing:
        raise ValueError(f"Ranking input missing required columns: {missing}")


def build_signal_heatmap_snapshot(ranking_df: pd.DataFrame) -> pd.DataFrame:
    validate_input_schema(ranking_df)
    out = ranking_df[SIGNAL_HEATMAP_COLS].copy()
    out = out.sort_values(["rank_overall", "ticker"], kind="mergesort").reset_index(drop=True)
    return out


def main() -> None:
    args = parse_args()
    if not args.input_parquet.exists():
        raise FileNotFoundError(f"Input parquet not found: {args.input_parquet}")

    ranking_df = pd.read_parquet(args.input_parquet)
    signal_snapshot = build_signal_heatmap_snapshot(ranking_df)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    signal_snapshot.to_csv(args.output_csv, index=False)

    print(f"Signal heatmap snapshot CSV written: {args.output_csv} (rows={len(signal_snapshot):,})")


if __name__ == "__main__":
    main()
