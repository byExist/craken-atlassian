"""Remote issue link schema."""

from atlassian.jira.schema.base import JiraModel


class RemoteObject(JiraModel):
    """The remote object linked to an issue.

    OpenAPI: RemoteObject
    """

    url: str | None = None
    title: str | None = None
    summary: str | None = None


class RemoteIssueLink(JiraModel):
    """A remote issue link.

    OpenAPI: RemoteIssueLink
    """

    id: int | None = None
    relationship: str | None = None
    object: RemoteObject | None = None


class RemoteIssueLinkIdentifies(JiraModel):
    """Response from creating a remote issue link.

    OpenAPI: RemoteIssueLinkIdentifies
    """

    id: int | None = None
