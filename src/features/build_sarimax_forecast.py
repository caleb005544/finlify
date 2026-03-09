from __future__ import annotations

"""
Build per-ticker forecast export for Streamlit asset detail charts (v2).

v2 changes:
- Forecast target is log(close), not daily return.
- Forecast prices are exp(predicted_log_price).
- Uncertainty bands are volatility-based scenario bands, not compounded CI returns.
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
MODEL_LABEL = "sarimax_logprice_v2"
MODEL_LABEL_NOEXOG = "sarimax_logprice_v2_noexog_fallback"
MODEL_LABEL_LINEAR = "linear_logtrend_v2_fallback"
REQUIRED_INPUT_COLS = [
    "source_ticker",
    "ticker",
    "asset_type",
    "date",
    "close",
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
    parser = argparse.ArgumentParser(description="Build per-ticker log-price forecast export for Streamlit.")
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
    parser.add_argument(
        "--band-multiplier",
        type=float,
        default=1.5,
        help="Multiplier for volatility-based scenario bands.",
    )
    return parser.parse_args()


def validate_input_schema(df: pd.DataFrame) -> None:
    missing = sorted(set(REQUIRED_INPUT_COLS) - set(df.columns))
    if missing:
        raise ValueError(f"Input parquet missing required columns: {missing}")


def _prepare_ticker_data(ticker_df: pd.DataFrame) -> pd.DataFrame:
    work = ticker_df.sort_values("date").drop_duplicates(subset=["date"], keep="last").copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work = work.dropna(subset=["date", "close"]).copy()

    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    for col in EXOG_COLS:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work = work[work["close"] > 0].copy()
    work["log_close"] = np.log(work["close"].astype(float))
    return work


def _build_future_exog(last_row: pd.Series, steps: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ret_20d": [float(last_row["ret_20d"])] * steps,
            "volatility_20d": [float(last_row["volatility_20d"])] * steps,
            "dist_from_52w_high": [float(last_row["dist_from_52w_high"])] * steps,
            "volume": [float(last_row["volume"])] * steps,
        }
    )


def _fit_sarimax(endog: pd.Series, exog: pd.DataFrame | None, steps: int, future_exog: pd.DataFrame | None) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        warnings.simplefilter("ignore", ValueWarning)
        warnings.simplefilter("ignore", FutureWarning)
        model = SARIMAX(
            endog=endog.astype(float),
            exog=None if exog is None else exog.astype(float),
            order=(1, 0, 1),
            seasonal_order=(0, 0, 0, 0),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        fit = model.fit(disp=False)
        forecast_obj = fit.get_forecast(steps=steps, exog=future_exog if exog is not None else None)
    pred = pd.Series(forecast_obj.predicted_mean).astype(float).reset_index(drop=True)
    if pred.isna().any() or not np.isfinite(pred).all():
        raise ValueError("predicted log-price contains non-finite values")
    return pred


def _linear_log_trend_fallback(log_close_series: pd.Series, steps: int, window: int = 60) -> pd.Series:
    hist = log_close_series.astype(float).dropna()
    n = min(window, len(hist))
    if n < 20:
        raise ValueError("insufficient observations for linear trend fallback")

    y = hist.iloc[-n:].values
    x = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(x, y, deg=1)

    future_x = np.arange(n, n + steps, dtype=float)
    pred = intercept + (slope * future_x)
    return pd.Series(pred)


def _latest_volatility_for_band(work: pd.DataFrame) -> float:
    vol = pd.to_numeric(work["volatility_20d"], errors="coerce").dropna()
    if not vol.empty and float(vol.iloc[-1]) > 0:
        return float(vol.iloc[-1])

    # If volatility_20d is unavailable, estimate from recent log-return std as a safe fallback.
    log_ret = work["log_close"].diff()
    fallback = log_ret.rolling(20, min_periods=10).std().dropna()
    if not fallback.empty and float(fallback.iloc[-1]) > 0:
        return float(fallback.iloc[-1])

    return 0.01


def _log_to_price(pred_log: pd.Series) -> pd.Series:
    bounded_log = pred_log.astype(float).clip(lower=np.log(1e-6), upper=np.log(1e9))
    return pd.Series(np.exp(bounded_log), index=pred_log.index)


def _implied_forecast_return(forecast_price: pd.Series, last_actual_close: float) -> pd.Series:
    prior = pd.Series([float(last_actual_close)] + forecast_price.iloc[:-1].tolist())
    implied = (forecast_price.values / prior.values) - 1.0
    return pd.Series(implied, index=forecast_price.index).replace([np.inf, -np.inf], np.nan)


def _forecast_looks_unstable(
    forecast_price: pd.Series,
    last_actual_close: float,
    latest_volatility: float,
) -> bool:
    if forecast_price.empty:
        return True
    if not np.isfinite(forecast_price.values).all():
        return True
    if (forecast_price <= 0).any():
        return True

    implied = _implied_forecast_return(forecast_price, last_actual_close=last_actual_close)
    if implied.isna().any():
        return True

    median_abs_ret = float(implied.abs().median())
    p90_abs_ret = float(implied.abs().quantile(0.90))
    end_return = float((forecast_price.iloc[-1] / float(last_actual_close)) - 1.0)

    # Guardrail: if implied daily moves are far above recent realized volatility or
    # end-horizon move is extreme, prefer deterministic linear trend fallback.
    daily_limit = max(0.03, 3.0 * latest_volatility)
    tail_limit = max(0.06, 5.0 * latest_volatility)
    if median_abs_ret > daily_limit:
        return True
    if p90_abs_ret > tail_limit:
        return True
    if end_return < -0.70 or end_return > 1.50:
        return True
    return False


def _forecast_one_ticker(
    ticker_df: pd.DataFrame,
    horizon_bdays: int,
    min_usable_observations: int,
    band_multiplier: float,
) -> tuple[pd.DataFrame | None, dict[str, str] | None]:
    work = _prepare_ticker_data(ticker_df)
    if work.empty:
        return None, {"status": "skipped", "reason": "no usable rows after cleaning"}

    usable = work.dropna(subset=["log_close", *EXOG_COLS]).copy()
    if len(usable) < min_usable_observations:
        return None, {
            "status": "skipped",
            "reason": f"insufficient usable rows ({len(usable)} < {min_usable_observations})",
        }

    last_row = work.iloc[-1]
    last_actual_date = pd.to_datetime(last_row["date"], errors="coerce")
    last_actual_close = pd.to_numeric(last_row["close"], errors="coerce")
    if pd.isna(last_actual_date):
        return None, {"status": "skipped", "reason": "missing last_actual_date"}
    if pd.isna(last_actual_close) or float(last_actual_close) <= 0:
        return None, {"status": "skipped", "reason": "invalid last_actual_close"}

    latest_vol = _latest_volatility_for_band(work)
    model_label = MODEL_LABEL
    pred_log: pd.Series
    fit_note = ""

    try:
        endog = usable["log_close"].astype(float)
        exog = usable[EXOG_COLS].astype(float)
        future_exog = _build_future_exog(usable.iloc[-1], steps=horizon_bdays)
        pred_log = _fit_sarimax(endog=endog, exog=exog, steps=horizon_bdays, future_exog=future_exog)
    except Exception as exc_exog:  # noqa: BLE001
        # Exogenous regressors can be unstable for some tickers (near-constant, collinear, or poorly scaled).
        # In that case we gracefully retry with SARIMAX on log-price only before using linear fallback.
        try:
            endog_noexog = work["log_close"].dropna().astype(float)
            if len(endog_noexog) < min_usable_observations:
                raise ValueError("insufficient rows for no-exog fallback")
            pred_log = _fit_sarimax(endog=endog_noexog, exog=None, steps=horizon_bdays, future_exog=None)
            model_label = MODEL_LABEL_NOEXOG
            fit_note = f"; exog_fit_failed={type(exc_exog).__name__}"
        except Exception as exc_noexog:  # noqa: BLE001
            try:
                pred_log = _linear_log_trend_fallback(work["log_close"], steps=horizon_bdays, window=60)
                model_label = MODEL_LABEL_LINEAR
                fit_note = (
                    f"; exog_fit_failed={type(exc_exog).__name__}; noexog_fit_failed={type(exc_noexog).__name__}"
                )
            except Exception as exc_linear:  # noqa: BLE001
                return None, {
                    "status": "failed",
                    "reason": (
                        "fit_failure: "
                        f"exog={type(exc_exog).__name__}: {str(exc_exog)} | "
                        f"noexog={type(exc_noexog).__name__}: {str(exc_noexog)} | "
                        f"linear={type(exc_linear).__name__}: {str(exc_linear)}"
                    ),
                }

    if model_label != MODEL_LABEL_LINEAR:
        candidate_price = _log_to_price(pred_log)
        if _forecast_looks_unstable(
            forecast_price=candidate_price,
            last_actual_close=float(last_actual_close),
            latest_volatility=latest_vol,
        ):
            try:
                pred_log = _linear_log_trend_fallback(work["log_close"], steps=horizon_bdays, window=60)
                if model_label == MODEL_LABEL:
                    fit_note = f"{fit_note}; unstable_sarimax_path_replaced_with_linear"
                else:
                    fit_note = f"{fit_note}; unstable_noexog_path_replaced_with_linear"
                model_label = MODEL_LABEL_LINEAR
            except Exception:
                # Keep SARIMAX output if linear fallback is unavailable.
                pass

    forecast_price = _log_to_price(pred_log)
    forecast_ret_1d = _implied_forecast_return(forecast_price, float(last_actual_close))

    horizons = np.arange(1, horizon_bdays + 1, dtype=int)
    band_width_pct = band_multiplier * latest_vol * np.sqrt(horizons)
    # Cap max width for chart readability and to avoid explosive fan shapes in v2.
    band_width_pct = np.clip(band_width_pct, 0.0, 0.60)

    lower_ci = forecast_price.values * (1.0 - band_width_pct)
    upper_ci = forecast_price.values * (1.0 + band_width_pct)
    lower_ci = np.maximum(lower_ci, 1e-6)

    forecast_dates = pd.bdate_range(last_actual_date + pd.offsets.BDay(1), periods=horizon_bdays)

    out = pd.DataFrame(
        {
            "ticker": str(work.iloc[-1]["ticker"]),
            "source_ticker": str(work.iloc[-1]["source_ticker"]),
            "asset_type": str(work.iloc[-1]["asset_type"]),
            "forecast_date": forecast_dates,
            "horizon": horizons,
            "model": model_label,
            # Derived implied daily return from consecutive forecast prices.
            "forecast_ret_1d": forecast_ret_1d.values,
            "forecast_price": forecast_price.values,
            # Scenario band from latest volatility_20d, not statistical CI from SARIMAX.
            "lower_ci": lower_ci,
            "upper_ci": upper_ci,
            "last_actual_date": pd.Timestamp(last_actual_date),
            "last_actual_close": float(last_actual_close),
        }
    )

    if fit_note:
        return out, {"status": "processed_with_fallback", "reason": f"{model_label}{fit_note}"}
    return out, None


def build_sarimax_forecast(
    factor_df: pd.DataFrame,
    horizon_bdays: int,
    min_usable_observations: int,
    band_multiplier: float,
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    results: list[pd.DataFrame] = []
    events: list[dict[str, str]] = []

    grouped = factor_df.sort_values(["ticker", "source_ticker", "date"]).groupby("source_ticker", dropna=False)
    for source_ticker, g in grouped:
        ticker_name = str(g["ticker"].iloc[-1]) if "ticker" in g.columns and not g.empty else str(source_ticker)
        forecast_df, event = _forecast_one_ticker(
            ticker_df=g,
            horizon_bdays=horizon_bdays,
            min_usable_observations=min_usable_observations,
            band_multiplier=band_multiplier,
        )

        if event is not None:
            events.append(
                {
                    "ticker": ticker_name,
                    "source_ticker": str(source_ticker),
                    "status": event["status"],
                    "reason": event["reason"],
                }
            )

        if forecast_df is not None:
            results.append(forecast_df)

    if results:
        out = pd.concat(results, ignore_index=True)[OUTPUT_COLS]
        out = out.sort_values(["ticker", "forecast_date"], kind="mergesort").reset_index(drop=True)
    else:
        out = pd.DataFrame(columns=OUTPUT_COLS)
    return out, events


def main() -> None:
    args = parse_args()
    if args.horizon_bdays <= 0:
        raise ValueError("horizon_bdays must be a positive integer.")
    if args.min_usable_observations <= 0:
        raise ValueError("min_usable_observations must be a positive integer.")
    if args.band_multiplier <= 0:
        raise ValueError("band_multiplier must be a positive number.")
    if not args.input_parquet.exists():
        raise FileNotFoundError(f"Input parquet not found: {args.input_parquet}")

    factor_df = pd.read_parquet(args.input_parquet)
    validate_input_schema(factor_df)
    factor_df["date"] = pd.to_datetime(factor_df["date"], errors="coerce")
    factor_df = factor_df.dropna(subset=["source_ticker", "ticker", "asset_type", "date"]).copy()

    output_df, events = build_sarimax_forecast(
        factor_df=factor_df,
        horizon_bdays=args.horizon_bdays,
        min_usable_observations=args.min_usable_observations,
        band_multiplier=args.band_multiplier,
    )

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(args.output_csv, index=False)

    processed_tickers = int(output_df["source_ticker"].nunique()) if not output_df.empty else 0
    skipped_tickers = sum(1 for e in events if e["status"] == "skipped")
    failed_tickers = sum(1 for e in events if e["status"] == "failed")
    fallback_tickers = sum(1 for e in events if e["status"] == "processed_with_fallback")
    min_forecast_date = output_df["forecast_date"].min() if not output_df.empty else None
    max_forecast_date = output_df["forecast_date"].max() if not output_df.empty else None

    print(f"Output CSV written: {args.output_csv}")
    print(f"Tickers processed: {processed_tickers}")
    print(f"Tickers skipped: {skipped_tickers}")
    print(f"Tickers failed: {failed_tickers}")
    print(f"Tickers with fallback model: {fallback_tickers}")
    print(f"Forecast date range: {min_forecast_date} -> {max_forecast_date}")
    print(f"Total output rows: {len(output_df):,}")

    if events:
        print("\nTicker event details:")
        for row in events:
            print(f"- {row['ticker']} ({row['source_ticker']}): {row['status']} | {row['reason']}")

        event_summary = (
            pd.DataFrame(events)[["status", "reason"]]
            .value_counts()
            .rename("count")
            .reset_index()
            .sort_values(["status", "count"], ascending=[True, False])
        )
        print("\nEvent summary:")
        print(event_summary.to_string(index=False))

    print("\nSample output rows:")
    if output_df.empty:
        print("(no output rows)")
    else:
        print(output_df.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
