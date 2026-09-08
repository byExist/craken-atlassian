"""Task schema (Confluence v2 API)."""

from atlassian.confluence.schema.adf import Body
from atlassian.confluence.schema.base import ConfluenceModel, CursorPage


class Task(ConfluenceModel):
    """An inline task (action item) on a page or blog post.

    OpenAPI (v2): Task
    """

    id: str | None = None
    status: str | None = None
    body: Body = None


class MultiEntityResultTask(CursorPage):
    """Cursor-paginated task list.

    OpenAPI (v2): MultiEntityResult<Task>
    """

    results: list[Task] = []
