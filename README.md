# Finlify

Finlify is a quantitative asset ranking platform that runs a daily factor-scoring pipeline and serves the results through a Next.js web app. It covers ~90 stocks and ETFs, updated automatically each trading day after NYSE close.

**Live Demo:** https://finlify.vercel.app

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, ShadCN UI, Recharts |
| Database | Supabase (PostgreSQL) |
| Pipeline | Python, GitHub Actions (daily cron, weekdays 23:00 UTC) |
| Data Source | Polygon.io Grouped Daily API |
| Deployment | Vercel |

---

## Architecture

```
Polygon.io API
      |
      v
ingest_polygon.py          (Step 1 — daily incremental ingest)
      |
      v
stock_prices.parquet  -->  Supabase (PostgreSQL)
      |                          |
      v                          v
Pipeline Steps 2-8         Next.js App (Vercel)
  - build_ticker_master         |
  - build_latest_snapshot       +--> /               Market Overview
  - build_price_features        +--> /asset/[ticker]  Asset Detail
  - build_factor_snapshot
  - build_rankings
  - build_signal_heatmap_snapshot
  - build_visualization_exports
      |
      v
  top_ranked_assets  -->  Supabase (rankings table)
```

---

## Features

- **Market Overview** — full universe ranked by composite factor score with BUY / HOLD / WATCH / AVOID signals
- **Stock / ETF filter** — cross-filter KPI cards and Top Opportunities panel
- **Asset Detail page** — interactive price chart with MA30 / MA50 / MA120 lines and statistical fan chart forecast bands
- **Company info card** — name, sector, description via Polygon Ticker Details v3
- **Rule-based decision explanation** — plain-English rationale for each BUY / WATCH / AVOID signal

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- A `.env.local` file in `app/` with `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Backend pipeline

```bash
pip install -r requirements.txt

# Full pipeline (steps 1-8)
python scripts/run_pipeline.py

# Subset of steps
python scripts/run_pipeline.py --from-step 2 --to-step 6

# Dry run
python scripts/run_pipeline.py --dry-run

# Ingest today's prices only
python -m src.ingestion.ingest_polygon
```

### Frontend

```bash
cd app
npm install
npm run dev
```

---

## Pipeline Steps

| Step | Script | Output |
|------|--------|--------|
| 1 | `src/ingestion/ingest_polygon.py` | `data/raw/.../stock_prices.parquet` + Supabase |
| 2 | `src/transform/build_ticker_master.py` | `data/staging/.../ticker_master.parquet` |
| 3 | `src/transform/build_latest_snapshot.py` | `data/staging/.../latest_snapshot.parquet` |
| 4 | `src/features/build_price_features.py` | `data/mart/.../factor_features.parquet` |
| 5 | `src/ranking/build_factor_snapshot_latest.py` | `data/mart/.../factor_snapshot_latest.parquet` |
| 6 | `src/ranking/build_rankings.py` | `data/mart/.../top_ranked_assets.parquet` + Supabase |
| 7 | `src/visualization/build_signal_heatmap_snapshot.py` | `data/visualization/.../signal_heatmap_snapshot.csv` |
| 8 | `src/visualization/build_visualization_exports.py` | `data/visualization/.../*.csv` |

Each run writes logs and a `summary.json` to `output/pipeline_runs/<run_id>/`.
