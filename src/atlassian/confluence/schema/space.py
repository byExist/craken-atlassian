"""Space schema (Confluence v2 API)."""

from atlassian.confluence.schema.base import ConfluenceModel


class Space(ConfluenceModel):
    """A Confluence space.

    OpenAPI (v2): SpaceBulk / SpaceSingle
    """

    id: str | None = None
    key: str | None = None
    name: str | None = None
    type: str | None = None
    status: str | None = None


class MultiEntityResultSpace(ConfluenceModel):
    """Cursor-paginated space list.

    OpenAPI (v2): MultiEntityResult<Space> -- GET /wiki/api/v2/spaces response
    """

    results: list[Space] = []
    cursor: str | None = None
