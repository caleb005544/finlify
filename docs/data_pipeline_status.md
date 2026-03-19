# Finlify Data Pipeline Status

This document reflects the current implementation in the repository as of the latest successful full orchestration run:

- Run ID: `orchestration_full_20260313`
- Summary: `output/pipeline_runs/orchestration_full_20260313/summary.json`

## Current Architecture

Finlify currently runs as a local, file-based analytics pipeline:

`input TXT -> raw parquet -> staging parquet -> mart parquet -> visualization CSV -> Streamlit`

Current characteristics:

- Storage is local parquet and CSV
- Transformations are implemented in Python modules under `src/`
- Orchestration is handled by `scripts/run_pipeline.py`
- The app reads files directly rather than querying a database or API

## End-to-End Flow

1. Raw ingest
   - Local Stooq TXT files under `input/stock price/daily/us/**` are consolidated into one raw parquet file.
2. Staging
   - Raw price rows are normalized into ticker metadata and latest per-ticker snapshot datasets.
3. Mart
   - The Finlify core universe is filtered and feature-engineered.
   - A latest factor snapshot is built.
   - Rankings are computed from the latest factor snapshot.
4. Visualization
   - Historical price and latest ranking CSV exports are produced.
   - Forecast CSV export is produced for the Streamlit asset-detail view.
5. App serving
   - Streamlit reads local files from `data/mart/` and `data/visualization/`.

## Current Artifacts

Observed from the latest successful full run:

| Layer | Artifact | Exists | Rows | Notes |
|---|---|---:|---:|---|
| Raw | `data/raw/stock_price_stooq/stock_prices.parquet` | Yes | 27,368,667 | Consolidated historical raw store |
| Staging | `data/staging/stock_price_stooq/ticker_master.parquet` | Yes | 11,933 | Ticker metadata and `is_active` flag |
| Staging | `data/staging/stock_price_stooq/latest_snapshot.parquet` | Yes | 11,933 | Latest row per source ticker |
| Mart | `data/mart/investment/factor_features.parquet` | Yes | 319,679 | Universe-filtered feature mart |
| Mart | `data/mart/investment/factor_snapshot_latest.parquet` | Yes | 90 | One latest row per universe ticker |
| Mart | `data/mart/investment/top_ranked_assets.parquet` | Yes | 90 | Ranked latest snapshot output with signal metadata fields |
| Mart | `data/mart/investment/top_ranked_assets.csv` | Yes | 90 | Ranking CSV mirror used by Streamlit, including signal metadata fields |
| Visualization | `data/visualization/investment/price_history_for_pbi.csv` | Yes | 319,679 | Price history export |
| Visualization | `data/visualization/investment/latest_ranking_for_pbi.csv` | Yes | 90 | Latest ranking export |
| Visualization | `data/visualization/investment/asset_forecast_for_streamlit.csv` | Yes | 8,100 | 90 business-day forecast x 90 tickers |

Optional file mirrors also exist in the repository, including:

- `data/staging/stock_price_stooq/ticker_master.csv`
- `data/staging/stock_price_stooq/latest_snapshot.csv`
- `data/mart/investment/factor_snapshot_latest.csv`

The ranking CSV mirror is refreshed by the current ranking step. Other CSV mirrors are still optional and are not all refreshed by the orchestration wrapper by default.

Current additive signal fields in ranking output:

- `confidence`
- `regime`
- `risk_level`
- `horizon_days`

## Orchestration Status

The active orchestration path is:

- `scripts/run_pipeline.py`

Supported behavior:

- runs steps in canonical order
- supports `--dry-run`
- supports `--from-step` and `--to-step`
- writes per-step logs to `output/pipeline_runs/<run_id>/`
- writes one run summary JSON file
- performs lightweight existence, non-empty, and row-count checks on expected outputs

The wrapper is working for the current file-based pipeline. It is not a scheduler and does not provide external alerting or queue-based execution.

## Streamlit Consumption

The app currently reads:

- `data/mart/investment/top_ranked_assets.csv`
- `data/visualization/investment/price_history_for_pbi.csv`
- `data/visualization/investment/asset_forecast_for_streamlit.csv`

This means the app depends on a ranking CSV mirror in `data/mart/investment/` in addition to the visualization exports.

## Current Working State

What is currently working:

- full step 1 to 8 orchestration through `scripts/run_pipeline.py`
- raw, staging, mart, visualization, and forecast outputs
- run-level logs and summary artifacts
- ranking CSV output refreshed by step 6 for the app read path
- Streamlit-compatible CSV exports for price history and forecast

## Current Implementation Gaps

- No database-backed storage in the active path
- No dbt project in the active path
- No Airflow/Prefect-style scheduler committed in the repo
- No formal deployment environments for the pipeline runtime
