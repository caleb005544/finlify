"""Tests for POST /forecast contract correctness."""

from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# Fixed test series — 10 daily observations
DAILY_PAYLOAD = {
    "series_id": "test_daily",
    "freq": "D",
    "horizon": 7,
    "y": [
        {"ds": f"2025-01-{10 + i:02d}", "y": 100.0 + i}
        for i in range(10)
    ],
}

WEEKLY_PAYLOAD = {
    "series_id": "test_weekly",
    "freq": "W",
    "horizon": 4,
    "y": [
        {"ds": f"2025-01-{7 * (i + 1):02d}", "y": 200.0 + i * 5}
        for i in range(4)
    ],
}

MONTHLY_PAYLOAD = {
    "series_id": "test_monthly",
    "freq": "M",
    "horizon": 3,
    "y": [
        {"ds": f"2025-{i + 1:02d}-15", "y": 50.0}
        for i in range(6)
    ],
}


class TestForecastContract:
    """Core contract: response shape, field types, lengths."""

    def test_returns_200(self):
        resp = client.post("/forecast", json=DAILY_PAYLOAD)
        assert resp.status_code == 200

    def test_request_id_present(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        assert "request_id" in data
        assert isinstance(data["request_id"], str)
        assert len(data["request_id"]) > 0

    def test_model_used_is_dummy(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        assert data["model_used"] == "dummy_v0"

    def test_routing_reason(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        assert data["routing_reason"] == "v3.0_dummy"

    def test_forecast_length_equals_horizon(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        assert len(data["forecast"]) == DAILY_PAYLOAD["horizon"]

    def test_forecast_points_have_required_fields(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        for pt in data["forecast"]:
            assert "ds" in pt
            assert "yhat" in pt
            assert "yhat_lower" in pt
            assert "yhat_upper" in pt

    def test_forecast_values_are_numeric(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        for pt in data["forecast"]:
            assert isinstance(pt["yhat"], (int, float))
            assert isinstance(pt["yhat_lower"], (int, float))
            assert isinstance(pt["yhat_upper"], (int, float))

    def test_lower_le_yhat_le_upper(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        for pt in data["forecast"]:
            assert pt["yhat_lower"] <= pt["yhat"] <= pt["yhat_upper"]

    def test_trace_present(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        assert "trace" in data
        assert "cache_hit" in data["trace"]
        assert "runtime_ms" in data["trace"]

    def test_metrics_present(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        assert "metrics" in data
        assert isinstance(data["metrics"], dict)


class TestDatesMonotonic:
    """Forecast dates must be monotonically increasing and match freq."""

    def _parse(self, ds: str) -> datetime:
        return datetime.fromisoformat(ds)

    def test_daily_dates_increasing(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        dates = [self._parse(pt["ds"]) for pt in data["forecast"]]
        for i in range(1, len(dates)):
            assert dates[i] > dates[i - 1]

    def test_daily_dates_increment_by_one_day(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        dates = [self._parse(pt["ds"]) for pt in data["forecast"]]
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i - 1]).days
            assert delta == 1, f"Expected 1 day gap, got {delta}"

    def test_weekly_dates_increment_by_seven_days(self):
        data = client.post("/forecast", json=WEEKLY_PAYLOAD).json()
        dates = [self._parse(pt["ds"]) for pt in data["forecast"]]
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i - 1]).days
            assert delta == 7, f"Expected 7 day gap, got {delta}"

    def test_monthly_dates_increasing(self):
        data = client.post("/forecast", json=MONTHLY_PAYLOAD).json()
        dates = [self._parse(pt["ds"]) for pt in data["forecast"]]
        for i in range(1, len(dates)):
            assert dates[i] > dates[i - 1]

    def test_forecast_dates_start_after_last_observation(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        last_obs = self._parse(DAILY_PAYLOAD["y"][-1]["ds"])
        first_fc = self._parse(data["forecast"][0]["ds"])
        assert first_fc > last_obs


class TestDeterminism:
    """Dummy forecast must be deterministic across calls."""

    def test_same_input_same_output(self):
        resp1 = client.post("/forecast", json=DAILY_PAYLOAD).json()
        resp2 = client.post("/forecast", json=DAILY_PAYLOAD).json()

        # request_id will differ — compare forecasts
        fc1 = [(p["ds"], p["yhat"]) for p in resp1["forecast"]]
        fc2 = [(p["ds"], p["yhat"]) for p in resp2["forecast"]]
        assert fc1 == fc2


class TestDummyBaseline:
    """Dummy forecast uses last y as flat baseline."""

    def test_yhat_equals_last_observation(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        expected = DAILY_PAYLOAD["y"][-1]["y"]
        for pt in data["forecast"]:
            assert pt["yhat"] == expected

    def test_bounds_are_10_percent(self):
        data = client.post("/forecast", json=DAILY_PAYLOAD).json()
        baseline = DAILY_PAYLOAD["y"][-1]["y"]
        for pt in data["forecast"]:
            assert abs(pt["yhat_lower"] - baseline * 0.9) < 0.01
            assert abs(pt["yhat_upper"] - baseline * 1.1) < 0.01


class TestEdgeCases:
    """Error handling and edge cases."""

    def test_empty_y_returns_400(self):
        payload = {
            "series_id": "empty",
            "freq": "D",
            "horizon": 7,
            "y": [],
        }
        resp = client.post("/forecast", json=payload)
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "EMPTY_SERIES"

    def test_invalid_freq_returns_422(self):
        payload = {
            "series_id": "bad_freq",
            "freq": "X",
            "horizon": 7,
            "y": [{"ds": "2025-01-01", "y": 1.0}],
        }
        resp = client.post("/forecast", json=payload)
        assert resp.status_code == 422

    def test_horizon_zero_returns_422(self):
        payload = {
            "series_id": "zero_h",
            "freq": "D",
            "horizon": 0,
            "y": [{"ds": "2025-01-01", "y": 1.0}],
        }
        resp = client.post("/forecast", json=payload)
        assert resp.status_code == 422

    def test_horizon_exceeds_max_returns_422(self):
        payload = {
            "series_id": "over_h",
            "freq": "D",
            "horizon": 999,
            "y": [{"ds": "2025-01-01", "y": 1.0}],
        }
        resp = client.post("/forecast", json=payload)
        assert resp.status_code == 422

    def test_optional_fields_can_be_omitted(self):
        """exog, constraints, model_hint, policy_id are all optional."""
        payload = {
            "series_id": "minimal",
            "freq": "D",
            "horizon": 3,
            "y": [{"ds": "2025-01-01", "y": 42.0}],
        }
        resp = client.post("/forecast", json=payload)
        assert resp.status_code == 200

    def test_single_observation(self):
        payload = {
            "series_id": "single",
            "freq": "D",
            "horizon": 5,
            "y": [{"ds": "2025-06-01", "y": 99.9}],
        }
        resp = client.post("/forecast", json=payload)
        assert resp.status_code == 200
        assert len(resp.json()["forecast"]) == 5
