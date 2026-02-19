from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
import os
from datetime import datetime, timedelta

app = FastAPI(title="Finlify Backend")

def _parse_cors_origins() -> list[str]:
    raw = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["http://localhost:3000"]

_cors_origins = _parse_cors_origins()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class AssumptionProfile(BaseModel):
    risk_level: str
    horizon: str
    sector_preference: str

class ScoreRequest(BaseModel):
    ticker: str = "AAPL"
    profile: AssumptionProfile
    policy_id: Optional[str] = None  # Per-request policy selection

class ExplanationItem(BaseModel):
    dimension: str
    weight: float
    points: float
    reason: str

class ScoreResponse(BaseModel):
    score: float  # NEW: normalized score (0.0-1.0)
    total_score: int  # Display score (0-100)
    rating: int
    action: str
    explanation: List[ExplanationItem]  # NEW: per-dimension trace
    reasons: List[str]  # Legacy
    breakdown: dict
    policy_id: str
    policy_version: str
    strategy_name: str

class StrategyItem(BaseModel):
    policy_id: str
    policy_version: str
    strategy_name: str
    description: str
    factors: dict  # simplified weights: {dimension: weight}
    thresholds: dict


class PolicyVersionItem(BaseModel):
    policy_id: str
    policy_version: str
    strategy_name: str
    description: str
    active: bool


class PolicyVersionStateResponse(BaseModel):
    active_policy_id: str
    updated_at: str
    history: list
    versions: List[PolicyVersionItem]


class PolicyActivateRequest(BaseModel):
    policy_id: str
    actor: str = "system"
    reason: Optional[str] = None


class PolicyRollbackRequest(BaseModel):
    actor: str = "system"
    reason: Optional[str] = None


class ForecastRequest(BaseModel):
    ticker: str
    days: int = 30

# --- Routes ---
@app.get("/")
def read_root():
    return {"message": "Finlify Backend v1"}

from policy import PolicyLoader, apply_policy, ScoringPolicy

@app.post("/score", response_model=ScoreResponse)
def calculate_score(request: ScoreRequest):
    # Policy selection precedence: request > env > default
    if request.policy_id:
        try:
            policy = PolicyLoader.load_policy_by_id(request.policy_id)
        except FileNotFoundError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "UNKNOWN_POLICY_ID",
                    "message": f"policy_id '{request.policy_id}' not found. "
                               f"Use GET /strategies to list available policies."
                }
            )
    else:
        policy = PolicyLoader.get_policy()
    
    # Calculate using Policy Engine
    result = apply_policy(request.ticker, request.profile, policy)
    
    return result

@app.get("/strategies", response_model=List[StrategyItem])
def list_strategies():
    """List all available scoring strategies with metadata."""
    try:
        policies = PolicyLoader.list_policies()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        StrategyItem(
            policy_id=p.policy_id,
            policy_version=p.policy_version,
            strategy_name=p.strategy_name,
            description=p.description,
            factors={dim: cfg.weight for dim, cfg in p.factors.items()},
            thresholds=p.thresholds,
        )
        for p in policies
    ]


@app.get("/policy/versions", response_model=PolicyVersionStateResponse)
def get_policy_versions():
    try:
        return PolicyLoader.get_policy_version_state()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/policy/activate", response_model=PolicyVersionStateResponse)
def activate_policy_version(request: PolicyActivateRequest):
    try:
        return PolicyLoader.activate_policy_version(
            policy_id=request.policy_id,
            actor=request.actor,
            reason=request.reason,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "UNKNOWN_POLICY_ID",
                "message": f"policy_id '{request.policy_id}' not found.",
            },
        )


@app.post("/policy/rollback", response_model=PolicyVersionStateResponse)
def rollback_policy_version(request: PolicyRollbackRequest):
    try:
        return PolicyLoader.rollback_policy_version(
            actor=request.actor,
            reason=request.reason,
        )
    except ValueError as e:
        if str(e) == "NO_PREVIOUS_VERSION":
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "NO_PREVIOUS_VERSION",
                    "message": "No policy version history available to rollback.",
                },
            )
        raise

@app.post("/forecast")
def get_forecast(request: ForecastRequest):
    # Mock forecast data
    data = []
    base_price = 150.0
    # Use ticker hash for stable mock
    seed = sum(ord(c) for c in request.ticker)
    
    for i in range(request.days):
        date = (datetime.now() + timedelta(days=i+1)).strftime("%Y-%m-%d")
        
        # Determine trend based on seed
        trend = (seed % 10 - 5) / 10.0 # -0.5 to 0.5
        noise = (i % 5 - 2) / 2.0
        
        val = base_price + (i * trend) + noise
        
        data.append({
            "date": date,
            "value": round(val, 2),
            "confidence_low": round(val * 0.9, 2),
            "confidence_high": round(val * 1.1, 2)
        })
    return data

@app.get("/api/quotes")
def get_quote(ticker: str):
    # Proxy / Mock
    # In real app, call Yahoo Finance here
    seed = sum(ord(c) for c in ticker)
    price = (seed % 500) + 50
    change = (seed % 20) - 10
    market_cap = (seed % 2500 + 50) * 1_000_000_000
    pe_ratio = ((seed % 320) / 10.0) + 5.0
    eps = ((seed % 120) / 10.0) + 0.5
    volume = (seed % 40 + 1) * 1_000_000

    return {
        "ticker": ticker.upper(),
        "name": f"{ticker.upper()} Inc.",
        "price": round(price, 2),
        "change": round(change, 2),
        "change_percent": round((change / price) * 100, 2),
        "market_cap": int(market_cap),
        "pe_ratio": round(pe_ratio, 2),
        "eps": round(eps, 2),
        "volume": int(volume),
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

@app.get("/api/history")
def get_history(ticker: str, time_range: str = Query("1m", alias="range")):
    # Proxy / Mock
    days_map = {
        "1d": 1,
        "3d": 3,
        "1w": 7,
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "12m": 365,
        "1y": 365,
        "3y": 1095,
        "all": 1000,
    }
    normalized = time_range.lower()
    days = days_map.get(normalized, 30)
    
    data = []
    base_price = 150.0
    current = base_price
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    for i in range(max(days, 2)):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        change = (random.random() - 0.5) * 5
        current += change
        data.append({
            "date": date,
            "value": round(current, 2)
        })
        
    return data
