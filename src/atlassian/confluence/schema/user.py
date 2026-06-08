"""User schema (Confluence v1 API)."""

from atlassian.confluence.schema.base import ConfluenceModel


class PersonalSpace(ConfluenceModel):
    """The authenticated user's personal space (v1 ``expand=personalSpace``).

    Only the key is surfaced: v1 space ids are integers while the v2 space tools
    take string ids, so the key is the identifier that carries over — the space
    tools accept a key directly.
    """

    key: str | None = None
    name: str | None = None


class User(ConfluenceModel):
    """Confluence user.

    OpenAPI (v1): User -- GET /wiki/rest/api/user/current response
    """

    account_id: str | None = None
    display_name: str | None = None
    personal_space: PersonalSpace | None = None
