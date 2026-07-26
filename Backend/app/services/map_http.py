import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class MapHttpClient:

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._last_request_times: dict[str, float] = {}
        self._lock = threading.Lock()
        self._session = requests.Session()

        retry = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def _wait_for_slot(self, url: str, min_interval_seconds: float):
        if min_interval_seconds <= 0:
            return

        host = urlparse(url).netloc

        with self._lock:
            elapsed = time.time() - self._last_request_times.get(host, 0.0)

            if elapsed < min_interval_seconds:
                time.sleep(min_interval_seconds - elapsed)

            self._last_request_times[host] = time.time()

    def _store_cache(self, cache_key: str | None, value: Any):
        if cache_key:
            self._cache[cache_key] = value

    def _cached(self, cache_key: str | None) -> Any:
        if not cache_key:
            return None

        return self._cache.get(cache_key)

    def _raise_for_status(self, response: Response, context: str):
        if response.ok:
            return

        try:
            payload = response.json()
        except ValueError:
            payload = response.text

        raise ValueError(
            f"{context} failed with status {response.status_code}: {payload}"
        )

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: int = 15,
        cache_key: str | None = None,
        min_interval_seconds: float = 0,
        context: str = "HTTP request",
        before_request: Callable[[], None] | None = None,
    ) -> Any:
        cached = self._cached(cache_key)

        if cached is not None:
            return cached

        self._wait_for_slot(url, min_interval_seconds)

        if before_request:
            before_request()

        response = self._session.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout,
        )

        self._raise_for_status(response, context)

        data = response.json()
        self._store_cache(cache_key, data)

        return data

    def post_json(
        self,
        url: str,
        *,
        json_body: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        cache_key: str | None = None,
        min_interval_seconds: float = 0,
        context: str = "HTTP request",
        before_request: Callable[[], None] | None = None,
    ) -> Any:
        cached = self._cached(cache_key)

        if cached is not None:
            return cached

        self._wait_for_slot(url, min_interval_seconds)

        if before_request:
            before_request()

        response = self._session.post(
            url,
            json=json_body,
            headers=headers,
            timeout=timeout,
        )

        self._raise_for_status(response, context)

        data = response.json()
        self._store_cache(cache_key, data)

        return data


map_http_client = MapHttpClient()
