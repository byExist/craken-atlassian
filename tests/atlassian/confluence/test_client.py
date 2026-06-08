"""Tests for atlassian.confluence.client — request shaping and response parsing.

Confluence mixes v1 (/wiki/rest/api) and v2 (/wiki/api/v2) endpoints, extracts
ADF bodies out of the nested ``body.atlas_doc_format.value`` JSON string, and
pulls pagination cursors out of ``_links.next``. These behaviours are the focus.
"""

import json
from collections.abc import Callable
from typing import Any

import pytest

from atlassian.confluence import client
from atlassian.confluence.schema.analytics import ContentViews
from atlassian.confluence.schema.blog_post import BlogPost
from atlassian.confluence.schema.comment import Comment
from atlassian.confluence.schema.page import Page
from atlassian.confluence.schema.search import SearchResults
from atlassian.confluence.schema.space import MultiEntityResultSpace, Space
from atlassian.confluence.schema.user import User
from support import MockServer


def _adf_body(doc: dict[str, Any]) -> dict[str, Any]:
    """Wrap an ADF doc the way the v2 API nests it in a response."""
    return {
        "atlas_doc_format": {
            "value": json.dumps(doc),
            "representation": "atlas_doc_format",
        }
    }


def _next_link(cursor: str) -> dict[str, Any]:
    return {"_links": {"next": f"/wiki/api/v2/x?cursor={cursor}&limit=25"}}


# ---------------------------------------------------------------------------
# Read — v1 API
# ---------------------------------------------------------------------------


def test_get_current_user_expands_personal_space(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/rest/api/user/current",
        json={
            "accountId": "a",
            "displayName": "D",
            "personalSpace": {"key": "~a", "name": "P"},
        },
    )

    user = client.get_current_user()

    assert confluence_api.last.url.params["expand"] == "personalSpace"
    assert isinstance(user, User)
    assert user.account_id == "a"
    assert user.personal_space is not None
    assert user.personal_space.key == "~a"


def test_search_content_passes_cql_start_and_limit(confluence_api: MockServer):
    confluence_api.add("GET", "/wiki/rest/api/search", json={"results": [], "size": 0})

    result = client.search_content("type=page", start=20, limit=10)

    req = confluence_api.request("GET", "/wiki/rest/api/search")
    assert req.url.params["cql"] == "type=page"
    assert req.url.params["start"] == "20"
    assert req.url.params["limit"] == "10"
    assert isinstance(result, SearchResults)


def test_search_users_uses_user_search_path(confluence_api: MockServer):
    confluence_api.add("GET", "/wiki/rest/api/search/user", json={"results": []})

    client.search_users("user.fullname~alice", start=5)

    assert confluence_api.last.url.params["cql"] == "user.fullname~alice"
    assert confluence_api.last.url.params["start"] == "5"


def test_get_page_views_returns_content_views(confluence_api: MockServer):
    confluence_api.add(
        "GET", "/wiki/rest/api/analytics/content/55/views", json={"count": 42}
    )

    views = client.get_page_views("55")

    assert isinstance(views, ContentViews)
    assert views.count == 42


def test_get_attachment_content_returns_bytes_and_type(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/rest/api/content/10/child/attachment/att-1/download",
        content=b"PDFDATA",
        headers={"content-type": "application/pdf"},
    )

    data, content_type = client.get_attachment_content("10", "att-1")

    assert data == b"PDFDATA"
    assert content_type == "application/pdf"


# ---------------------------------------------------------------------------
# Read — v2 API: spaces & pages
# ---------------------------------------------------------------------------


def test_list_spaces_extracts_cursor_and_maps_filters(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/spaces",
        json={"results": [{"id": "1", "key": "DEV"}], **_next_link("CUR42")},
    )

    result = client.list_spaces(
        keys=["DEV", "~a"], space_type="global", status="current"
    )

    req = confluence_api.last
    assert req.url.params["keys"] == "DEV,~a"
    assert req.url.params["type"] == "global"
    assert req.url.params["status"] == "current"
    assert isinstance(result, MultiEntityResultSpace)
    assert result.results[0].key == "DEV"
    assert result.cursor == "CUR42"


def test_list_spaces_omits_absent_filters(confluence_api: MockServer):
    confluence_api.add("GET", "/wiki/api/v2/spaces", json={"results": []})

    result = client.list_spaces()

    assert "keys" not in confluence_api.last.url.params
    assert "type" not in confluence_api.last.url.params
    assert "status" not in confluence_api.last.url.params
    assert result.cursor is None


def test_get_space_fetches_by_id(confluence_api: MockServer):
    confluence_api.add("GET", "/wiki/api/v2/spaces/99", json={"id": "99", "key": "DEV"})

    space = client.get_space("99")

    assert isinstance(space, Space)
    assert space.id == "99"


def test_resolve_space_id_returns_numeric_unchanged():
    assert client.resolve_space_id("123") == "123"


def test_resolve_space_id_looks_up_key(confluence_api: MockServer):
    confluence_api.add(
        "GET", "/wiki/api/v2/spaces", json={"results": [{"id": "99", "key": "DEV"}]}
    )

    assert client.resolve_space_id("DEV") == "99"
    assert confluence_api.last.url.params["keys"] == "DEV"


def test_resolve_space_id_raises_when_key_missing(confluence_api: MockServer):
    confluence_api.add("GET", "/wiki/api/v2/spaces", json={"results": []})

    with pytest.raises(ValueError, match="no Confluence space"):
        client.resolve_space_id("NOPE")


def test_list_pages_parses_adf_and_cursor(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/spaces/1/pages",
        json={
            "results": [
                {"id": "p1", "title": "Page", "body": _adf_body({"type": "doc"})}
            ],
            **_next_link("NEXT"),
        },
    )

    result = client.list_pages("1", title="Page")

    assert confluence_api.last.url.params["title"] == "Page"
    assert result.results[0].body == {"type": "doc"}
    assert result.cursor == "NEXT"


def test_get_page_requests_adf_and_extracts_body(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/pages/p1",
        json={
            "id": "p1",
            "title": "T",
            "body": _adf_body({"type": "doc", "content": []}),
        },
    )

    page = client.get_page("p1")

    assert confluence_api.last.url.params["body-format"] == "atlas_doc_format"
    assert isinstance(page, Page)
    assert page.body == {"type": "doc", "content": []}


def test_get_page_with_no_body_yields_none(confluence_api: MockServer):
    confluence_api.add("GET", "/wiki/api/v2/pages/p1", json={"id": "p1", "title": "T"})

    page = client.get_page("p1")

    assert page.body is None


def test_get_page_children_extracts_cursor(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/pages/p1/children",
        json={"results": [{"id": "c1"}], **_next_link("CHILDCUR")},
    )

    result = client.get_page_children("p1")

    assert result.results[0].id == "c1"
    assert result.cursor == "CHILDCUR"


def test_get_page_descendants_passes_depth(confluence_api: MockServer):
    confluence_api.add("GET", "/wiki/api/v2/pages/p1/descendants", json={"results": []})

    client.get_page_descendants("p1", depth=3)

    assert confluence_api.last.url.params["depth"] == "3"


def test_get_page_versions_parses_versions(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/pages/p1/versions",
        json={"results": [{"number": 2}, {"number": 1}], **_next_link("V")},
    )

    result = client.get_page_versions("p1")

    assert [v.number for v in result.results] == [2, 1]
    assert result.cursor == "V"


def test_get_ancestors_parses_results(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/pages/p1/ancestors",
        json={"results": [{"id": "root"}, {"id": "mid"}]},
    )

    result = client.get_ancestors("p1")

    assert [a.id for a in result.results] == ["root", "mid"]


# ---------------------------------------------------------------------------
# Read — v2 API: comments, labels, attachments, likes, blog posts, tasks
# ---------------------------------------------------------------------------


def test_get_comments_requests_adf_and_extracts_bodies(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/pages/p1/footer-comments",
        json={
            "results": [{"id": "c1", "body": _adf_body({"type": "doc"})}],
            **_next_link("CC"),
        },
    )

    result = client.get_comments("p1")

    assert confluence_api.last.url.params["body-format"] == "atlas_doc_format"
    assert result.results[0].body == {"type": "doc"}
    assert result.cursor == "CC"


def test_get_comment_children_extracts_bodies(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/footer-comments/c1/children",
        json={"results": [{"id": "r1", "body": _adf_body({"type": "doc"})}]},
    )

    result = client.get_comment_children("c1")

    assert result.results[0].body == {"type": "doc"}


def test_get_inline_comments_extracts_bodies(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/pages/p1/inline-comments",
        json={"results": [{"id": "i1", "body": _adf_body({"type": "doc"})}]},
    )

    result = client.get_inline_comments("p1")

    assert result.results[0].body == {"type": "doc"}


def test_get_inline_comment_children_extracts_bodies(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/inline-comments/i1/children",
        json={"results": [{"id": "ir1", "body": _adf_body({"type": "doc"})}]},
    )

    result = client.get_inline_comment_children("i1")

    assert result.results[0].body == {"type": "doc"}


def test_get_labels_extracts_cursor(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/pages/p1/labels",
        json={"results": [{"name": "doc"}], **_next_link("LC")},
    )

    result = client.get_labels("p1")

    assert result.results[0].name == "doc"
    assert result.cursor == "LC"


def test_get_attachments_parses_results(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/pages/p1/attachments",
        json={"results": [{"id": "att-1", "title": "a.png"}]},
    )

    result = client.get_attachments("p1")

    assert result.results[0].id == "att-1"


def test_get_likes_count_returns_int(confluence_api: MockServer):
    confluence_api.add("GET", "/wiki/api/v2/pages/p1/likes/count", json={"count": 7})

    assert client.get_likes_count("p1") == 7


def test_list_blog_posts_maps_space_id(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/blogposts",
        json={"results": [{"id": "b1", "body": _adf_body({"type": "doc"})}]},
    )

    result = client.list_blog_posts(space_id="space-1")

    assert confluence_api.last.url.params["space-id"] == "space-1"
    assert result.results[0].body == {"type": "doc"}


def test_get_blog_post_extracts_body(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/blogposts/b1",
        json={"id": "b1", "body": _adf_body({"type": "doc"})},
    )

    post = client.get_blog_post("b1")

    assert isinstance(post, BlogPost)
    assert post.body == {"type": "doc"}


def test_list_tasks_maps_filters_and_extracts_bodies(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/tasks",
        json={
            "results": [
                {"id": "t1", "status": "complete", "body": _adf_body({"type": "doc"})}
            ]
        },
    )

    result = client.list_tasks(page_id="p1", status="complete")

    req = confluence_api.last
    assert req.url.params["page-id"] == "p1"
    assert req.url.params["status"] == "complete"
    assert result.results[0].body == {"type": "doc"}


# ---------------------------------------------------------------------------
# Write — v2 API
# ---------------------------------------------------------------------------


def test_create_page_serializes_adf_body(confluence_api: MockServer):
    confluence_api.add("POST", "/wiki/api/v2/pages", json={"id": "p9", "title": "T"})

    client.create_page("space-1", "T", body={"type": "doc"}, parent_id="parent-1")

    body = confluence_api.body(confluence_api.last)
    assert body["spaceId"] == "space-1"
    assert body["status"] == "current"
    assert body["parentId"] == "parent-1"
    assert json.loads(body["body"]["value"]) == {"type": "doc"}
    assert body["body"]["representation"] == "atlas_doc_format"


def test_create_page_without_body_omits_body(confluence_api: MockServer):
    confluence_api.add("POST", "/wiki/api/v2/pages", json={"id": "p9"})

    client.create_page("space-1", "T")

    assert "body" not in confluence_api.body(confluence_api.last)


def test_update_page_sets_version_and_message(confluence_api: MockServer):
    confluence_api.add("PUT", "/wiki/api/v2/pages/p1", json={"id": "p1"})

    client.update_page(
        "p1", "T", body={"type": "doc"}, version_number=4, version_message="tidy"
    )

    body = confluence_api.body(confluence_api.last)
    assert body["version"] == {"number": 4, "message": "tidy"}
    assert json.loads(body["body"]["value"]) == {"type": "doc"}


def test_delete_page_issues_delete(confluence_api: MockServer):
    confluence_api.add("DELETE", "/wiki/api/v2/pages/p1", json={})

    client.delete_page("p1")

    assert confluence_api.last.method == "DELETE"


def test_add_comment_wraps_body_and_parses_response(confluence_api: MockServer):
    confluence_api.add(
        "POST",
        "/wiki/api/v2/footer-comments",
        json={"id": "c1", "body": _adf_body({"type": "doc"})},
    )

    result = client.add_comment("p1", {"type": "doc"})

    body = confluence_api.body(confluence_api.last)
    assert body["pageId"] == "p1"
    assert json.loads(body["body"]["value"]) == {"type": "doc"}
    assert isinstance(result, Comment)
    assert result.body == {"type": "doc"}


def test_get_comment_version_reads_number(confluence_api: MockServer):
    confluence_api.add(
        "GET", "/wiki/api/v2/footer-comments/c1", json={"version": {"number": 9}}
    )

    assert client.get_comment_version("c1") == 9


def test_edit_comment_sends_version(confluence_api: MockServer):
    confluence_api.add("PUT", "/wiki/api/v2/footer-comments/c1", json={"id": "c1"})

    client.edit_comment("c1", body={"type": "doc"}, version_number=5)

    body = confluence_api.body(confluence_api.last)
    assert body["version"] == {"number": 5}


def test_reply_to_comment_sets_parent(confluence_api: MockServer):
    confluence_api.add(
        "POST", "/wiki/api/v2/footer-comments", json={"id": "r1", "body": None}
    )

    client.reply_to_comment("p1", "c1", body={"type": "doc"})

    body = confluence_api.body(confluence_api.last)
    assert body["pageId"] == "p1"
    assert body["parentCommentId"] == "c1"


def test_create_inline_comment_includes_properties(confluence_api: MockServer):
    confluence_api.add(
        "POST", "/wiki/api/v2/inline-comments", json={"id": "i1", "body": None}
    )

    client.create_inline_comment(
        "p1",
        body={"type": "doc"},
        inline_marker_ref="ref-1",
        inline_original_selection="selected text",
    )

    body = confluence_api.body(confluence_api.last)
    assert body["inlineCommentProperties"] == {
        "inlineMarkerRef": "ref-1",
        "inlineOriginalSelection": "selected text",
    }


def test_create_inline_comment_omits_empty_properties(confluence_api: MockServer):
    confluence_api.add(
        "POST", "/wiki/api/v2/inline-comments", json={"id": "i1", "body": None}
    )

    client.create_inline_comment("p1", body={"type": "doc"})

    assert "inlineCommentProperties" not in confluence_api.body(confluence_api.last)


def test_resolve_inline_comment_bumps_version_and_resolves(confluence_api: MockServer):
    confluence_api.add(
        "GET",
        "/wiki/api/v2/inline-comments/i1",
        json={"version": {"number": 3}, "body": _adf_body({"type": "doc"})},
    )
    confluence_api.add(
        "PUT", "/wiki/api/v2/inline-comments/i1", json={"id": "i1", "body": None}
    )

    client.resolve_inline_comment("i1")

    body = confluence_api.body(
        confluence_api.request("PUT", "/wiki/api/v2/inline-comments/i1")
    )
    assert body["version"] == {"number": 4}
    assert body["resolutionStatus"] == "resolved"


def test_delete_attachment_issues_delete(confluence_api: MockServer):
    confluence_api.add("DELETE", "/wiki/api/v2/attachments/att-1", json={})

    client.delete_attachment("att-1")

    assert confluence_api.last.method == "DELETE"
    assert confluence_api.last.url.path == "/wiki/api/v2/attachments/att-1"


def test_create_blog_post_serializes_body(confluence_api: MockServer):
    confluence_api.add("POST", "/wiki/api/v2/blogposts", json={"id": "b1"})

    client.create_blog_post("space-1", "Title", body={"type": "doc"})

    body = confluence_api.body(confluence_api.last)
    assert body["spaceId"] == "space-1"
    assert json.loads(body["body"]["value"]) == {"type": "doc"}


def test_update_blog_post_sets_version(confluence_api: MockServer):
    confluence_api.add("PUT", "/wiki/api/v2/blogposts/b1", json={"id": "b1"})

    client.update_blog_post("b1", "Title", body={"type": "doc"}, version_number=2)

    assert confluence_api.body(confluence_api.last)["version"] == {"number": 2}


def test_update_task_sends_status(confluence_api: MockServer):
    confluence_api.add(
        "PUT", "/wiki/api/v2/tasks/t1", json={"id": "t1", "status": "complete"}
    )

    client.update_task("t1", "complete")

    assert confluence_api.body(confluence_api.last) == {"status": "complete"}


# ---------------------------------------------------------------------------
# Write — v1 API
# ---------------------------------------------------------------------------


def test_upload_attachment_uses_multipart_and_nocheck(confluence_api: MockServer):
    confluence_api.add(
        "POST",
        "/wiki/rest/api/content/p1/child/attachment",
        json={"results": [{"id": "att-1", "title": "f.png"}]},
    )

    result = client.upload_attachment(
        "p1", filename="f.png", data=b"bytes", comment="v1"
    )

    req = confluence_api.last
    assert req.headers["X-Atlassian-Token"] == "nocheck"
    assert b"f.png" in req.content
    assert b"minorEdit" in req.content
    assert result.id == "att-1"


def test_upload_attachment_handles_empty_results(confluence_api: MockServer):
    confluence_api.add(
        "POST", "/wiki/rest/api/content/p1/child/attachment", json={"results": []}
    )

    result = client.upload_attachment("p1", filename="f.png", data=b"bytes")

    assert result.id is None


def test_move_page_uses_position_and_target_path(confluence_api: MockServer):
    confluence_api.add("PUT", "/wiki/rest/api/content/p1/move/append/target-1", json={})

    client.move_page("p1", "append", "target-1")

    assert confluence_api.last.method == "PUT"
    assert (
        confluence_api.last.url.path == "/wiki/rest/api/content/p1/move/append/target-1"
    )


def test_copy_page_sets_destination_and_flags(confluence_api: MockServer):
    confluence_api.add("POST", "/wiki/rest/api/content/p1/copy", json={})

    client.copy_page(
        "p1", destination_type="space", destination_value="DEV", title="Copy"
    )

    body = confluence_api.body(confluence_api.last)
    assert body["destination"] == {"type": "space", "value": "DEV"}
    assert body["copyAttachments"] is True
    assert body["copyLabels"] is True
    assert body["pageTitle"] == "Copy"


def test_restore_page_version_uses_restore_operation(confluence_api: MockServer):
    confluence_api.add("POST", "/wiki/rest/api/content/p1/version", json={})

    client.restore_page_version("p1", 3, message="revert")

    body = confluence_api.body(confluence_api.last)
    assert body["operationKey"] == "restore"
    assert body["params"] == {"versionNumber": 3, "message": "revert"}


def test_add_label_posts_global_prefix_and_parses(confluence_api: MockServer):
    confluence_api.add(
        "POST",
        "/wiki/rest/api/content/p1/label",
        json={"results": [{"name": "urgent"}]},
    )

    labels = client.add_label("p1", "urgent")

    assert confluence_api.body(confluence_api.last) == [
        {"prefix": "global", "name": "urgent"}
    ]
    assert [label.name for label in labels] == ["urgent"]


def test_remove_label_passes_name_param(confluence_api: MockServer):
    confluence_api.add("DELETE", "/wiki/rest/api/content/p1/label", json={})

    client.remove_label("p1", "urgent")

    assert confluence_api.last.url.params["name"] == "urgent"


# ---------------------------------------------------------------------------
# cursor pagination is forwarded on every v2 list endpoint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("invoke", "path"),
    [
        (lambda: client.list_spaces(cursor="C"), "/wiki/api/v2/spaces"),
        (lambda: client.list_pages("1", cursor="C"), "/wiki/api/v2/spaces/1/pages"),
        (
            lambda: client.get_page_children("p1", cursor="C"),
            "/wiki/api/v2/pages/p1/children",
        ),
        (
            lambda: client.get_page_descendants("p1", cursor="C"),
            "/wiki/api/v2/pages/p1/descendants",
        ),
        (
            lambda: client.get_page_versions("p1", cursor="C"),
            "/wiki/api/v2/pages/p1/versions",
        ),
        (
            lambda: client.get_comments("p1", cursor="C"),
            "/wiki/api/v2/pages/p1/footer-comments",
        ),
        (
            lambda: client.get_comment_children("c1", cursor="C"),
            "/wiki/api/v2/footer-comments/c1/children",
        ),
        (
            lambda: client.get_inline_comments("p1", cursor="C"),
            "/wiki/api/v2/pages/p1/inline-comments",
        ),
        (
            lambda: client.get_inline_comment_children("c1", cursor="C"),
            "/wiki/api/v2/inline-comments/c1/children",
        ),
        (lambda: client.get_labels("p1", cursor="C"), "/wiki/api/v2/pages/p1/labels"),
        (
            lambda: client.get_attachments("p1", cursor="C"),
            "/wiki/api/v2/pages/p1/attachments",
        ),
        (lambda: client.list_blog_posts(cursor="C"), "/wiki/api/v2/blogposts"),
        (lambda: client.list_tasks(cursor="C"), "/wiki/api/v2/tasks"),
    ],
)
def test_cursor_param_is_forwarded(
    confluence_api: MockServer, invoke: Callable[[], object], path: str
):
    invoke()

    assert confluence_api.request("GET", path).url.params["cursor"] == "C"


# ---------------------------------------------------------------------------
# v2 delete endpoints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("invoke", "path"),
    [
        (lambda: client.delete_comment("c1"), "/wiki/api/v2/footer-comments/c1"),
        (lambda: client.delete_inline_comment("i1"), "/wiki/api/v2/inline-comments/i1"),
        (lambda: client.delete_blog_post("b1"), "/wiki/api/v2/blogposts/b1"),
    ],
)
def test_delete_endpoints_issue_delete(
    confluence_api: MockServer, invoke: Callable[[], object], path: str
):
    invoke()

    assert confluence_api.last.method == "DELETE"
    assert confluence_api.last.url.path == path
