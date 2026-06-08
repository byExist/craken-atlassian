"""Issue type create metadata schema."""

from atlassian.jira.schema.base import JiraModel


class IssueTypeCreateMeta(JiraModel):
    """Issue type metadata for issue creation.

    OpenAPI: IssueTypeIssueCreateMetadata
    """

    name: str | None = None
    subtask: bool | None = None


class PageOfCreateMetaIssueTypes(JiraModel):
    """Paginated issue type create metadata.

    OpenAPI: PageOfCreateMetaIssueTypes
    """

    issue_types: list[IssueTypeCreateMeta] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
