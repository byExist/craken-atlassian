"""Board schema (Agile API)."""

from atlassian.jira.schema.base import JiraModel


class BoardLocationBean(JiraModel):
    """The container that a board is located in.

    OpenAPI (jira-software): BoardLocationBean
    """

    project_key: str | None = None


class Board(JiraModel):
    """An agile board.

    OpenAPI (jira-software): Board
    """

    id: int | None = None
    name: str | None = None
    type: str | None = None
    location: BoardLocationBean | None = None


class PageBeanBoard(JiraModel):
    """Paginated board list.

    OpenAPI (jira-software): PageBeanBoard — GET /rest/agile/1.0/board response
    """

    values: list[Board] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
    is_last: bool | None = None
