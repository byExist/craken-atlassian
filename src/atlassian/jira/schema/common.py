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

    id: str | None = None
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

    id: str | None = None
    name: str | None = None


class Resolution(JiraModel):
    """Issue resolution (e.g. 'Done', "Won't Do").

    OpenAPI: Resolution
    """

    id: str | None = None
    name: str | None = None


class IssueTypeWithStatus(JiraModel):
    """Issue type with the statuses available to it in a project.

    OpenAPI: IssueTypeWithStatus — GET /rest/api/3/project/{key}/statuses item
    (required: id, name, self, statuses, subtask — only name/statuses are modelled)
    """

    name: str
    statuses: list[StatusDetails]
