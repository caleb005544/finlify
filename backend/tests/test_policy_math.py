"""
Test B: Policy Mathematical Invariants

Validates mathematical properties of policy files:
- Weights sum to 1.0 (±0.001 tolerance)
- Thresholds are strictly monotonically decreasing
- Thresholds are within valid range (0-1)
- No negative weights
"""
import json


class TestPolicyMath:
    """Mathematical invariant tests for policy files."""

    def test_weights_sum_to_one(self, policy_file, required_dimensions):
        """Test that factor weights sum to 1.0 within tolerance."""
        with open(policy_file) as f:
            data = json.load(f)
        
        weights = [data["factors"][dim]["weight"] for dim in required_dimensions]
        weight_sum = sum(weights)
        
        tolerance = 0.001
        assert abs(weight_sum - 1.0) <= tolerance, (
            f"Weights sum to {weight_sum:.6f}, expected 1.0 (±{tolerance})"
        )
    
    def test_weights_are_positive(self, policy_file, required_dimensions):
        """Test that all weights are non-negative."""
        with open(policy_file) as f:
            data = json.load(f)
        
        for dim in required_dimensions:
            weight = data["factors"][dim]["weight"]
            assert weight >= 0, f"Weight for '{dim}' is negative: {weight}"
    
    def test_weights_in_valid_range(self, policy_file, required_dimensions):
        """Test that all weights are between 0 and 1."""
        with open(policy_file) as f:
            data = json.load(f)
        
        for dim in required_dimensions:
            weight = data["factors"][dim]["weight"]
            assert 0.0 <= weight <= 1.0, (
                f"Weight for '{dim}' out of range [0,1]: {weight}"
            )
    
    def test_thresholds_monotonically_decreasing(self, policy_file):
        """Test that thresholds are strictly monotonically decreasing."""
        with open(policy_file) as f:
            data = json.load(f)
        
        t = data["thresholds"]
        
        assert t["strong_buy"] > t["buy"], (
            f"strong_buy ({t['strong_buy']}) must be > buy ({t['buy']})"
        )
        assert t["buy"] > t["hold"], (
            f"buy ({t['buy']}) must be > hold ({t['hold']})"
        )
        assert t["hold"] > t["sell"], (
            f"hold ({t['hold']}) must be > sell ({t['sell']})"
        )
    
    def test_thresholds_in_valid_range(self, policy_file):
        """Test that all thresholds are within [0, 1]."""
        with open(policy_file) as f:
            data = json.load(f)
        
        thresholds = data["thresholds"]
        
        for name, value in thresholds.items():
            assert 0.0 <= value <= 1.0, (
                f"Threshold '{name}' out of range [0,1]: {value}"
            )
    
    def test_weights_are_numeric(self, policy_file, required_dimensions):
        """Test that all weights are numeric (int or float)."""
        with open(policy_file) as f:
            data = json.load(f)
        
        for dim in required_dimensions:
            weight = data["factors"][dim]["weight"]
            assert isinstance(weight, (int, float)), (
                f"Weight for '{dim}' is not numeric: {type(weight).__name__}"
            )
    
    def test_thresholds_are_numeric(self, policy_file):
        """Test that all thresholds are numeric (int or float)."""
        with open(policy_file) as f:
            data = json.load(f)
        
        for name, value in data["thresholds"].items():
            assert isinstance(value, (int, float)), (
                f"Threshold '{name}' is not numeric: {type(value).__name__}"
            )
