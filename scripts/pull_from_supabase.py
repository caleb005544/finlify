"""
scripts/pull_from_supabase.py

Pull all rows from Supabase stock_prices table and rebuild the local
raw parquet file in the exact schema used by the pipeline.

Usage:
    python scripts/pull_from_supabase.py             # full rebuild
    python scripts/pull_from_supabase.py --dry-run   # show row count only
"""

import argparse
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv
import psycopg2

load_dotenv()

PARQUET_PATH = Path("data/raw/stock_price_stooq/stock_prices.parquet")
DB_URL = os.environ["SUPABASE_DB_URL"]

RAW_SCHEMA = pa.schema(
    [
        pa.field("source_system", pa.string()),
        pa.field("ingestion_run_id", pa.string()),
        pa.field("ingested_at", pa.timestamp("us", tz="UTC")),
        pa.field("symbol_raw", pa.string()),
        pa.field("payload_date", pa.string()),
        pa.field("open_raw", pa.float64()),
        pa.field("high_raw", pa.float64()),
        pa.field("low_raw", pa.float64()),
        pa.field("close_raw", pa.float64()),
        pa.field("volume_raw", pa.float64()),
    ]
)


def main(dry_run: bool = False):
    conn = psycopg2.connect(DB_URL)
    print("Connected to Supabase.")

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM stock_prices")
        total = cur.fetchone()[0]
    print(f"Rows in stock_prices: {total:,}")

    if dry_run:
        conn.close()
        print("[dry-run] No parquet written.")
        return

    t0 = time.time()
    print("Fetching all rows...")

    sql = """
        SELECT source_ticker, ticker, date, open, high, low, close,
               volume, source_system, ingested_at
        FROM stock_prices
        ORDER BY source_ticker, date
    """
    df = pd.read_sql(sql, conn)
    conn.close()
    print(f"  Fetched {len(df):,} rows in {time.time() - t0:.1f}s")

    # Map to raw parquet schema
    raw = pd.DataFrame(
        {
            "source_system": df["source_system"].astype("str"),
            "ingestion_run_id": "supabase_pull",
            "ingested_at": pd.to_datetime(df["ingested_at"], utc=True),
            "symbol_raw": df["source_ticker"].astype("str"),
            "payload_date": pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d"),
            "open_raw": df["open"].astype("float64"),
            "high_raw": df["high"].astype("float64"),
            "low_raw": df["low"].astype("float64"),
            "close_raw": df["close"].astype("float64"),
            "volume_raw": df["volume"].astype("float64"),
        }
    )

    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pandas(raw, schema=RAW_SCHEMA, preserve_index=False)
    pq.write_table(table, PARQUET_PATH, compression="snappy")

    elapsed = time.time() - t0
    final_pf = pq.ParquetFile(PARQUET_PATH)
    print(f"\nParquet written: {PARQUET_PATH}")
    print(f"  Rows: {final_pf.metadata.num_rows:,}")
    print(f"  Time: {elapsed:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show row count only")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
