from __future__ import annotations
import time
import requests
from .middleware import BaseMiddleware, RetryMiddleware


class FetchError(Exception):
    """Levee quand fetch() a epuise tous les retries disponibles."""


class Fetcher:
    def __init__(self, config, middlewares: list[BaseMiddleware] | None = None):
        self.config = config
        self.middlewares = middlewares or []
        self.session = requests.Session()
        # Le User-Agent vient toujours de la config, jamais du defaut Python
        self.session.headers.update({"User-Agent": config.fetcher.user_agent})
        self._retry_mw = next(
            (m for m in self.middlewares if isinstance(m, RetryMiddleware)), None
        )

    def fetch(self, url: str) -> str:
        
        attempt = 0

        while True:
            req_url, req_headers = url, dict(self.session.headers)
            for mw in self.middlewares:
                req_url, req_headers = mw.process_request(req_url, req_headers)

            try:
                response = self.session.get(
                    req_url,
                    headers=req_headers,
                    timeout=self.config.fetcher.timeout,
                )
                response.encoding = response.apparent_encoding
                
                for mw in self.middlewares:
                    response = mw.process_response(response)

                if response.status_code >= 400:
                    if self._retry_mw and self._retry_mw.should_retry(attempt, response=response):
                        time.sleep(self._retry_mw.backoff_delay(attempt))
                        attempt += 1
                        continue
                    response.raise_for_status()

                return response.text

            except requests.RequestException as e:
                if self._retry_mw and self._retry_mw.should_retry(attempt, exception=e):
                    time.sleep(self._retry_mw.backoff_delay(attempt))
                    attempt += 1
                    continue
                raise FetchError(
                    f"Echec du fetch apres {attempt + 1} tentative(s) sur {url} : {e}"
                ) from e

    def fetch_all(self, urls: list[str]) -> list[str]:
        
        resultats = []
        for i, url in enumerate(urls):
            resultats.append(self.fetch(url))
            if i < len(urls) - 1:
                time.sleep(self.config.fetcher.delay)
        return resultats
