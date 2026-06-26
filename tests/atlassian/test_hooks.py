"""Tests for atlassian.hooks.error_hook.

403 -> actionable PermissionError; other 4xx/5xx -> HTTPStatusError carrying the
Atlassian response body so the offending field is visible without bisecting.
"""

from typing import Any

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


def test_400_surfaces_jira_field_errors():
    hook = error_hook("Jira", "project")
    body: dict[str, Any] = {
        "errorMessages": [],
        "errors": {"priority": "Field 'priority' cannot be set."},
    }

    with pytest.raises(httpx.HTTPStatusError) as exc:
        hook(_response(400, body))

    message = str(exc.value)
    assert "400" in message
    assert "priority: Field 'priority' cannot be set." in message


def test_400_surfaces_jira_error_messages():
    hook = error_hook("Jira", "project")

    with pytest.raises(httpx.HTTPStatusError) as exc:
        hook(
            _response(400, {"errorMessages": ["Issue type is required."], "errors": {}})
        )

    assert "Issue type is required." in str(exc.value)


def test_error_surfaces_confluence_error_list():
    hook = error_hook("Confluence", "space")
    body = {"errors": [{"status": 400, "title": "Bad", "detail": "Body is invalid."}]}

    with pytest.raises(httpx.HTTPStatusError) as exc:
        hook(_response(400, body))

    assert "Body is invalid." in str(exc.value)


def test_error_falls_back_to_message_field():
    hook = error_hook("Confluence", "space")

    with pytest.raises(httpx.HTTPStatusError) as exc:
        hook(_response(404, {"message": "Page not found"}))

    assert "Page not found" in str(exc.value)


def test_error_handles_non_dict_json_body():
    hook = error_hook("Jira", "project")

    with pytest.raises(httpx.HTTPStatusError) as exc:
        hook(_response(400, ["unexpected", "list"]))

    assert "unexpected" in str(exc.value)


def test_error_handles_non_json_body():
    hook = error_hook("Jira", "project")
    resp = httpx.Response(
        500,
        text="Internal Server Error",
        request=httpx.Request("GET", "https://test.atlassian.net/x"),
    )

    with pytest.raises(httpx.HTTPStatusError) as exc:
        hook(resp)

    assert "500" in str(exc.value)
    assert "Internal Server Error" in str(exc.value)


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

    assert "priority: Field 'priority' cannot be set." in str(exc.value)


def test_403_propagates_through_a_real_client(jira_api: MockServer):
    """The hook is wired into the client, so a 403 surfaces as PermissionError."""
    from atlassian.jira import client

    jira_api.add("GET", "/rest/api/3/myself", status=403, json={"message": "denied"})

    with pytest.raises(PermissionError):
        client.get_current_user()
