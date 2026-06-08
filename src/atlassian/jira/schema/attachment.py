"""Attachment schema."""

from atlassian.jira.schema.base import JiraModel


class Attachment(JiraModel):
    """An issue attachment.

    OpenAPI: Attachment — POST /rest/api/3/issue/{id}/attachments response item
    """

    id: str | None = None
    filename: str | None = None
