# Finlify v2 Policy Schema Specification

## Overview
Finlify v2 policies are JSON files that define scoring behavior. All weights, thresholds, and explanations must come from the policy file—no hardcoded values in code.

## Required Fields

### Core Metadata
```json
{
  "policy_id": "string",           // Must match filename (without .json)
  "policy_version": "string",      // Semantic version (e.g., "v1.0")
  "strategy_name": "string",       // Human-readable name
  "description": "string"          // Strategy description
}
```

### Scoring Dimensions
```json
{
  "factors": {
    "sector_match": { "weight": 0.25 },      // Float, 0.0-1.0
    "risk_match": { "weight": 0.25 },
    "horizon_match": { "weight": 0.25 },
    "fundamentals": { "weight": 0.25 }
  }
}
```

**Validation Rules**:
- All weights must be floats between 0.0 and 1.0
- Sum of all weights MUST equal 1.0 (tolerance: ±0.001)
- Dimension keys MUST match: `sector_match`, `risk_match`, `horizon_match`, `fundamentals`

### Thresholds
```json
{
  "thresholds": {
    "strong_buy": 0.80,    // Float, 0.0-1.0
    "buy": 0.60,
    "hold": 0.40,
    "sell": 0.20
  }
}
```

**Validation Rules**:
- Must be monotonically decreasing: `strong_buy > buy > hold > sell`
- All values must be floats between 0.0 and 1.0

### Rating Labels
```json
{
  "rating_labels": {
    "5": "Strong Buy",
    "4": "Buy",
    "3": "Hold",
    "2": "Sell",
    "1": "Strong Sell"
  }
}
```

### Action Mapping
```json
{
  "action_mapping": {
    "strong_buy": "STRONG_BUY",
    "buy": "BUY",
    "hold": "HOLD",
    "sell": "SELL",
    "strong_sell": "STRONG_SELL"
  }
}
```

### Assumption Modifiers
```json
{
  "assumption_modifiers": {
    "risk_low_penalty_threshold": 10,      // Integer
    "risk_medium_penalty_threshold": 18,
    "risk_high_penalty_threshold": 28
  }
}
```

### Reason Templates
```json
{
  "reason_templates": {
    "sector_match": {
      "match": "Sector '{sector}' aligns with your preference.",
      "mismatch": "Sector '{sector}' is neutral regarding your preference."
    },
    "risk_match": {
      "match": "Risk profile matches asset class.",
      "mismatch": "Volatility exceeds your {risk} risk tolerance."
    },
    "horizon_match": {
      "match": "Long-term horizon favorable for accumulated growth.",
      "mismatch": "Short-term volatility may impact returns."
    },
    "fundamentals": {
      "good": "Fundamental indicators are strong.",
      "neutral": "Fundamentals are average."
    }
  }
}
```

**Template Variables**:
- `{sector}`: User's sector preference
- `{risk}`: User's risk level
- `{points:.2f}`: Dimension score (formatted to 2 decimals)

## Complete Example

See `docs/policies/balanced_v1.json` for a complete, valid policy file.

## Validation Checklist

Before deploying a policy, verify:
- [ ] `policy_id` matches filename
- [ ] All required fields present
- [ ] Weights sum to 1.0 (within 0.001 tolerance)
- [ ] Thresholds are monotonic
- [ ] All dimension keys match engine expectations
- [ ] All reason templates exist for each dimension
- [ ] Template variables are correctly formatted

## Dimension Semantics

### sector_match
- **Purpose**: Reward alignment with user's preferred sector
- **Calculation**: Binary (1.0 if match, 0.0 if not)
- **Weight**: Multiplied by dimension score

### risk_match
- **Purpose**: Penalize stocks exceeding user's risk tolerance
- **Calculation**: Based on ticker volatility vs. risk threshold
- **Weight**: Applied when risk is acceptable

### horizon_match
- **Purpose**: Favor long-term holdings for long-term investors
- **Calculation**: Binary based on user's horizon
- **Weight**: Applied for matching horizons

### fundamentals
- **Purpose**: Baseline quality assessment
- **Calculation**: Mock (always positive in v2)
- **Weight**: Always applied

## File Location
All policy files must be stored in: `docs/policies/{policy_id}.json`
