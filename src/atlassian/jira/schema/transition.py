"""Transition schema."""

from atlassian.jira.schema.base import JiraModel
from atlassian.jira.schema.common import StatusDetails


class IssueTransition(JiraModel):
    """An issue status transition.

    OpenAPI: IssueTransition
    """

    id: str | None = None
    name: str | None = None
    to: StatusDetails | None = None


class Transitions(JiraModel):
    """Available transitions for an issue.

    OpenAPI: Transitions — GET /rest/api/3/issue/{id}/transitions response
    """

    transitions: list[IssueTransition] = []
