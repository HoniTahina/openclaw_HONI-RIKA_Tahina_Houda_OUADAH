import time
from unittest.mock import MagicMock
from dataharvest.middleware import LoggingMiddleware, RetryMiddleware, RateLimitMiddleware


class _FakeFetcherSection:
    retries = 3


class _FakeConfig:
    fetcher = _FakeFetcherSection()


def test_logging_middleware_passthrough():
    mw = LoggingMiddleware()
    url, headers = mw.process_request("https://example.com", {"User-Agent": "x"})
    assert url == "https://example.com"

    fake_response = MagicMock()
    fake_response.status_code = 200
    result = mw.process_response(fake_response)
    assert result is fake_response


def test_retry_middleware_backoff_exponentiel():
    mw = RetryMiddleware(_FakeConfig(), base_delay=1.0)
    assert mw.backoff_delay(0) == 1.0
    assert mw.backoff_delay(1) == 2.0
    assert mw.backoff_delay(2) == 4.0


def test_retry_middleware_should_retry_on_exception():
    mw = RetryMiddleware(_FakeConfig(), base_delay=0.001)
    assert mw.should_retry(0, exception=Exception("boom")) is True


def test_retry_middleware_stops_after_max_retries():
    mw = RetryMiddleware(_FakeConfig(), base_delay=0.001)
    assert mw.should_retry(3, exception=Exception("boom")) is False


def test_retry_middleware_retries_on_5xx():
    mw = RetryMiddleware(_FakeConfig(), base_delay=0.001)
    fake_response = MagicMock()
    fake_response.status_code = 503
    assert mw.should_retry(0, response=fake_response) is True


def test_rate_limit_middleware_enforces_delay():
    mw = RateLimitMiddleware(min_delay=0.05)
    mw.process_request("https://example.com/a", {})

    debut = time.perf_counter()
    mw.process_request("https://example.com/b", {})
    ecoule = time.perf_counter() - debut

    assert ecoule >= 0.04  # marge pour l'imprecision du timer
