"""
Backfill: fetch historical price data for a date range via Polygon.io API.

Writes new rows into the same raw schema used by initial_ingest.py:
  source_system, ingestion_run_id, ingested_at, symbol_raw, payload_date,
  open_raw, high_raw, low_raw, close_raw, volume_raw

Usage examples:
  # Backfill new tickers only (auto-detect start from parquet max_date + 1)
  python -m src.ingestion.backfill_polygon --tickers JOBY,NBIS,PLTR

  # Backfill with explicit date range
  python -m src.ingestion.backfill_polygon --tickers PLTR --since 2024-04-04 --end 2026-04-10

  # Backfill full universe up to yesterday
  python -m src.ingestion.backfill_polygon
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import psycopg2
import pyarrow as pa
import pyarrow.parquet as pq
from psycopg2.extras import execute_values

from src.ingestion.fetch_polygon import fetch_ticker_range

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
UNIVERSE_CSV = Path("input/finlify_core_universe.csv")
PARQUET_PATH = Path("data/raw/stock_price_stooq/stock_prices.parquet")
RATE_LIMIT_SECONDS = 12
SOURCE_SYSTEM = "polygon_backfill"


def _build_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"backfill_{ts}_{uuid.uuid4().hex[:8]}"


def _load_universe() -> list[str]:
    df = pd.read_csv(UNIVERSE_CSV)
    tickers = df["symbol"].str.strip().str.upper().tolist()
    return sorted(set(tickers))


def _max_dates_per_ticker(parquet_path: Path) -> dict[str, date]:
    """Read only the columns we need and compute max payload_date per symbol."""
    pf = pq.ParquetFile(parquet_path)
    table = pf.read(columns=["symbol_raw", "payload_date"])
    df = table.to_pandas()
    df["payload_date"] = pd.to_datetime(df["payload_date"], errors="coerce")
    max_dates = df.groupby("symbol_raw")["payload_date"].max()
    return {ticker: d.date() for ticker, d in max_dates.items() if pd.notna(d)}


def _polygon_to_raw_schema(
    poly_df: pd.DataFrame,
    run_id: str,
    ingested_at: datetime,
) -> pd.DataFrame:
    """Convert fetch_polygon output to the raw parquet schema."""
    raw = pd.DataFrame(
        {
            "source_system": SOURCE_SYSTEM,
            "ingestion_run_id": run_id,
            "ingested_at": ingested_at,
            "symbol_raw": poly_df["source_ticker"],  # e.g. "AAPL.US"
            "payload_date": poly_df["date"].dt.date,
            "open_raw": poly_df["open"].astype(float),
            "high_raw": poly_df["high"].astype(float),
            "low_raw": poly_df["low"].astype(float),
            "close_raw": poly_df["close"].astype(float),
            "volume_raw": poly_df["volume"].astype(float),
        }
    )
    return raw


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
    parser = argparse.ArgumentParser(description="Backfill Polygon.io price data into raw parquet + Supabase")
    parser.add_argument("--tickers", type=str, default=None, help="Comma-separated tickers to backfill (default: full universe)")
    parser.add_argument("--since", type=str, default=None, help="Start date YYYY-MM-DD (default: parquet max_date + 1 per ticker)")
    parser.add_argument("--end", type=str, default=None, help="End date YYYY-MM-DD (default: yesterday)")
    args = parser.parse_args()

    end_date = date.fromisoformat(args.end) if args.end else date.today() - timedelta(days=1)
    since_date = date.fromisoformat(args.since) if args.since else None

    run_id = _build_run_id()
    ingested_at = datetime.now(timezone.utc)

    print(f"Backfill run: {run_id}")
    print(f"Target end date: {end_date}")
    print()

    # 1. Load universe / ticker list
    if args.tickers:
        tickers = sorted(set(t.strip().upper() for t in args.tickers.split(",")))
        print(f"Tickers (from --tickers): {', '.join(tickers)}")
    else:
        tickers = _load_universe()
        print(f"Universe: {len(tickers)} tickers from {UNIVERSE_CSV}")

    # 2. Read existing max dates (symbol_raw has .US suffix)
    print("Reading existing parquet max dates...")
    old_pf = pq.ParquetFile(PARQUET_PATH)
    old_row_count = old_pf.metadata.num_rows
    max_dates = _max_dates_per_ticker(PARQUET_PATH)
    print(f"Existing parquet: {old_row_count:,} rows\n")

    # 3. Fetch per ticker
    all_new: list[pd.DataFrame] = []
    zero_rows: list[str] = []
    failed: list[tuple[str, str]] = []
    total = len(tickers)

    for i, ticker in enumerate(tickers, 1):
        symbol_raw = f"{ticker}.US"
        existing_max = max_dates.get(symbol_raw)

        if existing_max and existing_max >= end_date:
            print(f"[{i:>3}/{total}] {ticker} — already up to date ({existing_max}), skipping")
            continue

        if since_date:
            start = since_date
        else:
            start = (existing_max + timedelta(days=1)) if existing_max else date(2020, 1, 1)
        print(f"[{i:>3}/{total}] {ticker} — fetching {start} to {end_date}...")

        try:
            # Polygon uses dots not hyphens for share classes (BRK.B not BRK-B)
            poly_ticker = ticker.replace("-", ".")
            df = fetch_ticker_range(poly_ticker, start, end_date)

            # Normalize date: strip time component, cast to datetime64[ns]
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"].dt.date)
                # Restore original ticker convention for source_ticker
                df["source_ticker"] = ticker.upper() + ".US"
                df["ticker"] = ticker.upper()

            if df.empty:
                zero_rows.append(ticker)
                print(f"[{i:>3}/{total}] {ticker} — 0 rows fetched")
            else:
                raw = _polygon_to_raw_schema(df, run_id, ingested_at)
                all_new.append(raw)
                print(f"[{i:>3}/{total}] {ticker} — {len(raw)} rows fetched")
        except Exception as e:
            failed.append((ticker, str(e)))
            print(f"[{i:>3}/{total}] {ticker} — ERROR: {e}")

        # Rate limit (skip sleep after the last ticker)
        if i < total:
            time.sleep(RATE_LIMIT_SECONDS)

    # 4. Combine and validate
    if not all_new:
        print("\nNo new rows to append. Done.")
        return

    new_df = pd.concat(all_new, ignore_index=True)
    print(f"\nTotal new rows collected: {len(new_df):,}")

    # Dedup check: only load the two key columns, use vectorized set ops
    print("Checking for duplicates against existing parquet...")
    pf = pq.ParquetFile(PARQUET_PATH)
    existing_schema = pf.schema_arrow

    # Only check the ~90 symbols we're inserting — skip the vast majority of
    # the 27M rows.  Stream row-groups so memory stays low.
    new_symbols = set(new_df["symbol_raw"].unique())
    new_dates_min = str(new_df["payload_date"].min())
    existing_keys: set[tuple[str, str]] = set()
    for rg in range(pf.metadata.num_row_groups):
        chunk = pf.read_row_group(rg, columns=["symbol_raw", "payload_date"]).to_pandas()
        chunk = chunk[chunk["symbol_raw"].isin(new_symbols)]
        chunk["payload_date"] = chunk["payload_date"].astype(str)
        chunk = chunk[chunk["payload_date"] >= new_dates_min]
        if not chunk.empty:
            existing_keys.update(zip(chunk["symbol_raw"], chunk["payload_date"]))
        del chunk

    new_df["_date_str"] = new_df["payload_date"].astype(str)
    dupe_mask = [
        (sym, d) in existing_keys
        for sym, d in zip(new_df["symbol_raw"], new_df["_date_str"])
    ]
    n_dupes = sum(dupe_mask)
    if n_dupes:
        print(f"WARNING: {n_dupes} duplicate (symbol, date) pairs found — removing them")
        new_df = new_df[~pd.Series(dupe_mask, index=new_df.index)]
    new_df = new_df.drop(columns=["_date_str"])
    del existing_keys  # free memory

    if new_df.empty:
        print("All rows were duplicates. Nothing to append.")
        return

    # 5. Append to parquet — streaming, row-group-at-a-time via temp file
    print(f"Appending {len(new_df):,} rows to {PARQUET_PATH}...")
    new_table = pa.Table.from_pandas(new_df, preserve_index=False)
    new_table = new_table.cast(existing_schema)

    # Copy original to a temp file so we read from it while writing to a new file
    tmp_dir = PARQUET_PATH.parent
    tmp_fd, tmp_path = tempfile.mkstemp(dir=tmp_dir, suffix=".parquet.tmp")
    try:
        os.close(tmp_fd)
        shutil.copy2(PARQUET_PATH, tmp_path)

        src_pf = pq.ParquetFile(tmp_path)
        writer = pq.ParquetWriter(str(PARQUET_PATH), existing_schema, compression="snappy")
        try:
            # Stream existing row groups one at a time (never all in memory)
            for rg in range(src_pf.metadata.num_row_groups):
                writer.write_table(src_pf.read_row_group(rg))
            # Append new data
            writer.write_table(new_table)
        except Exception:
            writer.close()
            # Restore original on failure
            shutil.copy2(tmp_path, PARQUET_PATH)
            raise
        else:
            writer.close()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # 6. Upsert to Supabase
    print("Upserting to Supabase...")
    sb_inserted = _upsert_to_supabase(new_df)
    if sb_inserted is not None:
        print(f"  Supabase: {sb_inserted} inserted, {len(new_df) - sb_inserted} skipped (already existed)")

    # 7. Verify
    final_pf = pq.ParquetFile(PARQUET_PATH)
    final_row_count = final_pf.metadata.num_rows

    # ------ Summary ------
    print("\n" + "=" * 60)
    print("BACKFILL SUMMARY")
    print("=" * 60)
    print(f"  Run ID:              {run_id}")
    print(f"  End date:            {end_date}")
    print(f"  Tickers processed:   {total}")
    print(f"  Rows appended:       {len(new_df):,}")
    print(f"  Old parquet rows:    {old_row_count:,}")
    print(f"  New parquet rows:    {final_row_count:,}")
    if zero_rows:
        print(f"  Zero-row tickers:    {', '.join(zero_rows)}")
    if failed:
        print(f"  Failed tickers ({len(failed)}):")
        for t, err in failed:
            print(f"    {t}: {err}")
    print("=" * 60)


if __name__ == "__main__":
    main()
