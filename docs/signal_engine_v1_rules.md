# Signal Engine v1 Rules

This document defines the proposed v1 rule set for Finlify Signal Engine without changing current code, ranking calculations, or Streamlit behavior.

## Design Intent

Signal Engine v1 should match Finlify's current product positioning:

- short-term tactical investment decision platform
- decision support over a 30 to 90 day window
- ranking-first system, not a precise price prediction engine
- simple, explainable, stable rules

v1 should therefore:

- reuse the current ranking outputs
- add interpretable decision metadata
- avoid opaque models or hidden statistical layers
- remain easy to explain in the UI and documentation

## Source Inputs Available Today

The v1 rule set should derive only from current ranking and latest feature fields already available in the mart layer.

Primary inputs from `top_ranked_assets.*`:

- `decision`
- `trend_score`
- `momentum_score`
- `risk_penalty`
- `composite_score`
- `rank_overall`
- `rank_within_asset_type`
- `ret_20d`
- `ret_60d`
- `ret_120d`
- `ret_252d`
- `volatility_20d`
- `volatility_60d`
- `dist_from_52w_high`
- `dist_from_52w_low`
- `asset_type`
- `is_active`

Optional upstream inputs from `factor_snapshot_latest.parquet` if needed:

- `ma_20`
- `ma_50`
- `ma_200`
- `close`

## Final Allowed Values

### `decision`

Allowed values:

- `BUY`
- `HOLD`
- `WATCH`
- `AVOID`

Notes:

- keep exactly the current enum
- do not expand or rename in v1

### `regime`

Allowed values:

- `TRENDING`
- `MIXED`
- `RISK_OFF`

Why this set:

- small enum surface
- matches a tactical decision platform
- easy to explain using current trend, momentum, and volatility-related fields

### `risk_level`

Allowed values:

- `LOW`
- `MEDIUM`
- `HIGH`

Why this set:

- stable and familiar
- sufficiently granular for v1 without false precision

## Final Representation

### `confidence`

Final representation:

- integer from `0` to `100`

Interpretation bands for UI or downstream use:

- `0-39`: low confidence
- `40-69`: medium confidence
- `70-100`: high confidence

Why numeric first:

- easier to sort, filter, and threshold
- can still be bucketed later in visualization
- avoids having to commit to a categorical-only field too early

### `horizon_days`

Final representation:

- integer

Allowed v1 values:

- `30`
- `60`
- `90`

Why:

- directly aligned with current product framing
- consistent with existing forecast UX choices
- simple for users and implementation

## Rule Definitions

## 1. `decision`

### v1 rule

Use the current `decision` produced by the ranking step unchanged.

### Inputs

- current ranking output `decision`

### Rationale

- already part of the ranking layer
- already used by Streamlit
- changing it now would create unnecessary drift between ranking and signal design

### v2 note

- if decision logic evolves later, keep backward-compatible mapping tables for legacy UI and exports

## 2. `regime`

### Business meaning

`regime` is the broad tactical market posture of the asset right now, based on whether positive trend and momentum dominate or whether risk drag dominates.

### Inputs

- `trend_score`
- `momentum_score`
- `risk_penalty`
- `ret_20d`
- `ret_60d`

### Helper values

Define:

- `risk_abs = abs(risk_penalty)`
- `positive_stack = trend_score + momentum_score`

### v1 step-by-step rules

1. If `decision == "AVOID"`, set `regime = "RISK_OFF"`.
2. Else if both `ret_20d > 0` and `ret_60d > 0` and `trend_score >= 18` and `momentum_score >= 24` and `risk_abs <= 4`, set `regime = "TRENDING"`.
3. Else if `risk_abs >= 7`, set `regime = "RISK_OFF"`.
4. Else if `positive_stack < 30`, set `regime = "RISK_OFF"`.
5. Else set `regime = "MIXED"`.

### Rationale

- rule 1 preserves consistency with the current decision output
- rule 2 identifies assets with aligned medium-term returns and strong score components
- rules 3 and 4 prevent a superficially positive asset from being labeled trending when risk drag is too high or positive evidence is too weak
- `MIXED` captures the large middle zone where the asset is investable but not cleanly directional

### v2 note

- v2 could refine regime using explicit moving-average structure from `close`, `ma_20`, `ma_50`, and `ma_200`

## 3. `risk_level`

### Business meaning

`risk_level` is a simple tactical risk classification for current decision-making, not a formal portfolio risk model.

### Inputs

- `volatility_20d`
- `volatility_60d`
- `risk_penalty`
- `dist_from_52w_high`

### Helper values

Define:

- `risk_abs = abs(risk_penalty)`
- `volatility_anchor = max(volatility_20d, volatility_60d)`

### v1 step-by-step rules

1. If `risk_abs >= 7`, set `risk_level = "HIGH"`.
2. Else if `volatility_anchor >= 0.035`, set `risk_level = "HIGH"`.
3. Else if `risk_abs >= 4`, set `risk_level = "MEDIUM"`.
4. Else if `volatility_anchor >= 0.020`, set `risk_level = "MEDIUM"`.
5. Else if `dist_from_52w_high <= -0.20`, set `risk_level = "MEDIUM"`.
6. Else set `risk_level = "LOW"`.

### Rationale

- `risk_penalty` is already the current ranking system's explicit risk summary, so it should lead the label
- realized volatility provides an independent sanity check
- a large drawdown from 52-week highs is useful as a secondary caution signal in a tactical system

### v2 note

- thresholds may later be calibrated by asset type so ETFs and equities are not treated identically

## 4. `confidence`

### Business meaning

`confidence` measures how clean and coherent the current signal is. It is not prediction confidence in a statistical sense.

### Inputs

- `composite_score`
- `trend_score`
- `momentum_score`
- `risk_penalty`
- `decision`

### Helper values

Define:

- `risk_abs = abs(risk_penalty)`
- `signal_balance_gap = abs(trend_score - momentum_score)`

### v1 step-by-step rules

Start from a base score determined by `decision`:

- `BUY` -> base `75`
- `HOLD` -> base `60`
- `WATCH` -> base `45`
- `AVOID` -> base `35`

Then apply adjustments:

1. If `composite_score >= 50`, add `10`.
2. Else if `composite_score >= 40`, add `5`.
3. Else if `composite_score < 20`, subtract `5`.

4. If `risk_abs >= 7`, subtract `15`.
5. Else if `risk_abs >= 4`, subtract `8`.

6. If `signal_balance_gap <= 5`, add `5`.
7. Else if `signal_balance_gap >= 12`, subtract `5`.

8. If `decision == "BUY"` and `trend_score >= 20` and `momentum_score >= 25`, add `5`.
9. If `decision == "AVOID"` and `risk_abs >= 7`, add `5`.

10. Clip the final value to the `0-100` range and round to integer.

### Rationale

- base score anchors confidence to the existing decision bucket
- composite score refines how far into that bucket the asset sits
- high risk drag lowers trust in a positive tactical signal
- strong agreement between trend and momentum increases clarity
- rule 9 allows confidence in a negative signal to still be high when the warning is clear

### v1 interpretation

- `BUY` with `confidence 80+` means strong tactical alignment
- `WATCH` with `confidence 45` means weak or mixed setup, not necessarily bad data quality
- `AVOID` with `confidence 70` means a strong warning signal, not a favorable opportunity

### v2 note

- v2 may replace some score-based thresholds with percentile-based calibration over rolling history

## 5. `horizon_days`

### Business meaning

`horizon_days` is the recommended tactical holding or review horizon for the current signal, not a guaranteed duration of profitability.

### Inputs

- `regime`
- `decision`
- `risk_level`
- `momentum_score`
- `trend_score`

### v1 step-by-step rules

1. If `regime == "RISK_OFF"`, set `horizon_days = 30`.
2. Else if `decision == "WATCH"`, set `horizon_days = 30`.
3. Else if `risk_level == "HIGH"`, set `horizon_days = 30`.
4. Else if `regime == "TRENDING"` and `trend_score >= momentum_score`, set `horizon_days = 90`.
5. Else if `regime == "TRENDING"` and `momentum_score > trend_score`, set `horizon_days = 60`.
6. Else set `horizon_days = 60`.

### Rationale

- negative or unstable setups should have short review cycles
- strong trend-led signals deserve longer tactical holding windows
- momentum-led signals are still tactical but typically shorter-lived than broad trend-led setups
- `60` is the default middle horizon and maps naturally to the current product framing

### v2 note

- v2 could allow asset-type-specific horizons or explicit portfolio turnover constraints

## Summary Table

| Field | Representation | Recommended v1 output |
|---|---|---|
| `decision` | enum | `BUY`, `HOLD`, `WATCH`, `AVOID` |
| `regime` | enum | `TRENDING`, `MIXED`, `RISK_OFF` |
| `risk_level` | enum | `LOW`, `MEDIUM`, `HIGH` |
| `confidence` | integer | `0-100` |
| `horizon_days` | integer | `30`, `60`, `90` |

## Recommended Layer Placement

These fields should be generated in the ranking layer, not only in the visualization layer.

Recommended source of truth:

- `data/mart/investment/top_ranked_assets.parquet`
- `data/mart/investment/top_ranked_assets.csv`

Reason:

- they are derived from current ranking semantics
- they should be stable across all downstream consumers
- the visualization layer should export them, not define them

## Unresolved Ambiguities

These items should be decided before implementation:

1. Whether volatility thresholds should be shared across stocks and ETFs in v1
2. Whether `confidence` should remain numeric only, or whether a derived `confidence_band` should also be exported
3. Whether `regime` should be forced to mirror `decision` more tightly for `HOLD` assets
4. Whether `horizon_days` should be constrained by asset type

Recommended v1 answer:

- keep one shared threshold set
- export numeric `confidence` only
- allow `HOLD` to appear in either `TRENDING` or `MIXED`
- do not branch on asset type yet

## Recommended Implementation Order

1. Add the new fields to the ranking output schema only
2. Populate them using the rule definitions in this document
3. Export the new fields into `top_ranked_assets.parquet` and `top_ranked_assets.csv`
4. Add optional downstream export such as `signal_heatmap_snapshot.csv`
5. Update Streamlit only after the ranking outputs are stable and documented

## Future v2 Improvement Areas

- use moving-average structure explicitly in `regime`
- calibrate thresholds by asset type
- add historical stability metrics to `confidence`
- add a derived `confidence_band`
- validate rule outcomes against realized 30, 60, and 90 day forward performance
