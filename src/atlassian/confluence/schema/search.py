"""Search schema (Confluence v1 API)."""

from atlassian.confluence.schema.base import ConfluenceModel
from atlassian.confluence.schema.user import User


class SearchResultContent(ConfluenceModel):
    """Minimal content reference in search results.

    OpenAPI (v1): Content
    """

    id: str | None = None
    type: str
    title: str | None = None


class SearchResultSpace(ConfluenceModel):
    """Minimal space reference in search results.

    OpenAPI (v1): Space
    """

    key: str
    name: str


class SearchResultItem(ConfluenceModel):
    """A single search result.

    OpenAPI (v1): SearchResult
    """

    content: SearchResultContent | None = None
    space: SearchResultSpace | None = None
    user: User | None = None
    title: str
    excerpt: str


class SearchResults(ConfluenceModel):
    """Paginated search results via CQL.

    OpenAPI (v1): SearchPageResponseSearchResult -- GET /wiki/rest/api/search response
    """

    results: list[SearchResultItem] = []
    start: int
    limit: int
    total_size: int
