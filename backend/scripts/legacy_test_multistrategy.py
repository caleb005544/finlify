import sys
import os
import json

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from policy import PolicyLoader, apply_policy, ScoringPolicy

# Mock Profile
class MockProfile:
    def __init__(self, risk, horizon, sector):
        self.risk_level = risk
        self.horizon = horizon
        self.sector_preference = sector

def test_policy_validation():
    """Test that all policy files are valid and meet requirements"""
    print("=" * 60)
    print("Testing Policy Validation")
    print("=" * 60)
    
    policy_dir = "../docs/policies"
    if not os.path.exists(policy_dir):
        policy_dir = "docs/policies"
    
    policy_files = ["balanced_v1.json", "growth_hightech_v1.json", "conservative_v1.json"]
    
    for policy_file in policy_files:
        path = os.path.join(policy_dir, policy_file)
        print(f"\n✓ Validating {policy_file}...")
        
        with open(path, 'r') as f:
            data = json.load(f)
            policy = ScoringPolicy(**data)
        
        # Check weights sum to 1.0
        total_weight = sum(f.weight for f in policy.factors.values())
        assert abs(total_weight - 1.0) < 0.001, f"Weights must sum to 1.0, got {total_weight}"
        print(f"  - Weights sum to {total_weight:.3f} ✓")
        
        # Check thresholds are monotonic
        t = policy.thresholds
        assert t['strong_buy'] > t['buy'] > t['hold'] > t['sell'], "Thresholds must be monotonic"
        print(f"  - Thresholds are monotonic ✓")
        
        # Check policy_id matches filename
        expected_id = policy_file.replace('.json', '')
        assert policy.policy_id == expected_id, f"Policy ID mismatch: {policy.policy_id} != {expected_id}"
        print(f"  - Policy ID matches filename ✓")
        
        print(f"  - Strategy: {policy.strategy_name}")

def test_strategy_switching():
    """Test that different policies produce different scores"""
    print("\n" + "=" * 60)
    print("Testing Strategy Switching")
    print("=" * 60)
    
    profile = MockProfile("Medium", "Long", "Tech")
    ticker = "AAPL"
    
    results = {}
    
    for policy_id in ["balanced_v1", "growth_hightech_v1", "conservative_v1"]:
        # Force reload policy
        PolicyLoader._policy = None
        os.environ["FINLIFY_POLICY_ID"] = policy_id
        
        policy = PolicyLoader.load_policy(policy_id)
        result = apply_policy(ticker, profile, policy)
        
        results[policy_id] = result
        print(f"\n{policy.strategy_name} ({policy_id}):")
        print(f"  Score: {result['total_score']}")
        print(f"  Rating: {result['rating']}")
        print(f"  Action: {result['action']}")
    
    # Verify different strategies produce different results
    scores = [r['total_score'] for r in results.values()]
    assert len(set(scores)) > 1, "Different strategies should produce different scores"
    print("\n✓ Different strategies produce different scores")

def test_env_var_selection():
    """Test that FINLIFY_POLICY_ID environment variable works"""
    print("\n" + "=" * 60)
    print("Testing Environment Variable Selection")
    print("=" * 60)
    
    # Test default (balanced)
    PolicyLoader._policy = None
    os.environ.pop("FINLIFY_POLICY_ID", None)
    policy = PolicyLoader.get_policy()
    assert policy.policy_id == "balanced_v1", "Default should be balanced_v1"
    print("✓ Default policy is balanced_v1")
    
    # Test explicit selection
    PolicyLoader._policy = None
    os.environ["FINLIFY_POLICY_ID"] = "growth_hightech_v1"
    policy = PolicyLoader.get_policy()
    assert policy.policy_id == "growth_hightech_v1"
    print("✓ Environment variable selection works")

if __name__ == "__main__":
    try:
        test_policy_validation()
        test_strategy_switching()
        test_env_var_selection()
        print("\n" + "=" * 60)
        print("✅ All Tests Passed")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
