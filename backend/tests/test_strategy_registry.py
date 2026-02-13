"""
Test B (v2.1): Strategy Registry — GET /strategies

Validates that the endpoint returns a deterministic, well-formed list
of all available policies.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from policy import PolicyLoader


client = TestClient(app)


REQUIRED_ITEM_FIELDS = [
    "policy_id", "policy_version", "strategy_name",
    "description", "factors", "thresholds",
]

OFFICIAL_IDS = ["balanced_v1", "growth_hightech_v1", "conservative_v1"]


class TestStrategyEndpoint:
    """Tests against GET /strategies HTTP endpoint."""

    def test_returns_200(self):
        resp = client.get("/strategies")
        assert resp.status_code == 200

    def test_returns_list(self):
        data = client.get("/strategies").json()
        assert isinstance(data, list)

    def test_finds_all_official_policies(self):
        data = client.get("/strategies").json()
        ids = [item["policy_id"] for item in data]
        for oid in OFFICIAL_IDS:
            assert oid in ids, f"Official policy '{oid}' missing from /strategies"

    def test_at_least_three_policies(self):
        data = client.get("/strategies").json()
        assert len(data) >= 3

    def test_each_item_has_required_fields(self):
        data = client.get("/strategies").json()
        for item in data:
            for field in REQUIRED_ITEM_FIELDS:
                assert field in item, (
                    f"Missing field '{field}' in strategy '{item.get('policy_id', '?')}'"
                )

    def test_factors_keys_match_required_dimensions(self):
        data = client.get("/strategies").json()
        required_dims = set(PolicyLoader.REQUIRED_DIMENSIONS)
        for item in data:
            fkeys = set(item["factors"].keys())
            assert fkeys == required_dims, (
                f"Factor keys mismatch in '{item['policy_id']}': {fkeys} != {required_dims}"
            )

    def test_thresholds_contain_required_keys(self):
        data = client.get("/strategies").json()
        required = {"strong_buy", "buy", "hold", "sell"}
        for item in data:
            tkeys = set(item["thresholds"].keys())
            assert required.issubset(tkeys), (
                f"Missing thresholds in '{item['policy_id']}': {required - tkeys}"
            )

    def test_factors_values_are_numeric(self):
        data = client.get("/strategies").json()
        for item in data:
            for dim, weight in item["factors"].items():
                assert isinstance(weight, (int, float)), (
                    f"Non-numeric weight for '{dim}' in '{item['policy_id']}': {weight}"
                )

    def test_deterministic_ordering(self):
        """Official policies appear first in preferred order."""
        data = client.get("/strategies").json()
        ids = [item["policy_id"] for item in data]
        # All three official policies should appear as the first three
        assert ids[:3] == OFFICIAL_IDS, (
            f"Expected first 3 to be {OFFICIAL_IDS}, got {ids[:3]}"
        )

    def test_ordering_is_stable_across_calls(self):
        ids1 = [item["policy_id"] for item in client.get("/strategies").json()]
        ids2 = [item["policy_id"] for item in client.get("/strategies").json()]
        assert ids1 == ids2, "Ordering should be stable across calls"


class TestListPoliciesHelper:
    """Tests against PolicyLoader.list_policies() directly."""

    def test_returns_list_of_scoring_policies(self):
        policies = PolicyLoader.list_policies()
        assert isinstance(policies, list)
        assert len(policies) >= 3
        for p in policies:
            assert hasattr(p, "policy_id")
            assert hasattr(p, "strategy_name")

    def test_preferred_order(self):
        policies = PolicyLoader.list_policies()
        ids = [p.policy_id for p in policies]
        assert ids[:3] == OFFICIAL_IDS

    def test_weights_differ_across_strategies(self):
        """Sanity check: at least two strategies have different weights."""
        policies = PolicyLoader.list_policies()
        weights_sets = []
        for p in policies:
            w = tuple(p.factors[d].weight for d in PolicyLoader.REQUIRED_DIMENSIONS)
            weights_sets.append(w)
        assert len(set(weights_sets)) > 1, "Strategies should have different weights"
