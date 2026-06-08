"""Changelog schema."""

from atlassian.jira.schema.base import JiraModel
from atlassian.jira.schema.user import User


class ChangeDetail(JiraModel):
    """A single field change in a changelog entry.

    OpenAPI: ChangeDetails
    """

    field: str | None = None
    from_string: str | None = None
    to_string: str | None = None


class Changelog(JiraModel):
    """A changelog entry on an issue.

    OpenAPI: Changelog
    """

    author: User | None = None
    created: str | None = None
    items: list[ChangeDetail] = []


class PageBeanChangelog(JiraModel):
    """Paginated changelog list.

    OpenAPI: PageBeanChangelog
    """

    values: list[Changelog] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
    is_last: bool | None = None
