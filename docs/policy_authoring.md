# Policy Authoring Guide

This guide explains how to create new scoring policies for Finlify v2.

---

## Quick Start

1. **Copy an existing policy** as a template:
   ```bash
   cp docs/policies/balanced_v1.json docs/policies/my_strategy_v1.json
   ```

2. **Edit the policy** (see schema below)

3. **Validate**:
   ```bash
   cd backend
   python3 -m pytest tests/ -q
   ```

4. **Test locally**:
   ```bash
   FINLIFY_POLICY_ID=my_strategy_v1 docker-compose up --build
   ```

---

## Policy Schema

For complete schema documentation, see **[POLICY_SCHEMA.md](POLICY_SCHEMA.md)**.

### Required Fields

```json
{
  "policy_id": "my_strategy_v1",
  "policy_version": "v1.0",
  "strategy_name": "My Strategy Name",
  "description": "Brief description of strategy",
  "factors": { ... },
  "thresholds": { ... },
  "rating_labels": { ... },
  "action_mapping": { ... },
  "assumption_modifiers": { ... },
  "reason_templates": { ... }
}
```

---

## Step-by-Step Guide

### 1. Metadata
```json
{
  "policy_id": "my_strategy_v1",
  "policy_version": "v1.0",
  "strategy_name": "My Strategy Name",
  "description": "A strategy focused on..."
}
```

**Rules**:
- `policy_id` must match filename (without `.json`)
- Use semantic versioning for `policy_version`

### 2. Factor Weights

**CRITICAL**: Weights must sum to exactly 1.0 (±0.001 tolerance)

```json
{
  "factors": {
    "sector_match": {"weight": 0.30},
    "risk_match": {"weight": 0.25},
    "horizon_match": {"weight": 0.20},
    "fundamentals": {"weight": 0.25}
  }
}
```

**Required Dimensions** (fixed, cannot add/remove):
- `sector_match`
- `risk_match`
- `horizon_match`
- `fundamentals`

**Weight Guidelines**:
- Higher weight = more important to strategy
- All weights must be in range [0.0, 1.0]
- Sum must equal 1.0

### 3. Thresholds

**CRITICAL**: Must be strictly monotonically decreasing

```json
{
  "thresholds": {
    "strong_buy": 0.80,
    "buy": 0.60,
    "hold": 0.40,
    "sell": 0.20
  }
}
```

**Rules**:
- `strong_buy > buy > hold > sell`
- All values in range [0.0, 1.0]
- These map normalized score (0-1) to ratings

### 4. Rating Labels
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

### 5. Action Mapping
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

### 6. Assumption Modifiers
```json
{
  "assumption_modifiers": {
    "risk_low_penalty_threshold": 15,
    "risk_medium_penalty_threshold": 25,
    "risk_high_penalty_threshold": 40
  }
}
```

### 7. Reason Templates

**CRITICAL**: Must include templates for all dimensions

```json
{
  "reason_templates": {
    "sector_match": {
      "match": "Sector '{sector}' aligns with your preference.",
      "mismatch": "Sector '{sector}' does not match your preference."
    },
    "risk_match": {
      "match": "Risk profile matches asset class.",
      "mismatch": "Risk level '{risk}' may not suit this asset."
    },
    "horizon_match": {
      "match": "Long-term horizon favorable for accumulated growth.",
      "mismatch": "Short-term horizon may not capture full potential."
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
- Other variables can be added as needed

---

## Validation Checklist

Before submitting your policy:

- [ ] `policy_id` matches filename
- [ ] Weights sum to 1.0 (±0.001)
- [ ] Thresholds are monotonically decreasing
- [ ] All 4 required dimensions present
- [ ] Reason templates for all dimensions
- [ ] All required action codes present
- [ ] Tests pass: `python3 -m pytest tests/ -q`

---

## Testing Your Policy

### 1. Schema Validation
```bash
cd backend
python3 -m pytest tests/test_policy_schema.py::TestPolicySchema::test_required_top_level_fields[my_strategy_v1] -v
```

### 2. Math Validation
```bash
python3 -m pytest tests/test_policy_math.py -v
```

### 3. Load Test
```bash
python3 -c "from policy import PolicyLoader; p = PolicyLoader.load_policy('my_strategy_v1'); print(f'Loaded: {p.policy_id}')"
```

### 4. Scoring Test
```bash
FINLIFY_POLICY_ID=my_strategy_v1 python3 backend/generate_example_response.py
```

---

## Common Mistakes

### ❌ Weights Don't Sum to 1.0
```json
{
  "factors": {
    "sector_match": {"weight": 0.30},
    "risk_match": {"weight": 0.30},
    "horizon_match": {"weight": 0.20},
    "fundamentals": {"weight": 0.15}  // Sum = 0.95 ❌
  }
}
```

### ❌ Thresholds Not Monotonic
```json
{
  "thresholds": {
    "strong_buy": 0.60,  // ❌ Should be > buy
    "buy": 0.70,
    "hold": 0.40,
    "sell": 0.20
  }
}
```

### ❌ Missing Dimension
```json
{
  "factors": {
    "sector_match": {"weight": 0.33},
    "risk_match": {"weight": 0.33},
    "fundamentals": {"weight": 0.34}
    // ❌ Missing horizon_match
  }
}
```

---

## Strategy Design Tips

### Conservative Strategy
- Higher weight on `fundamentals`
- Higher weight on `risk_match`
- Higher thresholds (more selective)

### Growth Strategy
- Higher weight on `sector_match`
- Lower weight on `risk_match`
- Lower thresholds (more aggressive)

### Balanced Strategy
- Equal or near-equal weights
- Moderate thresholds

---

## Deployment

1. **Create PR** with new policy file
2. **Include test results** in PR description
3. **Get review** from 2+ team members
4. **Merge** after approval
5. **Deploy** by setting `FINLIFY_POLICY_ID` environment variable

---

## Need Help?

- **Schema Reference**: [POLICY_SCHEMA.md](POLICY_SCHEMA.md)
- **Governance Rules**: [governance.md](governance.md)
- **Available Strategies**: [strategies.md](strategies.md)
