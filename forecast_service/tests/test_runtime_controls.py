from fastapi.testclient import TestClient

from app.main import app, tier_manager
from app.runtime import SQLiteUsageLogger, UsageEvent

client = TestClient(app)


def _payload(series_id: str) -> dict:
    return {
        "series_id": series_id,
        "freq": "D",
        "horizon": 3,
        "y": [{"ds": "2025-01-01", "y": 100.0}, {"ds": "2025-01-02", "y": 101.0}],
    }


def test_quota_exceeded_returns_429():
    previous = tier_manager._tiers["demo"]["daily_quota"]
    tier_manager._tiers["demo"]["daily_quota"] = 1
    try:
        headers = {"X-Finlify-Tier": "demo", "X-Client-Id": "quota-client"}
        first = client.post("/forecast", json=_payload("quota-series"), headers=headers)
        second = client.post("/forecast", json=_payload("quota-series"), headers=headers)
        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["detail"]["error"] == "QUOTA_EXCEEDED"
    finally:
        tier_manager._tiers["demo"]["daily_quota"] = previous


def test_usage_endpoint_returns_items():
    resp = client.post("/forecast", json=_payload("usage-series"))
    assert resp.status_code == 200

    usage = client.get("/usage").json()
    assert "items" in usage
    assert len(usage["items"]) >= 1
    event = usage["items"][-1]
    assert event["series_id"] == "usage-series"
    assert event["model_used"] in {"dummy_v0", "sarima_v0", "prophet_v0", "xgboost_v0"}


def test_runtime_status_summary_and_clear_endpoints():
    # Seed one request so runtime stores have data.
    resp = client.post("/forecast", json=_payload("ops-series"))
    assert resp.status_code == 200

    status = client.get("/runtime/status")
    assert status.status_code == 200
    status_data = status.json()
    assert "cache" in status_data
    assert "quota" in status_data
    assert "usage" in status_data
    assert status_data["usage"]["stored_events"] >= 1

    summary = client.get("/runtime/summary")
    assert summary.status_code == 200
    summary_data = summary.json()
    assert "usage" in summary_data
    assert summary_data["usage"]["total_calls"] >= 1
    assert "p95_runtime_ms" in summary_data["usage"]
    assert "p99_runtime_ms" in summary_data["usage"]

    clear = client.post("/runtime/clear")
    assert clear.status_code == 200
    clear_data = clear.json()
    assert "cleared" in clear_data

    after = client.get("/runtime/status").json()
    assert after["cache"]["entries"] == 0
    assert after["usage"]["stored_events"] == 0


def test_sqlite_usage_logger_persists_between_instances(tmp_path):
    db_path = tmp_path / "usage.sqlite3"
    logger1 = SQLiteUsageLogger(db_path=str(db_path), max_items=100)
    logger1.clear()
    logger1.append(
        UsageEvent(
            ts="2026-01-01T00:00:00+00:00",
            series_id="persist-series",
            model_used="dummy_v0",
            cache_hit=False,
            runtime_ms=12,
        )
    )

    logger2 = SQLiteUsageLogger(db_path=str(db_path), max_items=100)
    rows = logger2.recent(limit=10)
    assert len(rows) == 1
    assert rows[0]["series_id"] == "persist-series"
