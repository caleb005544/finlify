from fastapi.testclient import TestClient

from main import app
from policy import PolicyLoader


client = TestClient(app)


def _reset_loader():
    PolicyLoader._policy = None
    PolicyLoader._policy_cache = {}


def _score_payload():
    return {
        "ticker": "AAPL",
        "profile": {
            "risk_level": "Medium",
            "horizon": "Long",
            "sector_preference": "Tech",
        },
    }


def test_policy_versions_endpoint_returns_state(tmp_path, monkeypatch):
    monkeypatch.setenv("FINLIFY_POLICY_REGISTRY_PATH", str(tmp_path / "policy_registry.json"))
    _reset_loader()

    resp = client.get("/policy/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_policy_id" in data
    assert "versions" in data
    assert len(data["versions"]) >= 3
    assert any(v["active"] is True for v in data["versions"])


def test_activate_policy_and_score_uses_active(tmp_path, monkeypatch):
    monkeypatch.setenv("FINLIFY_POLICY_REGISTRY_PATH", str(tmp_path / "policy_registry.json"))
    _reset_loader()

    activate = client.post(
        "/policy/activate",
        json={"policy_id": "growth_hightech_v1", "actor": "test"},
    )
    assert activate.status_code == 200
    assert activate.json()["active_policy_id"] == "growth_hightech_v1"

    score = client.post("/score", json=_score_payload())
    assert score.status_code == 200
    assert score.json()["policy_id"] == "growth_hightech_v1"


def test_activate_unknown_policy_returns_400(tmp_path, monkeypatch):
    monkeypatch.setenv("FINLIFY_POLICY_REGISTRY_PATH", str(tmp_path / "policy_registry.json"))
    _reset_loader()

    resp = client.post(
        "/policy/activate",
        json={"policy_id": "unknown_policy", "actor": "test"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "UNKNOWN_POLICY_ID"


def test_rollback_without_history_returns_400(tmp_path, monkeypatch):
    monkeypatch.setenv("FINLIFY_POLICY_REGISTRY_PATH", str(tmp_path / "policy_registry.json"))
    _reset_loader()

    resp = client.post("/policy/rollback", json={"actor": "test"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "NO_PREVIOUS_VERSION"


def test_rollback_restores_previous_policy(tmp_path, monkeypatch):
    monkeypatch.setenv("FINLIFY_POLICY_REGISTRY_PATH", str(tmp_path / "policy_registry.json"))
    monkeypatch.setenv("FINLIFY_POLICY_ID", "balanced_v1")
    _reset_loader()

    first = client.get("/policy/versions").json()["active_policy_id"]
    assert first == "balanced_v1"

    activate = client.post(
        "/policy/activate",
        json={"policy_id": "growth_hightech_v1", "actor": "test"},
    )
    assert activate.status_code == 200
    assert activate.json()["active_policy_id"] == "growth_hightech_v1"

    rollback = client.post("/policy/rollback", json={"actor": "test"})
    assert rollback.status_code == 200
    assert rollback.json()["active_policy_id"] == "balanced_v1"
