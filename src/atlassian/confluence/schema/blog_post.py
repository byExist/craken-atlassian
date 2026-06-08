"""Blog post schema (Confluence v2 API)."""

from atlassian.confluence.schema.adf import ADF
from atlassian.confluence.schema.base import ConfluenceModel
from atlassian.confluence.schema.page import Version


class BlogPost(ConfluenceModel):
    """A Confluence blog post.

    OpenAPI (v2): BlogPostBulk / BlogPostSingle
    """

    id: str | None = None
    status: str | None = None
    title: str | None = None
    space_id: str | None = None
    version: Version | None = None
    body: ADF | str | None = None


class MultiEntityResultBlogPost(ConfluenceModel):
    """Cursor-paginated blog post list.

    OpenAPI (v2): MultiEntityResult<BlogPost>
    """

    results: list[BlogPost] = []
    cursor: str | None = None
