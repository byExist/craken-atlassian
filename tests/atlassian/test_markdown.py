"""Tests for atlassian.markdown — the Markdown ⇄ ADF seam used by every tool."""

from unittest.mock import call

import pytest
from pytest_mock import MockerFixture

from atlassian import markdown


def test_render_converts_adf_with_plain_flag(mocker: MockerFixture):
    to_md = mocker.patch.object(markdown, "to_md", return_value="# Hi")

    assert markdown.render({"type": "doc"}, plain=False) == "# Hi"
    assert to_md.call_args == call({"type": "doc"}, plain=False)


@pytest.mark.parametrize("body", ["already text", None])
def test_render_passes_text_and_none_through(mocker: MockerFixture, body: str | None):
    to_md = mocker.patch.object(markdown, "to_md")

    assert markdown.render(body, plain=True) == body
    to_md.assert_not_called()


def test_parse_converts_markdown(mocker: MockerFixture):
    to_adf = mocker.patch.object(markdown, "to_adf", return_value={"adf": 1})

    assert markdown.parse("# Hi") == {"adf": 1}
    assert to_adf.call_args == call("# Hi")


def test_parse_leaves_missing_body_missing(mocker: MockerFixture):
    to_adf = mocker.patch.object(markdown, "to_adf")

    assert markdown.parse(None) is None
    to_adf.assert_not_called()
