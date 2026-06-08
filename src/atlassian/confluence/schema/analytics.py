"""Analytics schema (Confluence v1 API)."""

from atlassian.confluence.schema.base import ConfluenceModel


class ContentViews(ConfluenceModel):
    """View count for a piece of content.

    OpenAPI (v1): GET /wiki/rest/api/analytics/content/{id}/views response
    """

    count: int | None = None
