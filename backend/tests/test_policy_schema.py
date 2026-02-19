"""
Test A: Policy Schema Validation

Validates that all policy JSON files conform to the required schema:
- Required top-level fields exist
- Factor dimensions match exactly
- Reason templates cover all dimensions
- Action mapping contains required codes
"""
import json
from policy import PolicyLoader


class TestPolicySchema:
    """Schema validation tests for policy files."""
    
    def test_all_policies_exist(self, all_policy_files):
        """Verify at least one policy file exists."""
        assert len(all_policy_files) > 0, "No policy files found in docs/policies/"
    
    def test_required_top_level_fields(self, policy_file):
        """Test that all required top-level fields exist."""
        with open(policy_file) as f:
            data = json.load(f)
        
        required_fields = [
            "policy_id",
            "policy_version",
            "strategy_name",
            "description",
            "factors",
            "thresholds",
            "rating_labels",
            "action_mapping",
            "assumption_modifiers",
            "reason_templates"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_factor_dimensions_exact_match(self, policy_file, required_dimensions):
        """Test that factor dimensions match exactly (no missing, no extra)."""
        with open(policy_file) as f:
            data = json.load(f)
        
        factor_keys = set(data["factors"].keys())
        required_dims = set(required_dimensions)
        
        missing = required_dims - factor_keys
        extra = factor_keys - required_dims
        
        assert not missing, f"Missing required dimensions: {missing}"
        assert not extra, f"Unexpected dimensions: {extra}"
        assert factor_keys == required_dims, "Factor dimensions must match exactly"
    
    def test_reason_templates_coverage(self, policy_file, required_dimensions):
        """Test that reason_templates exist for all dimensions."""
        with open(policy_file) as f:
            data = json.load(f)
        
        templates = data["reason_templates"]
        
        for dim in required_dimensions:
            assert dim in templates, f"Missing reason_templates for dimension: {dim}"
            
            # Most dimensions need match/mismatch (except fundamentals)
            if dim != "fundamentals":
                assert "match" in templates[dim], f"Missing 'match' template for {dim}"
                assert "mismatch" in templates[dim], f"Missing 'mismatch' template for {dim}"
    
    def test_action_mapping_complete(self, policy_file):
        """Test that action_mapping contains all required action codes."""
        with open(policy_file) as f:
            data = json.load(f)
        
        required_actions = ["strong_buy", "buy", "hold", "sell", "strong_sell"]
        action_mapping = data["action_mapping"]
        
        for action in required_actions:
            assert action in action_mapping, f"Missing action_mapping for: {action}"
    
    def test_policy_id_matches_filename(self, policy_file):
        """Test that policy_id matches filename prefix."""
        with open(policy_file) as f:
            data = json.load(f)
        
        expected_id = policy_file.stem  # filename without .json
        actual_id = data["policy_id"]
        
        assert actual_id == expected_id, (
            f"Policy ID '{actual_id}' does not match filename '{expected_id}'"
        )
    
    def test_thresholds_exist(self, policy_file):
        """Test that all required threshold keys exist."""
        with open(policy_file) as f:
            data = json.load(f)
        
        required_thresholds = ["strong_buy", "buy", "hold", "sell"]
        thresholds = data["thresholds"]
        
        for t in required_thresholds:
            assert t in thresholds, f"Missing threshold: {t}"
