"""Project version schema."""

from atlassian.jira.schema.base import JiraModel


class ProjectVersion(JiraModel):
    """A project version (release).

    OpenAPI: Version
    """

    id: str | None = None
    name: str | None = None
    description: str | None = None
    archived: bool | None = None
    released: bool | None = None
    start_date: str | None = None
    release_date: str | None = None


class PageBeanVersion(JiraModel):
    """Paginated version list.

    OpenAPI: PageBeanVersion
    """

    values: list[ProjectVersion] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
    is_last: bool | None = None
