"""Label schema (Confluence v2 API)."""

from atlassian.confluence.schema.base import ConfluenceModel


class Label(ConfluenceModel):
    """A content label.

    OpenAPI (v2): Label
    """

    name: str | None = None


class MultiEntityResultLabel(ConfluenceModel):
    """Cursor-paginated label list.

    OpenAPI (v2): MultiEntityResult<Label>
    """

    results: list[Label] = []
    cursor: str | None = None
