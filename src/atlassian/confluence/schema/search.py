"""Search schema (Confluence v1 API)."""

from atlassian.confluence.schema.base import ConfluenceModel


class SearchResultContent(ConfluenceModel):
    """Minimal content reference in search results."""

    id: str | None = None
    type: str | None = None
    title: str | None = None


class SearchResultSpace(ConfluenceModel):
    """Minimal space reference in search results."""

    key: str | None = None
    name: str | None = None


class SearchResultItem(ConfluenceModel):
    """A single search result.

    OpenAPI (v1): SearchResult
    """

    content: SearchResultContent | None = None
    space: SearchResultSpace | None = None
    title: str | None = None
    excerpt: str | None = None


class SearchResults(ConfluenceModel):
    """Paginated search results via CQL.

    OpenAPI (v1): SearchPageResponseSearchResult -- GET /wiki/rest/api/search response
    """

    results: list[SearchResultItem] = []
    start: int | None = None
    limit: int | None = None
    total_size: int | None = None
