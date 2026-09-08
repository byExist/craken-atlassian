"""Issue schema."""

from pydantic import ConfigDict, Field

from atlassian.jira.schema.base import JiraModel
from atlassian.jira.schema.adf import ADF
from atlassian.jira.schema.attachment import Attachment
from atlassian.jira.schema.common import IssueTypeDetails, Priority, StatusDetails
from atlassian.jira.schema.issue_link import IssueLink
from atlassian.jira.schema.user import User


class JiraIssueFields(JiraModel):
    """Core fields of an issue.

    OpenAPI: IssueBean.fields (additionalProperties object — typed for common fields only)
    """

    model_config = ConfigDict(extra="allow")

    summary: str | None = None
    description: ADF | str | None = None
    status: StatusDetails | None = None
    assignee: User | None = None
    reporter: User | None = None
    issue_type: IssueTypeDetails | None = Field(
        default=None, validation_alias="issuetype"
    )
    priority: Priority | None = None
    labels: list[str] = []
    created: str | None = None
    updated: str | None = None
    resolution_date: str | None = Field(default=None, validation_alias="resolutiondate")
    issue_links: list[IssueLink] = Field(
        default_factory=list[IssueLink], validation_alias="issuelinks"
    )
    # None (not []) so list responses that don't request it omit the key
    # instead of reading as "no attachments".
    attachment: list[Attachment] | None = None


class IssueBean(JiraModel):
    """A JIRA issue.

    OpenAPI: IssueBean
    """

    key: str | None = None
    fields: JiraIssueFields | None = None


class CreatedIssue(JiraModel):
    """Response from creating an issue.

    OpenAPI: CreatedIssue
    """

    id: str | None = None
    key: str | None = None


class SearchResults(JiraModel):
    """Offset-based paginated issue search results.

    OpenAPI (jira-software): SearchResults — GET /rest/agile/1.0/sprint/{id}/issue response
    """

    issues: list[IssueBean] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None


class SearchAndReconcileResults(JiraModel):
    """Cursor-based paginated issue search results.

    OpenAPI: SearchAndReconcileResults — POST /rest/api/3/search/jql response
    """

    issues: list[IssueBean] = []
    next_page_token: str | None = None
    is_last: bool | None = None
