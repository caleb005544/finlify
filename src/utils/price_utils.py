from __future__ import annotations

"""
Utilities for normalizing raw price data into a stable project schema.
"""

from pathlib import Path
from typing import Iterator

import pandas as pd
import pyarrow.parquet as pq


DEFAULT_RAW_PARQUET = Path("data/raw/stock_price_stooq/stock_prices.parquet")


def normalize_ticker(source_ticker: str) -> str:
    """
    Return a cleaned ticker symbol while preserving exchange suffix in source_ticker.

    Rule:
    - If ticker ends with '.US' (case-insensitive), strip that suffix.
    - Otherwise keep ticker unchanged.
    """
    if not isinstance(source_ticker, str):
        return source_ticker
    token = source_ticker.strip().upper()
    if token.endswith(".US"):
        return token[:-3]
    return token


def _choose_column(df: pd.DataFrame, candidates: list[str], required: bool = True) -> str | None:
    existing = {str(c).lower(): str(c) for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in existing:
            return existing[candidate.lower()]
    if required:
        raise ValueError(f"Missing required column. Tried: {candidates}")
    return None


def normalize_price_schema(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize raw price dataframe to a cleaned schema:
    source_ticker, ticker, date, open, high, low, close, volume
    """
    if raw_df.empty:
        raise ValueError("Input dataframe is empty.")

    source_col = _choose_column(raw_df, ["source_ticker", "symbol_raw", "ticker", "symbol"])
    date_col = _choose_column(raw_df, ["date", "payload_date", "datetime", "trade_date"])
    open_col = _choose_column(raw_df, ["open", "open_raw", "o"], required=False)
    high_col = _choose_column(raw_df, ["high", "high_raw", "h"], required=False)
    low_col = _choose_column(raw_df, ["low", "low_raw", "l"], required=False)
    close_col = _choose_column(raw_df, ["close", "close_raw", "c"])
    volume_col = _choose_column(raw_df, ["volume", "volume_raw", "vol", "v"], required=False)

    out = pd.DataFrame()
    out["source_ticker"] = raw_df[source_col].astype("string").str.strip().str.upper()
    out["ticker"] = out["source_ticker"].map(normalize_ticker).astype("string")
    out["date"] = pd.to_datetime(raw_df[date_col], errors="coerce")

    # Keep OHLCV fields if present so downstream can aggregate consistently.
    out["open"] = pd.to_numeric(raw_df[open_col], errors="coerce") if open_col else pd.Series(pd.NA, index=raw_df.index)
    out["high"] = pd.to_numeric(raw_df[high_col], errors="coerce") if high_col else pd.Series(pd.NA, index=raw_df.index)
    out["low"] = pd.to_numeric(raw_df[low_col], errors="coerce") if low_col else pd.Series(pd.NA, index=raw_df.index)
    out["close"] = pd.to_numeric(raw_df[close_col], errors="coerce")
    out["volume"] = (
        pd.to_numeric(raw_df[volume_col], errors="coerce") if volume_col else pd.Series(pd.NA, index=raw_df.index)
    )

    out = out.dropna(subset=["source_ticker", "ticker", "date"]).copy()
    if out.empty:
        raise ValueError("No valid rows after schema normalization.")

    return out


def iter_normalized_price_chunks(parquet_path: Path) -> Iterator[pd.DataFrame]:
    """
    Yield normalized price data one parquet row-group at a time.
    """
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

    pf = pq.ParquetFile(parquet_path)
    for rg in range(pf.metadata.num_row_groups):
        table = pf.read_row_group(rg)
        raw_chunk = table.to_pandas()
        try:
            normalized = normalize_price_schema(raw_chunk)
        except ValueError:
            # Skip empty/invalid chunks after normalization.
            continue
        if normalized.empty:
            continue
        yield normalized
