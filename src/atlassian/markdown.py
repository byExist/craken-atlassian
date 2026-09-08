"""Markdown ⇄ ADF at the tool boundary.

Clients speak ADF (what the REST APIs store); tools speak Markdown (what the
model reads and writes). Every crossing goes through here.
"""

from typing import Any, overload

from marklas import to_adf, to_md


def render(body: dict[str, Any] | str | None, *, plain: bool) -> str | None:
    """ADF → Markdown. Text that is already rendered, or a missing body, passes through."""
    return to_md(body, plain=plain) if isinstance(body, dict) else body


@overload
def parse(text: str) -> dict[str, Any]: ...
@overload
def parse(text: None) -> None: ...
def parse(text: str | None) -> dict[str, Any] | None:
    """Markdown → ADF. A missing body stays missing so the field is left untouched."""
    return to_adf(text) if text is not None else None
