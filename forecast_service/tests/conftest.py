from app.main import forecast_cache, quota_limiter, usage_logger


def pytest_runtest_setup(item):
    forecast_cache.clear()
    quota_limiter.clear()
    usage_logger.clear()
