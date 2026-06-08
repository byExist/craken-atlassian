"""User schema."""

from atlassian.jira.schema.base import JiraModel


class User(JiraModel):
    """JIRA user.

    OpenAPI: User / UserDetails
    """

    account_id: str | None = None
    display_name: str | None = None
