"""Tests for atlassian.hooks.error_hook.

403 -> actionable PermissionError; other 4xx/5xx -> HTTPStatusError carrying the
response body verbatim so the offending field is visible without bisecting.
"""

import httpx
import pytest

from atlassian.hooks import error_hook
from support import MockServer


def _response(status: int, json: object | None = None) -> httpx.Response:
    return httpx.Response(
        status,
        json=json if json is not None else {"errorMessages": ["nope"]},
        request=httpx.Request("GET", "https://test.atlassian.net/x"),
    )


def test_403_raises_permission_error_with_actionable_message():
    hook = error_hook("Jira", "project")

    with pytest.raises(PermissionError) as exc:
        hook(_response(403))

    message = str(exc.value)
    assert "Jira" in message
    assert "403" in message
    assert "project" in message
    assert "Do not" in message  # tells the model not to retry


def test_hook_interpolates_service_and_scope():
    hook = error_hook("Confluence", "space")

    with pytest.raises(PermissionError) as exc:
        hook(_response(403))

    message = str(exc.value)
    assert "Confluence" in message
    assert "space" in message
    assert "Jira" not in message


@pytest.mark.parametrize("status", [200, 201, 204])
def test_success_responses_pass_through(status: int):
    hook = error_hook("Jira", "project")
    # Must not raise for any 2xx status.
    hook(httpx.Response(status, request=httpx.Request("GET", "https://x/y")))


def test_error_surfaces_json_body_verbatim():
    hook = error_hook("Jira", "project")
    body = {"errors": {"priority": "Field 'priority' cannot be set."}}

    with pytest.raises(httpx.HTTPStatusError) as exc:
        hook(_response(400, body))

    message = str(exc.value)
    assert "400" in message
    # The whole JSON envelope is attached, so the field name and reason are both there.
    assert "priority" in message
    assert "Field 'priority' cannot be set." in message


def test_error_surfaces_non_json_body():
    hook = error_hook("Jira", "project")
    resp = httpx.Response(
        500,
        text="<html>Bad Gateway</html>",
        request=httpx.Request("GET", "https://test.atlassian.net/x"),
    )

    with pytest.raises(httpx.HTTPStatusError) as exc:
        hook(resp)

    assert "500" in str(exc.value)
    assert "<html>Bad Gateway</html>" in str(exc.value)


def test_error_with_empty_body():
    hook = error_hook("Jira", "project")
    resp = httpx.Response(
        404, request=httpx.Request("GET", "https://test.atlassian.net/x")
    )

    with pytest.raises(httpx.HTTPStatusError) as exc:
        hook(resp)

    assert "(empty response body)" in str(exc.value)


def test_400_propagates_through_a_real_client(jira_api: MockServer):
    """The hook is wired into the client, so a 400 surfaces with its body."""
    from atlassian.jira import client

    jira_api.add(
        "POST",
        "/rest/api/3/issue",
        status=400,
        json={"errors": {"priority": "Field 'priority' cannot be set."}},
    )

    with pytest.raises(httpx.HTTPStatusError) as exc:
        client.create_issue("SAM", "x", priority="주요")

    assert "Field 'priority' cannot be set." in str(exc.value)


def test_403_propagates_through_a_real_client(jira_api: MockServer):
    """The hook is wired into the client, so a 403 surfaces as PermissionError."""
    from atlassian.jira import client

    jira_api.add("GET", "/rest/api/3/myself", status=403, json={"message": "denied"})

    with pytest.raises(PermissionError):
        client.get_current_user()
