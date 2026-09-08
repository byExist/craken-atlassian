"""Transition schema."""

from atlassian.jira.schema.base import JiraModel
from atlassian.jira.schema.common import StatusDetails
from atlassian.jira.schema.field_meta import FieldMetadata


class IssueTransition(JiraModel):
    """An issue status transition.

    OpenAPI: IssueTransition
    """

    id: str | None = None
    name: str | None = None
    to: StatusDetails | None = None
    has_screen: bool | None = None
    # Present with expand=transitions.fields: the transition screen's fields.
    fields: dict[str, FieldMetadata] | None = None


class Transitions(JiraModel):
    """Available transitions for an issue.

    OpenAPI: Transitions — GET /rest/api/3/issue/{id}/transitions response
    """

    transitions: list[IssueTransition] = []
