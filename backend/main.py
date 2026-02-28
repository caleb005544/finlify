from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, List, Optional
import os
import time
import httpx
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

# ---------------------------------------------------------------------------
# Finnhub market data integration
# ---------------------------------------------------------------------------

FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"
MARKET_CACHE_TTL = int(os.getenv("MARKET_CACHE_TTL_SECONDS", "60"))

_market_cache: dict[str, tuple[Any, float]] = {}


def _cache_get(key: str) -> Optional[Any]:
    entry = _market_cache.get(key)
    if entry and (time.time() - entry[1]) < MARKET_CACHE_TTL:
        return entry[0]
    return None


def _cache_set(key: str, value: Any) -> None:
    _market_cache[key] = (value, time.time())


def _finnhub(path: str, params: Optional[dict] = None) -> Any:
    """Synchronous Finnhub API call with structured error handling."""
    if not FINNHUB_API_KEY:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "FINNHUB_NOT_CONFIGURED",
                "message": "FINNHUB_API_KEY environment variable is not set.",
            },
        )
    try:
        merged = {"token": FINNHUB_API_KEY, **(params or {})}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{FINNHUB_BASE}{path}", params=merged)
        if resp.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail={"error": "RATE_LIMITED", "message": "Finnhub rate limit reached. Try again shortly."},
            )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail={"error": "UPSTREAM_ERROR", "message": f"Finnhub returned HTTP {resp.status_code}"},
            )
        return resp.json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail={"error": "UPSTREAM_TIMEOUT", "message": "Finnhub request timed out."},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": "UPSTREAM_ERROR", "message": str(exc)})


def _range_to_from_ts(range_str: str) -> int:
    """Convert a range string like '3m' into a unix timestamp for Finnhub /candle from= param."""
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
        "all": 1825,  # 5 years
    }
    days = days_map.get(range_str.lower(), 30)
    return int((datetime.now() - timedelta(days=days)).timestamp())


# ---------------------------------------------------------------------------
# Legacy mock forecast (backend) – kept for backward compat with frontend
# The real forecasting runs in forecast_service on port 8001.
# ---------------------------------------------------------------------------

@app.post("/forecast")
def get_forecast(request: ForecastRequest):
    seed = sum(ord(c) for c in request.ticker)
    base_price = 150.0
    data = []
    for i in range(request.days):
        date = (datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        trend = (seed % 10 - 5) / 10.0
        noise = (i % 5 - 2) / 2.0
        val = base_price + (i * trend) + noise
        data.append({
            "date": date,
            "value": round(val, 2),
            "confidence_low": round(val * 0.9, 2),
            "confidence_high": round(val * 1.1, 2),
        })
    return data


# ---------------------------------------------------------------------------
# Real market data endpoints (Finnhub-backed)
# ---------------------------------------------------------------------------

@app.get("/api/quotes")
def get_quote(ticker: str):
    key = f"quote:{ticker.upper()}"
    cached = _cache_get(key)
    if cached:
        return cached

    symbol = ticker.upper()

    # --- quote (price / change) ---
    q = _finnhub("/quote", {"symbol": symbol})
    price = float(q.get("c") or 0)
    prev_close = float(q.get("pc") or price)
    change = round(price - prev_close, 2)
    change_pct = round((change / prev_close * 100) if prev_close else 0, 2)

    # --- company profile (name, market cap) ---
    profile = _finnhub("/stock/profile2", {"symbol": symbol})
    name = profile.get("name") or f"{symbol} Inc."
    market_cap_millions = float(profile.get("marketCapitalization") or 0)
    market_cap = int(market_cap_millions * 1_000_000)

    # --- basic financials (P/E, EPS, volume) ---
    metrics_resp = _finnhub("/stock/metric", {"symbol": symbol, "metric": "all"})
    m = metrics_resp.get("metric") or {}
    pe_ratio = round(float(m.get("peNormalizedAnnual") or m.get("pe") or 0), 2)
    eps = round(float(m.get("epsBasicExclExtraItemsAnnual") or m.get("eps") or 0), 2)
    volume = int(m.get("10DayAverageTradingVolume") or 0) * 1_000  # reported in thousands

    result = {
        "ticker": symbol,
        "name": name,
        "price": round(price, 2),
        "change": change,
        "change_percent": change_pct,
        "market_cap": market_cap,
        "pe_ratio": pe_ratio,
        "eps": eps,
        "volume": volume,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    _cache_set(key, result)
    return result


@app.get("/api/history")
def get_history(ticker: str, time_range: str = Query("1m", alias="range")):
    symbol = ticker.upper()
    normalized = time_range.lower()
    key = f"history:{symbol}:{normalized}"
    cached = _cache_get(key)
    if cached:
        return cached

    from_ts = _range_to_from_ts(normalized)
    to_ts = int(datetime.now().timestamp())

    candle = _finnhub("/stock/candle", {
        "symbol": symbol,
        "resolution": "D",
        "from": from_ts,
        "to": to_ts,
    })

    if candle.get("s") == "no_data" or not candle.get("t"):
        raise HTTPException(
            status_code=404,
            detail={"error": "NO_DATA", "message": f"No history data for {symbol} in range '{normalized}'."},
        )

    timestamps = candle["t"]
    closes = candle["c"]
    data = [
        {"date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"), "value": round(float(close), 2)}
        for ts, close in zip(timestamps, closes)
    ]
    _cache_set(key, data)
    return data


@app.get("/api/search")
def search_stocks(q: str = Query(..., min_length=1)):
    """Search for stocks by ticker or company name. Returns [{ticker, name}]."""
    key = f"search:{q.lower()}"
    cached = _cache_get(key)
    if cached:
        return cached

    raw = _finnhub("/search", {"q": q})
    results = [
        {"ticker": item["displaySymbol"], "name": item["description"]}
        for item in (raw.get("result") or [])
        if item.get("type") == "Common Stock" and item.get("displaySymbol")
    ][:8]  # cap at 8 suggestions

    _cache_set(key, results)
    return results
