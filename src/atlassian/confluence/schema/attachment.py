"""Attachment schema (Confluence v2 API)."""

from atlassian.confluence.schema.base import ConfluenceModel, CursorPage


class Attachment(ConfluenceModel):
    """An attachment on a page.

    OpenAPI (v2): AttachmentBulk / AttachmentSingle — GET /attachments/{id} response
    """

    id: str | None = None
    status: str | None = None
    title: str | None = None
    created_at: str | None = None
    media_type: str | None = None
    file_size: int | None = None
    comment: str | None = None
    # Exactly one of these is set: the content the attachment belongs to.
    page_id: str | None = None
    blog_post_id: str | None = None
    custom_content_id: str | None = None


class MultiEntityResultAttachment(CursorPage):
    """Cursor-paginated attachment list.

    OpenAPI (v2): MultiEntityResult<AttachmentBulk>
    """

    results: list[Attachment] = []
