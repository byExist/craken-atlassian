"""Remote issue link schema."""

from atlassian.jira.schema.base import JiraModel


class RemoteObject(JiraModel):
    """The remote object linked to an issue.

    OpenAPI: RemoteObject (required: title, url)
    """

    url: str
    title: str
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
