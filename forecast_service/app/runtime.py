"""Runtime helpers for caching, quota, and usage logging."""

import hashlib
import json
import sqlite3
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Deque, Dict, Optional, Tuple

from .schemas import ForecastRequest, ForecastResponse


def build_cache_key(request: ForecastRequest) -> str:
    payload = request.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ForecastCache:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, Tuple[float, ForecastResponse]] = {}

    def get(self, key: str) -> Optional[ForecastResponse]:
        item = self._store.get(key)
        if item is None:
            return None
        expiry, value = item
        if time.time() > expiry:
            self._store.pop(key, None)
            return None
        return value.model_copy(deep=True)

    def set(self, key: str, value: ForecastResponse) -> None:
        expiry = time.time() + self.ttl_seconds
        self._store[key] = (expiry, value.model_copy(deep=True))

    def clear(self) -> None:
        self._store.clear()

    def _purge_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, (expiry, _) in self._store.items() if now > expiry]
        for key in expired_keys:
            self._store.pop(key, None)

    def stats(self) -> Dict[str, Any]:
        self._purge_expired()
        return {
            "ttl_seconds": self.ttl_seconds,
            "entries": len(self._store),
        }


class SeriesQuotaLimiter:
    """Simple daily in-memory quota per series_id."""

    def __init__(self, daily_limit: int):
        self.daily_limit = daily_limit
        self._state: Dict[str, Tuple[str, int]] = {}

    def allow(self, series_id: str) -> Tuple[bool, int]:
        return self.allow_for_limit(series_id, self.daily_limit)

    def allow_for_limit(self, key: str, daily_limit: int) -> Tuple[bool, int]:
        today = datetime.now(timezone.utc).date().isoformat()
        date_key, used = self._state.get(key, (today, 0))
        if date_key != today:
            used = 0
        if used >= daily_limit:
            self._state[key] = (today, used)
            return False, 0
        used += 1
        self._state[key] = (today, used)
        return True, max(daily_limit - used, 0)

    def clear(self) -> None:
        self._state.clear()

    def stats(self, limit: int = 10) -> Dict[str, Any]:
        today = datetime.now(timezone.utc).date().isoformat()
        active_series = 0
        top_series = []
        for series_id, (date_key, used) in self._state.items():
            if date_key != today:
                continue
            active_series += 1
            top_series.append(
                {
                    "series_id": series_id,
                    "used": used,
                    "remaining": max(self.daily_limit - used, 0),
                }
            )
        top_series.sort(key=lambda x: x["used"], reverse=True)
        return {
            "daily_limit": self.daily_limit,
            "active_series": active_series,
            "top_series": top_series[: max(1, limit)],
        }


class TierPolicyManager:
    """Manages tier-level limits and model availability."""

    def __init__(self, tiers: Dict[str, Dict[str, Any]], default_tier: str):
        if not tiers:
            raise ValueError("tiers config cannot be empty")
        self._tiers = tiers
        self._default_tier = default_tier if default_tier in tiers else next(iter(tiers))

    @property
    def default_tier(self) -> str:
        return self._default_tier

    def get_policy(self, tier_name: Optional[str]) -> Dict[str, Any]:
        name = (tier_name or "").strip().lower() or self._default_tier
        if name not in self._tiers:
            raise KeyError(f"unknown tier: {name}")
        cfg = self._tiers[name]
        return {
            "name": name,
            "daily_quota": int(cfg["daily_quota"]),
            "max_horizon": int(cfg["max_horizon"]),
            "allowed_models": list(cfg["allowed_models"]),
        }

    def is_model_allowed(self, tier_name: str, model_id: str) -> bool:
        policy = self.get_policy(tier_name)
        return model_id in policy["allowed_models"]

    def list_tiers(self) -> Dict[str, Any]:
        items = []
        for name, cfg in self._tiers.items():
            items.append(
                {
                    "tier": name,
                    "daily_quota": int(cfg["daily_quota"]),
                    "max_horizon": int(cfg["max_horizon"]),
                    "allowed_models": list(cfg["allowed_models"]),
                }
            )
        items.sort(key=lambda x: x["tier"])
        return {
            "default_tier": self._default_tier,
            "tiers": items,
        }


@dataclass
class UsageEvent:
    ts: str
    series_id: str
    model_used: str
    cache_hit: bool
    runtime_ms: int


class UsageLogger:
    def __init__(self, max_items: int):
        self._events: Deque[UsageEvent] = deque(maxlen=max_items)

    def append(self, event: UsageEvent) -> None:
        self._events.append(event)

    def recent(self, limit: int = 50) -> list[Dict[str, Any]]:
        items = list(self._events)[-limit:]
        return [
            {
                "ts": e.ts,
                "series_id": e.series_id,
                "model_used": e.model_used,
                "cache_hit": e.cache_hit,
                "runtime_ms": e.runtime_ms,
            }
            for e in items
        ]

    def clear(self) -> None:
        self._events.clear()


class SQLiteUsageLogger:
    """Persistent usage logger backed by SQLite."""

    def __init__(self, db_path: str, max_items: int):
        self._db_path = db_path
        self._max_items = max_items
        self._lock = Lock()
        self._conn = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def _init_db(self) -> None:
        db_file = Path(self._db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                series_id TEXT NOT NULL,
                model_used TEXT NOT NULL,
                cache_hit INTEGER NOT NULL,
                runtime_ms INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_events_ts ON usage_events(ts)"
        )
        conn.commit()

    def append(self, event: UsageEvent) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute(
                """
                INSERT INTO usage_events (ts, series_id, model_used, cache_hit, runtime_ms)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.ts,
                    event.series_id,
                    event.model_used,
                    1 if event.cache_hit else 0,
                    event.runtime_ms,
                ),
            )
            conn.execute(
                """
                DELETE FROM usage_events
                WHERE id NOT IN (
                    SELECT id FROM usage_events
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (self._max_items,),
            )
            conn.commit()

    def recent(self, limit: int = 50) -> list[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                """
                SELECT ts, series_id, model_used, cache_hit, runtime_ms
                FROM usage_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        rows.reverse()
        return [
            {
                "ts": row[0],
                "series_id": row[1],
                "model_used": row[2],
                "cache_hit": bool(row[3]),
                "runtime_ms": int(row[4]),
            }
            for row in rows
        ]

    def clear(self) -> int:
        with self._lock:
            conn = self._connect()
            cur = conn.execute("DELETE FROM usage_events")
            conn.commit()
            return int(cur.rowcount or 0)

    def count(self) -> int:
        with self._lock:
            conn = self._connect()
            row = conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()
            return int(row[0]) if row else 0

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            conn = self._connect()
            total_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_calls,
                    SUM(cache_hit) AS cache_hits,
                    AVG(runtime_ms) AS avg_runtime_ms
                FROM usage_events
                """
            ).fetchone()
            model_rows = conn.execute(
                """
                SELECT model_used, COUNT(*) AS calls
                FROM usage_events
                GROUP BY model_used
                ORDER BY calls DESC
                """
            ).fetchall()
            runtime_rows = conn.execute(
                """
                SELECT runtime_ms
                FROM usage_events
                ORDER BY runtime_ms ASC
                """
            ).fetchall()

        total_calls = int(total_row[0] or 0)
        cache_hits = int(total_row[1] or 0)
        avg_runtime_ms = float(total_row[2] or 0.0)
        by_model = {row[0]: int(row[1]) for row in model_rows}
        cache_hit_rate = float(cache_hits / total_calls) if total_calls else 0.0

        runtimes = [int(row[0]) for row in runtime_rows]

        def percentile(values, pct):
            if not values:
                return 0.0
            if len(values) == 1:
                return float(values[0])
            idx = max(0, min(len(values) - 1, int(round((pct / 100.0) * (len(values) - 1)))))
            return float(values[idx])

        return {
            "total_calls": total_calls,
            "cache_hits": cache_hits,
            "cache_hit_rate": round(cache_hit_rate, 4),
            "avg_runtime_ms": round(avg_runtime_ms, 2),
            "p50_runtime_ms": round(percentile(runtimes, 50), 2),
            "p95_runtime_ms": round(percentile(runtimes, 95), 2),
            "p99_runtime_ms": round(percentile(runtimes, 99), 2),
            "by_model": by_model,
        }
