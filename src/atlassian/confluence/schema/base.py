"""Base models for Confluence schemas."""

from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)


def _to_camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class ConfluenceModel(BaseModel):
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


class CursorPage(ConfluenceModel):
    """Cursor-paginated v2 list.

    The v2 API carries the next-page cursor only as a query parameter of
    ``_links.next``; it is lifted into ``cursor`` at parse time.
    """

    cursor: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _cursor_from_links(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw = cast(dict[str, Any], data)
        if "cursor" in raw:
            return raw
        links: dict[str, Any] = raw.get("_links") or {}
        next_url: str = links.get("next") or ""
        cursors = parse_qs(urlparse(next_url).query).get("cursor")
        return {**raw, "cursor": cursors[0]} if cursors else raw
