"""Test support: an httpx-level mock server shared by the fixtures and tests.

Lives in its own module (not conftest) so test modules can import ``MockServer``
for type annotations. ``tests`` is on both pytest's ``pythonpath`` and pyright's
``extraPaths`` (see pyproject) so ``from support import MockServer`` resolves.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class Route:
    method: str
    path_contains: str
    status: int
    json: Any
    content: bytes | None
    text: str | None
    headers: dict[str, str] | None


@dataclass
class MockServer:
    """Records every request and answers with routes registered by the test.

    Routes match on ``(method, substring-of-path)``, first match wins; an
    unmatched request gets ``200 {}`` so all-optional models still parse. A fresh
    ``httpx.Response`` is built per call, so a route may be hit repeatedly.
    """

    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])
    _routes: list[Route] = field(default_factory=list[Route])

    def add(
        self,
        method: str,
        path_contains: str,
        *,
        json: Any = None,
        status: int = 200,
        content: bytes | None = None,
        text: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> MockServer:
        self._routes.append(
            Route(method.upper(), path_contains, status, json, content, text, headers)
        )
        return self

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for route in self._routes:
            if (
                request.method == route.method
                and route.path_contains in request.url.path
            ):
                kwargs: dict[str, Any] = {}
                if route.json is not None:
                    kwargs["json"] = route.json
                if route.content is not None:
                    kwargs["content"] = route.content
                if route.text is not None:
                    kwargs["text"] = route.text
                if route.headers is not None:
                    kwargs["headers"] = route.headers
                return httpx.Response(route.status, **kwargs)
        return httpx.Response(200, json={})

    # -- assertions / inspection ------------------------------------------------

    @property
    def last(self) -> httpx.Request:
        assert self.requests, "no request was made"
        return self.requests[-1]

    def request(self, method: str, path_contains: str) -> httpx.Request:
        matches = [
            r
            for r in self.requests
            if r.method == method.upper() and path_contains in r.url.path
        ]
        assert matches, (
            f"no {method.upper()} request matching {path_contains!r}; "
            f"saw {[(r.method, r.url.path) for r in self.requests]}"
        )
        return matches[-1]

    @staticmethod
    def body(request: httpx.Request) -> Any:
        return json.loads(request.content) if request.content else None
