"""Field schema."""

from pydantic import Field

from atlassian.jira.schema.base import JiraModel


class JsonTypeBean(JiraModel):
    """The data type of a field. ``type: string`` with ``system`` description/environment or ``custom`` ending in ``:textarea`` means rich text (ADF).

    OpenAPI: JsonTypeBean
    """

    type: str
    items: str | None = None
    system: str | None = None
    custom: str | None = None
    custom_id: int | None = None


class FieldDetail(JiraModel):
    """A JIRA field (system or custom).

    OpenAPI: FieldDetails
    """

    id: str | None = None
    key: str | None = None
    name: str | None = None
    orderable: bool | None = None
    searchable: bool | None = None
    clause_names: list[str] = []
    # "schema" would shadow BaseModel.schema; keep the wire name via aliases.
    field_schema: JsonTypeBean | None = Field(
        default=None, validation_alias="schema", serialization_alias="schema"
    )


class PageBeanField(JiraModel):
    """Paginated field list.

    OpenAPI: PageBeanField
    """

    values: list[FieldDetail] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None
    is_last: bool | None = None
