from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq


DEFAULT_PARQUET = Path("data/raw/stock_price_stooq/stock_prices.parquet")


def summarize_raw_parquet(parquet_path: Path) -> tuple[int, int, str | None, str | None, list[str]]:
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

    pf = pq.ParquetFile(parquet_path)
    total_rows = pf.metadata.num_rows

    symbols: set[str] = set()
    min_date = None
    max_date = None

    for rg in range(pf.metadata.num_row_groups):
        table = pf.read_row_group(rg, columns=["symbol_raw", "payload_date"])

        unique_symbols = pc.unique(table["symbol_raw"]).to_pylist()
        for s in unique_symbols:
            if s is None:
                continue
            symbols.add(str(s))

        rg_min = pc.min(table["payload_date"]).as_py()
        rg_max = pc.max(table["payload_date"]).as_py()
        if rg_min is not None and (min_date is None or rg_min < min_date):
            min_date = rg_min
        if rg_max is not None and (max_date is None or rg_max > max_date):
            max_date = rg_max

    symbol_list = sorted(symbols)
    return total_rows, len(symbol_list), str(min_date) if min_date else None, str(max_date) if max_date else None, symbol_list


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export raw stock parquet summary to CSV."
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        default=DEFAULT_PARQUET,
        help="Path to raw parquet file.",
    )
    parser.add_argument(
        "--summary-csv",
        type=Path,
        default=Path("output/raw_data_summary.csv"),
        help="Output CSV path for one-row summary.",
    )
    parser.add_argument(
        "--ticker-csv",
        type=Path,
        default=Path("output/raw_data_tickers.csv"),
        help="Output CSV path for ticker list.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    total_rows, symbol_count, min_date, max_date, symbol_list = summarize_raw_parquet(args.parquet)

    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    args.ticker_csv.parent.mkdir(parents=True, exist_ok=True)

    summary_df = pd.DataFrame(
        [
            {
                "parquet_file": str(args.parquet),
                "total_rows": total_rows,
                "symbol_count": symbol_count,
                "date_start": min_date,
                "date_end": max_date,
            }
        ]
    )
    summary_df.to_csv(args.summary_csv, index=False)

    tickers_df = pd.DataFrame({"symbol_raw": symbol_list})
    tickers_df.to_csv(args.ticker_csv, index=False)

    print(f"Summary CSV written: {args.summary_csv}")
    print(f"Ticker CSV written: {args.ticker_csv}")


if __name__ == "__main__":
    main()
