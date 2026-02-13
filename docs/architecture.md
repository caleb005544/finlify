# Finlify v1 Architecture

## Overview
Finlify uses a strict monorepo structure to separate concerns between the UI (Frontend), Logic (Backend), and Data (Supabase).

```mermaid
graph TD
    User[User / Browser] -->|HTTPS| Frontend[Next.js Frontend]
    Frontend -->|Unauthenticated| Backend[FastAPI Backend]
    Frontend -->|Authenticated| Supabase[Supabase Auth & DB]
    Backend -->|Internal Logic| Scoring[Scoring Engine]
    Backend -->|Internal Logic| Forecast[Forecast Engine (Mocked)]
    Backend -.->|Read-Only| Supabase
```

## Contracts

1. **Frontend**:
    - NEVER accesses external APIs directly (Yahoo, etc.).
    - ALWAYS calls Backend for `scoring` and `forecasting`.
    - Uses Supabase SDK for Auth and CRUD on `user_watchlist` and `assumption_profiles`.

2. **Backend**:
    - stateless FastAPI service.
    - provides deterministic scoring logic.
    - provides mocked forecast data (simulating ML service).
    - proxies stock market data (simulated).

3. **Database (Supabase)**:
    - Truth for User Data.
    - RLS enabled on all tables.
