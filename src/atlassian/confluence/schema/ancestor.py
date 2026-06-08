"""Ancestor schema (Confluence v2 API)."""

from atlassian.confluence.schema.base import ConfluenceModel


class Ancestor(ConfluenceModel):
    """A page ancestor (parent chain).

    OpenAPI (v2): Ancestor — GET /wiki/api/v2/pages/{id}/ancestors response item
    """

    id: str | None = None


class MultiEntityResultAncestor(ConfluenceModel):
    """Paginated ancestor list.

    OpenAPI (v2): MultiEntityResult<Ancestor>
    """

    results: list[Ancestor] = []
