"""Local-file helpers for the download-edit-publish flow.

`get_*` tools can write a body to a local file (``to_file``) so it never passes
through the model's context; `create_*` / `update_*` tools can read a body back
from a file (``from_file``) after it's edited on disk. This keeps long documents
out of context and turns edits into deterministic file operations instead of
full-document regeneration.
"""

import tempfile
import unicodedata
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


def write_temp(data: bytes, name: str) -> str:
    """Write binary ``data`` as ``name`` inside a fresh temp directory; return its path.

    A new directory per call keeps the original filename without collisions.
    The file persists until the OS cleans its temp dir; copy it to keep it.
    """
    # Only the final component is used, so a server-supplied name can't escape the temp dir.
    # NFC: names uploaded from macOS arrive decomposed (NFD), which other tools
    # and typed-in paths don't match.
    safe = unicodedata.normalize("NFC", Path(name).name)
    if safe in ("", ".", ".."):
        safe = "attachment"
    path = Path(tempfile.mkdtemp()) / safe
    path.write_bytes(data)
    return str(path)


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
