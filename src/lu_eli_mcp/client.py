"""Async httpx client for Luxembourg Legilux open data (data.legilux.public.lu).

Legilux is keyless. Legal resources are addressed by their native ELI and dereferenced
as RDF/XML (the jolux ontology) via content negotiation. The full text of an act is a
"manifestation" file (Akoma Ntoso XML, HTML, PDF, DOCX) served from the filestore; the
RDF lists each manifestation's file URL under ``jolux:isExemplifiedBy``.

We keep our own backoff + disk cache. No SPARQL endpoint is exposed over HTTP, so discovery
is by ELI coordinates (no free-text search) - same shape as the ie-eli-mcp connector.
"""

from __future__ import annotations

import anyio
import httpx

from .cache import HttpCache

DEFAULT_BASE_URL = "https://data.legilux.public.lu"
DEFAULT_TIMEOUT = httpx.Timeout(40.0, connect=10.0)
USER_AGENT = "lu-eli-mcp/0.1.0 (+https://github.com/matematicsolutions/lu-eli-mcp)"

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3


class LegiluxClient:
    """Async client. Use as ``async with LegiluxClient() as c: ...``."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        cache: HttpCache | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._cache = cache or HttpCache()
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

    async def __aenter__(self) -> LegiluxClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()
        self._cache.close()

    async def _get(self, url: str, *, accept: str, category: str) -> str:
        cache_key = f"{accept} {url}"
        cached = self._cache.get(cache_key)
        if cached is not None and isinstance(cached, str):
            return cached
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                resp = await self._http.get(url, headers={"Accept": accept})
                resp.raise_for_status()
                self._cache.set(cache_key, resp.text, ttl=HttpCache.ttl_for(category))
                return resp.text
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code not in _RETRY_STATUS or attempt == _MAX_ATTEMPTS - 1:
                    raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
            await anyio.sleep(0.5 * (2**attempt))
        assert last_exc is not None
        raise last_exc

    async def get_rdf(self, eli_path: str) -> str:
        """Dereference an ELI resource as RDF/XML (jolux ontology)."""
        url = f"{self.base_url}/{eli_path}"
        return await self._get(url, accept="application/rdf+xml", category="act")

    async def get_file(self, file_url: str) -> str:
        """Fetch a manifestation file (e.g. the Akoma Ntoso XML) by its absolute URL."""
        return await self._get(file_url, accept="application/xml", category="act")
