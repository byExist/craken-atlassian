"""Attachment download result — what the HTTP layer hands to the file layer."""

import mimetypes
from dataclasses import dataclass
from typing import Self

import httpx


@dataclass(frozen=True)
class Download:
    data: bytes
    content_type: str

    @classmethod
    def from_response(cls, resp: httpx.Response) -> Self:
        return cls(
            resp.content,
            resp.headers.get("content-type", "application/octet-stream"),
        )

    @property
    def fallback_name(self) -> str:
        """``attachment`` plus an extension guessed from the content type, for when metadata carries no filename."""
        ext = mimetypes.guess_extension(self.content_type.split(";")[0].strip()) or ""
        return f"attachment{ext}"
