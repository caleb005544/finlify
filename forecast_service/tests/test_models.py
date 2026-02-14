"""Tests for GET /models endpoint."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestModels:
    def test_returns_200(self):
        resp = client.get("/models")
        assert resp.status_code == 200

    def test_returns_list(self):
        data = client.get("/models").json()
        assert isinstance(data, list)

    def test_contains_required_models(self):
        data = client.get("/models").json()
        ids = [m["model_id"] for m in data]
        assert "dummy_v0" in ids
        assert "sarima_v0" in ids
        assert "prophet_v0" in ids
        assert "xgboost_v0" in ids

    def test_model_has_required_fields(self):
        data = client.get("/models").json()
        for m in data:
            assert "model_id" in m
            assert "description" in m
            assert "status" in m

    def test_models_are_active(self):
        data = client.get("/models").json()
        statuses = {m["model_id"]: m["status"] for m in data}
        assert statuses["dummy_v0"] == "active"
        assert statuses["sarima_v0"] == "active"
        assert statuses["prophet_v0"] == "active"
        assert statuses["xgboost_v0"] == "active"
