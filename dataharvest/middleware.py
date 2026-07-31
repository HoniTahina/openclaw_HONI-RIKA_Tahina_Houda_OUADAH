
from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from urllib.parse import urlparse

logger = logging.getLogger("dataharvest")


class BaseMiddleware(ABC):
    @abstractmethod
    def process_request(self, url: str, headers: dict) -> tuple[str, dict]:
        """Retourne (url, headers) potentiellement modifies."""

    @abstractmethod
    def process_response(self, response):
        """Retourne la response potentiellement transformee."""


class LoggingMiddleware(BaseMiddleware):
    """Affiche [GET url] avant la requete et [status - Xs] apres."""

    def __init__(self):
        self._start = None

    def process_request(self, url: str, headers: dict) -> tuple[str, dict]:
        self._start = time.perf_counter()
        print(f"[GET {url}]")
        return url, headers

    def process_response(self, response):
        elapsed = time.perf_counter() - self._start if self._start is not None else 0.0
        status = getattr(response, "status_code", "?")
        print(f"[{status} - {elapsed:.2f}s]")
        return response


class RetryMiddleware(BaseMiddleware):
    

    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(self, config, base_delay: float = 1.0):
        self.max_retries = getattr(config.fetcher, "retries", 3)
        self.base_delay = base_delay

    def process_request(self, url: str, headers: dict) -> tuple[str, dict]:
        return url, headers

    def process_response(self, response):
        return response

    def should_retry(self, attempt: int, exception: Exception = None, response=None) -> bool:
        if attempt >= self.max_retries:
            return False
        if exception is not None:
            return True
        if response is not None and getattr(response, "status_code", 200) in self.RETRY_STATUS_CODES:
            return True
        return False

    def backoff_delay(self, attempt: int) -> float:
        return self.base_delay * (2 ** attempt)


class RateLimitMiddleware(BaseMiddleware):
    
    def __init__(self, min_delay: float = 1.0):
        self.min_delay = min_delay
        self._last_request: dict[str, float] = {}

    def process_request(self, url: str, headers: dict) -> tuple[str, dict]:
        domain = urlparse(url).netloc
        now = time.perf_counter()
        last = self._last_request.get(domain)
        if last is not None:
            wait = self.min_delay - (now - last)
            if wait > 0:
                time.sleep(wait)
        self._last_request[domain] = time.perf_counter()
        return url, headers

    def process_response(self, response):
        return response
