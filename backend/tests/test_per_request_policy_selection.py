"""
Test C1: Per-Request Policy Selection

Validates that POST /score accepts an optional policy_id field
with correct precedence: request > env > default.
"""
import os
import pytest
from fastapi.testclient import TestClient

from main import app
from policy import PolicyLoader


client = TestClient(app)

FIXED_PAYLOAD = {
    "ticker": "AAPL",
    "profile": {
        "risk_level": "Medium",
        "horizon": "Long",
        "sector_preference": "Tech"
    }
}


class TestDefaultBehavior:
    """Requests without policy_id use env/default fallback."""

    def test_no_policy_id_returns_default(self):
        resp = client.post("/score", json=FIXED_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        # Should use env default or balanced_v1
        expected = os.getenv("FINLIFY_POLICY_ID", "balanced_v1")
        assert data["policy_id"] == expected

    def test_backward_compatible_with_old_request_format(self):
        """Existing clients without policy_id field must still work."""
        payload = {"ticker": "AAPL", "profile": {"risk_level": "Medium", "horizon": "Long", "sector_preference": "Tech"}}
        resp = client.post("/score", json=payload)
        assert resp.status_code == 200
        assert "policy_id" in resp.json()


class TestExplicitPolicySelection:
    """Requests with explicit policy_id use the requested policy."""

    def test_balanced_v1_explicit(self):
        payload = {**FIXED_PAYLOAD, "policy_id": "balanced_v1"}
        resp = client.post("/score", json=payload)
        assert resp.status_code == 200
        assert resp.json()["policy_id"] == "balanced_v1"
        assert resp.json()["strategy_name"] == "Balanced Baseline"

    def test_growth_hightech_v1_explicit(self):
        payload = {**FIXED_PAYLOAD, "policy_id": "growth_hightech_v1"}
        resp = client.post("/score", json=payload)
        assert resp.status_code == 200
        assert resp.json()["policy_id"] == "growth_hightech_v1"
        assert resp.json()["strategy_name"] == "High Growth Tech"

    def test_conservative_v1_explicit(self):
        payload = {**FIXED_PAYLOAD, "policy_id": "conservative_v1"}
        resp = client.post("/score", json=payload)
        assert resp.status_code == 200
        assert resp.json()["policy_id"] == "conservative_v1"
        assert resp.json()["strategy_name"] == "Conservative Stability"

    def test_response_includes_full_explanation(self):
        payload = {**FIXED_PAYLOAD, "policy_id": "growth_hightech_v1"}
        resp = client.post("/score", json=payload)
        data = resp.json()
        assert "explanation" in data
        assert len(data["explanation"]) == 4
        assert "score" in data
        assert "total_score" in data


class TestUnknownPolicy:
    """Requests with unknown policy_id return 400."""

    def test_unknown_policy_returns_400(self):
        payload = {**FIXED_PAYLOAD, "policy_id": "does_not_exist"}
        resp = client.post("/score", json=payload)
        assert resp.status_code == 400

    def test_unknown_policy_error_code(self):
        payload = {**FIXED_PAYLOAD, "policy_id": "does_not_exist"}
        resp = client.post("/score", json=payload)
        detail = resp.json()["detail"]
        assert detail["error"] == "UNKNOWN_POLICY_ID"

    def test_unknown_policy_error_message(self):
        payload = {**FIXED_PAYLOAD, "policy_id": "does_not_exist"}
        resp = client.post("/score", json=payload)
        detail = resp.json()["detail"]
        assert "does_not_exist" in detail["message"]
        assert "GET /strategies" in detail["message"]


class TestCacheSafety:
    """Sequential calls with different policy_ids must not leak stale cache."""

    def test_alternating_policies_return_correct_metadata(self):
        """Two calls with different policy_ids return different metadata."""
        payload_balanced = {**FIXED_PAYLOAD, "policy_id": "balanced_v1"}
        payload_growth = {**FIXED_PAYLOAD, "policy_id": "growth_hightech_v1"}

        resp1 = client.post("/score", json=payload_balanced)
        resp2 = client.post("/score", json=payload_growth)

        assert resp1.json()["policy_id"] == "balanced_v1"
        assert resp2.json()["policy_id"] == "growth_hightech_v1"
        assert resp1.json()["strategy_name"] != resp2.json()["strategy_name"]

    def test_weights_differ_across_selected_policies(self):
        """Weights in explanation must reflect the selected policy, not a cached one."""
        payload_balanced = {**FIXED_PAYLOAD, "policy_id": "balanced_v1"}
        payload_growth = {**FIXED_PAYLOAD, "policy_id": "growth_hightech_v1"}

        resp1 = client.post("/score", json=payload_balanced)
        resp2 = client.post("/score", json=payload_growth)

        weights1 = [e["weight"] for e in resp1.json()["explanation"]]
        weights2 = [e["weight"] for e in resp2.json()["explanation"]]

        assert weights1 != weights2

    def test_three_sequential_policies_all_correct(self):
        """Three sequential calls with different policy_ids all return correct metadata."""
        for pid in ["balanced_v1", "growth_hightech_v1", "conservative_v1"]:
            payload = {**FIXED_PAYLOAD, "policy_id": pid}
            resp = client.post("/score", json=payload)
            assert resp.status_code == 200
            assert resp.json()["policy_id"] == pid
