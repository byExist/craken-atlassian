"""Atlassian Document Format (ADF) type for Confluence."""

import json
from typing import Annotated, Any, cast

from pydantic import BeforeValidator

ADF = dict[str, Any]
"""Atlassian Document Format -- a JSON document tree."""


def _unwrap_v2_body(value: Any) -> Any:
    # v2 responses nest the document as body.atlas_doc_format.value (a JSON
    # string); a bare ADF dict or an already-rendered Markdown str passes through.
    if not value:
        return None
    if not isinstance(value, dict):
        return value
    wrapper = cast(dict[str, Any], value)
    if "atlas_doc_format" not in wrapper:
        return wrapper
    adf_format: dict[str, Any] = wrapper.get("atlas_doc_format") or {}
    inner: Any = adf_format.get("value")
    if not inner:
        return None
    return json.loads(inner) if isinstance(inner, str) else inner


Body = Annotated[ADF | str | None, BeforeValidator(_unwrap_v2_body)]
"""Content body: ADF from the API, Markdown once the tool layer renders it."""
