"""Shared httpx event hooks for the Jira and Confluence clients."""

from collections.abc import Callable

import httpx


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
      body (e.g. ``"priority": "Field 'priority' cannot be set."``). httpx's
      default ``raise_for_status`` discards that body and leaves only the status
      line, so we attach it verbatim. It's almost always a small JSON
      ``ErrorCollection``, readable as-is; on the rare non-JSON gateway error the
      raw text is surfaced just the same. No parsing, no truncation — the harness
      handles an oversized body if one ever arrives.
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
        body = response.text.strip() or "(empty response body)"
        raise httpx.HTTPStatusError(
            f"{service} returned {response.status_code} "
            f"{response.reason_phrase}: {body}",
            request=response.request,
            response=response,
        )

    return _raise_on_error
