"""
scripts/load_historical_to_supabase.py

One-time historical load: migrates local parquet → Supabase stock_prices table.
Safe to re-run (uses ON CONFLICT DO NOTHING).

Usage:
    python scripts/load_historical_to_supabase.py                        # default: 2024-01-01 onwards
    python scripts/load_historical_to_supabase.py --since 2023-01-01     # custom start date
    python scripts/load_historical_to_supabase.py --dry-run              # show row count only
"""

import os
import argparse
import time
import pandas as pd
import pyarrow.parquet as pq
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

PARQUET_PATH = "data/raw/stock_price_stooq/stock_prices.parquet"
UNIVERSE_CSV = "input/finlify_core_universe.csv"
BATCH_SIZE = 10_000
DB_URL = os.environ["SUPABASE_DB_URL"]


def _load_universe() -> set[str]:
    """Return universe tickers in symbol_raw format (e.g. AAPL.US)."""
    df = pd.read_csv(UNIVERSE_CSV)
    tickers = df["symbol"].str.strip().str.upper()
    return {f"{t}.US" for t in tickers}


def transform_chunk(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw parquet columns → stock_prices table columns."""
    out = pd.DataFrame()
    out["source_ticker"] = df["symbol_raw"]
    out["ticker"] = df["symbol_raw"].str.replace(r"\.\w+$", "", regex=True)
    out["date"] = pd.to_datetime(df["payload_date"]).dt.date
    out["open"] = df["open_raw"]
    out["high"] = df["high_raw"]
    out["low"] = df["low_raw"]
    out["close"] = df["close_raw"]
    out["volume"] = df["volume_raw"]
    out["source_system"] = df["source_system"]
    out["ingested_at"] = df["ingested_at"]
    return out.dropna(subset=["source_ticker", "date"])


def load_to_supabase(conn, rows: list[tuple]) -> int:
    sql = """
        INSERT INTO stock_prices
            (source_ticker, ticker, date, open, high, low, close, volume, source_system, ingested_at)
        VALUES %s
        ON CONFLICT (source_ticker, date) DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=BATCH_SIZE)
        inserted = cur.rowcount
    conn.commit()
    return inserted


def count_filtered_rows(pf: pq.ParquetFile, since: str, universe: set[str]) -> int:
    total = 0
    for batch in pf.iter_batches(batch_size=50_000, columns=["payload_date", "symbol_raw"]):
        df = batch.to_pandas()
        dates = pd.to_datetime(df["payload_date"], errors="coerce")
        mask = (dates >= since) & (df["symbol_raw"].isin(universe))
        total += mask.sum()
    return total


def main(dry_run: bool = False, since: str = "2024-01-01"):
    universe = _load_universe()
    pf = pq.ParquetFile(PARQUET_PATH)
    total_parquet_rows = pf.metadata.num_rows

    print(f"Parquet total rows : {total_parquet_rows:,}")
    print(f"Universe tickers   : {len(universe)}")
    print(f"Loading since      : {since}")

    print("Counting filtered rows...")
    filtered_rows = count_filtered_rows(pf, since, universe)
    print(f"Rows to load       : {filtered_rows:,}")

    if dry_run:
        print("[dry-run] No data written.")
        return

    conn = psycopg2.connect(DB_URL)
    print("Connected to Supabase.\n")

    total_inserted = 0
    total_skipped = 0
    processed = 0
    t0 = time.time()

    for batch in pf.iter_batches(batch_size=BATCH_SIZE):
        df = batch.to_pandas()
        dates = pd.to_datetime(df["payload_date"], errors="coerce")
        df = df[(dates >= since) & (df["symbol_raw"].isin(universe))].copy()
        if df.empty:
            continue

        df = transform_chunk(df)
        rows = list(df.itertuples(index=False, name=None))
        inserted = load_to_supabase(conn, rows)
        skipped = len(rows) - inserted

        total_inserted += inserted
        total_skipped += skipped
        processed += len(rows)

        elapsed = time.time() - t0
        pct = processed / filtered_rows * 100 if filtered_rows > 0 else 0
        rps = processed / elapsed if elapsed > 0 else 0
        eta = (filtered_rows - processed) / rps if rps > 0 else 0
        print(
            f"  {processed:>8,} / {filtered_rows:,} ({pct:.1f}%)  "
            f"+{inserted} inserted  {skipped} skipped  "
            f"{rps:,.0f} rows/s  ETA {eta/60:.1f}min"
        )

    conn.close()
    elapsed = time.time() - t0
    print(f"\nDone. {total_inserted:,} inserted, {total_skipped:,} skipped.")
    print(f"Total time: {elapsed/60:.1f} min")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--since", default="2024-01-01", help="Load data from this date (YYYY-MM-DD)")
    args = parser.parse_args()
    main(dry_run=args.dry_run, since=args.since)
