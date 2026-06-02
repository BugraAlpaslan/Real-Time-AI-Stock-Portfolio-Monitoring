import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

import app.services.price_service as ps


def _mock_response(data: dict) -> MagicMock:
    body = json.dumps(data).encode()
    m = MagicMock()
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    m.read.return_value = body
    return m


@pytest.fixture(autouse=True)
def clear_cache():
    ps._cache.clear()
    yield
    ps._cache.clear()


class TestFetchMidas:
    def test_returns_price_from_list_response(self):
        payload = [{"price": 182.5}]
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            result = ps._fetch_midas("AAPL")
        assert result == 182.5

    def test_returns_none_on_network_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            result = ps._fetch_midas("AAPL")
        assert result is None

    def test_returns_none_for_empty_list(self):
        with patch("urllib.request.urlopen", return_value=_mock_response([])):
            result = ps._fetch_midas("AAPL")
        assert result is None


class TestFetchYahoo:
    def test_returns_regular_market_price(self):
        payload = {"chart": {"result": [{"meta": {"regularMarketPrice": 175.0}}]}}
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            result = ps._fetch_yahoo("AAPL")
        assert result == 175.0

    def test_returns_none_on_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            result = ps._fetch_yahoo("AAPL")
        assert result is None


class TestGetPrice:
    def test_returns_decimal_when_midas_succeeds(self):
        with patch.object(ps, "_fetch_midas", return_value=180.0):
            with patch.object(ps, "_fetch_yahoo", return_value=None):
                result = ps.get_price("AAPL")
        assert isinstance(result, Decimal)
        assert result == Decimal("180.0")

    def test_falls_back_to_yahoo_when_midas_fails(self):
        with patch.object(ps, "_fetch_midas", return_value=None):
            with patch.object(ps, "_fetch_yahoo", return_value=175.5):
                result = ps.get_price("AAPL")
        assert result == Decimal("175.5")

    def test_returns_none_when_both_fail(self):
        with patch.object(ps, "_fetch_midas", return_value=None):
            with patch.object(ps, "_fetch_yahoo", return_value=None):
                result = ps.get_price("AAPL")
        assert result is None

    def test_cache_hit_skips_api_calls(self):
        import time
        ps._cache["TSLA"] = (250.0, time.monotonic())
        with patch.object(ps, "_fetch_midas") as m_midas:
            with patch.object(ps, "_fetch_yahoo") as m_yahoo:
                result = ps.get_price("TSLA")
        m_midas.assert_not_called()
        m_yahoo.assert_not_called()
        assert result == Decimal("250.0")

    def test_expired_cache_refetches(self):
        import time
        ps._cache["MSFT"] = (300.0, time.monotonic() - ps.CACHE_TTL - 1)
        with patch.object(ps, "_fetch_midas", return_value=310.0):
            with patch.object(ps, "_fetch_yahoo", return_value=None):
                result = ps.get_price("MSFT")
        assert result == Decimal("310.0")
