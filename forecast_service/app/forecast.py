"""Dummy forecast implementation for V3.0.

Produces deterministic, schema-correct forecasts using the last observed
value as a flat baseline. No real ML model is used.
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import List

from .schemas import (
    ForecastRequest,
    ForecastResponse,
    ForecastPoint,
    ForecastTrace,
)


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


def generate_dummy_forecast(request: ForecastRequest) -> ForecastResponse:
    """Generate a deterministic dummy forecast.

    Strategy:
    - Uses y[-1].y as the flat baseline for all forecast points
    - yhat_lower = baseline * 0.9
    - yhat_upper = baseline * 1.1
    - Dates increment based on freq from the last observed ds
    """
    start_ms = time.monotonic_ns() // 1_000_000

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

    elapsed_ms = int(time.monotonic_ns() // 1_000_000 - start_ms)

    return ForecastResponse(
        request_id=str(uuid.uuid4()),
        model_used="dummy_v0",
        routing_reason="v3.0_dummy",
        forecast=forecast_points,
        metrics={},
        trace=ForecastTrace(cache_hit=False, runtime_ms=elapsed_ms),
    )
