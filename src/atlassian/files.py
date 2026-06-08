"""Local-file helpers for the download-edit-publish flow.

`get_*` tools can write a body to a local file (``to_file``) so it never passes
through the model's context; `create_*` / `update_*` tools can read a body back
from a file (``from_file``) after it's edited on disk. This keeps long documents
out of context and turns edits into deterministic file operations instead of
full-document regeneration.
"""

import mimetypes
import os
import tempfile
from pathlib import Path


def write_body(path: str, body: str) -> str:
    """Write ``body`` to ``path`` (creating parent dirs); return the resolved path.

    Use an absolute path — the MCP server's working directory is the plugin
    root, not your project, so a relative path lands somewhere unexpected.
    """
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return str(p)


def write_temp(data: bytes, content_type: str) -> str:
    """Write binary ``data`` to a uniquely-named temp file; return its path.

    The extension is derived from ``content_type`` (e.g. ``image/png`` → ``.png``)
    so the model's image support and other readers can recognize the file. The
    file persists until the OS cleans its temp dir; copy it if you need to keep it.
    """
    ext = mimetypes.guess_extension((content_type or "").split(";")[0].strip()) or ""
    fd, path = tempfile.mkstemp(suffix=ext)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def read_body(path: str) -> str:
    """Read body text from ``path`` (UTF-8)."""
    return Path(path).expanduser().read_text(encoding="utf-8")


def read_bytes(path: str) -> tuple[bytes, str]:
    """Read a binary file; return ``(data, filename)`` for upload.

    Use an absolute path — the MCP server's working directory is the plugin
    root, not your project, so a relative path lands somewhere unexpected.
    """
    p = Path(path).expanduser()
    return p.read_bytes(), p.name
