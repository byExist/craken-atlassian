"""Shared httpx event hooks for the Jira and Confluence clients."""

import json
from collections.abc import Callable
from typing import Any, cast

import httpx


def _format_error_body(response: httpx.Response) -> str:
    """Distil an Atlassian error response into a single human-readable line.

    Jira returns ``{"errorMessages": [...], "errors": {"field": "why"}}`` and
    Confluence returns ``{"errors": [{"title": ..., "detail": ...}]}`` or a bare
    ``{"message": ...}``. Without this the only signal is the HTTP status, which
    forces callers to bisect their parameters to find the offending field.
    """
    try:
        raw = response.json()
    except (json.JSONDecodeError, ValueError):
        text = response.text.strip()
        return text[:1000] if text else "(empty response body)"

    if not isinstance(raw, dict):
        return json.dumps(raw)[:1000]
    data = cast(dict[str, Any], raw)

    parts: list[str] = []
    messages = data.get("errorMessages")
    if isinstance(messages, list):
        parts.extend(str(m) for m in cast(list[Any], messages))

    errors = data.get("errors")
    if isinstance(errors, dict):
        # Jira: {"priority": "Field 'priority' cannot be set."}
        parts.extend(
            f"{field}: {why}" for field, why in cast(dict[str, Any], errors).items()
        )
    elif isinstance(errors, list):
        # Confluence: [{"title": ..., "detail": ...}]
        for err in cast(list[Any], errors):
            if isinstance(err, dict):
                err_obj = cast(dict[str, Any], err)
                detail = err_obj.get("detail") or err_obj.get("title")
                if detail:
                    parts.append(str(detail))

    if not parts and data.get("message"):
        parts.append(str(data["message"]))

    return "; ".join(parts) if parts else json.dumps(data)[:1000]


def error_hook(service: str, scope: str) -> Callable[[httpx.Response], None]:
    """Build an httpx response hook that turns error statuses into useful errors.

    Two cases, both addressed to the LLM calling the tool rather than an end user:

    * ``403`` — a ``{scope}``-level permission denial can't be resolved by
      retrying or by the model, so the message says not to retry and to relay the
      gap to the user. Jira surfaces account-wide gaps ahead of time in tool
      descriptions (see ``atlassian.jira.permissions``); Confluence has no such
      API, so a 403 is its only signal. Either way the per-``{scope}`` case is
      only knowable once the call is attempted.

    * any other 4xx/5xx — Atlassian names the offending field(s) in the response
      body (e.g. ``priority: Field 'priority' cannot be set.``). httpx's default
      ``raise_for_status`` discards that body and leaves only the status line, so
      we read the body and fold it into the raised error.
    """

    def _raise_on_error(response: httpx.Response) -> None:
        if response.is_success:
            return
        response.read()
        if response.status_code == 403:
            raise PermissionError(
                f"{service} returned 403 Forbidden: your account lacks the "
                f"permission required for this action in this {scope}. Do not "
                f"retry; tell the user they lack the required {scope} permission. "
                f"It may exist in other {scope}s — a {scope} admin can grant it, "
                f"or use an account that has it."
            )
        raise httpx.HTTPStatusError(
            f"{service} returned {response.status_code} "
            f"{response.reason_phrase}: {_format_error_body(response)}",
            request=response.request,
            response=response,
        )

    return _raise_on_error
