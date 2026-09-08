"""httpx client construction shared by the Jira and Confluence clients."""

import httpx

from atlassian.config import get_auth
from atlassian.hooks import error_hook


def make_client(service: str, scope: str) -> httpx.Client:
    """An authenticated client for one Atlassian service.

    ``service`` and ``scope`` only feed the error hook's messages (e.g. "Jira" /
    "project"); the site, credentials, and headers are the same for both.
    """
    auth = get_auth()
    return httpx.Client(
        base_url=auth.url.rstrip("/"),
        auth=(auth.user, auth.token.get_secret_value()),
        # No default Content-Type: httpx sets it per request (application/json
        # for json=, multipart for files=). A fixed default would break uploads.
        headers={"Accept": "application/json"},
        event_hooks={"response": [error_hook(service, scope)]},
    )
