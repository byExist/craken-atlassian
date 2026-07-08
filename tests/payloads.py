"""Minimal-valid payload builders for models with required fields.

Each returns the smallest camelCase dict ``model_validate`` accepts, so a future
requiredness change edits one place instead of every fixture. All-optional models
validate from ``{}`` and need no entry.
"""

from typing import Any


def remote_object(**overrides: Any) -> dict[str, Any]:
    return {"url": "https://example.test", "title": "Example", **overrides}


def issue_type_with_status(**overrides: Any) -> dict[str, Any]:
    return {"name": "Bug", "statuses": [], **overrides}


def issue_link(**overrides: Any) -> dict[str, Any]:
    return {"type": {}, **overrides}
