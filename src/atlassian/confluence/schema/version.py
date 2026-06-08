"""Page version schema (Confluence v2 API)."""

from atlassian.confluence.schema.base import ConfluenceModel


class PageVersion(ConfluenceModel):
    """A version in a page's history.

    OpenAPI (v2): Version — GET /wiki/api/v2/pages/{id}/versions response item
    """

    number: int | None = None
    message: str | None = None
    created_at: str | None = None
    minor_edit: bool | None = None


class MultiEntityResultPageVersion(ConfluenceModel):
    """Cursor-paginated page version list.

    OpenAPI (v2): MultiEntityResult<Version>
    """

    results: list[PageVersion] = []
    cursor: str | None = None
