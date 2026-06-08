"""Shared httpx event hooks for the Jira and Confluence clients."""

from collections.abc import Callable

import httpx


def forbidden_hook(service: str, scope: str) -> Callable[[httpx.Response], None]:
    """Build an httpx response hook that turns 403 into an actionable error.

    The message addresses the LLM calling the tool, not an end user: a
    ``{scope}``-level permission denial can't be resolved by retrying or by the
    model, so it says not to retry and to relay the gap to the user. Jira
    surfaces account-wide gaps ahead of time in tool descriptions (see
    ``atlassian.jira.permissions``); Confluence has no such API, so a 403 is its
    only signal. Either way the per-``{scope}`` case is only knowable once the
    call is attempted.
    """

    def _raise_on_forbidden(response: httpx.Response) -> None:
        if response.status_code == 403:
            response.read()
            raise PermissionError(
                f"{service} returned 403 Forbidden: your account lacks the "
                f"permission required for this action in this {scope}. Do not "
                f"retry; tell the user they lack the required {scope} permission. "
                f"It may exist in other {scope}s — a {scope} admin can grant it, "
                f"or use an account that has it."
            )

    return _raise_on_forbidden
