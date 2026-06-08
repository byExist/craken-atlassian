"""Tests for atlassian.confluence.tools — the MCP tool layer.

``client`` and the ``to_md``/``to_adf`` seams are patched with ``mocker`` so the
tool's own logic is exercised: body stripping on lists, Markdown<->ADF
conversion, optimistic-lock version handling on updates, attachment file
reads, and "OK" returns.
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from pytest_mock import MockerFixture

from atlassian.confluence import client, tools
from atlassian.confluence.schema.blog_post import BlogPost, MultiEntityResultBlogPost
from atlassian.confluence.schema.comment import Comment, MultiEntityResultComment
from atlassian.confluence.schema.inline_comment import (
    InlineComment,
    MultiEntityResultInlineComment,
)
from atlassian.confluence.schema.page import (
    MultiEntityResultPage,
    Page,
    Version,
)
from atlassian.confluence.schema.task import MultiEntityResultTask, Task


# ---------------------------------------------------------------------------
# Body stripping on list endpoints
# ---------------------------------------------------------------------------


def test_list_pages_strips_bodies(mocker: MockerFixture):
    page = MultiEntityResultPage(results=[Page(id="p1", body={"type": "doc"})])
    list_pages = mocker.patch.object(client, "list_pages", return_value=page)

    out = tools.list_pages("space-1", title="x")

    assert list_pages.call_args == call("space-1", title="x", limit=25)
    assert out.results[0].body is None


def test_list_blog_posts_strips_bodies(mocker: MockerFixture):
    posts = MultiEntityResultBlogPost(results=[BlogPost(id="b1", body={"type": "doc"})])
    mocker.patch.object(client, "list_blog_posts", return_value=posts)

    out = tools.list_blog_posts(space_id="space-1")

    assert out.results[0].body is None


# ---------------------------------------------------------------------------
# ADF -> Markdown on reads
# ---------------------------------------------------------------------------


def test_get_page_converts_body_to_markdown(mocker: MockerFixture):
    mocker.patch.object(
        client, "get_page", return_value=Page(id="p1", body={"type": "doc"})
    )
    to_md = mocker.patch.object(tools, "to_md", return_value="# Body")

    out = tools.get_page("p1")

    assert to_md.call_args == call({"type": "doc"}, plain=True)
    assert out.body == "# Body"


def test_get_page_forwards_plain_false_and_writes_file(
    mocker: MockerFixture, tmp_path: Path
):
    mocker.patch.object(
        client, "get_page", return_value=Page(id="p1", body={"type": "doc"})
    )
    to_md = mocker.patch.object(tools, "to_md", return_value="file body")
    target = tmp_path / "page.md"

    out = tools.get_page("p1", plain=False, to_file=str(target))

    assert to_md.call_args == call({"type": "doc"}, plain=False)
    assert target.read_text() == "file body"
    assert out.body is None


def test_get_blog_post_converts_body(mocker: MockerFixture):
    mocker.patch.object(
        client, "get_blog_post", return_value=BlogPost(id="b1", body={"x": 1})
    )
    mocker.patch.object(tools, "to_md", return_value="md")

    assert tools.get_blog_post("b1").body == "md"


def test_get_comments_converts_bodies(mocker: MockerFixture):
    result = MultiEntityResultComment(results=[Comment(id="c1", body={"type": "doc"})])
    mocker.patch.object(client, "get_comments", return_value=result)
    mocker.patch.object(tools, "to_md", return_value="md")

    assert tools.get_comments("p1").results[0].body == "md"


def test_get_comment_replies_converts_bodies(mocker: MockerFixture):
    result = MultiEntityResultComment(results=[Comment(id="r1", body={"type": "doc"})])
    mocker.patch.object(client, "get_comment_children", return_value=result)
    mocker.patch.object(tools, "to_md", return_value="md")

    assert tools.get_comment_replies("c1").results[0].body == "md"


def test_get_inline_comments_converts_bodies(mocker: MockerFixture):
    result = MultiEntityResultInlineComment(
        results=[InlineComment(id="i1", body={"type": "doc"})]
    )
    mocker.patch.object(client, "get_inline_comments", return_value=result)
    mocker.patch.object(tools, "to_md", return_value="md")

    assert tools.get_inline_comments("p1").results[0].body == "md"


def test_get_tasks_converts_bodies(mocker: MockerFixture):
    result = MultiEntityResultTask(results=[Task(id="t1", body={"type": "doc"})])
    mocker.patch.object(client, "list_tasks", return_value=result)
    mocker.patch.object(tools, "to_md", return_value="md")

    assert tools.get_tasks("p1").results[0].body == "md"


def test_get_likes_wraps_count(mocker: MockerFixture):
    mocker.patch.object(client, "get_likes_count", return_value=12)

    assert tools.get_likes("p1") == {"count": 12}


# ---------------------------------------------------------------------------
# Markdown -> ADF on creates
# ---------------------------------------------------------------------------


def test_create_page_converts_and_returns_id(mocker: MockerFixture):
    create = mocker.patch.object(client, "create_page", return_value=Page(id="p1"))
    mocker.patch.object(tools, "to_adf", return_value={"adf": 1})

    assert tools.create_page("space-1", "T", content="# Hi") == "p1"
    assert create.call_args == call("space-1", "T", body={"adf": 1}, parent_id=None)


def test_create_page_passes_none_without_content(mocker: MockerFixture):
    create = mocker.patch.object(client, "create_page")
    to_adf = mocker.patch.object(tools, "to_adf")

    tools.create_page("space-1", "T")

    to_adf.assert_not_called()
    assert create.call_args == call("space-1", "T", body=None, parent_id=None)


def test_create_page_reads_from_file(mocker: MockerFixture, tmp_path: Path):
    f = tmp_path / "body.md"
    f.write_text("on disk")
    mocker.patch.object(client, "create_page")
    to_adf = mocker.patch.object(tools, "to_adf", return_value={"adf": 1})

    tools.create_page("space-1", "T", from_file=str(f))

    assert to_adf.call_args == call("on disk")


def test_create_page_rejects_content_and_from_file():
    with pytest.raises(ValueError, match="not both"):
        tools.create_page("space-1", "T", content="x", from_file="/tmp/y.md")


# ---------------------------------------------------------------------------
# update_page — optimistic locking
# ---------------------------------------------------------------------------


@pytest.fixture
def update_page_at_v5(mocker: MockerFixture) -> MagicMock:
    """Page currently at version 5; return the update mock to assert against."""
    mocker.patch.object(
        client, "get_page", return_value=Page(id="p1", version=Version(number=5))
    )
    mocker.patch.object(tools, "to_adf", return_value={"adf": 1})
    return mocker.patch.object(client, "update_page")


def test_update_page_increments_version(update_page_at_v5: MagicMock):
    assert tools.update_page("p1", "T", content="new") == "OK"
    assert update_page_at_v5.call_args == call(
        "p1", "T", body={"adf": 1}, version_number=6
    )


def test_update_page_accepts_matching_expected_version(update_page_at_v5: MagicMock):
    assert tools.update_page("p1", "T", content="new", expected_version=5) == "OK"


def test_update_page_rejects_stale_expected_version(update_page_at_v5: MagicMock):
    with pytest.raises(ValueError, match="version conflict"):
        tools.update_page("p1", "T", content="new", expected_version=3)
    update_page_at_v5.assert_not_called()


def test_update_page_requires_content_or_file(update_page_at_v5: MagicMock):
    with pytest.raises(ValueError, match="provide either content or from_file"):
        tools.update_page("p1", "T")


def test_update_page_rejects_content_and_from_file():
    with pytest.raises(ValueError, match="not both"):
        tools.update_page("p1", "T", content="x", from_file="/tmp/y.md")


def test_update_blog_post_increments_version(mocker: MockerFixture):
    mocker.patch.object(
        client,
        "get_blog_post",
        return_value=BlogPost(id="b1", version=Version(number=2)),
    )
    mocker.patch.object(tools, "to_adf", return_value={"adf": 1})
    update = mocker.patch.object(client, "update_blog_post")

    assert tools.update_blog_post("b1", "T", content="new") == "OK"
    assert update.call_args == call("b1", "T", body={"adf": 1}, version_number=3)


def test_update_blog_post_rejects_stale_version(mocker: MockerFixture):
    mocker.patch.object(
        client,
        "get_blog_post",
        return_value=BlogPost(id="b1", version=Version(number=4)),
    )
    mocker.patch.object(tools, "to_adf", return_value={"adf": 1})
    mocker.patch.object(client, "update_blog_post")

    with pytest.raises(ValueError, match="version conflict"):
        tools.update_blog_post("b1", "T", content="new", expected_version=1)


# ---------------------------------------------------------------------------
# Comment editing fetches the current version first
# ---------------------------------------------------------------------------


def test_edit_comment_bumps_fetched_version(mocker: MockerFixture):
    mocker.patch.object(client, "get_comment_version", return_value=7)
    edit = mocker.patch.object(client, "edit_comment")
    mocker.patch.object(tools, "to_adf", return_value={"adf": 1})

    assert tools.edit_comment("c1", "updated") == "OK"
    assert edit.call_args == call("c1", body={"adf": 1}, version_number=8)


# ---------------------------------------------------------------------------
# Attachment & version helpers
# ---------------------------------------------------------------------------


def test_upload_attachment_reads_file(mocker: MockerFixture, tmp_path: Path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"file-bytes")
    upload = mocker.patch.object(client, "upload_attachment")

    assert tools.upload_attachment("p1", str(f), comment="c") == "OK"
    assert upload.call_args == call(
        "p1", filename="f.bin", data=b"file-bytes", comment="c"
    )


def test_download_attachment_writes_temp(mocker: MockerFixture):
    mocker.patch.object(
        client, "get_attachment_content", return_value=(b"\x89PNG", "image/png")
    )

    path = tools.download_attachment("p1", "att-1")
    try:
        assert path.endswith(".png")
    finally:
        Path(path).unlink(missing_ok=True)


def test_restore_page_version_defaults_message(mocker: MockerFixture):
    restore = mocker.patch.object(client, "restore_page_version")

    tools.restore_page_version("p1", 3)

    assert restore.call_args == call("p1", 3, message="Restored to version 3")


# ---------------------------------------------------------------------------
# Write tools that return "OK"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("invoke", "client_attr"),
    [
        (lambda: tools.add_comment("p1", "hi"), "add_comment"),
        (lambda: tools.delete_comment("c1"), "delete_comment"),
        (lambda: tools.reply_to_comment("p1", "c1", "re"), "reply_to_comment"),
        (lambda: tools.create_inline_comment("p1", "note"), "create_inline_comment"),
        (lambda: tools.resolve_inline_comment("i1"), "resolve_inline_comment"),
        (lambda: tools.delete_inline_comment("i1"), "delete_inline_comment"),
        (lambda: tools.add_label("p1", "x"), "add_label"),
        (lambda: tools.remove_label("p1", "x"), "remove_label"),
        (lambda: tools.delete_attachment("att-1"), "delete_attachment"),
        (lambda: tools.delete_page("p1"), "delete_page"),
        (lambda: tools.move_page("p1", "append", "t1"), "move_page"),
        (lambda: tools.copy_page("p1", "space", "DEV"), "copy_page"),
        (lambda: tools.delete_blog_post("b1"), "delete_blog_post"),
        (lambda: tools.update_task("t1", "complete"), "update_task"),
    ],
)
def test_write_tools_return_ok(
    mocker: MockerFixture, invoke: Callable[[], object], client_attr: str
):
    client_mock = mocker.patch.object(client, client_attr, return_value=None)

    assert invoke() == "OK"
    client_mock.assert_called_once()


# ---------------------------------------------------------------------------
# Pass-through readers — delegate to client with mapped args, return its result
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("invoke", "client_attr", "expected"),
    [
        (lambda: tools.get_current_user(), "get_current_user", call()),
        (lambda: tools.get_space("s1"), "get_space", call("s1")),
        (
            lambda: tools.list_spaces(limit=10),
            "list_spaces",
            call(keys=None, space_type=None, status=None, cursor=None, limit=10),
        ),
        (
            lambda: tools.search_content("cql", limit=10),
            "search_content",
            call("cql", limit=10),
        ),
        (
            lambda: tools.get_page_children("p1", limit=10),
            "get_page_children",
            call("p1", limit=10),
        ),
        (
            lambda: tools.get_page_descendants("p1", limit=10),
            "get_page_descendants",
            call("p1", depth=None, limit=10),
        ),
        (
            lambda: tools.get_page_versions("p1", limit=10),
            "get_page_versions",
            call("p1", limit=10),
        ),
        (lambda: tools.get_ancestors("p1"), "get_ancestors", call("p1")),
        (lambda: tools.get_page_views("p1"), "get_page_views", call("p1")),
        (
            lambda: tools.get_attachments("p1", limit=10),
            "get_attachments",
            call("p1", limit=10),
        ),
        (
            lambda: tools.search_users("cql", limit=10),
            "search_users",
            call("cql", limit=10),
        ),
        (lambda: tools.get_labels("p1"), "get_labels", call("p1")),
    ],
)
def test_reader_delegates_to_client(
    mocker: MockerFixture,
    invoke: Callable[[], object],
    client_attr: str,
    expected: object,
):
    sentinel = object()
    delegate = mocker.patch.object(client, client_attr, return_value=sentinel)

    assert invoke() is sentinel
    assert delegate.call_args == expected


def test_get_inline_comment_replies_converts_bodies(mocker: MockerFixture):
    result = MultiEntityResultInlineComment(
        results=[InlineComment(id="i1", body={"type": "doc"})]
    )
    mocker.patch.object(client, "get_inline_comment_children", return_value=result)
    mocker.patch.object(tools, "to_md", return_value="md")

    assert tools.get_inline_comment_replies("i1").results[0].body == "md"


def test_get_blog_post_to_file_writes_body_and_omits_it(
    mocker: MockerFixture, tmp_path: Path
):
    mocker.patch.object(
        client, "get_blog_post", return_value=BlogPost(id="b1", body={"type": "doc"})
    )
    mocker.patch.object(tools, "to_md", return_value="file body")
    target = tmp_path / "bp.md"

    out = tools.get_blog_post("b1", to_file=str(target))

    assert target.read_text() == "file body"
    assert out.body is None


def test_update_page_reads_from_file(mocker: MockerFixture, tmp_path: Path):
    f = tmp_path / "body.md"
    f.write_text("disk body")
    mocker.patch.object(
        client, "get_page", return_value=Page(id="p1", version=Version(number=2))
    )
    mocker.patch.object(client, "update_page")
    to_adf = mocker.patch.object(tools, "to_adf", return_value={"adf": 1})

    assert tools.update_page("p1", "T", from_file=str(f)) == "OK"
    assert to_adf.call_args == call("disk body")


def test_update_blog_post_requires_content_or_file():
    with pytest.raises(ValueError, match="provide either content or from_file"):
        tools.update_blog_post("b1", "T")


def test_update_blog_post_reads_from_file(mocker: MockerFixture, tmp_path: Path):
    f = tmp_path / "body.md"
    f.write_text("disk body")
    mocker.patch.object(
        client,
        "get_blog_post",
        return_value=BlogPost(id="b1", version=Version(number=1)),
    )
    mocker.patch.object(client, "update_blog_post")
    to_adf = mocker.patch.object(tools, "to_adf", return_value={"adf": 1})

    assert tools.update_blog_post("b1", "T", from_file=str(f)) == "OK"
    assert to_adf.call_args == call("disk body")


def test_create_blog_post_converts_and_returns_id(mocker: MockerFixture):
    create = mocker.patch.object(
        client, "create_blog_post", return_value=BlogPost(id="b1")
    )
    mocker.patch.object(tools, "to_adf", return_value={"adf": 1})

    assert tools.create_blog_post("space-1", "T", content="# Hi") == "b1"
    assert create.call_args == call("space-1", "T", body={"adf": 1})


def test_create_blog_post_rejects_content_and_from_file():
    with pytest.raises(ValueError, match="not both"):
        tools.create_blog_post("space-1", "T", content="x", from_file="/tmp/y.md")


def test_create_blog_post_reads_from_file(mocker: MockerFixture, tmp_path: Path):
    f = tmp_path / "body.md"
    f.write_text("disk body")
    mocker.patch.object(client, "create_blog_post", return_value=BlogPost(id="b1"))
    to_adf = mocker.patch.object(tools, "to_adf", return_value={"adf": 1})

    assert tools.create_blog_post("space-1", "T", from_file=str(f)) == "b1"
    assert to_adf.call_args == call("disk body")


def test_update_blog_post_rejects_content_and_from_file():
    with pytest.raises(ValueError, match="not both"):
        tools.update_blog_post("b1", "T", content="x", from_file="/tmp/y.md")
