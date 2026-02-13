from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import random
from datetime import datetime, timedelta

app = FastAPI(title="Finlify Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
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
    
    return {
        "ticker": ticker.upper(),
        "name": f"{ticker.upper()} Inc.",
        "price": round(price, 2),
        "change": round(change, 2),
        "change_percent": round((change / price) * 100, 2)
    }

@app.get("/api/history")
def get_history(ticker: str, range: str = "1m"):
    # Proxy / Mock
    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "all": 1000}
    days = days_map.get(range.lower(), 30)
    
    data = []
    base_price = 150.0
    current = base_price
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    for i in range(days):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        change = (random.random() - 0.5) * 5
        current += change
        data.append({
            "date": date,
            "value": round(current, 2)
        })
        
    return data
