# Finlify Orchestration Plan (Design-Only)

This plan is a design document for orchestrating the existing script-based pipeline in a controlled and repeatable way.

It is based on:

- `docs/folder_structure.md`
- `docs/data_pipeline_status.md`
- `docs/pipeline_runbook.md`
- `docs/current_gaps_and_next_steps.md`

No code changes are proposed here.

## Objective

Define a canonical, repeatable pipeline execution model that:

- runs the current scripts in correct dependency order,
- performs lightweight validation gates between steps,
- stops safely on critical failures,
- records run-level status for operations,
- remains compatible with the current file-based architecture.

## Canonical Pipeline Order (Current Scripts)

1. `src/ingestion/initial_ingest.py` *(raw ingest)*
2. `src/transform/build_ticker_master.py` *(staging metadata)*
3. `src/transform/build_latest_snapshot.py` *(staging latest snapshot)*
4. `src/features/build_price_features.py` *(mart features)*
5. `src/ranking/build_factor_snapshot_latest.py` *(mart latest factor snapshot)*
6. `src/ranking/build_rankings.py` *(mart rankings)*
7. `src/visualization/build_visualization_exports.py` *(serving CSV exports)*
8. `src/features/build_sarimax_forecast.py` *(serving forecast export)*

Notes:

- Step 3 is useful for staging observability but appears non-critical for current Streamlit path. **Needs verification** whether it must run every daily cycle.
- Step 1 may be full refresh from local TXT dump (not incremental). **Needs verification** for intended daily frequency.

## Step-by-Step Orchestration Contract

| Step | Script | Purpose | Expected Input | Expected Output | Validation Check | Failure Should Stop Pipeline |
|---|---|---|---|---|---|---|
| 1 | `src/ingestion/initial_ingest.py` | Build raw parquet from local Stooq TXT files | `input/*/daily/us/**/*.txt` | `data/raw/stock_price_stooq/stock_prices.parquet` | output file exists; row count > 0; failed log generated/updated | Yes |
| 2 | `src/transform/build_ticker_master.py` | Build ticker metadata (`min/max date`, `is_active`) | raw parquet from step 1 | `data/staging/stock_price_stooq/ticker_master.parquet` (+csv optional) | file exists; rows > 0; unique `source_ticker` | Yes |
| 3 | `src/transform/build_latest_snapshot.py` | Build latest per-ticker snapshot | raw parquet + ticker master parquet | `data/staging/stock_price_stooq/latest_snapshot.parquet` (+csv optional) | file exists; rows = ticker master rows | No (recommended warning-only) |
| 4 | `src/features/build_price_features.py` | Build universe-filtered mart features | raw parquet + ticker master + `input/finlify_core_universe.csv` | `data/mart/investment/factor_features.parquet` (+sample csv optional) | file exists; rows > 0; `source_ticker` count expected (currently 90) | Yes |
| 5 | `src/ranking/build_factor_snapshot_latest.py` | Keep latest row per `source_ticker` | factor features parquet | `data/mart/investment/factor_snapshot_latest.parquet` (+csv optional) | file exists; row count = unique `source_ticker` | Yes |
| 6 | `src/ranking/build_rankings.py` | Compute trend/momentum/risk/composite ranks | factor snapshot latest parquet | `data/mart/investment/top_ranked_assets.parquet` (+csv optional) | file exists; rows > 0; `rank_overall` sequential | Yes |
| 7 | `src/visualization/build_visualization_exports.py` | Build app/BI serving CSVs | factor features parquet + ranked assets parquet | `data/visualization/investment/price_history_for_pbi.csv`, `data/visualization/investment/latest_ranking_for_pbi.csv` | files exist; non-empty; date parsing succeeds | Yes |
| 8 | `src/features/build_sarimax_forecast.py` | Build app forecast serving CSV | factor features parquet | `data/visualization/investment/asset_forecast_for_streamlit.csv` | file exists; rows = `tickers * horizon` (currently 90*90) | No (recommended warning-only with previous forecast fallback) |

## Proposed Single Entrypoint (Future Implementation)

### Preferred option

- Add one orchestration wrapper script: `scripts/run_pipeline.py`

Responsibilities:

- execute steps in canonical order,
- pass explicit arguments/paths,
- capture stdout/stderr + return code per step,
- run post-step validation checks,
- emit one run summary file (JSON) and concise console report.

### Alternative option

- `Makefile` wrapper with explicit targets (`ingest`, `staging`, `mart`, `serve`, `forecast`, `all`).

Tradeoff:

- simpler but weaker runtime metadata/reporting than Python wrapper.

## Proposed Logging and Checkpoint Strategy

For each pipeline run, create a run-id and write:

- `output/pipeline_runs/<run_id>/step_<n>_<name>.log`
- `output/pipeline_runs/<run_id>/summary.json`

Suggested `summary.json` fields:

- `run_id`, `start_ts`, `end_ts`, `status`
- step-level `status` (`success`, `warning`, `failed`, `skipped`)
- step-level `duration_sec`
- output artifacts + row/date stats (when available)
- exception details if failed

Checkpoint behavior:

- After each successful step, record checkpoint status in summary.
- If rerun with same run-id mode, allow resume from last successful checkpoint (**needs verification** design preference).

## Proposed Retry Boundary Strategy

Use targeted retries only where transient failures are likely:

- Step 1 ingest: retry once (input discovery/file read issues can be transient in mounted environments).
- Step 8 forecast: retry once per full step if runtime/fit instability causes step-level failure.

No automatic retries recommended for deterministic schema/validation errors (steps 2,4,5,6,7).

Failure categories:

- `hard_fail` (stop): missing required input, schema mismatch, empty critical output
- `soft_fail` (warn + continue): optional stage outputs, forecast export failure if prior forecast exists (**needs verification** policy)

## Operational Risks in Current File-Based Flow

1. Atomicity risk
   - Partial overwrite of CSV/parquet outputs can leave mixed-state artifacts if run fails mid-pipeline.

2. Repeatability/versioning risk
   - No run registry + weak data versioning; difficult to trace exactly which inputs produced current app files.

3. Scheduling/monitoring risk
   - No committed scheduler/alerting; failures may go unnoticed until manual app checks.

4. Concurrency risk
   - Parallel/manual runs can race and overwrite shared output files.

5. Serving freshness risk
   - Streamlit reads static files; stale output can persist if upstream step fails silently.

## What Should Later Move to dbt vs Remain in Python

### Good dbt candidates (once DB layer exists)

- Staging and mart transformations that are table-centric:
  - ticker master-like aggregations,
  - latest snapshot logic,
  - factor snapshot latest,
  - ranking output mart tables.

### Keep in Python (recommended)

- Raw TXT ingestion/parsing from local files.
- Forecast model generation (`build_sarimax_forecast.py`), including fallback logic.
- App-specific export shaping only if still needed for backward compatibility.

### Needs verification

- Whether rolling feature engineering in `build_price_features.py` should fully migrate to SQL/dbt or remain hybrid (SQL + Python UDF style).

## Recommended Minimal Next Implementation

1. Implement `scripts/run_pipeline.py` wrapper only (no business-logic changes).
2. Add run-level logs + `summary.json` output under `output/pipeline_runs/`.
3. Enforce stop/warn policy from this document.
4. Add one daily scheduler trigger (Cron/CI scheduled workflow) that runs the single entrypoint.
5. Add a lightweight health check command that validates key serving files before app use.

This provides controlled operations immediately while preserving the current file-based architecture.
