"""Comment schema (Confluence v2 API)."""

from atlassian.confluence.schema.adf import Body
from atlassian.confluence.schema.base import ConfluenceModel, CursorPage


class Comment(ConfluenceModel):
    """A footer comment on a page.

    OpenAPI (v2): FooterCommentModel
    """

    id: str | None = None
    parent_comment_id: str | None = None
    body: Body = None


class MultiEntityResultComment(CursorPage):
    """Cursor-paginated comment list.

    OpenAPI (v2): MultiEntityResult<FooterCommentModel>
    """

    results: list[Comment] = []
