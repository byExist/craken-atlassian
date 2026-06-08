"""Field schema."""

from atlassian.jira.schema.base import JiraModel


class FieldDetail(JiraModel):
    """A JIRA field (system or custom).

    OpenAPI: FieldDetails
    """

    id: str | None = None
    key: str | None = None
    name: str | None = None
    orderable: bool | None = None
    searchable: bool | None = None
    clause_names: list[str] = []


class PageBeanField(JiraModel):
    """Paginated field list.

    OpenAPI: PageBeanField
    """

    values: list[FieldDetail] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
    is_last: bool | None = None
