"""Permission schema."""

from atlassian.jira.schema.base import JiraModel


class UserPermission(JiraModel):
    """A permission and whether the user has it in the queried context.

    OpenAPI: UserPermission
    """

    id: str | None = None
    key: str | None = None
    name: str | None = None
    type: str | None = None
    description: str | None = None
    have_permission: bool | None = None
    deprecated_key: bool | None = None


class Permissions(JiraModel):
    """Result of Get my permissions.

    OpenAPI: Permissions
    """

    permissions: dict[str, UserPermission] = {}
