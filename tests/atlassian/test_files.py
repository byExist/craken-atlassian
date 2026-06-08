"""Tests for atlassian.files — local-file helpers for download/edit/publish."""

import os
from pathlib import Path

from pytest_mock import MockerFixture

from atlassian.files import read_body, read_bytes, write_body, write_temp


def test_write_body_writes_utf8_and_returns_resolved_path(tmp_path: Path):
    target = tmp_path / "note.md"

    returned = write_body(str(target), "héllo · 본문")

    assert returned == str(target)
    assert target.read_text(encoding="utf-8") == "héllo · 본문"


def test_write_body_creates_missing_parent_dirs(tmp_path: Path):
    target = tmp_path / "a" / "b" / "c" / "deep.md"

    write_body(str(target), "content")

    assert target.read_text(encoding="utf-8") == "content"


def test_write_body_expands_user(tmp_path: Path, mocker: MockerFixture):
    mocker.patch.dict(os.environ, {"HOME": str(tmp_path)})
    mocker.patch.object(Path, "home", lambda: tmp_path)

    returned = write_body("~/inside-home.md", "x")

    assert returned == str(tmp_path / "inside-home.md")
    assert (tmp_path / "inside-home.md").read_text() == "x"


def test_read_body_roundtrips_with_write_body(tmp_path: Path):
    target = tmp_path / "round.md"
    write_body(str(target), "round-trip ·")

    assert read_body(str(target)) == "round-trip ·"


def test_write_temp_derives_extension_from_content_type():
    path = write_temp(b"\x89PNG\r\n", "image/png")

    try:
        assert path.endswith(".png")
        assert Path(path).read_bytes() == b"\x89PNG\r\n"
    finally:
        Path(path).unlink(missing_ok=True)


def test_write_temp_strips_charset_parameter():
    path = write_temp(b"hi", "text/plain; charset=utf-8")

    try:
        assert path.endswith(".txt")
    finally:
        Path(path).unlink(missing_ok=True)


def test_write_temp_handles_unknown_content_type():
    path = write_temp(b"data", "")

    try:
        assert Path(path).suffix == ""
        assert Path(path).read_bytes() == b"data"
    finally:
        Path(path).unlink(missing_ok=True)


def test_read_bytes_returns_data_and_filename(tmp_path: Path):
    target = tmp_path / "upload.bin"
    target.write_bytes(b"\x00\x01\x02")

    data, filename = read_bytes(str(target))

    assert data == b"\x00\x01\x02"
    assert filename == "upload.bin"
