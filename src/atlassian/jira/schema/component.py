"""Project component schema."""

from atlassian.jira.schema.base import JiraModel


class Component(JiraModel):
    """A project component.

    OpenAPI: ProjectComponent
    """

    name: str | None = None
