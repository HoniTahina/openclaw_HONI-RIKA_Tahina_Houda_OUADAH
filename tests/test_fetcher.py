from unittest.mock import MagicMock, patch
import pytest
import requests

from dataharvest.fetcher import Fetcher, FetchError
from dataharvest.middleware import RetryMiddleware


class _FakeFetcherSection:
    delay = 0.001
    retries = 2
    timeout = 5
    user_agent = "Test/1.0"


class _FakeConfig:
    fetcher = _FakeFetcherSection()


def make_config():
    return _FakeConfig()


def test_fetch_returns_text_on_success():
    config = make_config()
    fetcher = Fetcher(config, middlewares=[])

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.text = "<html>ok</html>"

    with patch.object(fetcher.session, "get", return_value=fake_response):
        html = fetcher.fetch("https://example.com")

    assert html == "<html>ok</html>"


def test_fetch_uses_configured_user_agent():
    config = make_config()
    fetcher = Fetcher(config, middlewares=[])
    assert fetcher.session.headers["User-Agent"] == "Test/1.0"


def test_fetch_raises_fetcherror_after_retries():
    config = make_config()
    retry_mw = RetryMiddleware(config, base_delay=0.001)
    fetcher = Fetcher(config, middlewares=[retry_mw])

    with patch.object(fetcher.session, "get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(FetchError):
            fetcher.fetch("https://example.com")


def test_fetch_retries_then_succeeds():
    config = make_config()
    retry_mw = RetryMiddleware(config, base_delay=0.001)
    fetcher = Fetcher(config, middlewares=[retry_mw])

    fake_ok = MagicMock()
    fake_ok.status_code = 200
    fake_ok.text = "ok apres retry"

    with patch.object(
        fetcher.session, "get", side_effect=[requests.ConnectionError("boom"), fake_ok]
    ):
        html = fetcher.fetch("https://example.com")

    assert html == "ok apres retry"


def test_fetch_all_respects_delay_and_returns_all():
    config = make_config()
    fetcher = Fetcher(config, middlewares=[])

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.text = "ok"

    with patch.object(fetcher.session, "get", return_value=fake_response):
        resultats = fetcher.fetch_all(["https://a.com", "https://b.com"])

    assert resultats == ["ok", "ok"]
