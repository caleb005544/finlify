# Finlify Folder Structure

This document describes the repository layout as it currently exists and how each folder relates to the active file-based pipeline.

## Top-Level Layout

- `app/`
- `data/`
- `docs/`
- `input/`
- `output/`
- `scripts/`
- `src/`
- `test/`
- `tests/`
- `README.md`
- `requirements.txt`

## App Layer

- `app/finlify_streamlit_mvp_app.py`
  - Streamlit app entrypoint
  - reads local output files directly
  - current read path includes:
    - `data/mart/investment/top_ranked_assets.csv`
    - `data/visualization/investment/price_history_for_pbi.csv`
    - `data/visualization/investment/asset_forecast_for_streamlit.csv`

## Orchestration Layer

- `scripts/run_pipeline.py`
  - canonical wrapper for the active pipeline
  - executes steps in order
  - supports dry-run and partial ranges
  - writes logs and summary files under `output/pipeline_runs/`

- `scripts/validate_rankings_calibration.py`
  - auxiliary validation script

## Source Code Layout

### `src/ingestion/`

- `initial_ingest.py`
  - ingests local Stooq TXT files into raw parquet
- `raw_data_summary.py`
  - utility script for profiling raw parquet contents

### `src/transform/`

- `build_ticker_master.py`
  - builds ticker metadata from raw parquet
- `build_latest_snapshot.py`
  - builds latest per-ticker snapshot from raw parquet plus ticker master

### `src/features/`

- `build_price_features.py`
  - builds the feature mart for the Finlify core universe
- `build_sarimax_forecast.py`
  - builds forecast CSV output for Streamlit

### `src/ranking/`

- `build_factor_snapshot_latest.py`
  - keeps the latest feature row per source ticker
- `build_rankings.py`
  - computes score components, decisions, and rankings

### `src/visualization/`

- `build_visualization_exports.py`
  - exports chart and ranking CSV files for BI and Streamlit-adjacent use

### `src/utils/`

- `price_utils.py`
  - shared price schema normalization utilities

### Other `src/` Directories Present

- `src/api/`
- `src/db/`
- `src/models/`
- `src/schemas/`
- `src/services/`

These directories exist in the repository but are not part of the active file-based pipeline execution path today.

## Data Layout

### `input/`

- `input/finlify_core_universe.csv`
  - curated asset universe for feature building
- `input/stock price/daily/us/**`
  - local TXT price source files used by ingest
- additional exploratory/reference CSVs also exist

### `data/raw/`

- `data/raw/stock_price_stooq/stock_prices.parquet`
  - consolidated raw price store
- `data/raw/_failed_logs/*.csv`
  - ingest failure logs

### `data/staging/`

- `data/staging/stock_price_stooq/ticker_master.parquet`
- `data/staging/stock_price_stooq/latest_snapshot.parquet`

Optional CSV mirrors may also exist:

- `data/staging/stock_price_stooq/ticker_master.csv`
- `data/staging/stock_price_stooq/latest_snapshot.csv`

### `data/mart/`

- `data/mart/investment/factor_features.parquet`
- `data/mart/investment/factor_snapshot_latest.parquet`
- `data/mart/investment/top_ranked_assets.parquet`

Optional mirrors and samples currently present in the repo include:

- `data/mart/investment/factor_features_sample.csv`
- `data/mart/investment/factor_snapshot_latest.csv`
- `data/mart/investment/top_ranked_assets.csv`

### `data/visualization/`

- `data/visualization/investment/price_history_for_pbi.csv`
- `data/visualization/investment/latest_ranking_for_pbi.csv`
- `data/visualization/investment/asset_forecast_for_streamlit.csv`

## Run Output Layout

### `output/pipeline_runs/`

Each pipeline execution writes a run folder:

- `output/pipeline_runs/<run_id>/summary.json`
- `output/pipeline_runs/<run_id>/step_<n>_<name>.log`

This folder is the current run-history and lightweight observability surface for the pipeline.

## Tests

- `tests/test_build_rankings.py`
- `tests/test_build_visualization_exports.py`
- `tests/getstooq.py`
- `test/test.py`

`tests/` contains the active focused tests. `test/test.py` is a legacy/manual-style test file still present in the repo.

## Current Structural Notes

- The repository is aligned around a local file pipeline, not a database-backed application stack.
- `scripts/run_pipeline.py` is now the active orchestration entrypoint and should be treated as part of the current architecture.
- Some CSV mirrors under `data/staging/` and `data/mart/` are optional or manually refreshed rather than guaranteed outputs of the wrapper.
