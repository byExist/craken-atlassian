"""Watcher schema."""

from atlassian.jira.schema.base import JiraModel
from atlassian.jira.schema.user import User


class Watchers(JiraModel):
    """Watchers of an issue.

    OpenAPI: Watchers
    """

    is_watching: bool | None = None
    watch_count: int | None = None
    watchers: list[User] = []
