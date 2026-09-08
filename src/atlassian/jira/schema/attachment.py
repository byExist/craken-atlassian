"""Attachment schema."""

from atlassian.jira.schema.base import JiraModel


class Attachment(JiraModel):
    """An issue attachment.

    OpenAPI: Attachment — POST /rest/api/3/issue/{id}/attachments response item
    """

    id: str | None = None
    filename: str | None = None


class AttachmentMetadata(JiraModel):
    """Metadata of a single attachment. Unlike ``Attachment``, the spec types ``id`` as an integer here.

    OpenAPI: AttachmentMetadata — GET /rest/api/3/attachment/{id} response
    """

    id: int | None = None
    filename: str | None = None
