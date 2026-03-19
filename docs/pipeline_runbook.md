# Finlify Pipeline Runbook

This runbook documents the current script-driven pipeline exactly as implemented in the repository.

## Prerequisites

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Confirm required inputs exist:

- `input/stock price/daily/us/**/*.txt`
- `input/finlify_core_universe.csv`

3. Run commands from the repository root.

## Canonical Orchestration Entrypoint

Preferred command:

```bash
python scripts/run_pipeline.py
```

Useful variants:

```bash
python scripts/run_pipeline.py --dry-run
python scripts/run_pipeline.py --from-step 1 --to-step 3
python scripts/run_pipeline.py --from-step 4 --to-step 8
python scripts/run_pipeline.py --run-id my_manual_run
```

## Current Step Order

### Step 1: Raw Ingest

Script:

- `src/ingestion/initial_ingest.py`

Purpose:

- Load local TXT files and build the raw parquet layer

Command:

```bash
python -m src.ingestion.initial_ingest
```

Expected outputs:

- `data/raw/stock_price_stooq/stock_prices.parquet`
- `data/raw/_failed_logs/*_initial_ingest_failed_files.csv`

### Step 2: Build Ticker Master

Script:

- `src/transform/build_ticker_master.py`

Purpose:

- Build per-ticker metadata from the raw parquet layer

Command:

```bash
python -m src.transform.build_ticker_master
```

Optional CSV mirror:

```bash
python -m src.transform.build_ticker_master \
  --output-csv data/staging/stock_price_stooq/ticker_master.csv
```

Expected output:

- `data/staging/stock_price_stooq/ticker_master.parquet`

### Step 3: Build Latest Snapshot

Script:

- `src/transform/build_latest_snapshot.py`

Purpose:

- Build the latest row per ticker with `prev_close` and `daily_return`

Command:

```bash
python -m src.transform.build_latest_snapshot
```

Optional CSV mirror:

```bash
python -m src.transform.build_latest_snapshot \
  --output-csv data/staging/stock_price_stooq/latest_snapshot.csv
```

Expected output:

- `data/staging/stock_price_stooq/latest_snapshot.parquet`

### Step 4: Build Factor Features

Script:

- `src/features/build_price_features.py`

Purpose:

- Build the feature mart for the Finlify core universe

Command:

```bash
python -m src.features.build_price_features
```

Optional sample export:

```bash
python -m src.features.build_price_features \
  --history-years 15 \
  --sample-csv data/mart/investment/factor_features_sample.csv \
  --sample-rows 1000
```

Expected output:

- `data/mart/investment/factor_features.parquet`

### Step 5: Build Latest Factor Snapshot

Script:

- `src/ranking/build_factor_snapshot_latest.py`

Purpose:

- Keep one latest feature row per source ticker

Command:

```bash
python -m src.ranking.build_factor_snapshot_latest
```

Optional CSV mirror:

```bash
python -m src.ranking.build_factor_snapshot_latest \
  --output-csv data/mart/investment/factor_snapshot_latest.csv
```

Expected output:

- `data/mart/investment/factor_snapshot_latest.parquet`

### Step 6: Build Rankings

Script:

- `src/ranking/build_rankings.py`

Purpose:

- Compute ranking scores, decisions, and deterministic ranks

Command:

```bash
python -m src.ranking.build_rankings
```

Optional CSV mirror:

```bash
python -m src.ranking.build_rankings \
  --output-csv data/mart/investment/top_ranked_assets.csv
```

Expected output:

- `data/mart/investment/top_ranked_assets.parquet`
- `data/mart/investment/top_ranked_assets.csv`

### Step 7: Build Visualization Exports

Script:

- `src/visualization/build_visualization_exports.py`

Purpose:

- Export BI and chart-friendly CSV files from mart outputs

Command:

```bash
python -m src.visualization.build_visualization_exports
```

Expected outputs:

- `data/visualization/investment/price_history_for_pbi.csv`
- `data/visualization/investment/latest_ranking_for_pbi.csv`

### Step 8: Build Forecast Export

Script:

- `src/features/build_sarimax_forecast.py`

Purpose:

- Export per-ticker forecast data for the Streamlit asset-detail chart

Command:

```bash
python -m src.features.build_sarimax_forecast
```

Expected output:

- `data/visualization/investment/asset_forecast_for_streamlit.csv`

### Step 9: Run Streamlit

```bash
streamlit run app/finlify_streamlit_mvp_app.py
```

## What `scripts/run_pipeline.py` Adds

The wrapper provides:

- fixed step order
- partial step execution
- dry-run mode
- run IDs
- per-step log files
- summary JSON output
- basic output validation

Generated run artifacts:

- `output/pipeline_runs/<run_id>/summary.json`
- `output/pipeline_runs/<run_id>/step_<n>_<name>.log`

## Validation Checklist

After a successful full run:

- `output/pipeline_runs/<run_id>/` exists
- `summary.json` exists
- step logs exist for executed steps
- expected parquet and CSV outputs exist and are non-empty
- `price_history_for_pbi.csv` is readable
- `latest_ranking_for_pbi.csv` is readable
- `asset_forecast_for_streamlit.csv` is readable

Additional app-read-path check:

- confirm `data/mart/investment/top_ranked_assets.csv` exists if you plan to run the current Streamlit app

## Known Caveats

- There is no committed scheduler for automatic daily execution
- The wrapper is a local orchestration script, not a workflow platform
- Step 6 does not refresh the ranking CSV mirror by default
- Some optional CSV mirrors in `data/staging/` and `data/mart/` may exist from prior manual runs rather than the current wrapper execution
