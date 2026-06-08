"""Common types shared across JIRA schema modules."""

from atlassian.jira.schema.base import JiraModel


class StatusCategory(JiraModel):
    """Status category (e.g. 'To Do', 'In Progress', 'Done').

    OpenAPI: StatusCategory
    """

    key: str | None = None
    name: str | None = None


class StatusDetails(JiraModel):
    """Issue status.

    OpenAPI: StatusDetails
    """

    name: str | None = None
    status_category: StatusCategory | None = None


class IssueTypeDetails(JiraModel):
    """Issue type (e.g. 'Bug', 'Task', 'Story').

    OpenAPI: IssueTypeDetails
    """

    name: str | None = None
    subtask: bool | None = None
    hierarchy_level: int | None = None


class Priority(JiraModel):
    """Issue priority (e.g. 'High', 'Medium', 'Low').

    OpenAPI: Priority
    """

    name: str | None = None


class IssueTypeWithStatus(JiraModel):
    """Issue type with the statuses available to it in a project.

    OpenAPI: IssueTypeWithStatus — GET /rest/api/3/project/{key}/statuses item
    """

    name: str | None = None
    statuses: list[StatusDetails] = []
