from app.forecast import route_model
from app.schemas import ForecastRequest


def _request(n_obs: int, horizon: int = 7, model_hint: str = "auto") -> ForecastRequest:
    return ForecastRequest(
        series_id="routing-series",
        freq="D",
        horizon=horizon,
        model_hint=model_hint,
        y=[{"ds": f"2025-01-{i+1:02d}", "y": 100 + i} for i in range(n_obs)],
    )


def test_auto_routes_to_prophet_when_threshold_met():
    req = _request(n_obs=80, horizon=30)
    model, reason = route_model(
        req,
        config={
            "enable_sarima": True,
            "enable_prophet": True,
            "enable_xgboost": False,
            "prophet_min_obs": 60,
            "prophet_min_horizon": 21,
            "sarima_min_obs": 24,
            "xgboost_min_obs": 90,
            "xgboost_max_horizon": 14,
        },
    )
    assert model == "prophet_v0"
    assert reason == "auto_daily_long_with_history"


def test_auto_routes_to_sarima_when_prophet_not_met():
    req = _request(n_obs=40, horizon=14)
    model, reason = route_model(
        req,
        config={
            "enable_sarima": True,
            "enable_prophet": True,
            "enable_xgboost": False,
            "prophet_min_obs": 60,
            "prophet_min_horizon": 21,
            "sarima_min_obs": 24,
            "xgboost_min_obs": 90,
            "xgboost_max_horizon": 14,
        },
    )
    assert model == "sarima_v0"
    assert reason == "auto_trend_series"


def test_hint_respects_disabled_model():
    req = _request(n_obs=100, horizon=30, model_hint="prophet")
    model, reason = route_model(
        req,
        config={
            "enable_sarima": True,
            "enable_prophet": False,
            "enable_xgboost": True,
            "prophet_min_obs": 60,
            "prophet_min_horizon": 21,
            "sarima_min_obs": 24,
            "xgboost_min_obs": 90,
            "xgboost_max_horizon": 14,
        },
    )
    assert model == "dummy_v0"
    assert reason == "hint_prophet_disabled"


def test_auto_routes_to_xgboost_when_threshold_met():
    req = _request(n_obs=120, horizon=10)
    model, reason = route_model(
        req,
        config={
            "enable_sarima": True,
            "enable_prophet": True,
            "enable_xgboost": True,
            "prophet_min_obs": 200,
            "prophet_min_horizon": 30,
            "sarima_min_obs": 24,
            "xgboost_min_obs": 90,
            "xgboost_max_horizon": 14,
        },
    )
    assert model == "xgboost_v0"
    assert reason == "auto_short_horizon_dense_series"
