"""Lightweight performance benchmark for forecast_service.

Usage:
  cd forecast_service
  python3 scripts/benchmark_forecast.py
"""

import statistics
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app


def _payload(series_id: str, horizon: int = 14):
    start = datetime(2024, 1, 1)
    y = [
        {"ds": (start + timedelta(days=i)).strftime("%Y-%m-%d"), "y": 100.0 + (i * 0.15)}
        for i in range(180)
    ]
    return {
        "series_id": series_id,
        "freq": "D",
        "horizon": horizon,
        "model_hint": "auto",
        "y": y,
    }


def _bench(client: TestClient, runs: int, warmups: int, payload: dict, headers: dict):
    for _ in range(warmups):
        resp = client.post("/forecast", json=payload, headers=headers)
        assert resp.status_code == 200

    durations = []
    for _ in range(runs):
        t0 = time.perf_counter()
        resp = client.post("/forecast", json=payload, headers=headers)
        t1 = time.perf_counter()
        assert resp.status_code == 200
        durations.append((t1 - t0) * 1000.0)

    p50 = statistics.median(durations)
    p95 = sorted(durations)[int(len(durations) * 0.95) - 1]
    avg = statistics.mean(durations)
    return {"avg_ms": round(avg, 2), "p50_ms": round(p50, 2), "p95_ms": round(p95, 2)}


def main():
    client = TestClient(app)
    headers = {"X-Finlify-Tier": "pro", "X-Client-Id": "bench-client"}

    # Clear runtime state for a clean baseline.
    client.post("/runtime/clear")

    cold_payload = _payload("bench-cold")
    warm_payload = _payload("bench-warm")

    cold_stats = _bench(client, runs=20, warmups=0, payload=cold_payload, headers=headers)
    # Warm benchmark reuses the same payload to maximize cache hits.
    warm_stats = _bench(client, runs=20, warmups=1, payload=warm_payload, headers=headers)

    print("Forecast Benchmark (ms)")
    print(f"Cold path: avg={cold_stats['avg_ms']} p50={cold_stats['p50_ms']} p95={cold_stats['p95_ms']}")
    print(f"Warm path: avg={warm_stats['avg_ms']} p50={warm_stats['p50_ms']} p95={warm_stats['p95_ms']}")

    runtime_summary = client.get("/runtime/summary").json()
    print(f"Runtime summary: {runtime_summary}")


if __name__ == "__main__":
    main()
