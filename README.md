# Finlify v3.0

**Policy-Driven Investment Scoring & Forecasting Platform**

Finlify is an auditable, configurable investment decisioning platform. It uses JSON policy files to define scoring logic, ensuring transparency and flexibility across different investment strategies (Balanced, Growth, Conservative).

- **Backend (Scoring)**: FastAPI service driven by dynamic policy schemas.
- **Forecast Service**: Time-series forecasting service with model routing, cache/quota, and usage observability.
- **Frontend**: Next.js dashboard for real-time analysis.

---

## ✨ Latest Updates

### Public Demo & Ticker Dashboard
- Added public routes:
  - `/demo`
  - `/about`
- Added an interactive ticker dashboard at `/ticker/[ticker]` with:
  - History range controls (`3y`, `1y/12m`, `6m`, `3m`, `1m`, `1w`, `3d`, `1d`) plus `+ / -`
  - Forecast show/hide toggle and forecast range controls (`1m`, `3m`, `6m`) plus `+ / -`
  - Combined chart overlay (history + forecast)
  - Quote KPI cards: Market Cap, P/E Ratio, EPS, Trade Volume
  - Forecast summary table (ticker/company/date/close/period/forecast/recommendation/why)

### Backend Quote/History Enhancements
- `/api/quotes` now returns:
  - `market_cap`, `pe_ratio`, `eps`, `volume`, `date`
- `/api/history` supports expanded ranges:
  - `1d`, `3d`, `1w`, `1m`, `3m`, `6m`, `12m`, `1y`, `3y`, `all`

### UI Theme Refresh
- Updated to a beige + blue visual system for the public dashboard.

---

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local testing)

### 2. Setup Environment
Clone the repo and create your local environment file:
```bash
git clone https://github.com/YOUR_USERNAME/finlify.git
cd finlify
cp .env.example .env
```

Optional: configure forecast runtime controls in `.env`:
```env
# Forecast runtime controls
FORECAST_CACHE_TTL_SECONDS=300
FORECAST_SERIES_DAILY_QUOTA=200
FORECAST_USAGE_LOG_MAX_ITEMS=1000
FORECAST_USAGE_LOG_DB_PATH=/tmp/finlify_forecast_usage.sqlite3

# Forecast routing controls
FORECAST_ROUTING_ENABLE_SARIMA=true
FORECAST_ROUTING_ENABLE_PROPHET=true
FORECAST_ROUTING_ENABLE_XGBOOST=true
FORECAST_ROUTING_PROPHET_MIN_OBS=60
FORECAST_ROUTING_PROPHET_MIN_HORIZON=21
FORECAST_ROUTING_SARIMA_MIN_OBS=24
FORECAST_ROUTING_XGBOOST_MIN_OBS=90
FORECAST_ROUTING_XGBOOST_MAX_HORIZON=14
```

### 3. Run with Docker
Start all services (Backend, Forecast, Frontend) with one command:
```bash
docker compose up --build
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Scoring Service (Backend)**: [http://localhost:8000](http://localhost:8000)
- **Forecast Service**: [http://localhost:8001](http://localhost:8001)

Demo entry points:
- [http://localhost:3000/demo](http://localhost:3000/demo)
- [http://localhost:3000/ticker/AAPL](http://localhost:3000/ticker/AAPL)

### 4. Select a Scoring Strategy
Toggle strategies via the `FINLIFY_POLICY_ID` environment variable:
```bash
# Default: balanced_v1
FINLIFY_POLICY_ID=growth_hightech_v1 docker compose up
```

---

## 🧪 Testing

We value reliability. run the full suite across both core services:

### Local Testing
```bash
# Backend (Scoring)
cd backend && python3 -m pytest tests/ -v

# Forecast Service
cd forecast_service && python3 -m pytest tests/ -v
```

### In-Container Testing
```bash
# Backend
docker compose exec backend python3 -m pytest tests/ -q

# Forecast
docker compose exec forecast python3 -m pytest tests/ -q
```

---

## 🛠 Troubleshooting

### 1) `Cannot connect to the Docker daemon`
Docker Desktop is not running (or still starting).  
Fix:
```bash
open -a Docker
docker info
```

### 2) `docker compose ps -a` is empty
Usually means build failed before containers were created.  
Run again and inspect the first failing service:
```bash
docker compose up --build
```

### 3) Frontend build fails during `next build`
Most often TypeScript compile errors in frontend files.  
Check:
```bash
docker compose build frontend --no-cache
```

### 4) Backend `/api/history` returns 500
If you see `TypeError: 'str' object is not callable`, make sure backend changes are up to date and rebuild:
```bash
docker compose down
docker compose up --build
```

---

## 🏗 Repo Structure

```
finlify/
├── backend/            # Scoring Service (FastAPI)
│   ├── main.py         # API endpoints (/score, /strategies)
│   ├── policy.py       # PolicyLoader & engine
│   └── tests/          # 50+ test cases
├── forecast_service/   # Forecast Service (FastAPI)
│   ├── app/            # Routing, model providers, cache/quota/usage runtime
│   └── tests/          # Contract + routing/runtime tests
├── frontend/           # Dashboard (Next.js 16)
├── docs/               # Governance & Schema documentation
│   └── policies/       # JSON strategy definitions
└── docker-compose.yml  # Multi-service orchestration
```

---

## 📡 API Usage Example

### POST `/score` (Scoring Service)
Override the default policy for a specific request:
```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "policy_id": "growth_hightech_v1",
    "profile": {
      "risk_level": "Medium",
      "horizon": "Long",
      "sector_preference": "Tech"
    }
  }'
```

### POST `/forecast` (Forecast Service)
Generate forecasts with model routing (`dummy_v0`, `sarima_v0`, `prophet_v0`, `xgboost_v0`):
```bash
curl -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "series_id": "STK-AAPL",
    "freq": "D",
    "horizon": 14,
    "model_hint": "auto",
    "y": [{"ds": "2025-01-01", "y": 150.0}, {"ds": "2025-01-02", "y": 155.0}]
  }'
```

### GET `/models` (Forecast Service)
List available forecast models and status.

### GET `/usage` (Forecast Service)
Read recent forecast usage events.

### Runtime Ops Endpoints (Forecast Service)
- `GET /runtime/status`: cache/quota/usage runtime state
- `GET /runtime/summary`: aggregate runtime metrics
- `POST /runtime/clear`: clear runtime state (`cache`, `quota`, `usage`)

Example:
```bash
curl http://localhost:8001/runtime/status
curl http://localhost:8001/runtime/summary
curl -X POST "http://localhost:8001/runtime/clear?cache=true&quota=false&usage=false"
```

---

## ⚖️ Governance & Policies

Finlify is built on high-integrity policy schemas.
- **Rules Explorer**: See [docs/POLICY_SCHEMA.md](docs/POLICY_SCHEMA.md)
- **Governance**: See [docs/governance.md](docs/governance.md)
- **Authoring**: See [docs/policy_authoring.md](docs/policy_authoring.md)
