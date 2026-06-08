"""User schema (Confluence v1 API)."""

from atlassian.confluence.schema.base import ConfluenceModel


class User(ConfluenceModel):
    """Confluence user.

    OpenAPI (v1): User -- GET /wiki/rest/api/user/current response
    """

    account_id: str | None = None
    display_name: str | None = None
