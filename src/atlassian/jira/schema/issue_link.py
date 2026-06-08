"""Issue link schema."""

from pydantic import Field

from atlassian.jira.schema.base import JiraModel
from atlassian.jira.schema.common import IssueTypeDetails, Priority, StatusDetails
from atlassian.jira.schema.link_type import IssueLinkType
from atlassian.jira.schema.user import User


class LinkedIssueFields(JiraModel):
    """Key fields of a linked issue (summary view).

    OpenAPI: Fields — LinkedIssue.fields
    """

    summary: str | None = None
    status: StatusDetails | None = None
    priority: Priority | None = None
    issue_type: IssueTypeDetails | None = Field(
        default=None, validation_alias="issuetype"
    )
    assignee: User | None = None


class LinkedIssue(JiraModel):
    """The issue on one end of a link.

    OpenAPI: LinkedIssue
    """

    key: str | None = None
    fields: LinkedIssueFields | None = None


class IssueLink(JiraModel):
    """A link between two issues (e.g. 'blocks', 'relates to').

    OpenAPI: IssueLink
    """

    id: str | None = None
    type: IssueLinkType | None = None
    inward_issue: LinkedIssue | None = None
    outward_issue: LinkedIssue | None = None
