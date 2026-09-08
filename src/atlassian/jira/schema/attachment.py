"""Attachment schema."""

from atlassian.jira.schema.base import JiraModel


class Attachment(JiraModel):
    """An issue attachment.

    OpenAPI: Attachment — POST /rest/api/3/issue/{id}/attachments response item, IssueBean.fields.attachment item
    """

    id: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    size: int | None = None


class AttachmentMetadata(JiraModel):
    """Metadata of a single attachment. Unlike ``Attachment``, the spec types ``id`` as an integer here.

    OpenAPI: AttachmentMetadata — GET /rest/api/3/attachment/{id} response
    """

    id: int | None = None
    filename: str | None = None
