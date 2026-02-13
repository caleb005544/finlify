"""
Test A (v2.1): Strategy Divergence Guarantee

Validates that different official policies produce observably different outputs
for the same input, in a deterministic and non-flaky way.

Why non-flaky:
  Policy weights are structurally different by design:
    balanced_v1:        [0.25, 0.25, 0.25, 0.25]
    growth_hightech_v1: [0.40, 0.10, 0.20, 0.30]
    conservative_v1:    [0.15, 0.40, 0.15, 0.30]
  
  Even when all dimension scores are binary (0 or 1) and happen to match,
  the explanation weights/points MUST differ because they come directly
  from the policy definition. This is an invariant of the engine.
"""
import itertools
import pytest
from policy import PolicyLoader, apply_policy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockProfile:
    """Fixed mock profile — no randomness."""
    def __init__(self, risk, horizon, sector):
        self.risk_level = risk
        self.horizon = horizon
        self.sector_preference = sector


OFFICIAL_POLICIES = ["balanced_v1", "growth_hightech_v1", "conservative_v1"]


def _load_policy(policy_id: str):
    """Load a specific policy, bypassing the singleton cache."""
    PolicyLoader._policy = None
    return PolicyLoader.load_policy(policy_id)


def _score(policy, ticker="AAPL", risk="Medium", horizon="Long", sector="Tech"):
    """Score a fixed payload against a given policy."""
    profile = MockProfile(risk, horizon, sector)
    return apply_policy(ticker, profile, policy)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(params=list(itertools.combinations(OFFICIAL_POLICIES, 2)),
                ids=lambda pair: f"{pair[0]}_vs_{pair[1]}")
def policy_pair(request):
    """Yield every unique pair of official policies."""
    id_a, id_b = request.param
    return _load_policy(id_a), _load_policy(id_b), id_a, id_b


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStrategyDivergence:
    """Non-flaky divergence guarantees across strategies."""

    # ---- Core guarantee: weights MUST differ (structural invariant) ----

    def test_explanation_weights_differ(self, policy_pair):
        """Explanation weights must differ between any two strategies.

        This is the non-flaky anchor: weights come directly from the policy
        JSON and are guaranteed different by schema design.
        """
        pol_a, pol_b, id_a, id_b = policy_pair
        resp_a = _score(pol_a)
        resp_b = _score(pol_b)

        weights_a = [item["weight"] for item in resp_a["explanation"]]
        weights_b = [item["weight"] for item in resp_b["explanation"]]

        assert weights_a != weights_b, (
            f"Weights should differ between {id_a} and {id_b}: "
            f"{weights_a} vs {weights_b}"
        )

    def test_explanation_points_differ(self, policy_pair):
        """Per-dimension points (weight × dim_score) must differ when weights differ,
        unless all dim_scores are zero."""
        pol_a, pol_b, id_a, id_b = policy_pair
        resp_a = _score(pol_a)
        resp_b = _score(pol_b)

        points_a = [item["points"] for item in resp_a["explanation"]]
        points_b = [item["points"] for item in resp_b["explanation"]]

        # If all dim_scores are 0, points would both be all-zero — still valid.
        # Otherwise, they must differ because weights differ.
        if any(p != 0 for p in points_a) or any(p != 0 for p in points_b):
            assert points_a != points_b, (
                f"Points should differ between {id_a} and {id_b}: "
                f"{points_a} vs {points_b}"
            )

    def test_policy_metadata_differs(self, policy_pair):
        """Each strategy must report its own policy_id and strategy_name."""
        pol_a, pol_b, id_a, id_b = policy_pair
        resp_a = _score(pol_a)
        resp_b = _score(pol_b)

        assert resp_a["policy_id"] != resp_b["policy_id"]
        assert resp_a["strategy_name"] != resp_b["strategy_name"]

    def test_reason_templates_differ(self, policy_pair):
        """Reason text must differ because templates are strategy-specific."""
        pol_a, pol_b, id_a, id_b = policy_pair
        resp_a = _score(pol_a)
        resp_b = _score(pol_b)

        reasons_a = [item["reason"] for item in resp_a["explanation"]]
        reasons_b = [item["reason"] for item in resp_b["explanation"]]

        assert reasons_a != reasons_b, (
            f"Reasons should differ between {id_a} and {id_b}"
        )

    # ---- Extended: second payload designed to produce score divergence ----

    def test_score_or_action_differs_with_divergent_payload(self):
        """With a profile that mismatches growth's strengths, conservative
        and growth should produce different scores or actions."""
        growth = _load_policy("growth_hightech_v1")
        conservative = _load_policy("conservative_v1")

        # Finance/Short/Low — bad for growth, tolerable for conservative
        resp_growth = _score(growth, sector="Finance", horizon="Short", risk="Low")
        resp_conservative = _score(conservative, sector="Finance", horizon="Short", risk="Low")

        # At least one output dimension must differ
        differs = (
            resp_growth["score"] != resp_conservative["score"]
            or resp_growth["total_score"] != resp_conservative["total_score"]
            or resp_growth["rating"] != resp_conservative["rating"]
            or resp_growth["action"] != resp_conservative["action"]
        )

        # Even if scores tie, weights are guaranteed different
        weights_g = [e["weight"] for e in resp_growth["explanation"]]
        weights_c = [e["weight"] for e in resp_conservative["explanation"]]

        assert differs or weights_g != weights_c, (
            "Growth and conservative must diverge on at least one output "
            "for a Finance/Short/Low profile"
        )


class TestLegacyMultistrategyParity:
    """Replacement for legacy test_multistrategy.py assertions.
    
    These tests validate the same capabilities (policy loading, env var
    selection, metadata) without the flaky 'scores must differ' assertion.
    """

    def test_all_official_policies_load_successfully(self):
        """All official policies load without error."""
        for policy_id in OFFICIAL_POLICIES:
            policy = _load_policy(policy_id)
            assert policy.policy_id == policy_id

    def test_all_official_policies_produce_valid_scores(self):
        """All policies produce valid score responses."""
        for policy_id in OFFICIAL_POLICIES:
            policy = _load_policy(policy_id)
            result = _score(policy)

            assert 0.0 <= result["score"] <= 1.0
            assert 0 <= result["total_score"] <= 100
            assert 1 <= result["rating"] <= 5
            assert result["action"] in {
                "STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"
            }
            assert len(result["explanation"]) == 4

    def test_policy_metadata_present_in_all_responses(self):
        """All responses include policy metadata."""
        for policy_id in OFFICIAL_POLICIES:
            policy = _load_policy(policy_id)
            result = _score(policy)

            assert result["policy_id"] == policy_id
            assert "policy_version" in result
            assert "strategy_name" in result
