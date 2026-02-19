"""Finlify Forecast Service — V3.0."""

import time
import uuid
import os
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from .schemas import (
    ForecastRequest,
    ForecastResponse,
    ModelInfo,
    ForecastTrace,
)
from .forecast import route_model, generate_forecast_for_model
from .runtime import (
    ForecastCache,
    SeriesQuotaLimiter,
    SQLiteUsageLogger,
    TierPolicyManager,
    UsageEvent,
    build_cache_key,
)
from .settings import (
    SERVICE_NAME,
    SERVICE_VERSION,
    CACHE_TTL_SECONDS,
    SERIES_DAILY_QUOTA,
    USAGE_LOG_MAX_ITEMS,
    USAGE_LOG_DB_PATH,
    TIER_CONFIG,
    DEFAULT_TIER,
)

app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION,
    description="Time-series forecast service for Finlify (V3.0 dummy skeleton)",
)

def _parse_cors_origins() -> list[str]:
    raw = os.getenv("FORECAST_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["http://localhost:3000"]

_cors_origins = _parse_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

forecast_cache = ForecastCache(ttl_seconds=CACHE_TTL_SECONDS)
quota_limiter = SeriesQuotaLimiter(daily_limit=SERIES_DAILY_QUOTA)
usage_logger = SQLiteUsageLogger(
    db_path=USAGE_LOG_DB_PATH,
    max_items=USAGE_LOG_MAX_ITEMS,
)
tier_manager = TierPolicyManager(tiers=TIER_CONFIG, default_tier=DEFAULT_TIER)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Liveness / readiness probe."""
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.get("/models", response_model=List[ModelInfo])
def list_models():
    """List available forecast models."""
    return [
        ModelInfo(
            model_id="dummy_v0",
            description="Flat baseline model. Returns last observed value.",
            status="active",
        ),
        ModelInfo(
            model_id="sarima_v0",
            description="SARIMA baseline via statsmodels with safe fallback.",
            status="active",
        ),
        ModelInfo(
            model_id="prophet_v0",
            description="Prophet baseline with safe seasonal fallback.",
            status="active",
        ),
        ModelInfo(
            model_id="xgboost_v0",
            description="Gradient-boosted autoregressive baseline with safe fallback.",
            status="active",
        ),
    ]


@app.post("/forecast", response_model=ForecastResponse)
def create_forecast(
    request: ForecastRequest,
    x_finlify_tier: str = Header(default=None, alias="X-Finlify-Tier"),
    x_client_id: str = Header(default="anonymous", alias="X-Client-Id"),
):
    """Generate a forecast for the given time series."""
    if len(request.y) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "EMPTY_SERIES",
                "message": "y must contain at least one observation.",
            },
        )

    try:
        tier_policy = tier_manager.get_policy(x_finlify_tier)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "UNKNOWN_TIER",
                "message": f"tier '{x_finlify_tier}' is not configured.",
            },
        )

    if request.horizon > tier_policy["max_horizon"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "TIER_HORIZON_EXCEEDED",
                "message": (
                    f"tier '{tier_policy['name']}' allows horizon <= "
                    f"{tier_policy['max_horizon']}"
                ),
            },
        )

    quota_key = f"{x_client_id}:{tier_policy['name']}"
    allowed, quota_remaining = quota_limiter.allow_for_limit(
        quota_key,
        tier_policy["daily_quota"],
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "QUOTA_EXCEEDED",
                "message": (
                    f"Daily forecast quota exceeded for client '{x_client_id}' "
                    f"on tier '{tier_policy['name']}'."
                ),
            },
        )

    started_ms = time.monotonic_ns() // 1_000_000
    cache_key = build_cache_key(request)
    cached = forecast_cache.get(cache_key)
    if cached is not None:
        elapsed_ms = int(time.monotonic_ns() // 1_000_000 - started_ms)
        response = cached.model_copy(deep=True)
        response.request_id = str(uuid.uuid4())
        response.metrics["model_runtime_ms"] = 0
        response.metrics["overhead_runtime_ms"] = elapsed_ms
        response.trace = ForecastTrace(
            cache_hit=True,
            runtime_ms=elapsed_ms,
            quota_remaining=quota_remaining,
        )
        usage_logger.append(
            UsageEvent(
                ts=datetime.now(timezone.utc).isoformat(),
                series_id=request.series_id,
                model_used=response.model_used,
                cache_hit=True,
                runtime_ms=elapsed_ms,
            )
        )
        return response

    model_used, routing_reason = route_model(request)
    if not tier_manager.is_model_allowed(tier_policy["name"], model_used):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "MODEL_NOT_ALLOWED_FOR_TIER",
                "message": (
                    f"model '{model_used}' is not allowed for tier "
                    f"'{tier_policy['name']}'."
                ),
            },
        )
    inference_started_ms = time.monotonic_ns() // 1_000_000
    points, metrics = generate_forecast_for_model(request, model_used)
    inference_elapsed_ms = int(time.monotonic_ns() // 1_000_000 - inference_started_ms)
    elapsed_ms = int(time.monotonic_ns() // 1_000_000 - started_ms)
    metrics["model_runtime_ms"] = inference_elapsed_ms
    metrics["overhead_runtime_ms"] = max(elapsed_ms - inference_elapsed_ms, 0)

    response = ForecastResponse(
        request_id=str(uuid.uuid4()),
        model_used=model_used,
        routing_reason=routing_reason,
        forecast=points,
        metrics=metrics,
        trace=ForecastTrace(
            cache_hit=False,
            runtime_ms=elapsed_ms,
            quota_remaining=quota_remaining,
        ),
    )
    forecast_cache.set(cache_key, response)
    usage_logger.append(
        UsageEvent(
            ts=datetime.now(timezone.utc).isoformat(),
            series_id=request.series_id,
            model_used=response.model_used,
            cache_hit=False,
            runtime_ms=elapsed_ms,
        )
    )
    return response


@app.get("/tiers")
def list_tiers():
    """Expose current tier configuration for ops and product integration."""
    return tier_manager.list_tiers()


@app.get("/usage")
def usage(limit: int = 50):
    """Recent forecast calls for debugging/observability in local/dev."""
    safe_limit = max(1, min(limit, 500))
    return {"items": usage_logger.recent(limit=safe_limit)}


@app.get("/runtime/status")
def runtime_status():
    """Runtime status for cache, quota, and usage subsystems."""
    return {
        "cache": forecast_cache.stats(),
        "quota": quota_limiter.stats(limit=10),
        "usage": {
            "stored_events": usage_logger.count(),
            "max_items": USAGE_LOG_MAX_ITEMS,
            "db_path": USAGE_LOG_DB_PATH,
        },
        "tiers": tier_manager.list_tiers(),
    }


@app.get("/runtime/summary")
def runtime_summary():
    """Aggregate usage metrics for observability."""
    return {
        "usage": usage_logger.summary(),
        "quota": {
            "daily_limit": quota_limiter.daily_limit,
        },
        "cache": {
            "entries": forecast_cache.stats()["entries"],
            "ttl_seconds": forecast_cache.ttl_seconds,
        },
    }


@app.post("/runtime/clear")
def runtime_clear(cache: bool = True, quota: bool = True, usage: bool = True):
    """Clear selected runtime state containers."""
    cleared = {
        "cache": 0,
        "quota": 0,
        "usage": 0,
    }

    if cache:
        before = forecast_cache.stats()["entries"]
        forecast_cache.clear()
        cleared["cache"] = before

    if quota:
        before = quota_limiter.stats(limit=1000)["active_series"]
        quota_limiter.clear()
        cleared["quota"] = before

    if usage:
        cleared["usage"] = usage_logger.clear()

    return {"cleared": cleared}
