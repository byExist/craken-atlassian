"""Sprint schema (Agile API)."""

from atlassian.jira.schema.base import JiraModel


class SprintBean(JiraModel):
    """An agile sprint.

    OpenAPI (jira-software): SprintBean
    """

    id: int | None = None
    name: str | None = None
    state: str | None = None
    goal: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    complete_date: str | None = None


class SprintPage(JiraModel):
    """Paginated sprint list.

    OpenAPI (jira-software): GET /rest/agile/1.0/board/{boardId}/sprint response
    """

    values: list[SprintBean] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
    is_last: bool | None = None
