"""Inline comment schema (Confluence v2 API)."""

from atlassian.confluence.schema.adf import ADF
from atlassian.confluence.schema.base import ConfluenceModel


class InlineCommentProperties(ConfluenceModel):
    """Properties of an inline comment (text selection reference).

    OpenAPI (v2): InlineCommentProperties
    """

    inline_marker_ref: str | None = None
    inline_original_selection: str | None = None


class InlineComment(ConfluenceModel):
    """An inline comment on a page.

    OpenAPI (v2): PageInlineCommentModel
    """

    id: str | None = None
    status: str | None = None
    title: str | None = None
    parent_comment_id: str | None = None
    resolution_status: str | None = None
    body: ADF | str | None = None
    properties: InlineCommentProperties | None = None


class MultiEntityResultInlineComment(ConfluenceModel):
    """Cursor-paginated inline comment list.

    OpenAPI (v2): MultiEntityResult<PageInlineCommentModel>
    """

    results: list[InlineComment] = []
    cursor: str | None = None
