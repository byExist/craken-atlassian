"""Project schema."""

from atlassian.jira.schema.base import JiraModel
from atlassian.jira.schema.user import User


class Project(JiraModel):
    """A JIRA project.

    OpenAPI: Project
    """

    key: str | None = None
    name: str | None = None
    lead: User | None = None


class PageBeanProject(JiraModel):
    """Paginated project list.

    OpenAPI: PageBeanProject — GET /rest/api/3/project/search response
    """

    values: list[Project] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
    is_last: bool | None = None
