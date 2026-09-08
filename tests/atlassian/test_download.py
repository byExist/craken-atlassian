"""Tests for atlassian.download — turning an HTTP response into download bytes."""

import httpx
import pytest

from atlassian.download import Download


def test_from_response_reads_bytes_and_content_type():
    download = Download.from_response(
        httpx.Response(200, content=b"\x89PNG", headers={"content-type": "image/png"})
    )

    assert download.data == b"\x89PNG"
    assert download.content_type == "image/png"


def test_from_response_defaults_content_type_when_absent():
    download = Download.from_response(httpx.Response(200, content=b"raw"))

    assert download.content_type == "application/octet-stream"


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("image/png", "attachment.png"),
        ("text/plain; charset=utf-8", "attachment.txt"),
        ("", "attachment"),
    ],
)
def test_fallback_name_comes_from_content_type(content_type: str, expected: str):
    assert Download(b"", content_type).fallback_name == expected
