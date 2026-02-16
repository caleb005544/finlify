from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app

client = TestClient(app)


def _payload(horizon: int = 7) -> dict:
    start = datetime(2025, 1, 1)
    return {
        "series_id": "tier-series",
        "freq": "D",
        "horizon": horizon,
        "model_hint": "xgboost",
        "y": [
            {"ds": (start + timedelta(days=i)).strftime("%Y-%m-%d"), "y": 100.0 + i}
            for i in range(40)
        ],
    }


def test_tiers_endpoint_returns_default_and_items():
    resp = client.get("/tiers")
    assert resp.status_code == 200
    data = resp.json()
    assert "default_tier" in data
    assert "tiers" in data
    assert any(item["tier"] == "demo" for item in data["tiers"])


def test_demo_tier_blocks_disallowed_model():
    resp = client.post(
        "/forecast",
        json=_payload(horizon=7),
        headers={"X-Finlify-Tier": "demo", "X-Client-Id": "demo-client"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "MODEL_NOT_ALLOWED_FOR_TIER"


def test_demo_tier_blocks_horizon_over_limit():
    payload = _payload(horizon=21)
    payload["model_hint"] = "sarima"
    resp = client.post(
        "/forecast",
        json=payload,
        headers={"X-Finlify-Tier": "demo", "X-Client-Id": "demo-client"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "TIER_HORIZON_EXCEEDED"


def test_unknown_tier_returns_400():
    resp = client.post(
        "/forecast",
        json=_payload(horizon=7),
        headers={"X-Finlify-Tier": "unknown"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "UNKNOWN_TIER"
