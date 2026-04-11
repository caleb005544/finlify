"""
Daily incremental ingest: fetch EOD prices for the full universe via
Polygon.io Grouped Daily endpoint (single API call) and append to the
raw parquet layer.

Usage:
    python -m src.ingestion.ingest_polygon            # auto-detect latest missing date
    python -m src.ingestion.ingest_polygon --date 2026-04-03  # force a specific date
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import psycopg2
from psycopg2.extras import execute_values

from src.ingestion.fetch_polygon import fetch_grouped_daily

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
UNIVERSE_CSV = Path("input/finlify_core_universe.csv")
PARQUET_PATH = Path("data/raw/stock_price_stooq/stock_prices.parquet")
SOURCE_SYSTEM = "polygon_daily"


def _build_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"daily_{ts}_{uuid.uuid4().hex[:8]}"


def _load_universe() -> list[str]:
    df = pd.read_csv(UNIVERSE_CSV)
    return sorted(set(df["symbol"].str.strip().str.upper()))


def _global_max_date(parquet_path: Path, universe_symbols: set[str]) -> date | None:
    """Max payload_date across universe tickers only, streaming row groups."""
    pf = pq.ParquetFile(parquet_path)
    global_max: date | None = None
    for rg in range(pf.metadata.num_row_groups):
        chunk = pf.read_row_group(rg, columns=["symbol_raw", "payload_date"]).to_pandas()
        chunk = chunk[chunk["symbol_raw"].isin(universe_symbols)]
        if chunk.empty:
            continue
        chunk["payload_date"] = pd.to_datetime(chunk["payload_date"], errors="coerce")
        rg_max = chunk["payload_date"].max()
        if pd.notna(rg_max):
            rg_date = rg_max.date() if hasattr(rg_max, "date") else rg_max
            if global_max is None or rg_date > global_max:
                global_max = rg_date
        del chunk
    return global_max


def _polygon_to_raw_schema(
    poly_df: pd.DataFrame,
    run_id: str,
    ingested_at: datetime,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_system": SOURCE_SYSTEM,
            "ingestion_run_id": run_id,
            "ingested_at": ingested_at,
            "symbol_raw": poly_df["source_ticker"],
            "payload_date": poly_df["date"].dt.date,
            "open_raw": poly_df["open"].astype(float),
            "high_raw": poly_df["high"].astype(float),
            "low_raw": poly_df["low"].astype(float),
            "close_raw": poly_df["close"].astype(float),
            "volume_raw": poly_df["volume"].astype(float),
        }
    )


def _streaming_append(parquet_path: Path, new_table: pa.Table) -> None:
    """Append new_table to an existing parquet file via temp-file streaming."""
    pf = pq.ParquetFile(parquet_path)
    existing_schema = pf.schema_arrow
    new_table = new_table.cast(existing_schema)

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=parquet_path.parent, suffix=".parquet.tmp"
    )
    try:
        os.close(tmp_fd)
        shutil.copy2(parquet_path, tmp_path)

        src_pf = pq.ParquetFile(tmp_path)
        writer = pq.ParquetWriter(str(parquet_path), existing_schema, compression="snappy")
        try:
            for rg in range(src_pf.metadata.num_row_groups):
                writer.write_table(src_pf.read_row_group(rg))
            writer.write_table(new_table)
        except Exception:
            writer.close()
            shutil.copy2(tmp_path, parquet_path)
            raise
        else:
            writer.close()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _upsert_to_supabase(raw_df: pd.DataFrame) -> int | None:
    """Upsert raw_df rows into Supabase stock_prices. Returns inserted count or None if skipped."""
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("  WARNING: SUPABASE_DB_URL not set — skipping Supabase upsert")
        return None

    out = pd.DataFrame(
        {
            "source_ticker": raw_df["symbol_raw"],
            "ticker": raw_df["symbol_raw"].str.replace(r"\.\w+$", "", regex=True),
            "date": raw_df["payload_date"],
            "open": raw_df["open_raw"],
            "high": raw_df["high_raw"],
            "low": raw_df["low_raw"],
            "close": raw_df["close_raw"],
            "volume": raw_df["volume_raw"],
            "source_system": raw_df["source_system"],
            "ingested_at": raw_df["ingested_at"],
        }
    )

    sql = """
        INSERT INTO stock_prices
            (source_ticker, ticker, date, open, high, low, close, volume, source_system, ingested_at)
        VALUES %s
        ON CONFLICT (source_ticker, date) DO NOTHING
    """
    conn = psycopg2.connect(db_url)
    try:
        rows = list(out.itertuples(index=False, name=None))
        with conn.cursor() as cur:
            execute_values(cur, sql, rows, page_size=1000)
            inserted = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily Polygon.io ingest")
    parser.add_argument("--date", type=str, default=None, help="Override target date (YYYY-MM-DD)")
    args = parser.parse_args()

    run_id = _build_run_id()
    ingested_at = datetime.now(timezone.utc)

    # 1. Load universe
    tickers = _load_universe()
    universe_symbols = {f"{t}.US" for t in tickers}
    print(f"Universe: {len(tickers)} tickers")

    # 2. Find global max date in parquet (universe only)
    print("Reading existing parquet max date...")
    old_pf = pq.ParquetFile(PARQUET_PATH)
    old_row_count = old_pf.metadata.num_rows
    max_existing = _global_max_date(PARQUET_PATH, universe_symbols)
    print(f"  Existing rows:  {old_row_count:,}")
    print(f"  Max date:       {max_existing}")

    # 3. Determine target date
    if args.date:
        target_date = date.fromisoformat(args.date)
    else:
        today = date.today()
        if max_existing and max_existing >= today:
            print(f"\nAlready up to date (max date {max_existing} >= today {today}).")
            return
        # Walk backwards from today to find the next date to ingest
        target_date = today

    if max_existing and target_date <= max_existing:
        print(f"\nAlready up to date (max date {max_existing} >= target {target_date}).")
        return

    print(f"\nTarget date: {target_date}")
    print(f"Run ID:      {run_id}")

    # 4. Fetch — single API call for all tickers
    print("Fetching grouped daily data...")
    try:
        df = fetch_grouped_daily(target_date, tickers=tickers)
    except RuntimeError as e:
        if "403" in str(e) or "NOT_AUTHORIZED" in str(e):
            print(f"  API rejected {target_date} (free-tier may not have data for this date yet).")
            df = pd.DataFrame()
        else:
            raise

    if df.empty:
        # Market may have been closed — walk back up to 5 days
        if not args.date:
            for offset in range(1, 6):
                try_date = date.today() - timedelta(days=offset)
                if max_existing and try_date <= max_existing:
                    break
                print(f"  No data for {target_date}, trying {try_date}...")
                df = fetch_grouped_daily(try_date, tickers=tickers)
                if not df.empty:
                    target_date = try_date
                    break
        if df.empty:
            print("No data returned. Market may be closed.")
            return

    # 5. Normalize date
    df["date"] = pd.to_datetime(df["date"].dt.date)

    print(f"  Received {len(df)} rows for {df['ticker'].nunique()} tickers")

    # Convert to raw schema
    raw_df = _polygon_to_raw_schema(df, run_id, ingested_at)

    # 6. Dedup check (lightweight — single date)
    target_str = str(target_date)
    existing_keys: set[str] = set()
    pf = pq.ParquetFile(PARQUET_PATH)
    for rg in range(pf.metadata.num_row_groups):
        chunk = pf.read_row_group(rg, columns=["symbol_raw", "payload_date"]).to_pandas()
        chunk = chunk[chunk["symbol_raw"].isin(universe_symbols)]
        chunk["payload_date"] = chunk["payload_date"].astype(str)
        chunk = chunk[chunk["payload_date"] == target_str]
        if not chunk.empty:
            existing_keys.update(chunk["symbol_raw"])
        del chunk

    if existing_keys:
        before = len(raw_df)
        raw_df = raw_df[~raw_df["symbol_raw"].isin(existing_keys)]
        print(f"  Removed {before - len(raw_df)} duplicates")

    if raw_df.empty:
        print("All rows already exist. Nothing to append.")
        return

    # 7. Append
    print(f"Appending {len(raw_df):,} rows...")
    new_table = pa.Table.from_pandas(raw_df, preserve_index=False)
    _streaming_append(PARQUET_PATH, new_table)

    # 7b. Upsert to Supabase
    print("Upserting to Supabase...")
    sb_inserted = _upsert_to_supabase(raw_df)
    if sb_inserted is not None:
        print(f"  Supabase: {sb_inserted} inserted, {len(raw_df) - sb_inserted} skipped (already existed)")

    # 8. Summary
    final_pf = pq.ParquetFile(PARQUET_PATH)
    final_row_count = final_pf.metadata.num_rows

    print("\n" + "=" * 60)
    print("DAILY INGEST SUMMARY")
    print("=" * 60)
    print(f"  Run ID:            {run_id}")
    print(f"  Target date:       {target_date}")
    print(f"  Tickers updated:   {raw_df['symbol_raw'].nunique()}")
    print(f"  Rows appended:     {len(raw_df):,}")
    print(f"  Old parquet rows:  {old_row_count:,}")
    print(f"  New parquet rows:  {final_row_count:,}")
    print("=" * 60)


if __name__ == "__main__":
    main()
