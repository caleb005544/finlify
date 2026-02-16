from app.main import forecast_cache, quota_limiter, usage_logger, tier_manager
from app.forecast import reset_model_caches


def pytest_runtest_setup(item):
    forecast_cache.clear()
    quota_limiter.clear()
    usage_logger.clear()
    tier_manager._tiers["demo"]["daily_quota"] = 25
    reset_model_caches()
