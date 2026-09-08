"""Attachment download result — what the HTTP layer hands to the file layer."""

import mimetypes
from dataclasses import dataclass
from email.message import Message
from typing import Self

import httpx


@dataclass(frozen=True)
class Download:
    data: bytes
    content_type: str
    filename: str | None

    @classmethod
    def from_response(cls, resp: httpx.Response) -> Self:
        return cls(
            resp.content,
            resp.headers.get("content-type", "application/octet-stream"),
            _disposition_filename(resp.headers.get("content-disposition")),
        )

    @property
    def name(self) -> str:
        """Filename to save under: the server's, or ``attachment`` plus an extension guessed from the content type."""
        if self.filename:
            return self.filename
        ext = mimetypes.guess_extension(self.content_type.split(";")[0].strip()) or ""
        return f"attachment{ext}"


def _disposition_filename(value: str | None) -> str | None:
    # email.message parses both filename="..." and RFC 5987 filename*=UTF-8''...
    if not value:
        return None
    msg = Message()
    msg["content-disposition"] = value
    return msg.get_filename()
