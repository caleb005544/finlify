# Finlify v3.0

**Policy-Driven Investment Scoring & Forecasting Platform**

Finlify is an auditable, configurable investment decisioning platform. It uses JSON policy files to define scoring logic, ensuring transparency and flexibility across different investment strategies (Balanced, Growth, Conservative).

- **Backend (Scoring)**: FastAPI service driven by dynamic policy schemas.
- **Forecast Service**: Time-series forecasting service (V3.0 dummy skeleton).
- **Frontend**: Next.js dashboard for real-time analysis.

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

### 3. Run with Docker
Start all services (Backend, Forecast, Frontend) with one command:
```bash
docker-compose up --build
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Scoring Service (Backend)**: [http://localhost:8000](http://localhost:8000)
- **Forecast Service**: [http://localhost:8001](http://localhost:8001)

### 4. Select a Strategy
Toggle strategies via the `FINLIFY_POLICY_ID` environment variable:
```bash
# Default: balanced_v1
FINLIFY_POLICY_ID=growth_hightech_v1 docker-compose up
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
docker-compose exec backend python3 -m pytest tests/ -q

# Forecast
docker-compose exec forecast python3 -m pytest tests/ -q
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
│   ├── app/            # Request/Response contract & dummy logic
│   └── tests/          # Contract correctness tests
├── frontend/           # Dashboard (Next.js 15)
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
Get deterministic, contract-correct forecasts:
```bash
curl -X POST http://localhost:8001/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "series_id": "STK-AAPL",
    "freq": "D",
    "horizon": 14,
    "y": [{"ds": "2025-01-01", "y": 150.0}, {"ds": "2025-01-02", "y": 155.0}]
  }'
```

---

## ⚖️ Governance & Policies

Finlify is built on high-integrity policy schemas.
- **Rules Explorer**: See [docs/POLICY_SCHEMA.md](docs/POLICY_SCHEMA.md)
- **Governance**: See [docs/governance.md](docs/governance.md)
- **Authoring**: See [docs/policy_authoring.md](docs/policy_authoring.md)
