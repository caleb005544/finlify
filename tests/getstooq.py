from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

try:
    from pandas_datareader import data as pdr
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "pandas-datareader is not installed. Please run: pip install pandas-datareader"
    ) from exc


def get_latest_stooq_row(symbol: str = "MSFT") -> pd.DataFrame:
    """
    Fetch recent daily OHLCV from Stooq and return the latest trading-day row
    with columns: Date, Open, High, Low, Close, Change, Volume.
    """
    end = datetime.utcnow().date()
    start = end - timedelta(days=60)

    raw = pdr.DataReader(symbol, "stooq", start=start, end=end)
    if raw.empty:
        raise ValueError(f"No data returned from Stooq for symbol={symbol}.")

    df = raw.sort_index().reset_index()  # Stooq usually returns descending index.
    if "Date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Date"})

    # Build "Change" as day-over-day close change (absolute).
    df["Change"] = df["Close"].diff()

    out = df[["Date", "Open", "High", "Low", "Close", "Change", "Volume"]].copy()
    latest = out.tail(1).reset_index(drop=True)
    return latest


def main() -> None:
    latest_df = get_latest_stooq_row("MSFT")
    print(latest_df.to_string(index=False))


if __name__ == "__main__":
    main()
