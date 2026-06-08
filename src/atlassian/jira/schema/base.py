"""Base model for JIRA schemas."""

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    SerializerFunctionWrapHandler,
    model_serializer,
)


def _to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class JiraModel(BaseModel):
    """camelCase JSON ↔ snake_case Python auto-conversion base model."""

    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )

    @model_serializer(mode="wrap")
    def _drop_none(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """Omit None-valued keys to keep MCP responses compact.

        FastMCP serializes tool results with model_dump(by_alias=True) and no
        exclude_none, so null fields would otherwise bloat every response.
        Empty collections are kept ([] still signals "fetched, none present").
        """
        return {k: v for k, v in handler(self).items() if v is not None}
