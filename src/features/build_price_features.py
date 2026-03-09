from __future__ import annotations

"""
Build universe-filtered price features for Finlify investment assets.

Pipeline:
raw prices -> normalize -> filter by universe source_ticker -> compute features -> write mart
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.price_utils import DEFAULT_RAW_PARQUET, iter_normalized_price_chunks, normalize_ticker


DEFAULT_UNIVERSE_CSV = Path("input/finlify_core_universe.csv")
DEFAULT_TICKER_MASTER = Path("data/staging/stock_price_stooq/ticker_master.parquet")
DEFAULT_OUTPUT_PARQUET = Path("data/mart/investment/factor_features.parquet")
DEFAULT_HISTORY_YEARS = 15


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build price factor features for the Finlify universe only.")
    parser.add_argument(
        "--input-parquet",
        type=Path,
        default=DEFAULT_RAW_PARQUET,
        help="Raw stock prices parquet path.",
    )
    parser.add_argument(
        "--ticker-master",
        type=Path,
        default=DEFAULT_TICKER_MASTER,
        help="Ticker master parquet path.",
    )
    parser.add_argument(
        "--universe-csv",
        type=Path,
        default=DEFAULT_UNIVERSE_CSV,
        help="Finlify core universe CSV path.",
    )
    parser.add_argument(
        "--output-parquet",
        type=Path,
        default=DEFAULT_OUTPUT_PARQUET,
        help="Output factor features parquet path.",
    )
    parser.add_argument(
        "--sample-csv",
        type=Path,
        default=None,
        help="Optional sample CSV output path.",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=500,
        help="Number of rows to write to sample CSV.",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Filter universe to active assets only (is_active=True).",
    )
    parser.add_argument(
        "--history-years",
        type=int,
        default=DEFAULT_HISTORY_YEARS,
        help="Limit each ticker history to this many years anchored at its latest date.",
    )
    return parser.parse_args()


def load_finlify_universe(universe_csv: Path, ticker_master_path: Path, active_only: bool = False) -> pd.DataFrame:
    """
    Build in-memory universe table:
    source_ticker, ticker, asset_type, source, is_active
    """
    if not universe_csv.exists():
        raise FileNotFoundError(f"Universe CSV not found: {universe_csv}")
    if not ticker_master_path.exists():
        raise FileNotFoundError(f"Ticker master parquet not found: {ticker_master_path}")

    universe_raw = pd.read_csv(universe_csv)
    required = {"symbol", "asset_type", "source"}
    missing = sorted(required - set(universe_raw.columns))
    if missing:
        raise ValueError(f"Universe CSV missing columns: {missing}")

    universe = universe_raw.copy()
    universe["ticker"] = (
        universe["symbol"]
        .astype("string")
        .str.strip()
        .str.upper()
        .map(normalize_ticker)
        .astype("string")
    )
    universe["asset_type"] = universe["asset_type"].astype("string").str.strip().str.lower()
    universe["source"] = universe["source"].astype("string").str.strip()
    universe = universe.dropna(subset=["ticker", "asset_type", "source"]).copy()

    dup_conflict = (
        universe.groupby("ticker", dropna=False)[["asset_type", "source"]]
        .nunique()
        .reset_index()
    )
    conflict_rows = dup_conflict[(dup_conflict["asset_type"] > 1) | (dup_conflict["source"] > 1)]
    if not conflict_rows.empty:
        sample = conflict_rows.head(5)["ticker"].tolist()
        raise ValueError(f"Universe has conflicting metadata for duplicate tickers, sample={sample}")

    universe = universe[["ticker", "asset_type", "source"]].drop_duplicates(subset=["ticker"], keep="first")

    ticker_master = pd.read_parquet(ticker_master_path, columns=["source_ticker", "ticker", "is_active"])
    ticker_master["ticker"] = ticker_master["ticker"].astype("string")

    joined = universe.merge(ticker_master, on="ticker", how="inner", validate="one_to_many")
    joined = joined[["source_ticker", "ticker", "asset_type", "source", "is_active"]].drop_duplicates(
        subset=["source_ticker"], keep="first"
    )
    joined["is_active"] = joined["is_active"].astype(bool)

    if active_only:
        joined = joined[joined["is_active"]].copy()

    if joined.empty:
        raise ValueError("Universe join returned zero tickers after applying filters.")

    return joined.sort_values(["ticker", "source_ticker"]).reset_index(drop=True)


def _compute_price_features_single_ticker(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute rolling and return features for one source_ticker.
    """
    out = df.sort_values("date").copy()
    close = out["close"].astype(float)
    out["ret_1d"] = close / close.shift(1) - 1.0
    out["ret_20d"] = close / close.shift(20) - 1.0
    out["ret_60d"] = close / close.shift(60) - 1.0
    out["ret_120d"] = close / close.shift(120) - 1.0
    out["ret_252d"] = close / close.shift(252) - 1.0

    out["ma_20"] = close.rolling(20, min_periods=20).mean()
    out["ma_50"] = close.rolling(50, min_periods=50).mean()
    out["ma_200"] = close.rolling(200, min_periods=200).mean()

    out["volatility_20d"] = out["ret_1d"].rolling(20, min_periods=20).std()
    out["volatility_60d"] = out["ret_1d"].rolling(60, min_periods=60).std()

    out["rolling_high_252d"] = close.rolling(252, min_periods=252).max()
    out["rolling_low_252d"] = close.rolling(252, min_periods=252).min()

    out["dist_from_52w_high"] = close / out["rolling_high_252d"] - 1.0
    out["dist_from_52w_low"] = close / out["rolling_low_252d"] - 1.0
    return out


def build_factor_features(
    input_parquet: Path,
    universe_df: pd.DataFrame,
    history_years: int = DEFAULT_HISTORY_YEARS,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Build row-level factor features for universe assets only.
    """
    if history_years <= 0:
        raise ValueError("history_years must be a positive integer.")

    universe_tickers = set(universe_df["source_ticker"].astype(str).tolist())
    if not universe_tickers:
        raise ValueError("Universe is empty.")

    per_ticker_chunks: dict[str, list[pd.DataFrame]] = {}
    for chunk in iter_normalized_price_chunks(input_parquet):
        filtered = chunk[chunk["source_ticker"].isin(universe_tickers)][
            ["source_ticker", "ticker", "date", "close", "volume"]
        ]
        if filtered.empty:
            continue

        filtered = filtered.sort_values(["source_ticker", "date"])
        for source_ticker, g in filtered.groupby("source_ticker", dropna=False):
            key = str(source_ticker)
            per_ticker_chunks.setdefault(key, []).append(g.copy())

    if not per_ticker_chunks:
        raise ValueError("No universe price rows found in raw parquet.")

    universe_meta = universe_df.set_index("source_ticker")[["ticker", "asset_type", "source", "is_active"]]

    results: list[pd.DataFrame] = []
    expected_counts: dict[str, int] = {}

    for source_ticker, meta_row in universe_meta.iterrows():
        parts = per_ticker_chunks.get(str(source_ticker), [])
        if not parts:
            continue
        prices = pd.concat(parts, ignore_index=True)
        prices = prices.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)

        latest_date = prices["date"].max()
        cutoff_date = latest_date - pd.DateOffset(years=history_years)
        prices = prices[prices["date"] >= cutoff_date].reset_index(drop=True)

        if prices.empty:
            continue
        expected_counts[str(source_ticker)] = len(prices)

        feats = _compute_price_features_single_ticker(prices)
        feats["source_ticker"] = str(source_ticker)
        feats["ticker"] = str(meta_row["ticker"])
        feats["asset_type"] = str(meta_row["asset_type"])
        feats["source"] = str(meta_row["source"])
        feats["is_active"] = bool(meta_row["is_active"])
        results.append(feats)

    if not results:
        raise ValueError("Feature computation produced zero rows.")

    out = pd.concat(results, ignore_index=True)
    out = out[
        [
            "source_ticker",
            "ticker",
            "asset_type",
            "date",
            "close",
            "volume",
            "ret_1d",
            "ret_20d",
            "ret_60d",
            "ret_120d",
            "ret_252d",
            "ma_20",
            "ma_50",
            "ma_200",
            "volatility_20d",
            "volatility_60d",
            "rolling_high_252d",
            "rolling_low_252d",
            "dist_from_52w_high",
            "dist_from_52w_low",
            "is_active",
            "source",
        ]
    ].sort_values(["ticker", "source_ticker", "date"]).reset_index(drop=True)
    return out, expected_counts


def build_representative_sample(factor_df: pd.DataFrame, sample_rows: int) -> pd.DataFrame:
    """
    Build a deterministic sample that covers all tickers and spans the time range.
    """
    if sample_rows <= 0:
        return factor_df.head(0).copy()
    if sample_rows >= len(factor_df):
        return factor_df.copy()

    work = factor_df.copy()
    work = work.sort_values(["date", "ticker", "source_ticker"], kind="mergesort").reset_index(drop=False)
    work = work.rename(columns={"index": "_row_id"})

    latest_per_ticker = (
        work.sort_values(["source_ticker", "date", "ticker"], kind="mergesort")
        .drop_duplicates(subset=["source_ticker"], keep="last")
    )

    selected = latest_per_ticker
    selected_ids = set(selected["_row_id"].tolist())

    remaining_rows = sample_rows - len(selected)
    if remaining_rows > 0:
        pool = work[~work["_row_id"].isin(selected_ids)].copy()
        if not pool.empty:
            extra_n = min(remaining_rows, len(pool))
            positions = np.linspace(0, len(pool) - 1, num=extra_n, dtype=int)
            extra = pool.iloc[positions]
            selected = pd.concat([selected, extra], ignore_index=True)

    selected = (
        selected.drop_duplicates(subset=["_row_id"], keep="first")
        .sort_values(["date", "ticker", "source_ticker"], kind="mergesort")
        .head(sample_rows)
        .drop(columns=["_row_id"])
        .reset_index(drop=True)
    )
    return selected


def validate_factor_features(factor_df: pd.DataFrame, universe_df: pd.DataFrame, expected_counts: dict[str, int]) -> None:
    """
    Validate universe filtering, ticker isolation, row-count consistency, and metadata joins.
    """
    universe_source_tickers = set(universe_df["source_ticker"].astype(str))
    output_source_tickers = set(factor_df["source_ticker"].astype(str))
    extra = sorted(output_source_tickers - universe_source_tickers)
    if extra:
        raise ValueError(f"Output contains non-universe source_ticker values, sample={extra[:5]}")

    ticker_per_source = factor_df.groupby("source_ticker")["ticker"].nunique()
    bad_ticker_groups = ticker_per_source[ticker_per_source > 1]
    if not bad_ticker_groups.empty:
        raise ValueError("Cross-ticker contamination detected: one source_ticker maps to multiple tickers.")

    actual_counts = factor_df.groupby("source_ticker", as_index=True).size().to_dict()
    mismatched_counts = [
        k for k, expected in expected_counts.items()
        if actual_counts.get(k, 0) != expected
    ]
    if mismatched_counts:
        raise ValueError(f"Row count mismatch for source_ticker sample={mismatched_counts[:5]}")

    expected_is_active = universe_df.set_index("source_ticker")["is_active"].astype(bool)
    merged = factor_df[["source_ticker", "is_active"]].drop_duplicates(subset=["source_ticker"])
    merged = merged.join(expected_is_active, on="source_ticker", rsuffix="_expected")
    bad_active = merged[merged["is_active"] != merged["is_active_expected"]]
    if not bad_active.empty:
        raise ValueError("is_active mismatch after join from ticker_master.")


def main() -> None:
    args = parse_args()
    universe = load_finlify_universe(
        universe_csv=args.universe_csv,
        ticker_master_path=args.ticker_master,
        active_only=args.active_only,
    )
    factor_df, expected_counts = build_factor_features(
        input_parquet=args.input_parquet,
        universe_df=universe,
        history_years=args.history_years,
    )
    validate_factor_features(factor_df, universe, expected_counts)

    args.output_parquet.parent.mkdir(parents=True, exist_ok=True)
    factor_df.to_parquet(args.output_parquet, index=False)
    print(f"Universe size: {len(universe):,}")
    print(f"Factor rows: {len(factor_df):,}")
    print(f"Parquet written: {args.output_parquet}")

    if args.sample_csv is not None:
        args.sample_csv.parent.mkdir(parents=True, exist_ok=True)
        sample_df = build_representative_sample(factor_df, sample_rows=max(0, args.sample_rows))
        sample_df.to_csv(args.sample_csv, index=False)
        print(f"Sample CSV written: {args.sample_csv} (rows={min(len(factor_df), max(0, args.sample_rows)):,})")


if __name__ == "__main__":
    main()
