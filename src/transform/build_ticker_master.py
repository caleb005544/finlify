from __future__ import annotations

"""
Build ticker master stats from raw Stooq parquet.

Outputs:
- data/staging/stock_price_stooq/ticker_master.parquet
- optional CSV mirror
"""

import argparse
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.utils.price_utils import DEFAULT_RAW_PARQUET, normalize_price_schema


DEFAULT_OUTPUT_PARQUET = Path("data/staging/stock_price_stooq/ticker_master.parquet")


def validate_input_columns(df: pd.DataFrame) -> None:
    required = {"source_ticker", "ticker", "date", "close", "volume"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing normalized columns: {missing}")


def inspect_parquet_schema(input_parquet: Path) -> tuple[int, int, list[tuple[str, str]]]:
    """
    Return basic parquet metadata for reporting.
    """
    pf = pq.ParquetFile(input_parquet)
    rows = pf.metadata.num_rows
    row_groups = pf.metadata.num_row_groups
    columns = []
    for i in range(pf.metadata.num_columns):
        col = pf.metadata.schema.column(i)
        columns.append((col.name, col.physical_type))
    return rows, row_groups, columns


def _update_stats_row(
    stats: dict[tuple[str, str], dict],
    key: tuple[str, str],
    min_date: pd.Timestamp,
    max_date: pd.Timestamp,
    row_count: int,
    non_null_close_count: int,
    non_null_volume_count: int,
    first_close: float | None,
    last_close: float | None,
) -> None:
    cur = stats.get(key)
    if cur is None:
        stats[key] = {
            "source_ticker": key[0],
            "ticker": key[1],
            "min_date": min_date,
            "max_date": max_date,
            "row_count": row_count,
            "non_null_close_count": non_null_close_count,
            "non_null_volume_count": non_null_volume_count,
            "first_close": first_close,
            "last_close": last_close,
        }
        return

    if min_date < cur["min_date"]:
        cur["min_date"] = min_date
        cur["first_close"] = first_close
    elif min_date == cur["min_date"] and cur["first_close"] is None and first_close is not None:
        cur["first_close"] = first_close
    if max_date > cur["max_date"]:
        cur["max_date"] = max_date
        cur["last_close"] = last_close
    elif max_date == cur["max_date"] and cur["last_close"] is None and last_close is not None:
        cur["last_close"] = last_close

    cur["row_count"] += row_count
    cur["non_null_close_count"] += non_null_close_count
    cur["non_null_volume_count"] += non_null_volume_count


def build_ticker_master_from_parquet(input_parquet: Path) -> pd.DataFrame:
    """
    Build ticker-level aggregates by scanning parquet row groups incrementally.
    """
    pf = pq.ParquetFile(input_parquet)
    stats: dict[tuple[str, str], dict] = {}
    dataset_max_date: pd.Timestamp | None = None

    for rg in range(pf.metadata.num_row_groups):
        table = pf.read_row_group(rg)
        raw_chunk = table.to_pandas()
        normalized = normalize_price_schema(raw_chunk)
        validate_input_columns(normalized)

        chunk = normalized.sort_values(["source_ticker", "date"]).copy()
        chunk_max = chunk["date"].max()
        if dataset_max_date is None or chunk_max > dataset_max_date:
            dataset_max_date = chunk_max

        grouped = chunk.groupby(["source_ticker", "ticker"], dropna=False)
        for (source_ticker, ticker), g in grouped:
            close_series = g["close"]
            volume_series = g["volume"]

            first_close = close_series.iloc[0] if len(close_series) else None
            last_close = close_series.iloc[-1] if len(close_series) else None
            if pd.isna(first_close):
                first_close = None
            if pd.isna(last_close):
                last_close = None

            _update_stats_row(
                stats=stats,
                key=(str(source_ticker), str(ticker)),
                min_date=g["date"].min(),
                max_date=g["date"].max(),
                row_count=int(len(g)),
                non_null_close_count=int(close_series.notna().sum()),
                non_null_volume_count=int(volume_series.notna().sum()),
                first_close=first_close,
                last_close=last_close,
            )

    if dataset_max_date is None:
        raise ValueError("Dataset appears empty after normalization.")

    out = pd.DataFrame(list(stats.values()))
    out["has_volume"] = out["non_null_volume_count"] > 0
    out["is_active"] = (dataset_max_date - out["max_date"]).dt.days <= 10
    out["source"] = "stooq"

    ordered_cols = [
        "source_ticker",
        "ticker",
        "min_date",
        "max_date",
        "row_count",
        "non_null_close_count",
        "non_null_volume_count",
        "first_close",
        "last_close",
        "is_active",
        "has_volume",
        "source",
    ]
    out = out[ordered_cols].sort_values(["ticker", "source_ticker"]).reset_index(drop=True)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ticker master dataset from raw stooq parquet.")
    parser.add_argument(
        "--input-parquet",
        type=Path,
        default=DEFAULT_RAW_PARQUET,
        help="Path to raw parquet file.",
    )
    parser.add_argument(
        "--output-parquet",
        type=Path,
        default=DEFAULT_OUTPUT_PARQUET,
        help="Destination parquet file path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional CSV output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input_parquet.exists():
        raise FileNotFoundError(f"Input parquet not found: {args.input_parquet}")

    rows, row_groups, columns = inspect_parquet_schema(args.input_parquet)
    print(f"Input parquet: {args.input_parquet}")
    print(f"Rows: {rows:,}")
    print(f"Row groups: {row_groups:,}")
    print("Columns:")
    for name, dtype in columns:
        print(f"  - {name}: {dtype}")

    ticker_master = build_ticker_master_from_parquet(args.input_parquet)

    args.output_parquet.parent.mkdir(parents=True, exist_ok=True)
    ticker_master.to_parquet(args.output_parquet, index=False)
    print(f"Ticker master parquet written: {args.output_parquet}")

    if args.output_csv is not None:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        ticker_master.to_csv(args.output_csv, index=False)
        print(f"Ticker master csv written: {args.output_csv}")

    print(f"Rows: {len(ticker_master):,}")
    print(f"Date range: {ticker_master['min_date'].min()} -> {ticker_master['max_date'].max()}")


if __name__ == "__main__":
    main()
