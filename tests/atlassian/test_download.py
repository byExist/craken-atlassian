"""Tests for atlassian.download — turning an HTTP response into a named download."""

import httpx
import pytest

from atlassian.download import Download


def _response(**headers: str) -> httpx.Response:
    return httpx.Response(200, content=b"\x89PNG", headers=headers)


@pytest.mark.parametrize(
    ("disposition", "expected"),
    [
        (
            'attachment; filename="image-20250710-092813.png"',
            "image-20250710-092813.png",
        ),
        ("attachment; filename=plain.txt", "plain.txt"),
        ("attachment; filename*=UTF-8''%EC%82%AC%EC%A7%84.png", "사진.png"),
        ("attachment", None),
        ("", None),
    ],
)
def test_from_response_reads_filename_from_disposition(
    disposition: str, expected: str | None
):
    download = Download.from_response(
        _response(**{"content-type": "image/png", "content-disposition": disposition})
    )

    assert download.data == b"\x89PNG"
    assert download.content_type == "image/png"
    assert download.filename == expected


def test_from_response_defaults_when_headers_are_absent():
    download = Download.from_response(httpx.Response(200, content=b"raw"))

    assert download.content_type == "application/octet-stream"
    assert download.filename is None


def test_name_prefers_server_filename():
    assert Download(b"", "image/png", "shot.png").name == "shot.png"


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("image/png", "attachment.png"),
        ("text/plain; charset=utf-8", "attachment.txt"),
        ("", "attachment"),
    ],
)
def test_name_falls_back_to_content_type_extension(content_type: str, expected: str):
    assert Download(b"", content_type, None).name == expected
