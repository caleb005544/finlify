"""Forecast model implementations and routing for V3.0.

This module intentionally keeps models lightweight/deterministic so the service
stays runnable in local/dev environments while we phase in real ML models.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from functools import lru_cache
from statistics import mean
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from .schemas import (
    ForecastRequest,
    ForecastPoint,
)
from .settings import (
    ROUTING_ENABLE_XGBOOST,
    ROUTING_ENABLE_PROPHET,
    ROUTING_ENABLE_SARIMA,
    ROUTING_PROPHET_MIN_HORIZON,
    ROUTING_PROPHET_MIN_OBS,
    ROUTING_SARIMA_MIN_OBS,
    ROUTING_XGBOOST_MAX_HORIZON,
    ROUTING_XGBOOST_MIN_OBS,
    XGBOOST_MODEL_CACHE_TTL_SECONDS,
)


@lru_cache(maxsize=1)
def _load_sarimax():
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    return SARIMAX


@lru_cache(maxsize=1)
def _load_prophet_stack():
    import pandas as pd
    from prophet import Prophet
    return pd, Prophet


@lru_cache(maxsize=1)
def _load_xgboost_stack():
    import numpy as np
    from xgboost import XGBRegressor
    return np, XGBRegressor


_xgboost_model_cache: Dict[str, Tuple[float, Any, int, float]] = {}
_xgboost_cache_lock = Lock()


def _xgboost_model_cache_key(
    request: ForecastRequest,
    ys: List[float],
    lag_count: int,
) -> str:
    payload = {
        "series_id": request.series_id,
        "freq": request.freq,
        "lag_count": lag_count,
        "y": ys,
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _xgboost_get_cached_model(
    key: str,
) -> Optional[Tuple[Any, int, float]]:
    now = time.time()
    with _xgboost_cache_lock:
        entry = _xgboost_model_cache.get(key)
        if not entry:
            return None
        expires_at, model, lag_count, sigma = entry
        if now > expires_at:
            _xgboost_model_cache.pop(key, None)
            return None
        return model, lag_count, sigma


def _xgboost_set_cached_model(
    key: str,
    model: Any,
    lag_count: int,
    sigma: float,
) -> None:
    expires_at = time.time() + XGBOOST_MODEL_CACHE_TTL_SECONDS
    with _xgboost_cache_lock:
        _xgboost_model_cache[key] = (expires_at, model, lag_count, sigma)


def _increment_date(ds: str, freq: str, step: int) -> str:
    """Increment a date string by `step` periods of the given frequency.

    Handles D (daily), W (weekly), M (monthly) deterministically.
    """
    dt = datetime.fromisoformat(ds)

    if freq == "D":
        dt += timedelta(days=step)
    elif freq == "W":
        dt += timedelta(weeks=step)
    elif freq == "M":
        # Simple month increment without dateutil dependency
        month = dt.month - 1 + step
        year = dt.year + month // 12
        month = month % 12 + 1
        # Clamp day to valid range for the target month
        import calendar
        max_day = calendar.monthrange(year, month)[1]
        day = min(dt.day, max_day)
        dt = dt.replace(year=year, month=month, day=day)

    return dt.strftime("%Y-%m-%d")


def _flat_forecast(request: ForecastRequest) -> List[ForecastPoint]:
    baseline = request.y[-1].y
    last_ds = request.y[-1].ds
    forecast_points: List[ForecastPoint] = []
    for i in range(1, request.horizon + 1):
        ds = _increment_date(last_ds, request.freq, i)
        forecast_points.append(
            ForecastPoint(
                ds=ds,
                yhat=round(baseline, 4),
                yhat_lower=round(baseline * 0.9, 4),
                yhat_upper=round(baseline * 1.1, 4),
            )
        )
    return forecast_points


def _trend_forecast(request: ForecastRequest) -> List[ForecastPoint]:
    """Simple AR-like trend proxy for sarima_v0."""
    ys = [pt.y for pt in request.y]
    baseline = ys[-1]
    last_ds = request.y[-1].ds
    deltas = [ys[i] - ys[i - 1] for i in range(1, len(ys))]
    drift = mean(deltas[-8:]) if deltas else 0.0

    forecast_points: List[ForecastPoint] = []
    for i in range(1, request.horizon + 1):
        ds = _increment_date(last_ds, request.freq, i)
        yhat = baseline + drift * i
        band = max(abs(yhat) * 0.08, 1.0)
        forecast_points.append(
            ForecastPoint(
                ds=ds,
                yhat=round(yhat, 4),
                yhat_lower=round(yhat - band, 4),
                yhat_upper=round(yhat + band, 4),
            )
        )
    return forecast_points


def _freq_to_seasonal_period(freq: str) -> int:
    if freq == "D":
        return 7
    if freq == "W":
        return 4
    return 12


def _sarima_forecast(
    request: ForecastRequest,
) -> Tuple[List[ForecastPoint], Dict[str, Any]]:
    ys = [float(pt.y) for pt in request.y]
    last_ds = request.y[-1].ds
    seasonal_period = _freq_to_seasonal_period(request.freq)

    # Lightweight heuristic orders for a stable baseline.
    n_obs = len(ys)
    d = 1 if n_obs >= 8 else 0
    D = 1 if n_obs >= seasonal_period * 2 else 0
    p = 1 if n_obs >= 12 else 0
    q = 1 if n_obs >= 12 else 0
    P = 1 if n_obs >= seasonal_period * 3 else 0
    Q = 1 if n_obs >= seasonal_period * 3 else 0

    order = (p, d, q)
    seasonal_order = (P, D, Q, seasonal_period)

    try:
        SARIMAX = _load_sarimax()

        model = SARIMAX(
            ys,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
            trend="c",
        )
        result = model.fit(disp=False)
        pred = result.get_forecast(steps=request.horizon)
        means = [float(v) for v in pred.predicted_mean]
        ci = pred.conf_int(alpha=0.2)

        lower_values: List[float] = []
        upper_values: List[float] = []
        for idx in range(request.horizon):
            if hasattr(ci, "iloc"):
                lo = float(ci.iloc[idx, 0])
                hi = float(ci.iloc[idx, 1])
            else:
                lo = float(ci[idx][0])
                hi = float(ci[idx][1])
            lower_values.append(min(lo, hi))
            upper_values.append(max(lo, hi))

        points: List[ForecastPoint] = []
        for i in range(1, request.horizon + 1):
            ds = _increment_date(last_ds, request.freq, i)
            yhat = means[i - 1]
            yhat_lower = lower_values[i - 1]
            yhat_upper = upper_values[i - 1]
            points.append(
                ForecastPoint(
                    ds=ds,
                    yhat=round(yhat, 4),
                    yhat_lower=round(yhat_lower, 4),
                    yhat_upper=round(yhat_upper, 4),
                )
            )
        return points, {
            "sarima_backend": "statsmodels",
            "order": list(order),
            "seasonal_order": list(seasonal_order),
        }
    except Exception as exc:
        # Keep service resilient while still exposing SARIMA intent/failure.
        points = _trend_forecast(request)
        return points, {
            "sarima_backend": "fallback_trend_proxy",
            "fallback_reason": str(exc),
            "order": list(order),
            "seasonal_order": list(seasonal_order),
        }


def _seasonal_forecast(request: ForecastRequest) -> List[ForecastPoint]:
    """Simple seasonal trend proxy for prophet_v0."""
    ys = [pt.y for pt in request.y]
    baseline = ys[-1]
    last_ds = request.y[-1].ds
    deltas = [ys[i] - ys[i - 1] for i in range(1, len(ys))]
    drift = mean(deltas[-14:]) if deltas else 0.0

    season_period = _freq_to_seasonal_period(request.freq)

    seasonal_offsets: List[float] = []
    for idx, value in enumerate(ys[-season_period:]):
        seasonal_offsets.append(value - baseline + drift * (idx - season_period + 1))
    seasonal_mean = mean(seasonal_offsets) if seasonal_offsets else 0.0

    forecast_points: List[ForecastPoint] = []
    for i in range(1, request.horizon + 1):
        ds = _increment_date(last_ds, request.freq, i)
        period = max(len(seasonal_offsets), 1)
        phase = (i - 1) % period
        season_adj = seasonal_offsets[phase] - seasonal_mean if seasonal_offsets else 0.0
        yhat = baseline + drift * i + season_adj
        band = max(abs(yhat) * 0.12, 1.5)
        forecast_points.append(
            ForecastPoint(
                ds=ds,
                yhat=round(yhat, 4),
                yhat_lower=round(yhat - band, 4),
                yhat_upper=round(yhat + band, 4),
            )
        )
    return forecast_points


def _prophet_freq_code(freq: str) -> str:
    if freq == "D":
        return "D"
    if freq == "W":
        return "W"
    return "MS"


def _prophet_forecast(
    request: ForecastRequest,
) -> Tuple[List[ForecastPoint], Dict[str, Any]]:
    try:
        pd, Prophet = _load_prophet_stack()
    except Exception as exc:
        return _seasonal_forecast(request), {
            "prophet_backend": "fallback_seasonal_proxy",
            "fallback_reason": str(exc),
        }

    try:
        df = pd.DataFrame(
            {
                "ds": [pt.ds for pt in request.y],
                "y": [float(pt.y) for pt in request.y],
            }
        )
        df["ds"] = pd.to_datetime(df["ds"])
        df = df.sort_values("ds")

        model = Prophet(
            daily_seasonality=(request.freq == "D"),
            weekly_seasonality=(request.freq == "D"),
            yearly_seasonality=(request.freq in {"W", "M"}),
            interval_width=0.8,
        )
        model.fit(df)

        freq_code = _prophet_freq_code(request.freq)
        future = model.make_future_dataframe(
            periods=request.horizon,
            freq=freq_code,
            include_history=False,
        )
        fc = model.predict(future)

        points: List[ForecastPoint] = []
        for _, row in fc.iterrows():
            points.append(
                ForecastPoint(
                    ds=row["ds"].strftime("%Y-%m-%d"),
                    yhat=round(float(row["yhat"]), 4),
                    yhat_lower=round(float(row["yhat_lower"]), 4),
                    yhat_upper=round(float(row["yhat_upper"]), 4),
                )
            )

        return points, {
            "prophet_backend": "prophet",
            "seasonality_mode": "additive",
        }
    except Exception as exc:
        return _seasonal_forecast(request), {
            "prophet_backend": "fallback_seasonal_proxy",
            "fallback_reason": str(exc),
        }


def _xgboost_forecast(
    request: ForecastRequest,
) -> Tuple[List[ForecastPoint], Dict[str, Any]]:
    ys = [float(pt.y) for pt in request.y]
    last_ds = request.y[-1].ds
    lag_count = min(14, max(5, len(ys) // 8))

    if len(ys) <= lag_count + 1:
        points = _trend_forecast(request)
        return points, {
            "xgboost_backend": "fallback_trend_proxy",
            "fallback_reason": "insufficient_history_for_lag_features",
            "lag_count": lag_count,
        }

    try:
        np, XGBRegressor = _load_xgboost_stack()
    except Exception as exc:
        points = _trend_forecast(request)
        return points, {
            "xgboost_backend": "fallback_trend_proxy",
            "fallback_reason": str(exc),
            "lag_count": lag_count,
        }

    try:
        cache_key = _xgboost_model_cache_key(request, ys, lag_count)
        cached = _xgboost_get_cached_model(cache_key)

        model_cache_hit = False
        train_rows = 0
        if cached:
            model, lag_count, sigma = cached
            model_cache_hit = True
        else:
            X, y = [], []
            for i in range(lag_count, len(ys)):
                X.append(ys[i - lag_count: i])
                y.append(ys[i])

            x_arr = np.array(X, dtype=float)
            y_arr = np.array(y, dtype=float)
            train_rows = int(x_arr.shape[0])

            model = XGBRegressor(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="reg:squarederror",
                random_state=42,
                n_jobs=1,
            )
            model.fit(x_arr, y_arr)

            residuals = y_arr - model.predict(x_arr)
            sigma = float(np.std(residuals)) if residuals.size else 1.0
            sigma = max(sigma, 1.0)
            _xgboost_set_cached_model(cache_key, model, lag_count, sigma)

        history = ys[-lag_count:]
        preds: List[float] = []
        for _ in range(request.horizon):
            features = np.array(history[-lag_count:], dtype=float).reshape(1, -1)
            yhat = float(model.predict(features)[0])
            preds.append(yhat)
            history.append(yhat)

        points: List[ForecastPoint] = []
        for i in range(1, request.horizon + 1):
            ds = _increment_date(last_ds, request.freq, i)
            yhat = preds[i - 1]
            band = sigma * 1.28  # approx. 80% interval
            points.append(
                ForecastPoint(
                    ds=ds,
                    yhat=round(yhat, 4),
                    yhat_lower=round(yhat - band, 4),
                    yhat_upper=round(yhat + band, 4),
                )
            )

        return points, {
            "xgboost_backend": "xgboost",
            "lag_count": lag_count,
            "train_rows": train_rows,
            "model_cache_hit": model_cache_hit,
        }
    except Exception as exc:
        points = _trend_forecast(request)
        return points, {
            "xgboost_backend": "fallback_trend_proxy",
            "fallback_reason": str(exc),
            "lag_count": lag_count,
        }


def route_model(
    request: ForecastRequest,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """Pick model based on hint and basic routing heuristics."""
    routing_config = config or {
        "enable_sarima": ROUTING_ENABLE_SARIMA,
        "enable_prophet": ROUTING_ENABLE_PROPHET,
        "enable_xgboost": ROUTING_ENABLE_XGBOOST,
        "prophet_min_obs": ROUTING_PROPHET_MIN_OBS,
        "prophet_min_horizon": ROUTING_PROPHET_MIN_HORIZON,
        "sarima_min_obs": ROUTING_SARIMA_MIN_OBS,
        "xgboost_min_obs": ROUTING_XGBOOST_MIN_OBS,
        "xgboost_max_horizon": ROUTING_XGBOOST_MAX_HORIZON,
    }

    if request.model_hint == "dummy":
        return "dummy_v0", "hint_dummy"
    if request.model_hint == "sarima" and routing_config["enable_sarima"]:
        return "sarima_v0", "hint_sarima"
    if request.model_hint == "sarima" and not routing_config["enable_sarima"]:
        return "dummy_v0", "hint_sarima_disabled"
    if request.model_hint == "prophet" and routing_config["enable_prophet"]:
        return "prophet_v0", "hint_prophet"
    if request.model_hint == "prophet" and not routing_config["enable_prophet"]:
        return "dummy_v0", "hint_prophet_disabled"
    if request.model_hint == "xgboost" and routing_config["enable_xgboost"]:
        return "xgboost_v0", "hint_xgboost"
    if request.model_hint == "xgboost" and not routing_config["enable_xgboost"]:
        return "dummy_v0", "hint_xgboost_disabled"

    n_obs = len(request.y)
    if (
        routing_config["enable_xgboost"]
        and request.freq == "D"
        and n_obs >= routing_config["xgboost_min_obs"]
        and request.horizon <= routing_config["xgboost_max_horizon"]
    ):
        return "xgboost_v0", "auto_short_horizon_dense_series"
    if (
        routing_config["enable_prophet"]
        and request.freq == "D"
        and n_obs >= routing_config["prophet_min_obs"]
        and request.horizon >= routing_config["prophet_min_horizon"]
    ):
        return "prophet_v0", "auto_daily_long_with_history"
    if routing_config["enable_sarima"] and n_obs >= routing_config["sarima_min_obs"]:
        return "sarima_v0", "auto_trend_series"
    return "dummy_v0", "auto_short_series"


def generate_forecast_for_model(
    request: ForecastRequest,
    model_id: str,
) -> Tuple[List[ForecastPoint], Dict[str, Any]]:
    model_metrics: Dict[str, Any] = {}
    if model_id == "dummy_v0":
        points = _flat_forecast(request)
    elif model_id == "sarima_v0":
        points, model_metrics = _sarima_forecast(request)
    elif model_id == "prophet_v0":
        points, model_metrics = _prophet_forecast(request)
    elif model_id == "xgboost_v0":
        points, model_metrics = _xgboost_forecast(request)
    else:
        raise ValueError(f"Unsupported model: {model_id}")

    metrics: Dict[str, Any] = {
        "obs_count": float(len(request.y)),
        "horizon": float(request.horizon),
    }
    metrics.update(model_metrics)
    return points, metrics


def reset_model_caches() -> None:
    """Reset import/model caches for deterministic tests."""
    _load_sarimax.cache_clear()
    _load_prophet_stack.cache_clear()
    _load_xgboost_stack.cache_clear()
    with _xgboost_cache_lock:
        _xgboost_model_cache.clear()
