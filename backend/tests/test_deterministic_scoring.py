"""
Test C: Deterministic Scoring

Validates that scoring is deterministic and consistent:
- Same input produces identical output
- Explanation points sum equals score
- Total score equals round(score * 100)
- Dimension order is deterministic
"""
import pytest
from policy import PolicyLoader, apply_policy


class MockProfile:
    """Mock profile for testing."""
    def __init__(self, risk, horizon, sector):
        self.risk_level = risk
        self.horizon = horizon
        self.sector_preference = sector


class TestDeterministicScoring:
    """Deterministic scoring tests."""
    
    def test_identical_inputs_produce_identical_outputs(self, balanced_policy):
        """Test that same input produces identical output."""
        ticker = "AAPL"
        profile = MockProfile("Medium", "Long", "Tech")
        
        # Call apply_policy twice with same inputs
        result1 = apply_policy(ticker, profile, balanced_policy)
        result2 = apply_policy(ticker, profile, balanced_policy)
        
        # Verify identical results
        assert result1["score"] == result2["score"]
        assert result1["total_score"] == result2["total_score"]
        assert result1["rating"] == result2["rating"]
        assert result1["action"] == result2["action"]
        assert result1["explanation"] == result2["explanation"]
    
    def test_explanation_points_sum_equals_score(self, balanced_policy):
        """Test that sum of explanation points equals score."""
        ticker = "AAPL"
        profile = MockProfile("Medium", "Long", "Tech")
        
        result = apply_policy(ticker, profile, balanced_policy)
        
        points_sum = sum(e["points"] for e in result["explanation"])
        score = result["score"]
        
        tolerance = 1e-9
        assert abs(points_sum - score) < tolerance, (
            f"Points sum ({points_sum}) != score ({score})"
        )
    
    def test_total_score_equals_rounded_score(self, balanced_policy):
        """Test that total_score equals round(score * 100)."""
        ticker = "AAPL"
        profile = MockProfile("Medium", "Long", "Tech")
        
        result = apply_policy(ticker, profile, balanced_policy)
        
        expected_total = round(result["score"] * 100)
        actual_total = result["total_score"]
        
        assert actual_total == expected_total, (
            f"total_score ({actual_total}) != round(score*100) ({expected_total})"
        )
    
    def test_dimension_order_is_deterministic(self, balanced_policy, required_dimensions):
        """Test that explanation dimensions are in deterministic order."""
        ticker = "AAPL"
        profile = MockProfile("Medium", "Long", "Tech")
        
        result = apply_policy(ticker, profile, balanced_policy)
        
        actual_dims = [e["dimension"] for e in result["explanation"]]
        expected_dims = required_dimensions
        
        assert actual_dims == expected_dims, (
            f"Dimension order mismatch: {actual_dims} != {expected_dims}"
        )
    
    def test_explanation_has_all_required_fields(self, balanced_policy):
        """Test that each explanation item has all required fields."""
        ticker = "AAPL"
        profile = MockProfile("Medium", "Long", "Tech")
        
        result = apply_policy(ticker, profile, balanced_policy)
        
        required_fields = ["dimension", "weight", "points", "reason"]
        
        for exp in result["explanation"]:
            for field in required_fields:
                assert field in exp, f"Missing field '{field}' in explanation item"
    
    def test_response_has_all_required_fields(self, balanced_policy):
        """Test that response has all required fields."""
        ticker = "AAPL"
        profile = MockProfile("Medium", "Long", "Tech")
        
        result = apply_policy(ticker, profile, balanced_policy)
        
        required_fields = [
            "score",
            "total_score",
            "rating",
            "action",
            "explanation",
            "reasons",
            "breakdown",
            "policy_id",
            "policy_version",
            "strategy_name"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field '{field}' in response"
    
    def test_rating_matches_threshold(self, balanced_policy):
        """Test that rating correctly maps to thresholds."""
        ticker = "AAPL"
        profile = MockProfile("Medium", "Long", "Tech")
        
        result = apply_policy(ticker, profile, balanced_policy)
        
        score = result["score"]
        rating = result["rating"]
        action = result["action"]
        t = balanced_policy.thresholds
        
        # Verify rating matches threshold
        if score >= t["strong_buy"]:
            assert rating == 5
            assert action == "STRONG_BUY"
        elif score >= t["buy"]:
            assert rating == 4
            assert action == "BUY"
        elif score >= t["hold"]:
            assert rating == 3
            assert action == "HOLD"
        elif score >= t["sell"]:
            assert rating == 2
            assert action == "SELL"
        else:
            assert rating == 1
            assert action == "STRONG_SELL"
    
    @pytest.mark.parametrize("profile_data", [
        ("Medium", "Long", "Tech"),
        ("Low", "Short", "Finance"),
        ("High", "Long", "Tech"),
        ("Medium", "Short", "Healthcare"),
    ])
    def test_multiple_profiles_deterministic(self, balanced_policy, profile_data):
        """Test determinism across different profiles."""
        risk, horizon, sector = profile_data
        profile = MockProfile(risk, horizon, sector)
        ticker = "AAPL"
        
        # Call twice
        result1 = apply_policy(ticker, profile, balanced_policy)
        result2 = apply_policy(ticker, profile, balanced_policy)
        
        # Verify identical
        assert result1 == result2
    
    def test_score_in_valid_range(self, balanced_policy):
        """Test that score is always in [0, 1] range."""
        profiles = [
            MockProfile("Medium", "Long", "Tech"),
            MockProfile("Low", "Short", "Finance"),
            MockProfile("High", "Long", "Healthcare"),
        ]
        
        for profile in profiles:
            result = apply_policy("AAPL", profile, balanced_policy)
            score = result["score"]
            
            assert 0.0 <= score <= 1.0, f"Score out of range: {score}"
    
    def test_total_score_in_valid_range(self, balanced_policy):
        """Test that total_score is always in [0, 100] range."""
        profiles = [
            MockProfile("Medium", "Long", "Tech"),
            MockProfile("Low", "Short", "Finance"),
            MockProfile("High", "Long", "Healthcare"),
        ]
        
        for profile in profiles:
            result = apply_policy("AAPL", profile, balanced_policy)
            total_score = result["total_score"]
            
            assert 0 <= total_score <= 100, f"Total score out of range: {total_score}"
