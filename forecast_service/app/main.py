"""Finlify Forecast Service — V3.0 (dummy skeleton)."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from .schemas import (
    ForecastRequest,
    ForecastResponse,
    ModelInfo,
)
from .forecast import generate_dummy_forecast
from .settings import SERVICE_NAME, SERVICE_VERSION

app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION,
    description="Time-series forecast service for Finlify (V3.0 dummy skeleton)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            description="Flat baseline dummy model (V3.0 skeleton). "
                        "Returns last observed value as forecast.",
            status="active",
        )
    ]


@app.post("/forecast", response_model=ForecastResponse)
def create_forecast(request: ForecastRequest):
    """Generate a forecast for the given time series."""
    if len(request.y) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "EMPTY_SERIES",
                "message": "y must contain at least one observation.",
            },
        )

    return generate_dummy_forecast(request)
