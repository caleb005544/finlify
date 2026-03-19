# Current Gaps And Next Steps

This document records gaps relative to the current file-based implementation. It does not propose redesigning the project away from its present architecture.

## Current Baseline

Finlify currently operates as:

- a local parquet and CSV pipeline
- Python transformation scripts under `src/`
- a single orchestration wrapper in `scripts/run_pipeline.py`
- a Streamlit app that reads local output files directly

## What Already Exists

- raw ingest from local TXT files
- staging outputs for ticker metadata and latest snapshot
- mart outputs for factor features, latest snapshot, and rankings
- visualization CSV exports
- forecast CSV export
- orchestration run logs and `summary.json`
- unit tests for ranking and visualization export logic

## Gaps In The Current Implementation

### 1. App Input Consistency Gap

Current state:

- Streamlit reads `data/mart/investment/top_ranked_assets.csv`
- The orchestration wrapper refreshes `data/mart/investment/top_ranked_assets.parquet` in step 6

Impact:

- the app can read a stale ranking CSV if the CSV mirror is not regenerated separately

### 2. Scheduling Gap

Current state:

- the pipeline can be run end-to-end through `scripts/run_pipeline.py`
- there is no committed scheduler, cron config, CI schedule, or alerting integration

Impact:

- runs are still operationally manual

### 3. Validation Depth Gap

Current state:

- the wrapper checks file existence, non-empty status, and row counts
- individual scripts contain their own validation logic

Impact:

- there is no centralized cross-run data quality reporting or SLA monitoring

### 4. Reproducibility Gap

Current state:

- dependencies are listed in `requirements.txt`
- versions are not fully pinned for strict reproducibility

Impact:

- environment consistency may vary across machines or future reruns

### 5. Runtime Surface Gap

Current state:

- the repository contains `src/api`, `src/db`, `src/models`, `src/schemas`, and `src/services`
- these directories are not part of the active pipeline path

Impact:

- the repo structure suggests architectural expansion areas that are not yet implemented

### 6. Forecast Operations Gap

Current state:

- forecast export is produced successfully as a batch CSV
- many tickers use fallback forecast paths

Impact:

- forecasting works operationally, but monitoring is still log-based rather than managed as a formal operational service

## Recommended Next Steps

These are incremental improvements that stay within the current file-based architecture.

1. Align app input artifacts with orchestration output
   - either refresh `top_ranked_assets.csv` during the normal pipeline run or update the app to read the canonical ranking artifact

2. Add a scheduled trigger for `scripts/run_pipeline.py`
   - keep the current wrapper and add scheduling around it rather than redesigning the pipeline

3. Add lightweight post-run health checks
   - verify the app-read files exist and have expected row counts after each run

4. Improve dependency reproducibility
   - tighten version pinning in the execution environment

5. Keep documenting the active architecture clearly
   - avoid mixing future database or dbt plans into current-state operational docs

## Explicitly Out Of Scope For Current-State Docs

The following are not part of the active implementation and should not be described as current architecture:

- database-backed storage
- dbt-managed transformation models
- Airflow or Prefect DAG execution
- live database reads from Streamlit
