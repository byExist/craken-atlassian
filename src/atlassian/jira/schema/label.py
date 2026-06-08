"""Label schema."""

from atlassian.jira.schema.base import JiraModel


class PageBeanLabel(JiraModel):
    """Paginated label list.

    OpenAPI: PageBeanString (GET /rest/api/3/label)
    """

    values: list[str] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
    is_last: bool | None = None
