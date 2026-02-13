import json
import os
from pydantic import BaseModel
from typing import Dict, List, Any

# Define Policy Schema
class FactorConfig(BaseModel):
    weight: float

class ReasonTemplates(BaseModel):
    match: str
    mismatch: str

class ReasonConfig(BaseModel):
    sector_match: ReasonTemplates
    risk_match: ReasonTemplates
    horizon_match: ReasonTemplates
    fundamentals: Dict[str, str]

class ScoringPolicy(BaseModel):
    policy_id: str
    policy_version: str
    strategy_name: str
    description: str
    factors: Dict[str, FactorConfig]
    thresholds: Dict[str, float]
    rating_labels: Dict[str, str]
    action_mapping: Dict[str, str]
    assumption_modifiers: Dict[str, int]
    reason_templates: ReasonConfig

# Loader
class PolicyLoader:
    _instance = None
    _policy: ScoringPolicy = None
    _policy_cache: dict = {}  # Per-policy cache: {policy_id: ScoringPolicy}
    
    # Required dimensions that must exist in all policies
    REQUIRED_DIMENSIONS = ["sector_match", "risk_match", "horizon_match", "fundamentals"]

    @classmethod
    def get_policy(cls) -> ScoringPolicy:
        if cls._policy is None:
            cls.load_policy()
        return cls._policy

    @classmethod
    def load_policy(cls, policy_id: str = None):
        # Read from environment variable if not explicitly provided
        if policy_id is None:
            policy_id = os.getenv("FINLIFY_POLICY_ID", "balanced_v1")
        
        # Construct path to policy file
        possible_paths = [
            f"docs/policies/{policy_id}.json",
            f"../docs/policies/{policy_id}.json",
            f"/app/docs/policies/{policy_id}.json"
        ]
        
        policy_path = None
        for p in possible_paths:
            if os.path.exists(p):
                policy_path = p
                break
        
        if policy_path is None:
            # Fallback to balanced_v1 if specified policy not found
            print(f"Warning: Policy '{policy_id}' not found. Falling back to 'balanced_v1'.")
            if policy_id != "balanced_v1":
                return cls.load_policy("balanced_v1")
            else:
                raise FileNotFoundError(f"Could not find default policy 'balanced_v1' in {possible_paths}")
        
        with open(policy_path, "r") as f:
            data = json.load(f)
            policy = ScoringPolicy(**data)
            cls._policy = policy
            cls._policy_cache[policy.policy_id] = policy
            print(f"Loaded policy: {policy.policy_id} ({policy.strategy_name})")
            return policy

    @classmethod
    def load_policy_by_id(cls, policy_id: str) -> ScoringPolicy:
        """Load a specific policy by ID. Uses per-policy cache.
        Raises FileNotFoundError if the policy does not exist.
        """
        # Check cache first
        if policy_id in cls._policy_cache:
            return cls._policy_cache[policy_id]

        # Resolve path
        possible_paths = [
            f"docs/policies/{policy_id}.json",
            f"../docs/policies/{policy_id}.json",
            f"/app/docs/policies/{policy_id}.json"
        ]
        policy_path = None
        for p in possible_paths:
            if os.path.exists(p):
                policy_path = p
                break

        if policy_path is None:
            raise FileNotFoundError(f"Policy '{policy_id}' not found")

        with open(policy_path, "r") as f:
            data = json.load(f)
            policy = ScoringPolicy(**data)
            cls._policy_cache[policy_id] = policy
            return policy

    @classmethod
    def _find_policy_dir(cls):
        """Resolve the policy directory across local dev and Docker environments."""
        from pathlib import Path
        candidates = [
            Path("docs/policies"),
            Path("../docs/policies"),
            Path(__file__).resolve().parent / "docs" / "policies",
            Path("/app/docs/policies"),
        ]
        for d in candidates:
            if d.is_dir():
                return d
        return None

    # Preferred ordering for official strategies
    _PREFERRED_ORDER = ["balanced_v1", "growth_hightech_v1", "conservative_v1"]

    @classmethod
    def list_policies(cls) -> List[ScoringPolicy]:
        """Return all valid policies in deterministic order.

        Ordering: preferred strategies first (balanced → growth → conservative),
        then remaining policies alphabetically by policy_id.
        """
        policy_dir = cls._find_policy_dir()
        if policy_dir is None:
            raise FileNotFoundError(
                "Policy directory not found. Checked: docs/policies, "
                "../docs/policies, /app/docs/policies"
            )

        policies: List[ScoringPolicy] = []
        for path in sorted(policy_dir.glob("*.json")):
            with open(path, "r") as f:
                data = json.load(f)
            try:
                policies.append(ScoringPolicy(**data))
            except Exception as e:
                print(f"Warning: skipping invalid policy {path.name}: {e}")

        # Sort: preferred order first, then alphabetical
        def sort_key(p: ScoringPolicy):
            if p.policy_id in cls._PREFERRED_ORDER:
                return (0, cls._PREFERRED_ORDER.index(p.policy_id))
            return (1, p.policy_id)

        policies.sort(key=sort_key)
        return policies

def apply_policy(ticker: str, profile: Any, policy: ScoringPolicy) -> dict:
    """
    Apply policy to compute score with full per-dimension traceability.
    
    Returns dict with:
    - total_score: int (0-100 scale)
    - rating: int (1-5)
    - action: str
    - explanation: list of {dimension, weight, points, reason}
    - reasons: list of str (legacy, derived from explanation)
    - breakdown: dict (enhanced with per-dimension details)
    - policy_id, policy_version, strategy_name
    """
    
    # Store dimension scores (0.0-1.0 scale)
    dimension_scores = {}
    dimension_reasons = {}
    
    # 1. Sector Match Logic
    sector_weight = policy.factors['sector_match'].weight
    if profile.sector_preference.lower() in ["tech", "technology"]:
        dimension_scores['sector_match'] = 1.0
        dimension_reasons['sector_match'] = policy.reason_templates.sector_match.match.format(
            sector=profile.sector_preference
        )
    else:
        dimension_scores['sector_match'] = 0.0
        dimension_reasons['sector_match'] = policy.reason_templates.sector_match.mismatch.format(
            sector=profile.sector_preference
        )

    # 2. Risk Match Logic
    risk_weight = policy.factors['risk_match'].weight
    # Mock ticker volatility
    ticker_volatility = len(ticker) * 2 
    request_risk = profile.risk_level.lower()
    
    # Use assumption modifiers from policy
    risk_threshold = policy.assumption_modifiers.get(f'risk_{request_risk}_penalty_threshold', 15)
    
    if ticker_volatility > risk_threshold:
        # Penalty - no points
        dimension_scores['risk_match'] = 0.0
        dimension_reasons['risk_match'] = policy.reason_templates.risk_match.mismatch.format(
            risk=profile.risk_level
        )
    else:
        dimension_scores['risk_match'] = 1.0
        dimension_reasons['risk_match'] = policy.reason_templates.risk_match.match

    # 3. Horizon Match Logic
    horizon_weight = policy.factors['horizon_match'].weight
    if profile.horizon.lower() == "long":
        dimension_scores['horizon_match'] = 1.0
        dimension_reasons['horizon_match'] = policy.reason_templates.horizon_match.match
    else:
        dimension_scores['horizon_match'] = 0.0
        dimension_reasons['horizon_match'] = policy.reason_templates.horizon_match.mismatch

    # 4. Fundamentals (Mock - always positive)
    fund_weight = policy.factors['fundamentals'].weight
    dimension_scores['fundamentals'] = 1.0
    dimension_reasons['fundamentals'] = policy.reason_templates.fundamentals['good']

    # Build explanation array in deterministic order
    explanation = []
    total_score_raw = 0.0
    
    for dimension in PolicyLoader.REQUIRED_DIMENSIONS:
        weight = policy.factors[dimension].weight
        dim_score = dimension_scores[dimension]
        points = weight * dim_score
        reason = dimension_reasons[dimension]
        
        explanation.append({
            "dimension": dimension,
            "weight": weight,
            "points": points,
            "reason": reason
        })
        
        total_score_raw += points
    
    # Normalized score (0.0-1.0) - this is what we compare against thresholds
    score = total_score_raw
    
    # Display score (0-100) - use round() to avoid systematic downward bias
    total_score = round(score * 100)
    
    # Determine Rating/Action using normalized score against policy thresholds
    # CRITICAL: Compare score (0-1) against thresholds (0-1), NOT total_score (0-100)
    t = policy.thresholds
    if score >= t['strong_buy']:
        rating = 5
        action = policy.action_mapping['strong_buy']
    elif score >= t['buy']:
        rating = 4
        action = policy.action_mapping['buy']
    elif score >= t['hold']:
        rating = 3
        action = policy.action_mapping['hold']
    elif score >= t['sell']:
        rating = 2
        action = policy.action_mapping['sell']
    else:
        rating = 1
        action = policy.action_mapping['strong_sell']

    # Legacy reasons list (derived from explanation)
    reasons = [e["reason"] for e in explanation]
    
    # Enhanced breakdown
    breakdown = {
        dim: {
            "weight": policy.factors[dim].weight,
            "score": dimension_scores[dim],
            "points": policy.factors[dim].weight * dimension_scores[dim]
        }
        for dim in PolicyLoader.REQUIRED_DIMENSIONS
    }

    return {
        "score": score,  # NEW: normalized score (0.0-1.0)
        "total_score": total_score,  # Display score (0-100)
        "rating": rating,
        "action": action,
        "explanation": explanation,
        "reasons": reasons,
        "breakdown": breakdown,
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
        "strategy_name": policy.strategy_name
    }
