"""Epic schema (Agile API)."""

from atlassian.jira.schema.base import JiraModel


class Epic(JiraModel):
    """An agile epic.

    OpenAPI (agile): Epic — GET /rest/agile/1.0/epic/{epicIdOrKey} response

    The spec ships only an example for this endpoint, and the example omits
    ``key``; real responses carry it.
    """

    key: str | None = None
    name: str | None = None
    summary: str | None = None
    done: bool | None = None
