from __future__ import annotations

"""
Build first-pass per-ticker SARIMAX forecasts for Streamlit asset detail charts.

Design:
- Input: mart factor features parquet
- Model target: ret_1d
- Exogenous regressors: ret_20d, volatility_20d, dist_from_52w_high, volume
- Model: SARIMAX(1,0,1) with no seasonal term
- Horizon: 90 business days
"""

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning, ValueWarning
from statsmodels.tsa.statespace.sarimax import SARIMAX


DEFAULT_INPUT_PARQUET = Path("data/mart/investment/factor_features.parquet")
DEFAULT_OUTPUT_CSV = Path("data/visualization/investment/asset_forecast_for_streamlit.csv")
EXOG_COLS = ["ret_20d", "volatility_20d", "dist_from_52w_high", "volume"]
TARGET_COL = "ret_1d"
MODEL_LABEL = "SARIMAX(1,0,1)x(0,0,0,0)"
REQUIRED_INPUT_COLS = [
    "source_ticker",
    "ticker",
    "asset_type",
    "date",
    "close",
    TARGET_COL,
    *EXOG_COLS,
]
OUTPUT_COLS = [
    "ticker",
    "source_ticker",
    "asset_type",
    "forecast_date",
    "horizon",
    "model",
    "forecast_ret_1d",
    "forecast_price",
    "lower_ci",
    "upper_ci",
    "last_actual_date",
    "last_actual_close",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build per-ticker SARIMAX forecast export for Streamlit.")
    parser.add_argument(
        "--input-parquet",
        type=Path,
        default=DEFAULT_INPUT_PARQUET,
        help="Input factor features parquet path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help="Output CSV path for Streamlit forecast layer.",
    )
    parser.add_argument(
        "--horizon-bdays",
        type=int,
        default=90,
        help="Forecast horizon in business days.",
    )
    parser.add_argument(
        "--min-usable-observations",
        type=int,
        default=252,
        help="Minimum usable rows required after null filtering to fit a ticker model.",
    )
    return parser.parse_args()


def validate_input_schema(df: pd.DataFrame) -> None:
    missing = sorted(set(REQUIRED_INPUT_COLS) - set(df.columns))
    if missing:
        raise ValueError(f"Input parquet missing required columns: {missing}")


def _safe_compound(last_actual_close: float, returns: pd.Series) -> pd.Series:
    # Bound daily returns to keep price path numerically stable in v1 forecasts.
    bounded = returns.astype(float).clip(lower=-0.999, upper=1.0)
    with np.errstate(over="ignore", invalid="ignore"):
        path = float(last_actual_close) * (1.0 + bounded).cumprod()
    return pd.Series(path, index=returns.index).replace([np.inf, -np.inf], np.nan)


def _prepare_ticker_data(ticker_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    work = ticker_df.sort_values("date").drop_duplicates(subset=["date"], keep="last").copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work.dropna(subset=["date", "close"]).copy()

    for col in [TARGET_COL, *EXOG_COLS, "close"]:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    usable = work.dropna(subset=[TARGET_COL, *EXOG_COLS]).copy()
    return work, usable


def _future_exog_from_latest(usable: pd.DataFrame, steps: int) -> pd.DataFrame:
    latest = usable.iloc[-1]
    return pd.DataFrame(
        {
            "ret_20d": [float(latest["ret_20d"])] * steps,
            "volatility_20d": [float(latest["volatility_20d"])] * steps,
            "dist_from_52w_high": [float(latest["dist_from_52w_high"])] * steps,
            "volume": [float(latest["volume"])] * steps,
        }
    )


def _forecast_one_ticker(
    ticker_df: pd.DataFrame,
    horizon_bdays: int,
    min_usable_observations: int,
) -> tuple[pd.DataFrame | None, str | None]:
    full, usable = _prepare_ticker_data(ticker_df)
    if usable.empty:
        return None, "no usable rows after null filtering"
    if len(usable) < min_usable_observations:
        return None, f"insufficient usable rows ({len(usable)} < {min_usable_observations})"

    last_row = full.iloc[-1]
    last_actual_date = pd.to_datetime(last_row["date"], errors="coerce")
    last_actual_close = pd.to_numeric(last_row["close"], errors="coerce")
    if pd.isna(last_actual_date):
        return None, "missing last_actual_date"
    if pd.isna(last_actual_close) or float(last_actual_close) <= 0:
        return None, "invalid last_actual_close"

    endog = usable[TARGET_COL].astype(float)
    exog = usable[EXOG_COLS].astype(float)
    future_exog = _future_exog_from_latest(usable, steps=horizon_bdays)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        warnings.simplefilter("ignore", ValueWarning)
        warnings.simplefilter("ignore", FutureWarning)
        model = SARIMAX(
            endog=endog,
            exog=exog,
            order=(1, 0, 1),
            seasonal_order=(0, 0, 0, 0),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        fit = model.fit(disp=False)
        forecast_obj = fit.get_forecast(steps=horizon_bdays, exog=future_exog)
    mean_forecast = pd.Series(forecast_obj.predicted_mean).astype(float).reset_index(drop=True)

    ci = forecast_obj.conf_int(alpha=0.05)
    if isinstance(ci, pd.DataFrame) and ci.shape[1] >= 2:
        lower_ret = pd.to_numeric(ci.iloc[:, 0], errors="coerce").reset_index(drop=True)
        upper_ret = pd.to_numeric(ci.iloc[:, 1], errors="coerce").reset_index(drop=True)
    else:
        lower_ret = pd.Series(np.nan, index=range(horizon_bdays), dtype=float)
        upper_ret = pd.Series(np.nan, index=range(horizon_bdays), dtype=float)

    forecast_dates = pd.bdate_range(last_actual_date + pd.offsets.BDay(1), periods=horizon_bdays)
    forecast_price = _safe_compound(float(last_actual_close), mean_forecast)
    lower_price = _safe_compound(float(last_actual_close), lower_ret).astype(float)
    upper_price = _safe_compound(float(last_actual_close), upper_ret).astype(float)

    out = pd.DataFrame(
        {
            "ticker": str(usable.iloc[-1]["ticker"]),
            "source_ticker": str(usable.iloc[-1]["source_ticker"]),
            "asset_type": str(usable.iloc[-1]["asset_type"]),
            "forecast_date": forecast_dates,
            "horizon": np.arange(1, horizon_bdays + 1, dtype=int),
            "model": MODEL_LABEL,
            "forecast_ret_1d": mean_forecast.values,
            "forecast_price": forecast_price.values,
            "lower_ci": lower_price.values,
            "upper_ci": upper_price.values,
            "last_actual_date": pd.Timestamp(last_actual_date),
            "last_actual_close": float(last_actual_close),
        }
    )
    return out, None


def build_sarimax_forecast(
    factor_df: pd.DataFrame,
    horizon_bdays: int,
    min_usable_observations: int,
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    results: list[pd.DataFrame] = []
    failures: list[dict[str, str]] = []

    grouped = factor_df.sort_values(["ticker", "source_ticker", "date"]).groupby("source_ticker", dropna=False)
    for source_ticker, g in grouped:
        ticker_name = str(g["ticker"].iloc[-1]) if "ticker" in g.columns and not g.empty else str(source_ticker)
        try:
            forecast_df, skip_reason = _forecast_one_ticker(
                ticker_df=g,
                horizon_bdays=horizon_bdays,
                min_usable_observations=min_usable_observations,
            )
            if forecast_df is None:
                failures.append(
                    {
                        "ticker": ticker_name,
                        "source_ticker": str(source_ticker),
                        "reason": f"skipped: {skip_reason}",
                    }
                )
                continue
            results.append(forecast_df)
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "ticker": ticker_name,
                    "source_ticker": str(source_ticker),
                    "reason": f"fit_failure: {type(exc).__name__}: {str(exc)}",
                }
            )

    if results:
        out = pd.concat(results, ignore_index=True)[OUTPUT_COLS]
        out = out.sort_values(["ticker", "forecast_date"], kind="mergesort").reset_index(drop=True)
    else:
        out = pd.DataFrame(columns=OUTPUT_COLS)
    return out, failures


def main() -> None:
    args = parse_args()
    if args.horizon_bdays <= 0:
        raise ValueError("horizon_bdays must be a positive integer.")
    if args.min_usable_observations <= 0:
        raise ValueError("min_usable_observations must be a positive integer.")
    if not args.input_parquet.exists():
        raise FileNotFoundError(f"Input parquet not found: {args.input_parquet}")

    factor_df = pd.read_parquet(args.input_parquet)
    validate_input_schema(factor_df)
    factor_df["date"] = pd.to_datetime(factor_df["date"], errors="coerce")
    factor_df = factor_df.dropna(subset=["source_ticker", "ticker", "asset_type", "date"]).copy()

    output_df, failures = build_sarimax_forecast(
        factor_df=factor_df,
        horizon_bdays=args.horizon_bdays,
        min_usable_observations=args.min_usable_observations,
    )

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(args.output_csv, index=False)

    processed_tickers = int(output_df["source_ticker"].nunique()) if not output_df.empty else 0
    skipped_tickers = len(failures)
    min_forecast_date = output_df["forecast_date"].min() if not output_df.empty else None
    max_forecast_date = output_df["forecast_date"].max() if not output_df.empty else None

    print(f"Output CSV written: {args.output_csv}")
    print(f"Tickers processed: {processed_tickers}")
    print(f"Tickers skipped: {skipped_tickers}")
    print(f"Forecast date range: {min_forecast_date} -> {max_forecast_date}")
    print(f"Total output rows: {len(output_df):,}")

    if failures:
        print("\nSkipped / failed tickers:")
        for row in failures:
            print(f"- {row['ticker']} ({row['source_ticker']}): {row['reason']}")

        failure_summary = (
            pd.DataFrame(failures)["reason"]
            .value_counts()
            .rename_axis("reason")
            .reset_index(name="count")
        )
        print("\nFailure summary:")
        print(failure_summary.to_string(index=False))

    print("\nSample output rows:")
    if output_df.empty:
        print("(no output rows)")
    else:
        print(output_df.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
