"""Forecast service configuration."""

import os

SERVICE_NAME = "finlify-forecast"
SERVICE_VERSION = "3.0.0"
DEFAULT_MODEL = "dummy_v0"
AVAILABLE_MODELS = ("dummy_v0", "sarima_v0", "prophet_v0", "xgboost_v0")
MIN_HORIZON = 1
MAX_HORIZON = 365
PORT = 8001

# Runtime controls for V3 DataOps features.
CACHE_TTL_SECONDS = int(os.getenv("FORECAST_CACHE_TTL_SECONDS", "300"))
SERIES_DAILY_QUOTA = int(os.getenv("FORECAST_SERIES_DAILY_QUOTA", "200"))
USAGE_LOG_MAX_ITEMS = int(os.getenv("FORECAST_USAGE_LOG_MAX_ITEMS", "1000"))
USAGE_LOG_DB_PATH = os.getenv(
    "FORECAST_USAGE_LOG_DB_PATH",
    "/tmp/finlify_forecast_usage.sqlite3",
)

# Auto routing controls.
ROUTING_ENABLE_SARIMA = os.getenv("FORECAST_ROUTING_ENABLE_SARIMA", "true").lower() == "true"
ROUTING_ENABLE_PROPHET = os.getenv("FORECAST_ROUTING_ENABLE_PROPHET", "true").lower() == "true"
ROUTING_ENABLE_XGBOOST = os.getenv("FORECAST_ROUTING_ENABLE_XGBOOST", "true").lower() == "true"
ROUTING_PROPHET_MIN_OBS = int(os.getenv("FORECAST_ROUTING_PROPHET_MIN_OBS", "60"))
ROUTING_PROPHET_MIN_HORIZON = int(os.getenv("FORECAST_ROUTING_PROPHET_MIN_HORIZON", "21"))
ROUTING_SARIMA_MIN_OBS = int(os.getenv("FORECAST_ROUTING_SARIMA_MIN_OBS", "24"))
ROUTING_XGBOOST_MIN_OBS = int(os.getenv("FORECAST_ROUTING_XGBOOST_MIN_OBS", "90"))
ROUTING_XGBOOST_MAX_HORIZON = int(os.getenv("FORECAST_ROUTING_XGBOOST_MAX_HORIZON", "14"))
