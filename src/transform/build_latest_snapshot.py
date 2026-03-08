from __future__ import annotations

"""
Build latest snapshot dataset from raw stooq prices.

Output schema:
source_ticker, ticker, date, open, high, low, close, volume,
prev_close, daily_return, source, is_active
"""

import argparse
from pathlib import Path

import pandas as pd

from src.utils.price_utils import DEFAULT_RAW_PARQUET, iter_normalized_price_chunks


DEFAULT_TICKER_MASTER = Path("data/staging/stock_price_stooq/ticker_master.parquet")
DEFAULT_OUTPUT_PARQUET = Path("data/staging/stock_price_stooq/latest_snapshot.parquet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build latest per-ticker snapshot from raw stooq prices.")
    parser.add_argument(
        "--input-parquet",
        type=Path,
        default=DEFAULT_RAW_PARQUET,
        help="Path to raw parquet file.",
    )
    parser.add_argument(
        "--ticker-master",
        type=Path,
        default=DEFAULT_TICKER_MASTER,
        help="Path to ticker_master parquet file.",
    )
    parser.add_argument(
        "--output-parquet",
        type=Path,
        default=DEFAULT_OUTPUT_PARQUET,
        help="Destination parquet output path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional CSV output path.",
    )
    return parser.parse_args()


def _coalesce_latest_two_rows(
    existing: pd.DataFrame | None,
    incoming: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep at most the latest two distinct trading dates for a single source_ticker.
    """
    if existing is None or existing.empty:
        combined = incoming.copy()
    else:
        combined = pd.concat([existing, incoming], ignore_index=True)

    combined = combined.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return combined.tail(2).reset_index(drop=True)


def _build_latest_base(input_parquet: Path) -> pd.DataFrame:
    """
    Scan raw parquet incrementally and keep latest two rows per source_ticker.
    """
    latest_candidates: dict[str, pd.DataFrame] = {}

    for chunk in iter_normalized_price_chunks(input_parquet):
        needed_cols = ["source_ticker", "ticker", "date", "open", "high", "low", "close", "volume"]
        work = chunk[needed_cols].sort_values(["source_ticker", "date"])

        for source_ticker, group in work.groupby("source_ticker", dropna=False):
            compact = group.drop_duplicates(subset=["date"], keep="last").tail(2)
            key = str(source_ticker)
            latest_candidates[key] = _coalesce_latest_two_rows(latest_candidates.get(key), compact)

    rows: list[dict] = []
    for source_ticker, mini in latest_candidates.items():
        mini = mini.sort_values("date").drop_duplicates(subset=["date"], keep="last")
        latest = mini.iloc[-1]

        prev_close = None
        if len(mini) >= 2:
            prev_row = mini.iloc[-2]
            if prev_row["date"] < latest["date"]:
                prev_close = prev_row["close"]

        close_value = latest["close"]
        daily_return = None
        if prev_close is not None and pd.notna(prev_close) and pd.notna(close_value):
            daily_return = (float(close_value) / float(prev_close)) - 1.0

        rows.append(
            {
                "source_ticker": latest["source_ticker"],
                "ticker": latest["ticker"],
                "date": latest["date"],
                "open": latest["open"],
                "high": latest["high"],
                "low": latest["low"],
                "close": latest["close"],
                "volume": latest["volume"],
                "prev_close": prev_close,
                "daily_return": daily_return,
                "source": "stooq",
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError("No latest snapshot rows produced.")
    return out


def _validate_ticker_master(ticker_master: pd.DataFrame) -> None:
    required = {"source_ticker", "max_date", "is_active"}
    missing = sorted(required - set(ticker_master.columns))
    if missing:
        raise ValueError(f"ticker_master missing columns: {missing}")
    if ticker_master["source_ticker"].duplicated().any():
        raise ValueError("ticker_master has duplicated source_ticker values.")


def _validate_output(latest: pd.DataFrame, joined: pd.DataFrame) -> None:
    if len(latest) != latest["source_ticker"].nunique():
        raise ValueError("latest_snapshot does not have exactly one row per source_ticker.")

    mismatch = joined[joined["date"] != joined["max_date"]]
    if not mismatch.empty:
        sample = mismatch[["source_ticker", "date", "max_date"]].head(5).to_dict(orient="records")
        raise ValueError(f"latest_snapshot.date mismatch vs ticker_master.max_date, sample={sample}")

    invalid_null = joined[
        joined["daily_return"].isna()
        & joined["prev_close"].notna()
        & joined["close"].notna()
    ]
    if not invalid_null.empty:
        raise ValueError("daily_return is null while prev_close and close are available.")

    invalid_nonnull = joined[
        joined["daily_return"].notna()
        & (joined["prev_close"].isna() | joined["close"].isna())
    ]
    if not invalid_nonnull.empty:
        raise ValueError("daily_return exists when prev_close or close is unavailable.")

    if not joined["source"].eq("stooq").all():
        raise ValueError("source contains non-'stooq' values.")


def build_latest_snapshot(input_parquet: Path, ticker_master_path: Path) -> pd.DataFrame:
    """
    Build latest snapshot and validate against ticker_master.
    """
    if not input_parquet.exists():
        raise FileNotFoundError(f"Input parquet not found: {input_parquet}")
    if not ticker_master_path.exists():
        raise FileNotFoundError(f"Ticker master not found: {ticker_master_path}")

    latest = _build_latest_base(input_parquet)

    ticker_master = pd.read_parquet(ticker_master_path, columns=["source_ticker", "max_date", "is_active"])
    _validate_ticker_master(ticker_master)
    ticker_master["max_date"] = pd.to_datetime(ticker_master["max_date"], errors="coerce")

    joined = latest.merge(ticker_master, on="source_ticker", how="left", validate="one_to_one")
    if joined["is_active"].isna().any():
        missing = joined[joined["is_active"].isna()]["source_ticker"].head(5).tolist()
        raise ValueError(f"Missing is_active from ticker_master for source_ticker sample={missing}")

    joined["is_active"] = joined["is_active"].astype(bool)
    _validate_output(latest, joined)

    out = joined.drop(columns=["max_date"]).sort_values(["ticker", "source_ticker"]).reset_index(drop=True)
    return out[
        [
            "source_ticker",
            "ticker",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "prev_close",
            "daily_return",
            "source",
            "is_active",
        ]
    ]


def main() -> None:
    args = parse_args()
    latest_snapshot = build_latest_snapshot(args.input_parquet, args.ticker_master)

    args.output_parquet.parent.mkdir(parents=True, exist_ok=True)
    latest_snapshot.to_parquet(args.output_parquet, index=False)
    print(f"Latest snapshot parquet written: {args.output_parquet}")

    if args.output_csv is not None:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        latest_snapshot.to_csv(args.output_csv, index=False)
        print(f"Latest snapshot csv written: {args.output_csv}")

    print(f"Rows: {len(latest_snapshot):,}")
    print(f"Date range: {latest_snapshot['date'].min()} -> {latest_snapshot['date'].max()}")


if __name__ == "__main__":
    main()

