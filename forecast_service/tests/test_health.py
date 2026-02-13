"""Tests for GET /health endpoint."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealth:
    def test_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_status_ok(self):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_includes_service_name(self):
        data = client.get("/health").json()
        assert "service" in data
        assert isinstance(data["service"], str)

    def test_includes_version(self):
        data = client.get("/health").json()
        assert "version" in data
