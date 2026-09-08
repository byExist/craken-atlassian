"""Attachment schema (Confluence v2 API)."""

from atlassian.confluence.schema.base import ConfluenceModel, CursorPage


class Attachment(ConfluenceModel):
    """An attachment on a page.

    OpenAPI (v2): AttachmentBulk
    """

    id: str | None = None
    status: str | None = None
    title: str | None = None
    created_at: str | None = None
    media_type: str | None = None
    file_size: int | None = None
    comment: str | None = None


class MultiEntityResultAttachment(CursorPage):
    """Cursor-paginated attachment list.

    OpenAPI (v2): MultiEntityResult<AttachmentBulk>
    """

    results: list[Attachment] = []
