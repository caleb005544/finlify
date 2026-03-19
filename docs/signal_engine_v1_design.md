# Signal Engine v1 Design

This document audits the current ranking outputs and proposes a future Signal Engine v1 schema without changing the current ranking logic, Streamlit app, or pipeline architecture.

## Scope

This is a design-only document for the current local, file-based pipeline.

Current active path:

`input TXT -> raw parquet -> staging parquet -> mart parquet -> ranking CSV -> Streamlit`

Out of scope:

- changing scoring logic
- changing ranking thresholds
- changing Streamlit behavior
- redesigning the project around a database, dbt, or workflow platform

## Current Ranking Schemas

### `data/mart/investment/factor_snapshot_latest.parquet`

Current columns:

- `source_ticker`
- `ticker`
- `asset_type`
- `date`
- `close`
- `volume`
- `ret_1d`
- `ret_20d`
- `ret_60d`
- `ret_120d`
- `ret_252d`
- `ma_20`
- `ma_50`
- `ma_200`
- `volatility_20d`
- `volatility_60d`
- `rolling_high_252d`
- `rolling_low_252d`
- `dist_from_52w_high`
- `dist_from_52w_low`
- `is_active`
- `source`

This file is the latest per-ticker feature snapshot and is the direct input to the ranking step.

### `data/mart/investment/top_ranked_assets.parquet`

Current columns:

- `source_ticker`
- `ticker`
- `asset_type`
- `date`
- `close`
- `trend_score`
- `momentum_score`
- `risk_penalty`
- `composite_score`
- `decision`
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
- `is_active`
- `source`
- `decision_reason`

### `data/mart/investment/top_ranked_assets.csv`

Current columns are the same as the parquet output:

- `source_ticker`
- `ticker`
- `asset_type`
- `date`
- `close`
- `trend_score`
- `momentum_score`
- `risk_penalty`
- `composite_score`
- `decision`
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
- `is_active`
- `source`
- `decision_reason`

## Current Ranking-Related Fields

### Score fields

- `trend_score`
- `momentum_score`
- `risk_penalty`
- `composite_score`

### Decision-like fields

- `decision`
- `decision_reason`
- `rank_overall`
- `rank_within_asset_type`

### Return and momentum inputs

- `ret_1d` in `factor_snapshot_latest.parquet`
- `ret_20d`
- `ret_60d`
- `ret_120d`
- `ret_252d`

### Volatility and risk inputs

- `volatility_20d`
- `volatility_60d`

### Trend and moving-average inputs

- `close`
- `ma_20` in `factor_snapshot_latest.parquet`
- `ma_50` in `factor_snapshot_latest.parquet`
- `ma_200` in `factor_snapshot_latest.parquet`
- `dist_from_52w_high`
- `dist_from_52w_low`

### Identity and segmentation fields

- `source_ticker`
- `ticker`
- `asset_type`
- `date`
- `is_active`
- `source`

## Current Streamlit Ranking Dependencies

File read path:

- `app/finlify_streamlit_mvp_app.py` reads `data/mart/investment/top_ranked_assets.csv`

### Columns actively used by the UI

- `ticker`
- `source_ticker`
- `asset_type`
- `decision`
- `composite_score`
- `trend_score`
- `momentum_score`
- `risk_penalty`
- `rank_overall`

The app renames `rank_overall` to `rank` during load, then uses `rank` in rendering logic.

### Columns assumed to exist strongly

These are not always hard-validated up front, but much of the UI assumes they exist for the full experience:

- `ticker`
- `decision`
- `composite_score`
- `trend_score`
- `momentum_score`
- `risk_penalty`
- `rank_overall`

### Columns used conditionally

- `asset_type`
- `source_ticker`

The app checks for some columns before use, so missing optional fields degrade the UI rather than always crashing.

### Backward compatibility of adding new columns

Adding new columns to `top_ranked_assets.csv` is backward-compatible for the current app because:

- the app selects only a subset of ranking columns for display
- extra columns are ignored unless referenced explicitly
- existing column names and meanings are preserved

Compatibility would become risky only if:

- existing column names are changed
- existing score semantics are changed without updating UI labels
- new columns collide with current names like `rank`, `decision`, or `composite_score`

## Signal Engine v1 Goal

Signal Engine v1 should add decision-oriented fields on top of the existing ranking outputs while keeping current ranking outputs intact.

Recommended principle:

- derive signal fields from the ranking layer
- keep ranking outputs as the canonical source for signal metadata
- create a visualization-ready snapshot file only after the signal fields exist in the ranking output

## Proposed New Fields

### 1. `decision`

Business meaning:

- the user-facing investment stance for the asset

Current status:

- already exists in the ranking output

Candidate derivation inputs:

- `composite_score`
- existing percentile bucket thresholds

Recommended layer:

- ranking layer

Compatibility risk:

- low if retained as-is
- high if the meaning changes without updating current UI messaging

### 2. `confidence`

Business meaning:

- how strong or reliable the current signal is relative to peers and internal components

Candidate derivation inputs:

- `composite_score`
- distance between `trend_score + momentum_score` and `abs(risk_penalty)`
- percentile position of `composite_score`
- agreement between `trend_score` and `momentum_score`

Candidate representation:

- numeric `0-100`
- or categorical bands such as `low`, `medium`, `high`

Recommended layer:

- ranking layer

Reason:

- confidence should be derived from signal-generation inputs, not only for presentation

Compatibility risk:

- low if added as a new column
- moderate if later reused by UI without clearly defining whether it is percentile-based or rule-based

### 3. `regime`

Business meaning:

- simplified market posture for the asset, such as trend-up, mixed, or risk-off

Candidate derivation inputs:

- `trend_score`
- `momentum_score`
- `risk_penalty`
- `ret_20d`, `ret_60d`, `ret_120d`, `ret_252d`
- `dist_from_52w_high`
- moving-average relationships from `factor_snapshot_latest.parquet`

Candidate values:

- `bullish`
- `neutral`
- `cautious`
- `defensive`

Recommended layer:

- ranking layer

Reason:

- regime is an interpretation of core ranking inputs and should be reproducible upstream

Compatibility risk:

- low if added as a new field
- moderate if UI later treats it as authoritative without a stable enum definition

### 4. `risk_level`

Business meaning:

- normalized risk classification of the asset at the current snapshot

Candidate derivation inputs:

- `volatility_20d`
- `volatility_60d`
- `risk_penalty`
- possibly `dist_from_52w_high` and `dist_from_52w_low`

Candidate values:

- `low`
- `moderate`
- `high`

Recommended layer:

- ranking layer

Reason:

- risk level is a signal attribute derived from model inputs, not just a visualization concern

Compatibility risk:

- low if it is additive
- moderate if users assume it equals realized volatility rather than a rule-based risk label

### 5. `horizon_days`

Business meaning:

- intended decision horizon for interpreting the current signal

Candidate derivation inputs:

- static config such as `30`, `60`, or `90`
- or mapped from dominant input windows, for example:
  - shorter for momentum-dominant profiles
  - longer for trend-dominant profiles

Recommended layer:

- ranking layer

Reason:

- horizon is part of signal semantics and should travel with the signal itself

Compatibility risk:

- low if additive
- moderate if users assume it is a forecast horizon rather than a signal interpretation horizon

## Recommended Generation Location

### Recommended source of truth

Generate new signal fields in the ranking layer.

Preferred future canonical output:

- extend `data/mart/investment/top_ranked_assets.parquet`
- extend `data/mart/investment/top_ranked_assets.csv`

Reason:

- the ranking layer already owns `decision`, `decision_reason`, and the cross-sectional score outputs
- signal fields should be generated once and reused downstream
- the visualization layer should stay focused on exporting, reshaping, and filtering, not recomputing core signal semantics

### Recommended visualization role

The visualization layer should consume ranking-layer signal fields and export a presentation-ready snapshot for the app or BI use cases.

## Proposed Signal Engine v1 Schema

Recommended additive schema on top of current ranking outputs:

- existing current columns
- `confidence`
- `regime`
- `risk_level`
- `horizon_days`

`decision` remains part of the schema and remains the primary user-facing stance field.

## Proposed Future File

### `data/visualization/investment/signal_heatmap_snapshot.csv`

Purpose:

- a compact serving file for signal overview tables, heatmaps, and asset-comparison visuals

Recommended columns:

- `date`
- `ticker`
- `source_ticker`
- `asset_type`
- `decision`
- `confidence`
- `regime`
- `risk_level`
- `horizon_days`
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
- `decision_reason`
- `source`

Design intent:

- keep the file narrow enough for lightweight UI loading
- include both summary signal fields and the score drivers needed for tooltips or explainers
- avoid duplicating raw feature-only columns like `volume`, `rolling_high_252d`, and `rolling_low_252d` unless a downstream use case requires them

## Compatibility Risks

### Low-risk changes

- adding new columns to `top_ranked_assets.parquet`
- adding new columns to `top_ranked_assets.csv`
- creating a new visualization file such as `signal_heatmap_snapshot.csv`

### Medium-risk areas

- introducing categorical enums without documenting allowed values
- defining `confidence` ambiguously as either a percentile or a confidence score
- defining `horizon_days` ambiguously relative to forecast horizons

### High-risk changes

- renaming current columns used by Streamlit
- changing current `decision` semantics without updating the UI copy and charts
- moving signal derivation into the visualization layer only, which would split business logic across layers

## Recommendation

For Signal Engine v1:

1. keep the current ranking calculations unchanged
2. extend the ranking output schema with additive signal fields
3. keep `top_ranked_assets.*` as the canonical signal source
4. optionally export a derived `signal_heatmap_snapshot.csv` from the visualization layer for UI and BI consumption

This keeps the project aligned with the current file-based pipeline while preparing a clean path for decision-oriented signal metadata.
