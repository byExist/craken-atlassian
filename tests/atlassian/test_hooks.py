"""Tests for atlassian.hooks.forbidden_hook — 403 -> actionable PermissionError."""

import httpx
import pytest

from atlassian.hooks import forbidden_hook
from support import MockServer


def _response(status: int) -> httpx.Response:
    return httpx.Response(
        status,
        json={"errorMessages": ["nope"]},
        request=httpx.Request("GET", "https://test.atlassian.net/x"),
    )


def test_403_raises_permission_error_with_actionable_message():
    hook = forbidden_hook("Jira", "project")

    with pytest.raises(PermissionError) as exc:
        hook(_response(403))

    message = str(exc.value)
    assert "Jira" in message
    assert "403" in message
    assert "project" in message
    assert "Do not" in message  # tells the model not to retry


def test_hook_interpolates_service_and_scope():
    hook = forbidden_hook("Confluence", "space")

    with pytest.raises(PermissionError) as exc:
        hook(_response(403))

    message = str(exc.value)
    assert "Confluence" in message
    assert "space" in message
    assert "Jira" not in message


@pytest.mark.parametrize("status", [200, 201, 204, 400, 401, 404, 500])
def test_non_403_responses_pass_through(status: int):
    hook = forbidden_hook("Jira", "project")
    # Must not raise for any non-403 status.
    hook(_response(status))


def test_403_propagates_through_a_real_client(jira_api: MockServer):
    """The hook is wired into the client, so a 403 surfaces as PermissionError."""
    from atlassian.jira import client

    jira_api.add("GET", "/rest/api/3/myself", status=403, json={"message": "denied"})

    with pytest.raises(PermissionError):
        client.get_current_user()
