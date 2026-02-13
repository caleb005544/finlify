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

    def test_contains_dummy_v0(self):
        data = client.get("/models").json()
        ids = [m["model_id"] for m in data]
        assert "dummy_v0" in ids

    def test_model_has_required_fields(self):
        data = client.get("/models").json()
        for m in data:
            assert "model_id" in m
            assert "description" in m
            assert "status" in m

    def test_dummy_model_is_active(self):
        data = client.get("/models").json()
        dummy = [m for m in data if m["model_id"] == "dummy_v0"][0]
        assert dummy["status"] == "active"
