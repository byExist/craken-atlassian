"""Worklog schema."""

from atlassian.jira.schema.adf import ADF
from atlassian.jira.schema.base import JiraModel


class Worklog(JiraModel):
    """A worklog entry on an issue.

    OpenAPI: Worklog — POST /rest/api/3/issue/{id}/worklog response
    """

    started: str | None = None
    time_spent: str | None = None
    comment: ADF | str | None = None


class PageOfWorklogs(JiraModel):
    """Paginated worklog list.

    OpenAPI: PageOfWorklogs — GET /rest/api/3/issue/{id}/worklog response
    """

    worklogs: list[Worklog] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
