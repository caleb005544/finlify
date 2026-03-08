from __future__ import annotations

"""
Build latest factor snapshot: one most-recent row per source_ticker.
"""

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_PARQUET = Path("data/mart/investment/factor_features.parquet")
DEFAULT_OUTPUT_PARQUET = Path("data/mart/investment/factor_snapshot_latest.parquet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build latest factor snapshot from factor_features.")
    parser.add_argument(
        "--input-parquet",
        type=Path,
        default=DEFAULT_INPUT_PARQUET,
        help="Input factor_features parquet path.",
    )
    parser.add_argument(
        "--output-parquet",
        type=Path,
        default=DEFAULT_OUTPUT_PARQUET,
        help="Output factor_snapshot_latest parquet path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional CSV output path.",
    )
    return parser.parse_args()


def validate_input_schema(df: pd.DataFrame) -> None:
    required = {"source_ticker", "ticker", "date"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input factor_features missing required columns: {missing}")


def build_latest_snapshot(factor_features: pd.DataFrame) -> pd.DataFrame:
    """
    Keep exactly one latest row per source_ticker using deterministic ordering.
    """
    validate_input_schema(factor_features)

    if factor_features.empty:
        raise ValueError("Input factor_features is empty.")

    work = factor_features.copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work.dropna(subset=["source_ticker", "ticker", "date"]).copy()
    if work.empty:
        raise ValueError("No valid rows after basic date/ticker validation.")

    expected_universe_size = work["source_ticker"].nunique()

    # Deterministic: stable sort then keep the last row per source_ticker.
    latest = (
        work.sort_values(["source_ticker", "date", "ticker"], kind="mergesort")
        .drop_duplicates(subset=["source_ticker"], keep="last")
        .sort_values(["ticker", "source_ticker"], kind="mergesort")
        .reset_index(drop=True)
    )

    if latest["source_ticker"].duplicated().any():
        raise ValueError("Validation failed: duplicate source_ticker found in latest snapshot.")

    if latest["ticker"].duplicated().any():
        dup = latest.loc[latest["ticker"].duplicated(keep=False), "ticker"].head(5).tolist()
        raise ValueError(f"Validation failed: duplicate ticker found in latest snapshot, sample={dup}")

    if len(latest) != expected_universe_size:
        raise ValueError(
            f"Validation failed: latest row count {len(latest)} != universe size {expected_universe_size}."
        )

    max_dates = work.groupby("source_ticker", as_index=False)["date"].max().rename(columns={"date": "max_date"})
    check = latest[["source_ticker", "date"]].merge(max_dates, on="source_ticker", how="left", validate="one_to_one")
    mismatch = check[check["date"] != check["max_date"]]
    if not mismatch.empty:
        sample = mismatch.head(5).to_dict(orient="records")
        raise ValueError(f"Validation failed: snapshot date is not max date per ticker, sample={sample}")

    return latest


def main() -> None:
    args = parse_args()
    if not args.input_parquet.exists():
        raise FileNotFoundError(f"Input parquet not found: {args.input_parquet}")

    factor_features = pd.read_parquet(args.input_parquet)
    latest = build_latest_snapshot(factor_features)

    args.output_parquet.parent.mkdir(parents=True, exist_ok=True)
    latest.to_parquet(args.output_parquet, index=False)
    print(f"Latest snapshot parquet written: {args.output_parquet}")
    print(f"Rows: {len(latest):,}")

    if args.output_csv is not None:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        latest.to_csv(args.output_csv, index=False)
        print(f"Latest snapshot csv written: {args.output_csv}")


if __name__ == "__main__":
    main()

