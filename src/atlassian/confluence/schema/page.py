"""Page schema (Confluence v2 API)."""

from atlassian.confluence.schema.adf import Body
from atlassian.confluence.schema.base import ConfluenceModel, CursorPage


class Version(ConfluenceModel):
    """Content version.

    OpenAPI (v2): Version
    """

    number: int | None = None
    message: str | None = None
    created_at: str | None = None


class Page(ConfluenceModel):
    """A Confluence page.

    OpenAPI (v2): PageBulk / PageSingle
    """

    id: str | None = None
    status: str | None = None
    title: str | None = None
    space_id: str | None = None
    parent_id: str | None = None
    version: Version | None = None
    body: Body = None


class ChildPage(ConfluenceModel):
    """A child page reference.

    OpenAPI (v2): ChildPage -- GET /wiki/api/v2/pages/{id}/children response item
    """

    id: str | None = None
    status: str | None = None
    title: str | None = None
    space_id: str | None = None
    child_position: int | None = None


class MultiEntityResultPage(CursorPage):
    """Cursor-paginated page list.

    OpenAPI (v2): MultiEntityResult<Page>
    """

    results: list[Page] = []


class MultiEntityResultChildPage(CursorPage):
    """Cursor-paginated child page list.

    OpenAPI (v2): MultiEntityResult<ChildPage>
    """

    results: list[ChildPage] = []
