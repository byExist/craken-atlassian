"""Tests for atlassian.config — settings loaded from ATLASSIAN_* env vars."""

import os

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from atlassian.config import Auth, Config, get_auth

_CREDS = {
    "ATLASSIAN_DOMAIN": "acme.atlassian.net",
    "ATLASSIAN_USER": "dev@acme.com",
    "ATLASSIAN_TOKEN": "s3cr3t",
}


def test_config_defaults_to_read_only():
    assert Config().write_enabled is False


@pytest.mark.parametrize(
    ("value", "expected"),
    [("true", True), ("1", True), ("false", False), ("0", False)],
)
def test_config_reads_write_enabled_from_env(
    mocker: MockerFixture, value: str, expected: bool
):
    mocker.patch.dict(os.environ, {"ATLASSIAN_WRITE_ENABLED": value})
    assert Config().write_enabled is expected


def test_auth_reads_credentials_from_env(mocker: MockerFixture):
    mocker.patch.dict(os.environ, _CREDS)

    auth = Auth()  # type: ignore[call-arg]

    assert auth.url == "https://acme.atlassian.net"
    assert auth.user == "dev@acme.com"
    assert auth.token.get_secret_value() == "s3cr3t"


def test_auth_token_is_masked_in_repr(mocker: MockerFixture):
    mocker.patch.dict(os.environ, _CREDS)

    auth = Auth()  # type: ignore[call-arg]

    assert "s3cr3t" not in repr(auth)
    assert "s3cr3t" not in str(auth.token)


def test_auth_requires_all_credentials():
    # isolate_env has cleared ATLASSIAN_* — construction must fail, not guess.
    with pytest.raises(ValidationError):
        Auth()  # type: ignore[call-arg]


def test_get_auth_is_cached(mocker: MockerFixture):
    mocker.patch.dict(os.environ, _CREDS)
    get_auth.cache_clear()

    first = get_auth()
    second = get_auth()

    assert first is second
