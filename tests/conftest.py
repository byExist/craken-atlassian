"""Shared test fixtures wiring the mock server into the client singletons.

The Jira and Confluence clients are lazy ``httpx.Client`` singletons. Tests must
never hit the network, so the fixtures here:

* clear ``ATLASSIAN_*`` env vars (autouse) so a stray call fails loudly instead
  of reaching a real instance configured on the developer's machine;
* reset the client singletons between tests;
* inject an ``httpx.MockTransport`` whose handler is the recording router
  ``support.MockServer``, and patch ``get_auth`` so the real client is built with
  dummy credentials and its real ``event_hooks`` (the 403 ``forbidden_hook``).

All patching goes through pytest-mock's ``mocker`` (no ``monkeypatch``); env vars
are handled with ``mocker.patch.dict(os.environ)``, which snapshots and restores
the environment around each test.
"""

import os
from types import ModuleType
from typing import Any

import httpx
import pytest
from pytest_mock import MockerFixture

from atlassian.config import Auth, get_auth
from atlassian.confluence import client as confluence_client
from atlassian.jira import client as jira_client
from support import MockServer

# The genuine constructor, captured before any test patches ``httpx.Client``.
_REAL_HTTPX_CLIENT = httpx.Client

_FAKE_AUTH = Auth(
    domain="test.atlassian.net",
    user="tester@example.com",
    token="dummy-token",  # type: ignore[arg-type]
)

_ATLASSIAN_ENV = (
    "ATLASSIAN_DOMAIN",
    "ATLASSIAN_USER",
    "ATLASSIAN_TOKEN",
    "ATLASSIAN_WRITE_ENABLED",
)


def _install(mocker: MockerFixture, module: ModuleType) -> MockServer:
    """Point a client module's singleton at a fresh MockServer transport."""
    server = MockServer()
    mocker.patch.object(module, "_client", None)
    mocker.patch.object(module, "get_auth", lambda: _FAKE_AUTH)

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs.setdefault("transport", httpx.MockTransport(server.handler))
        return _REAL_HTTPX_CLIENT(**kwargs)

    mocker.patch.object(module.httpx, "Client", factory)
    return server


@pytest.fixture(autouse=True)
def isolate_env(mocker: MockerFixture) -> None:
    """Strip real Atlassian config and reset singletons around every test."""
    mocker.patch.dict(os.environ)  # snapshot; restored after the test
    for var in _ATLASSIAN_ENV:
        os.environ.pop(var, None)
    get_auth.cache_clear()
    mocker.patch.object(jira_client, "_client", None)
    mocker.patch.object(confluence_client, "_client", None)


@pytest.fixture
def jira_api(mocker: MockerFixture) -> MockServer:
    """A MockServer wired into the Jira client singleton."""
    return _install(mocker, jira_client)


@pytest.fixture
def confluence_api(mocker: MockerFixture) -> MockServer:
    """A MockServer wired into the Confluence client singleton."""
    return _install(mocker, confluence_client)
