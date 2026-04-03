"""
Fetch EOD OHLCV data from Polygon.io and return DataFrames matching
the project's stock_prices.parquet schema.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

from src.utils.price_utils import normalize_ticker

load_dotenv()

_BASE = "https://api.polygon.io"


def _api_key() -> str:
    key = os.getenv("POLYGON_API_KEY")
    if not key:
        raise RuntimeError("POLYGON_API_KEY is not set. Add it to .env")
    return key


def _build_df(results: list[dict], date_col: str = "t") -> pd.DataFrame:
    """Convert raw Polygon results into the canonical schema."""
    if not results:
        return pd.DataFrame(
            columns=["source_ticker", "ticker", "date", "open", "high", "low", "close", "volume"]
        )

    rows = []
    for r in results:
        ticker_raw = r.get("T", "")
        source = f"{ticker_raw}.US"
        rows.append(
            {
                "source_ticker": source,
                "ticker": normalize_ticker(source),
                "date": r.get(date_col),
                "open": r.get("o"),
                "high": r.get("h"),
                "low": r.get("l"),
                "close": r.get("c"),
                "volume": r.get("v"),
            }
        )

    df = pd.DataFrame(rows)
    df["source_ticker"] = df["source_ticker"].astype("string")
    df["ticker"] = df["ticker"].astype("string")
    df["date"] = pd.to_datetime(df["date"], unit="ms", errors="coerce")
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    return df[["source_ticker", "ticker", "date", "open", "high", "low", "close", "volume"]]


def fetch_grouped_daily(
    trade_date: date | str,
    tickers: list[str] | None = None,
) -> pd.DataFrame:
    """
    Fetch all US stock EOD bars for *trade_date* via the Grouped Daily endpoint.
    Optionally filter to a list of tickers.
    """
    if isinstance(trade_date, str):
        trade_date = date.fromisoformat(trade_date)

    url = f"{_BASE}/v2/aggs/grouped/locale/us/market/stocks/{trade_date.isoformat()}"
    resp = requests.get(url, params={"apiKey": _api_key()}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Polygon grouped-daily returned {resp.status_code}: {resp.text}")

    data = resp.json()
    results = data.get("results", [])

    if tickers:
        upper = {t.upper() for t in tickers}
        results = [r for r in results if r.get("T", "").upper() in upper]

    df = _build_df(results)
    # Override date from the endpoint parameter (Grouped Daily returns timestamp
    # at midnight which may drift; canonical date is the one we requested).
    if not df.empty:
        df["date"] = pd.Timestamp(trade_date)

    return df


def fetch_ticker_range(
    ticker: str,
    start: date | str,
    end: date | str,
) -> pd.DataFrame:
    """
    Backfill a date range for a single ticker via the Aggregates endpoint.
    """
    if isinstance(start, str):
        start = date.fromisoformat(start)
    if isinstance(end, str):
        end = date.fromisoformat(end)

    url = (
        f"{_BASE}/v2/aggs/ticker/{ticker.upper()}/range/1/day"
        f"/{start.isoformat()}/{end.isoformat()}"
    )
    resp = requests.get(url, params={"apiKey": _api_key(), "limit": 5000}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Polygon aggregates returned {resp.status_code}: {resp.text}")

    data = resp.json()
    results = data.get("results", [])

    # Aggregates endpoint doesn't include "T" in each result — inject it.
    for r in results:
        r["T"] = ticker.upper()

    df = _build_df(results)
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Inline test suite
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from datetime import datetime

    summary: dict[str, str] = {}

    # ------ TEST 1: API key loading ------
    print("=" * 60)
    print("TEST 1 — API key loading")
    print("=" * 60)
    try:
        key = _api_key()
        assert key, "API key is empty"
        print(f"API key loaded: OK (first 4 chars: {key[:4]}...)")
        summary["TEST 1"] = "PASS"
    except Exception as e:
        print(f"FAIL: {e}")
        summary["TEST 1"] = "FAIL"

    # ------ TEST 2: Grouped Daily fetch ------
    print("\n" + "=" * 60)
    print("TEST 2 — Grouped Daily fetch")
    print("=" * 60)
    try:
        target_tickers = ["AAPL", "MSFT", "NVDA", "PLTR", "SPY"]
        # Start from yesterday (free-tier can't fetch today before EOD)
        for offset in range(1, 7):
            try_date = date.today() - timedelta(days=offset)
            df_grouped = fetch_grouped_daily(try_date, tickers=target_tickers)
            if not df_grouped.empty:
                print(f"Using trade date: {try_date}")
                break
        else:
            raise RuntimeError("No data found in the last 5 days")

        print(df_grouped.head(10).to_string(index=False))
        print(f"\nShape: {df_grouped.shape}")

        found = set(df_grouped["ticker"].unique())
        missing = set(target_tickers) - found
        assert not missing, f"Missing tickers: {missing}"
        assert df_grouped["close"].notna().all(), "Null values in close column"
        assert pd.api.types.is_datetime64_any_dtype(df_grouped["date"]), "date is not datetime"
        assert df_grouped["source_ticker"].str.endswith(".US").all(), "source_ticker must end with .US"
        print("\nAll assertions passed.")
        summary["TEST 2"] = "PASS"
    except Exception as e:
        print(f"FAIL: {e}")
        summary["TEST 2"] = "FAIL"

    # ------ TEST 3: Schema match against existing parquet ------
    print("\n" + "=" * 60)
    print("TEST 3 — Schema match against existing parquet")
    print("=" * 60)
    try:
        parquet_path = "data/mart/investment/factor_features.parquet"
        df_parquet = pd.read_parquet(parquet_path).head(5)
        overlap = ["date", "open", "high", "low", "close", "volume"]
        present = [c for c in overlap if c in df_parquet.columns]

        # Use df_grouped if available from TEST 2, otherwise fetch fresh
        if "df_grouped" not in dir() or df_grouped is None or df_grouped.empty:
            df_schema_ref = fetch_ticker_range("AAPL", "2026-03-01", "2026-03-05")
        else:
            df_schema_ref = df_grouped

        print(f"{'Column':<12} {'Polygon dtype':<20} {'Parquet dtype':<20} {'Match'}")
        print("-" * 64)
        all_ok = True
        for col in present:
            poly_dtype = df_schema_ref[col].dtype
            parq_dtype = df_parquet[col].dtype
            match = (
                pd.api.types.is_datetime64_any_dtype(poly_dtype)
                and pd.api.types.is_datetime64_any_dtype(parq_dtype)
            ) if col == "date" else (
                pd.api.types.is_float_dtype(poly_dtype)
                and pd.api.types.is_float_dtype(parq_dtype)
            )
            flag = "OK" if match else "MISMATCH"
            if not match:
                all_ok = False
            print(f"{col:<12} {str(poly_dtype):<20} {str(parq_dtype):<20} {flag}")

        assert all_ok, "Dtype mismatch detected"
        print("\nAll dtypes compatible.")
        summary["TEST 3"] = "PASS"
    except Exception as e:
        print(f"FAIL: {e}")
        summary["TEST 3"] = "FAIL"

    # ------ TEST 4: Single ticker backfill ------
    print("\n" + "=" * 60)
    print("TEST 4 — Single ticker backfill (AAPL, 2026-03)")
    print("=" * 60)
    try:
        df_backfill = fetch_ticker_range("AAPL", "2026-03-01", "2026-03-31")
        n = len(df_backfill)
        print(f"Rows: {n}")
        print(f"Date range: {df_backfill['date'].min().date()} → {df_backfill['date'].max().date()}")
        print(df_backfill.head().to_string(index=False))

        assert 15 <= n <= 25, f"Expected ~21 trading days, got {n}"
        assert df_backfill["close"].notna().all(), "Null values in close"
        assert df_backfill["date"].is_monotonic_increasing, "Dates not sorted ascending"
        print("\nAll assertions passed.")
        summary["TEST 4"] = "PASS"
    except Exception as e:
        print(f"FAIL: {e}")
        summary["TEST 4"] = "FAIL"

    # ------ Summary ------
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test, result in summary.items():
        print(f"  {test}: {result}")
    print()
