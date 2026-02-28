"""
Tests for Finnhub-backed market data endpoints (/api/quotes, /api/history, /api/search).

All Finnhub HTTP calls are mocked — no real API key needed.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import main as app_module
from main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

FAKE_KEY = "test_api_key_12345"

FINNHUB_QUOTE = {"c": 182.50, "d": 1.23, "dp": 0.68, "h": 183.0, "l": 181.0, "o": 181.5, "pc": 181.27}
FINNHUB_PROFILE = {"name": "Apple Inc", "marketCapitalization": 2_800_000.0, "ticker": "AAPL"}
FINNHUB_METRIC = {
    "metric": {
        "peNormalizedAnnual": 28.5,
        "epsBasicExclExtraItemsAnnual": 6.13,
        "10DayAverageTradingVolume": 65_000,  # in thousands
    }
}
FINNHUB_CANDLE = {
    "s": "ok",
    "t": [1706745600, 1706832000, 1706918400],
    "c": [182.5, 183.0, 184.2],
    "o": [181.0, 182.0, 183.0],
    "h": [183.0, 184.0, 185.0],
    "l": [180.0, 181.0, 182.0],
    "v": [55_000_000, 60_000_000, 58_000_000],
}
FINNHUB_SEARCH = {
    "count": 2,
    "result": [
        {"description": "APPLE INC", "displaySymbol": "AAPL", "symbol": "AAPL", "type": "Common Stock"},
        {"description": "APPLE HOSPITALITY REIT", "displaySymbol": "APLE", "symbol": "APLE", "type": "Common Stock"},
        {"description": "APPLE BON FUND", "displaySymbol": "something", "symbol": "something", "type": "ETF"},  # filtered out
    ],
}


def _make_httpx_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a fake httpx.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    return mock_resp


# ---------------------------------------------------------------------------
# /api/quotes tests
# ---------------------------------------------------------------------------


class TestGetQuote:
    def setup_method(self):
        """Clear cache and set fake API key before each test."""
        app_module._market_cache.clear()
        app_module.FINNHUB_API_KEY = FAKE_KEY

    def _mock_get(self, url: str, **kwargs) -> MagicMock:
        """Route mock responses by URL path."""
        if "/quote" in url:
            return _make_httpx_response(FINNHUB_QUOTE)
        if "/profile2" in url:
            return _make_httpx_response(FINNHUB_PROFILE)
        if "/metric" in url:
            return _make_httpx_response(FINNHUB_METRIC)
        return _make_httpx_response({})

    def test_returns_correct_shape(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = self._mock_get

            resp = client.get("/api/quotes?ticker=AAPL")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["name"] == "Apple Inc"
        assert isinstance(data["price"], float)
        assert isinstance(data["change"], float)
        assert isinstance(data["change_percent"], float)
        assert isinstance(data["market_cap"], int)
        assert isinstance(data["pe_ratio"], float)
        assert isinstance(data["eps"], float)
        assert isinstance(data["volume"], int)
        assert "date" in data

    def test_price_and_change_computed_correctly(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = self._mock_get

            resp = client.get("/api/quotes?ticker=AAPL")

        data = resp.json()
        assert data["price"] == round(FINNHUB_QUOTE["c"], 2)
        expected_change = round(FINNHUB_QUOTE["c"] - FINNHUB_QUOTE["pc"], 2)
        assert data["change"] == expected_change

    def test_market_cap_converted_from_millions(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = self._mock_get

            resp = client.get("/api/quotes?ticker=AAPL")

        data = resp.json()
        # 2_800_000 million → 2.8 trillion
        assert data["market_cap"] == int(2_800_000.0 * 1_000_000)

    def test_returns_503_when_api_key_not_set(self):
        app_module.FINNHUB_API_KEY = ""
        resp = client.get("/api/quotes?ticker=AAPL")
        assert resp.status_code == 503
        assert resp.json()["detail"]["error"] == "FINNHUB_NOT_CONFIGURED"

    def test_returns_504_on_timeout(self):
        import httpx as httpx_mod

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = httpx_mod.TimeoutException("timed out")

            resp = client.get("/api/quotes?ticker=AAPL")

        assert resp.status_code == 504
        assert resp.json()["detail"]["error"] == "UPSTREAM_TIMEOUT"

    def test_caches_result(self):
        call_count = 0

        def counting_mock(url, **kwargs):
            nonlocal call_count
            call_count += 1
            return self._mock_get(url, **kwargs)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = counting_mock

            client.get("/api/quotes?ticker=AAPL")
            client.get("/api/quotes?ticker=AAPL")

        # 3 calls per quote (quote + profile + metric), but only on first request
        assert call_count == 3


# ---------------------------------------------------------------------------
# /api/history tests
# ---------------------------------------------------------------------------


class TestGetHistory:
    def setup_method(self):
        app_module._market_cache.clear()
        app_module.FINNHUB_API_KEY = FAKE_KEY

    def test_returns_list_of_date_value_dicts(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = _make_httpx_response(FINNHUB_CANDLE)

            resp = client.get("/api/history?ticker=AAPL&range=1m")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert "date" in data[0]
        assert "value" in data[0]
        assert isinstance(data[0]["date"], str)
        assert isinstance(data[0]["value"], float)

    def test_returns_404_when_no_data(self):
        no_data_candle = {"s": "no_data", "t": [], "c": []}
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = _make_httpx_response(no_data_candle)

            resp = client.get("/api/history?ticker=FAKEXYZ&range=1m")

        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "NO_DATA"

    def test_default_range_is_1m(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = _make_httpx_response(FINNHUB_CANDLE)

            resp = client.get("/api/history?ticker=AAPL")

        assert resp.status_code == 200

    def test_503_when_no_api_key(self):
        app_module.FINNHUB_API_KEY = ""
        resp = client.get("/api/history?ticker=AAPL&range=1m")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# /api/search tests
# ---------------------------------------------------------------------------


class TestSearchStocks:
    def setup_method(self):
        app_module._market_cache.clear()
        app_module.FINNHUB_API_KEY = FAKE_KEY

    def test_returns_list_of_ticker_name(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = _make_httpx_response(FINNHUB_SEARCH)

            resp = client.get("/api/search?q=Apple")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # ETF should be filtered out
        assert all(item["ticker"] in ("AAPL", "APLE") for item in data)
        assert {"ticker": "AAPL", "name": "APPLE INC"} in data

    def test_filters_non_common_stock(self):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value = _make_httpx_response(FINNHUB_SEARCH)

            resp = client.get("/api/search?q=Apple")

        data = resp.json()
        tickers = [item["ticker"] for item in data]
        assert "something" not in tickers  # ETF filtered

    def test_503_when_no_api_key(self):
        app_module.FINNHUB_API_KEY = ""
        resp = client.get("/api/search?q=Apple")
        assert resp.status_code == 503
