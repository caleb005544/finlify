# Finlify Scoring Strategies

Finlify v2.1 supports multiple official scoring strategies. Each strategy represents a different investment philosophy and risk profile.

## Available Strategies

### 1. Balanced Baseline (`balanced_v1`)
**Policy ID**: `balanced_v1`  
**Best suited for**: General-purpose recommendations, diversified portfolios  
**Risk Profile**: Medium  

**Characteristics**:
- Equal weighting across all factors (25% each)
- Moderate thresholds for buy/sell decisions
- Balanced risk tolerance

**Factor Weights**:
- Sector Match: 25%
- Risk Match: 25%
- Horizon Match: 25%
- Fundamentals: 25%

**Not recommended for**: Aggressive growth seekers or ultra-conservative investors

---

### 2. High Growth Tech (`growth_hightech_v1`)
**Policy ID**: `growth_hightech_v1`  
**Best suited for**: Tech-focused portfolios, growth-oriented investors  
**Risk Profile**: High  

**Characteristics**:
- Heavy emphasis on sector alignment (40% weight on tech)
- Lower risk penalties (accepts higher volatility)
- More aggressive buy thresholds

**Factor Weights**:
- Sector Match: 40%
- Risk Match: 10%
- Horizon Match: 20%
- Fundamentals: 30%

**Key trade-offs**: Higher potential returns with increased volatility  
**Not recommended for**: Risk-averse investors, short-term traders

**Risk Notice**: This strategy tolerates significantly higher volatility and may recommend stocks with elevated risk profiles.

---

### 3. Conservative Stability (`conservative_v1`)
**Policy ID**: `conservative_v1`  
**Best suited for**: Capital preservation, risk-averse investors  
**Risk Profile**: Low  

**Characteristics**:
- Heavy emphasis on risk management (40% weight)
- Strict volatility thresholds
- Higher bars for buy recommendations

**Factor Weights**:
- Sector Match: 15%
- Risk Match: 40%
- Horizon Match: 15%
- Fundamentals: 30%

**Key trade-offs**: Lower volatility at the cost of potential upside  
**Not recommended for**: Growth-focused investors, those seeking high returns

**Risk Notice**: This strategy prioritizes stability and may miss high-growth opportunities.

---

## Switching Strategies

To change the active strategy, set the `FINLIFY_POLICY_ID` environment variable:

```bash
# In .env file
FINLIFY_POLICY_ID=growth_hightech_v1
```

Then restart the backend:
```bash
docker-compose restart backend
```

## Strategy Traceability

Every `/score` API response includes:
- `policy_id`: The active policy identifier
- `policy_version`: The version of the policy
- `strategy_name`: Human-readable strategy name

This ensures full auditability of all recommendations.
