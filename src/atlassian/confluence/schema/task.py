"""Task schema (Confluence v2 API)."""

from atlassian.confluence.schema.adf import ADF
from atlassian.confluence.schema.base import ConfluenceModel


class Task(ConfluenceModel):
    """An inline task (action item) on a page or blog post.

    OpenAPI (v2): Task
    """

    id: str | None = None
    status: str | None = None
    body: ADF | str | None = None


class MultiEntityResultTask(ConfluenceModel):
    """Cursor-paginated task list.

    OpenAPI (v2): MultiEntityResult<Task>
    """

    results: list[Task] = []
    cursor: str | None = None
