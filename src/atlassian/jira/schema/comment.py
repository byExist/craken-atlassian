"""Comment schema."""

from atlassian.jira.schema.base import JiraModel
from atlassian.jira.schema.adf import ADF
from atlassian.jira.schema.user import User


class Comment(JiraModel):
    """An issue comment.

    OpenAPI: Comment
    """

    id: str | None = None
    author: User | None = None
    body: ADF | str | None = None
    created: str | None = None
    updated: str | None = None


class PageOfComments(JiraModel):
    """Paginated comments.

    OpenAPI: PageOfComments — GET /rest/api/3/issue/{id}/comment response
    """

    comments: list[Comment] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
