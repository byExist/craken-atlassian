"""Issue link type schema."""

from atlassian.jira.schema.base import JiraModel


class IssueLinkType(JiraModel):
    """An issue link type (e.g. 'Blocks', 'Duplicates').

    OpenAPI: IssueLinkType
    """

    name: str | None = None
    inward: str | None = None
    outward: str | None = None


class IssueLinkTypes(JiraModel):
    """Available issue link types.

    OpenAPI: IssueLinkTypes — GET /rest/api/3/issueLinkType response
    """

    issue_link_types: list[IssueLinkType] = []
