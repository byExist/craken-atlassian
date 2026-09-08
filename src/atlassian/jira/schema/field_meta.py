"""Per-field create/edit metadata schema."""

from pydantic import Field

from atlassian.jira.schema.base import JiraModel
from atlassian.jira.schema.field import JsonTypeBean


class FieldCreateMetadata(JiraModel):
    """A field available when creating an issue of one type in a project.

    OpenAPI: FieldCreateMetadata
    """

    field_id: str
    key: str
    name: str
    required: bool
    has_default_value: bool | None = None
    field_schema: JsonTypeBean = Field(
        validation_alias="schema", serialization_alias="schema"
    )


class PageOfCreateMetaIssueTypeWithField(JiraModel):
    """Paginated create field metadata.

    OpenAPI: PageOfCreateMetaIssueTypeWithField — GET /rest/api/3/issue/createmeta/{projectIdOrKey}/issuetypes/{issueTypeId} response
    """

    fields: list[FieldCreateMetadata] = []
    start_at: int | None = None
    max_results: int | None = None
    total: int | None = None


class FieldMetadata(JiraModel):
    """A field editable on an existing issue.

    OpenAPI: FieldMetadata
    """

    key: str
    name: str
    required: bool
    has_default_value: bool | None = None
    field_schema: JsonTypeBean = Field(
        validation_alias="schema", serialization_alias="schema"
    )


class IssueUpdateMetadata(JiraModel):
    """Edit metadata of an issue, keyed by field id.

    OpenAPI: IssueUpdateMetadata — GET /rest/api/3/issue/{issueIdOrKey}/editmeta response
    """

    fields: dict[str, FieldMetadata] = {}
