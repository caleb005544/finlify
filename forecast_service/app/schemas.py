"""Pydantic request/response models for the forecast API contract."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import date


class Point(BaseModel):
    """A single observed data point."""
    ds: str = Field(..., description="Date or datetime string (ISO format)")
    y: float = Field(..., description="Observed value")


class ForecastRequest(BaseModel):
    """Request body for POST /forecast."""
    series_id: str = Field(..., description="Unique identifier for the time series")
    freq: str = Field(
        ...,
        description="Frequency: 'D' (daily), 'W' (weekly), 'M' (monthly)",
    )
    horizon: int = Field(
        ..., ge=1, le=365,
        description="Number of future periods to forecast (1-365)",
    )
    y: List[Point] = Field(..., description="Historical observations")
    exog: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Exogenous variables (accepted but ignored in V3.0)",
    )
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Forecast constraints (accepted but ignored in V3.0)",
    )
    model_hint: Optional[str] = Field(
        default="auto",
        description="Model preference hint: auto|dummy|sarima|prophet|xgboost",
    )
    policy_id: Optional[str] = Field(
        default=None,
        description="Scoring policy alignment (accepted but ignored in V3.0)",
    )

    @field_validator("freq")
    @classmethod
    def validate_freq(cls, v):
        allowed = {"D", "W", "M"}
        if v.upper() not in allowed:
            raise ValueError(f"freq must be one of {allowed}, got '{v}'")
        return v.upper()

    @field_validator("model_hint")
    @classmethod
    def validate_model_hint(cls, v):
        if v is None:
            return "auto"
        hint = v.lower().strip()
        allowed = {"auto", "dummy", "sarima", "prophet", "xgboost"}
        if hint not in allowed:
            raise ValueError(f"model_hint must be one of {allowed}, got '{v}'")
        return hint


class ForecastPoint(BaseModel):
    """A single forecast point."""
    ds: str
    yhat: float
    yhat_lower: float
    yhat_upper: float


class ForecastTrace(BaseModel):
    """Execution trace metadata."""
    cache_hit: bool = False
    runtime_ms: int = 0
    quota_remaining: int = 0


class ForecastResponse(BaseModel):
    """Response body for POST /forecast."""
    request_id: str
    model_used: str
    routing_reason: str
    forecast: List[ForecastPoint]
    metrics: Dict[str, Any] = {}
    trace: ForecastTrace


class ModelInfo(BaseModel):
    """Model metadata for GET /models."""
    model_id: str
    description: str
    status: str
