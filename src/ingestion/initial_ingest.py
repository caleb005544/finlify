from __future__ import annotations

"""
Initial Ingest: Local Stooq TXT Dump -> Raw Parquet

Purpose:
- Bootstrap the raw stock price layer from a manually downloaded Stooq dataset.
- Standardize heterogeneous TXT files into one consistent raw schema used by downstream queries.

What this script does:
- Auto-detects an input folder under input/*/daily/us (or uses --input-root).
- Reads all TXT files recursively and validates required OHLCV fields.
- Converts rows into the project raw schema:
  source_system, ingestion_run_id, ingested_at, symbol_raw, payload_date,
  open_raw, high_raw, low_raw, close_raw, volume_raw.
- Writes one consolidated parquet file to data/raw/stock_price_stooq/stock_prices.parquet.
- Emits a failed-file log under data/raw/_failed_logs for auditability and retry.

Why this exists:
- API ingestion can fail due to rate limits or network issues.
- This script provides a deterministic, offline first-load path so the raw layer can be built reliably.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import uuid

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


INPUT_ROOT = Path("input/stock price/daily/us")
OUTPUT_DIR = Path("data/raw/stock_price_stooq")
FAILED_DIR = Path("data/raw/_failed_logs")
OUTPUT_FILE = OUTPUT_DIR / "stock_prices.parquet"
SOURCE_SYSTEM = "stooq_manual_dump"


def build_ingestion_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_id = uuid.uuid4().hex[:8]
    return f"initial_{ts}_{short_id}"


def list_price_files(input_root: Path) -> list[Path]:
    return sorted(
        p for p in input_root.rglob("*.txt")
        if p.is_file() and p.name != ".DS_Store"
    )


def discover_input_root(explicit_input_root: Path | None) -> Path:
    if explicit_input_root is not None:
        if explicit_input_root.exists():
            return explicit_input_root
        raise FileNotFoundError(f"--input-root not found: {explicit_input_root}")

    input_dir = Path("input")
    candidates: list[Path] = [
        INPUT_ROOT,
        Path("input/data 2/daily/us"),
    ]

    if input_dir.exists():
        for child in sorted(p for p in input_dir.iterdir() if p.is_dir()):
            candidate = child / "daily" / "us"
            candidates.append(candidate)

    # De-duplicate while preserving order.
    deduped: list[Path] = []
    seen: set[str] = set()
    for c in candidates:
        key = str(c.resolve()) if c.exists() else str(c)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    scored: list[tuple[int, Path]] = []
    for c in deduped:
        if not c.exists():
            continue
        txt_count = sum(1 for _ in c.rglob("*.txt"))
        if txt_count > 0:
            scored.append((txt_count, c))

    if not scored:
        available = "\n".join(f"- {p}" for p in deduped if p.exists()) or "- (none)"
        raise FileNotFoundError(
            "No input folder with .txt price files found under input/*/daily/us.\n"
            f"Existing candidates:\n{available}"
        )

    # Pick the richest folder in case multiple exist.
    scored.sort(key=lambda x: x[0], reverse=True)
    chosen_count, chosen_root = scored[0]
    print(f"Auto-detected input root: {chosen_root} ({chosen_count:,} txt files)")
    return chosen_root


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().strip("<>").lower() for c in df.columns]
    return df


def parse_txt_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = normalize_columns(df)

    required = {"ticker", "date", "open", "high", "low", "close", "vol"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")

    if "per" in df.columns:
        df = df[df["per"].astype(str).str.upper() == "D"].copy()

    if df.empty:
        raise ValueError("no daily rows in file")

    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d", errors="coerce")
    df["open"] = pd.to_numeric(df["open"], errors="coerce")
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["vol"] = pd.to_numeric(df["vol"], errors="coerce")

    df = df.dropna(subset=["ticker", "date", "open", "high", "low", "close", "vol"]).copy()
    if df.empty:
        raise ValueError("no valid rows after type conversion")

    return df


def to_raw_schema(
    parsed_df: pd.DataFrame,
    ingestion_run_id: str,
    ingested_at: datetime,
) -> pd.DataFrame:
    raw_df = pd.DataFrame(
        {
            "source_system": SOURCE_SYSTEM,
            "ingestion_run_id": ingestion_run_id,
            "ingested_at": ingested_at,
            "symbol_raw": parsed_df["ticker"],
            "payload_date": parsed_df["date"].dt.date,
            "open_raw": parsed_df["open"].astype(float),
            "high_raw": parsed_df["high"].astype(float),
            "low_raw": parsed_df["low"].astype(float),
            "close_raw": parsed_df["close"].astype(float),
            "volume_raw": parsed_df["vol"].astype(float),
        }
    )
    return raw_df


def save_failed_log(failed_rows: list[dict], ingestion_run_id: str) -> Path:
    FAILED_DIR.mkdir(parents=True, exist_ok=True)
    out = FAILED_DIR / f"{ingestion_run_id}_initial_ingest_failed_files.csv"
    pd.DataFrame(failed_rows).to_csv(out, index=False)
    return out


def run_ingestion(
    input_root: Path,
    output_file: Path,
    log_every: int = 200,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    FAILED_DIR.mkdir(parents=True, exist_ok=True)

    files = list_price_files(input_root)
    if not files:
        raise FileNotFoundError(f"No .txt files found under {input_root}")

    ingestion_run_id = build_ingestion_run_id()
    ingested_at = datetime.now(timezone.utc)

    writer: pq.ParquetWriter | None = None
    failed_rows: list[dict] = []
    total_rows = 0
    total_symbols: set[str] = set()
    success_files = 0

    if output_file.exists():
        output_file.unlink()

    print(f"Starting initial ingest: {ingestion_run_id}")
    print(f"Input root: {input_root}")
    print(f"Output parquet: {output_file}")
    print(f"Total files discovered: {len(files):,}")

    try:
        for idx, path in enumerate(files, start=1):
            try:
                parsed = parse_txt_file(path)
                raw_df = to_raw_schema(parsed, ingestion_run_id=ingestion_run_id, ingested_at=ingested_at)
                table = pa.Table.from_pandas(raw_df, preserve_index=False)

                if writer is None:
                    writer = pq.ParquetWriter(str(output_file), table.schema, compression="snappy")
                writer.write_table(table)

                success_files += 1
                total_rows += len(raw_df)
                total_symbols.update(raw_df["symbol_raw"].unique().tolist())
            except Exception as e:
                failed_rows.append(
                    {
                        "ingestion_run_id": ingestion_run_id,
                        "file_path": str(path),
                        "error_message": str(e),
                        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                )

            if idx % max(1, log_every) == 0 or idx == len(files):
                print(
                    f"[{idx:,}/{len(files):,}] "
                    f"success_files={success_files:,} failed_files={len(failed_rows):,} "
                    f"rows_written={total_rows:,}"
                )
    finally:
        if writer is not None:
            writer.close()

    failed_log_path = save_failed_log(failed_rows, ingestion_run_id)

    print("\nInitial ingest completed")
    print(f"Ingestion Run ID: {ingestion_run_id}")
    print(f"Success files: {success_files:,}")
    print(f"Failed files: {len(failed_rows):,}")
    print(f"Total rows written: {total_rows:,}")
    print(f"Unique symbols written: {len(total_symbols):,}")
    print(f"Output parquet: {output_file}")
    print(f"Failed log: {failed_log_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initial ingest from local Stooq txt dump into raw parquet layer."
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=None,
        help="Root folder containing downloaded .txt files. If omitted, auto-detect from input/*/daily/us.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=OUTPUT_FILE,
        help="Destination parquet file path.",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=200,
        help="Progress logging interval (files).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_root = discover_input_root(args.input_root)
    run_ingestion(
        input_root=input_root,
        output_file=args.output_file,
        log_every=args.log_every,
    )


if __name__ == "__main__":
    main()
