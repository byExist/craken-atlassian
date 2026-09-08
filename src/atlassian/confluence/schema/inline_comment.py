"""Inline comment schema (Confluence v2 API)."""

from atlassian.confluence.schema.adf import Body
from atlassian.confluence.schema.base import ConfluenceModel, CursorPage
from atlassian.confluence.schema.page import Version


class InlineCommentProperties(ConfluenceModel):
    """Properties of an inline comment (text selection reference).

    OpenAPI (v2): InlineCommentProperties
    """

    inline_marker_ref: str | None = None
    inline_original_selection: str | None = None


class InlineComment(ConfluenceModel):
    """An inline comment on a page, or a reply to one.

    OpenAPI (v2): PageInlineCommentModel / InlineCommentChildrenModel
    (``parentCommentId`` is set only on replies)
    """

    id: str | None = None
    status: str | None = None
    title: str | None = None
    parent_comment_id: str | None = None
    resolution_status: str | None = None
    version: Version | None = None
    body: Body = None
    properties: InlineCommentProperties | None = None


class MultiEntityResultInlineComment(CursorPage):
    """Cursor-paginated inline comment list.

    OpenAPI (v2): MultiEntityResult<PageInlineCommentModel>
    """

    results: list[InlineComment] = []
