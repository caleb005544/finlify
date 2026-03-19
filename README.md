# Finlify

Finlify is a local, file-based investment analytics pipeline with a Streamlit front end.

Current architecture:

`input TXT -> raw parquet -> staging parquet -> mart parquet -> visualization CSV -> Streamlit`

The repository does not currently run on a database, dbt project, or Airflow-style scheduler. The active implementation is Python-script driven and orchestrated by [`scripts/run_pipeline.py`](/Users/caleb/Projects/finlify/scripts/run_pipeline.py).

## What The Project Does

- Ingests local Stooq TXT price files
- Builds normalized raw and staging datasets
- Computes factor-style price features for the Finlify core universe
- Produces latest rankings and offline forecast exports
- Serves the outputs through a Streamlit dashboard

## Main Entrypoints

- App: [`app/finlify_streamlit_mvp_app.py`](/Users/caleb/Projects/finlify/app/finlify_streamlit_mvp_app.py)
- Orchestration: [`scripts/run_pipeline.py`](/Users/caleb/Projects/finlify/scripts/run_pipeline.py)

## Core Pipeline Steps

1. `src/ingestion/initial_ingest.py`
   - TXT -> `data/raw/stock_price_stooq/stock_prices.parquet`
2. `src/transform/build_ticker_master.py`
   - raw -> `data/staging/stock_price_stooq/ticker_master.parquet`
3. `src/transform/build_latest_snapshot.py`
   - raw + ticker master -> `data/staging/stock_price_stooq/latest_snapshot.parquet`
4. `src/features/build_price_features.py`
   - raw + universe config -> `data/mart/investment/factor_features.parquet`
5. `src/ranking/build_factor_snapshot_latest.py`
   - factor features -> `data/mart/investment/factor_snapshot_latest.parquet`
6. `src/ranking/build_rankings.py`
   - latest factor snapshot -> `data/mart/investment/top_ranked_assets.parquet`
7. `src/visualization/build_visualization_exports.py`
   - mart -> `data/visualization/investment/*.csv`
8. `src/features/build_sarimax_forecast.py`
   - factor features -> `data/visualization/investment/asset_forecast_for_streamlit.csv`

## Run Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the full pipeline:

```bash
python scripts/run_pipeline.py
```

Dry run:

```bash
python scripts/run_pipeline.py --dry-run
```

Run a subset of steps:

```bash
python scripts/run_pipeline.py --from-step 4 --to-step 8
```

Run the app:

```bash
streamlit run app/finlify_streamlit_mvp_app.py
```

## Pipeline Run Outputs

Each orchestration run writes:

- `output/pipeline_runs/<run_id>/summary.json`
- `output/pipeline_runs/<run_id>/step_<n>_<name>.log`

These files provide step status, durations, output checks, and captured stdout/stderr.

## Key Data Folders

- `data/raw/`
- `data/staging/`
- `data/mart/`
- `data/visualization/`
- `output/pipeline_runs/`

## Current Documentation

- [`docs/data_pipeline_status.md`](/Users/caleb/Projects/finlify/docs/data_pipeline_status.md)
- [`docs/pipeline_runbook.md`](/Users/caleb/Projects/finlify/docs/pipeline_runbook.md)
- [`docs/current_gaps_and_next_steps.md`](/Users/caleb/Projects/finlify/docs/current_gaps_and_next_steps.md)
- [`docs/folder_structure.md`](/Users/caleb/Projects/finlify/docs/folder_structure.md)

## Current Caveat

The Streamlit app currently reads `data/mart/investment/top_ranked_assets.csv`, while the orchestration wrapper refreshes `data/mart/investment/top_ranked_assets.parquet` by default in step 6. A CSV mirror exists in the repo, but it is not refreshed automatically by the current wrapper unless `build_rankings.py` is run with `--output-csv`.
