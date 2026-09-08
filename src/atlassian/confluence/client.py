"""Confluence REST API client.

Lazy-singleton ``httpx.Client`` with module-level functions that return typed
Pydantic models.  The HTTP client is created on first use so that the MCP server
can always start even when environment variables are not yet configured.

Mixed API versions:
- v2 (primary): /wiki/api/v2/... -- spaces, pages, blog posts, comments, tasks
- v1 (fallback): /wiki/rest/api/... -- search, analytics, attachments, labels, copy/move/restore

Required environment variables
------------------------------
ATLASSIAN_DOMAIN - e.g. ``mycompany.atlassian.net``
ATLASSIAN_USER  - e.g. ``user@company.com``
ATLASSIAN_TOKEN - Atlassian API token
"""

import json
from typing import Any

import httpx

from atlassian.http import make_client
from atlassian.download import Download
from atlassian.confluence.schema.adf import ADF
from atlassian.confluence.schema.ancestor import MultiEntityResultAncestor
from atlassian.confluence.schema.analytics import ContentViews
from atlassian.confluence.schema.attachment import (
    Attachment,
    MultiEntityResultAttachment,
)
from atlassian.confluence.schema.blog_post import BlogPost, MultiEntityResultBlogPost
from atlassian.confluence.schema.comment import Comment, MultiEntityResultComment
from atlassian.confluence.schema.inline_comment import (
    InlineComment,
    MultiEntityResultInlineComment,
)
from atlassian.confluence.schema.label import Label, MultiEntityResultLabel
from atlassian.confluence.schema.page import (
    MultiEntityResultChildPage,
    MultiEntityResultPage,
    Page,
)
from atlassian.confluence.schema.search import SearchResults
from atlassian.confluence.schema.space import MultiEntityResultSpace, Space
from atlassian.confluence.schema.task import MultiEntityResultTask, Task
from atlassian.confluence.schema.user import User
from atlassian.confluence.schema.version import (
    MultiEntityResultPageVersion,
)

# ---------------------------------------------------------------------------
# Lazy singleton
# ---------------------------------------------------------------------------

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = make_client("Confluence", "space")
    return _client


# ---------------------------------------------------------------------------
# Read — v1 API (/wiki/rest/api)
# ---------------------------------------------------------------------------


def get_current_user() -> User:
    resp = _get_client().get(
        "/wiki/rest/api/user/current",
        params={"expand": "personalSpace"},
    )
    resp.raise_for_status()
    return User.model_validate(resp.json())


def search_content(
    cql: str,
    *,
    start: int = 0,
    limit: int = 25,
) -> SearchResults:
    resp = _get_client().get(
        "/wiki/rest/api/search",
        params={"cql": cql, "start": start, "limit": limit},
    )
    resp.raise_for_status()
    return SearchResults.model_validate(resp.json())


def search_users(
    cql: str,
    *,
    start: int = 0,
    limit: int = 25,
) -> SearchResults:
    resp = _get_client().get(
        "/wiki/rest/api/search/user",
        params={"cql": cql, "start": start, "limit": limit},
    )
    resp.raise_for_status()
    return SearchResults.model_validate(resp.json())


def get_page_views(page_id: str) -> ContentViews:
    resp = _get_client().get(
        f"/wiki/rest/api/analytics/content/{page_id}/views",
    )
    resp.raise_for_status()
    return ContentViews.model_validate(resp.json())


def get_attachment_content(page_id: str, attachment_id: str) -> Download:
    resp = _get_client().get(
        f"/wiki/rest/api/content/{page_id}/child/attachment/{attachment_id}/download",
        follow_redirects=True,
    )
    resp.raise_for_status()
    return Download.from_response(resp)


# ---------------------------------------------------------------------------
# Read — v2 API (/wiki/api/v2)
# ---------------------------------------------------------------------------


def list_spaces(
    *,
    keys: list[str] | None = None,
    space_type: str | None = None,
    status: str | None = None,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultSpace:
    params: dict[str, str | int] = {"limit": limit}
    if keys is not None:
        params["keys"] = ",".join(keys)
    if space_type is not None:
        params["type"] = space_type
    if status is not None:
        params["status"] = status
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get("/wiki/api/v2/spaces", params=params)
    resp.raise_for_status()
    return MultiEntityResultSpace.model_validate(resp.json())


def get_space(space_id: str) -> Space:
    resp = _get_client().get(f"/wiki/api/v2/spaces/{space_id}")
    resp.raise_for_status()
    return Space.model_validate(resp.json())


def list_pages(
    space_id: str,
    *,
    title: str | None = None,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultPage:
    params: dict[str, str | int] = {"limit": limit}
    if title is not None:
        params["title"] = title
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get(
        f"/wiki/api/v2/spaces/{space_id}/pages",
        params=params,
    )
    resp.raise_for_status()
    return MultiEntityResultPage.model_validate(resp.json())


def get_page(page_id: str) -> Page:
    resp = _get_client().get(
        f"/wiki/api/v2/pages/{page_id}",
        params={"body-format": "atlas_doc_format"},
    )
    resp.raise_for_status()
    return Page.model_validate(resp.json())


def get_page_children(
    page_id: str,
    *,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultChildPage:
    params: dict[str, str | int] = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get(
        f"/wiki/api/v2/pages/{page_id}/children",
        params=params,
    )
    resp.raise_for_status()
    return MultiEntityResultChildPage.model_validate(resp.json())


def get_page_descendants(
    page_id: str,
    *,
    depth: int | None = None,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultChildPage:
    params: dict[str, str | int] = {"limit": limit}
    if depth is not None:
        params["depth"] = depth
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get(
        f"/wiki/api/v2/pages/{page_id}/descendants",
        params=params,
    )
    resp.raise_for_status()
    return MultiEntityResultChildPage.model_validate(resp.json())


def get_page_versions(
    page_id: str,
    *,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultPageVersion:
    params: dict[str, str | int] = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get(
        f"/wiki/api/v2/pages/{page_id}/versions",
        params=params,
    )
    resp.raise_for_status()
    return MultiEntityResultPageVersion.model_validate(resp.json())


def get_ancestors(page_id: str) -> MultiEntityResultAncestor:
    resp = _get_client().get(f"/wiki/api/v2/pages/{page_id}/ancestors")
    resp.raise_for_status()
    return MultiEntityResultAncestor.model_validate(resp.json())


def get_comments(
    page_id: str,
    *,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultComment:
    params: dict[str, str | int] = {
        "limit": limit,
        "body-format": "atlas_doc_format",
    }
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get(
        f"/wiki/api/v2/pages/{page_id}/footer-comments",
        params=params,
    )
    resp.raise_for_status()
    return MultiEntityResultComment.model_validate(resp.json())


def get_comment_children(
    comment_id: str,
    *,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultComment:
    params: dict[str, str | int] = {
        "limit": limit,
        "body-format": "atlas_doc_format",
    }
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get(
        f"/wiki/api/v2/footer-comments/{comment_id}/children",
        params=params,
    )
    resp.raise_for_status()
    return MultiEntityResultComment.model_validate(resp.json())


def get_inline_comments(
    page_id: str,
    *,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultInlineComment:
    params: dict[str, str | int] = {
        "limit": limit,
        "body-format": "atlas_doc_format",
    }
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get(
        f"/wiki/api/v2/pages/{page_id}/inline-comments",
        params=params,
    )
    resp.raise_for_status()
    return MultiEntityResultInlineComment.model_validate(resp.json())


def get_inline_comment_children(
    comment_id: str,
    *,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultInlineComment:
    params: dict[str, str | int] = {
        "limit": limit,
        "body-format": "atlas_doc_format",
    }
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get(
        f"/wiki/api/v2/inline-comments/{comment_id}/children",
        params=params,
    )
    resp.raise_for_status()
    return MultiEntityResultInlineComment.model_validate(resp.json())


def get_labels(
    page_id: str,
    *,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultLabel:
    params: dict[str, str | int] = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get(
        f"/wiki/api/v2/pages/{page_id}/labels",
        params=params,
    )
    resp.raise_for_status()
    return MultiEntityResultLabel.model_validate(resp.json())


def get_attachments(
    page_id: str,
    *,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultAttachment:
    params: dict[str, str | int] = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get(
        f"/wiki/api/v2/pages/{page_id}/attachments",
        params=params,
    )
    resp.raise_for_status()
    return MultiEntityResultAttachment.model_validate(resp.json())


def get_likes_count(page_id: str) -> int:
    resp = _get_client().get(f"/wiki/api/v2/pages/{page_id}/likes/count")
    resp.raise_for_status()
    return resp.json().get("count", 0)


def list_blog_posts(
    *,
    space_id: str | None = None,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultBlogPost:
    params: dict[str, str | int] = {"limit": limit}
    if space_id is not None:
        params["space-id"] = space_id
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get("/wiki/api/v2/blogposts", params=params)
    resp.raise_for_status()
    return MultiEntityResultBlogPost.model_validate(resp.json())


def get_blog_post(blog_post_id: str) -> BlogPost:
    resp = _get_client().get(
        f"/wiki/api/v2/blogposts/{blog_post_id}",
        params={"body-format": "atlas_doc_format"},
    )
    resp.raise_for_status()
    return BlogPost.model_validate(resp.json())


def list_tasks(
    *,
    page_id: str | None = None,
    status: str | None = None,
    cursor: str | None = None,
    limit: int = 25,
) -> MultiEntityResultTask:
    params: dict[str, str | int] = {
        "limit": limit,
        "body-format": "atlas_doc_format",
    }
    if page_id is not None:
        params["page-id"] = page_id
    if status is not None:
        params["status"] = status
    if cursor is not None:
        params["cursor"] = cursor
    resp = _get_client().get("/wiki/api/v2/tasks", params=params)
    resp.raise_for_status()
    return MultiEntityResultTask.model_validate(resp.json())


# ---------------------------------------------------------------------------
# Write — v2 API (/wiki/api/v2)
# ---------------------------------------------------------------------------


def create_page(
    space_id: str,
    title: str,
    *,
    body: ADF | None = None,
    parent_id: str | None = None,
    status: str = "current",
) -> Page:
    payload: dict[str, Any] = {
        "spaceId": space_id,
        "status": status,
        "title": title,
    }
    if body is not None:
        payload["body"] = {
            "representation": "atlas_doc_format",
            "value": json.dumps(body),
        }
    if parent_id is not None:
        payload["parentId"] = parent_id
    resp = _get_client().post("/wiki/api/v2/pages", json=payload)
    resp.raise_for_status()
    return Page.model_validate(resp.json())


def update_page(
    page_id: str,
    title: str,
    *,
    body: ADF | None = None,
    version_number: int,
    version_message: str | None = None,
) -> Page:
    payload: dict[str, Any] = {
        "id": page_id,
        "status": "current",
        "title": title,
        "version": {"number": version_number},
    }
    if body is not None:
        payload["body"] = {
            "representation": "atlas_doc_format",
            "value": json.dumps(body),
        }
    if version_message is not None:
        payload["version"]["message"] = version_message
    resp = _get_client().put(
        f"/wiki/api/v2/pages/{page_id}",
        json=payload,
    )
    resp.raise_for_status()
    return Page.model_validate(resp.json())


def delete_page(page_id: str) -> None:
    resp = _get_client().delete(f"/wiki/api/v2/pages/{page_id}")
    resp.raise_for_status()


def add_comment(page_id: str, body: ADF) -> Comment:
    payload: dict[str, Any] = {
        "pageId": page_id,
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(body),
        },
    }
    resp = _get_client().post("/wiki/api/v2/footer-comments", json=payload)
    resp.raise_for_status()
    return Comment.model_validate(resp.json())


def get_comment(comment_id: str) -> Comment:
    resp = _get_client().get(
        f"/wiki/api/v2/footer-comments/{comment_id}",
        params={"body-format": "atlas_doc_format"},
    )
    resp.raise_for_status()
    return Comment.model_validate(resp.json())


def edit_comment(
    comment_id: str,
    *,
    body: ADF,
    version_number: int,
) -> Comment:
    payload: dict[str, Any] = {
        "version": {"number": version_number},
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(body),
        },
    }
    resp = _get_client().put(
        f"/wiki/api/v2/footer-comments/{comment_id}",
        json=payload,
    )
    resp.raise_for_status()
    return Comment.model_validate(resp.json())


def delete_comment(comment_id: str) -> None:
    resp = _get_client().delete(f"/wiki/api/v2/footer-comments/{comment_id}")
    resp.raise_for_status()


def reply_to_comment(
    page_id: str,
    parent_comment_id: str,
    *,
    body: ADF,
) -> Comment:
    payload: dict[str, Any] = {
        "pageId": page_id,
        "parentCommentId": parent_comment_id,
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(body),
        },
    }
    resp = _get_client().post("/wiki/api/v2/footer-comments", json=payload)
    resp.raise_for_status()
    return Comment.model_validate(resp.json())


def create_inline_comment(
    page_id: str,
    *,
    body: ADF,
    inline_marker_ref: str | None = None,
    inline_original_selection: str | None = None,
) -> InlineComment:
    payload: dict[str, Any] = {
        "pageId": page_id,
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(body),
        },
    }
    props: dict[str, str] = {}
    if inline_marker_ref is not None:
        props["inlineMarkerRef"] = inline_marker_ref
    if inline_original_selection is not None:
        props["inlineOriginalSelection"] = inline_original_selection
    if props:
        payload["inlineCommentProperties"] = props
    resp = _get_client().post("/wiki/api/v2/inline-comments", json=payload)
    resp.raise_for_status()
    return InlineComment.model_validate(resp.json())


def get_inline_comment(comment_id: str) -> InlineComment:
    resp = _get_client().get(
        f"/wiki/api/v2/inline-comments/{comment_id}",
        params={"body-format": "atlas_doc_format"},
    )
    resp.raise_for_status()
    return InlineComment.model_validate(resp.json())


def update_inline_comment(
    comment_id: str,
    *,
    body: ADF,
    version_number: int,
    resolved: bool,
) -> InlineComment:
    payload: dict[str, Any] = {
        "version": {"number": version_number},
        "body": {
            "representation": "atlas_doc_format",
            "value": json.dumps(body),
        },
        "resolved": resolved,
    }
    resp = _get_client().put(
        f"/wiki/api/v2/inline-comments/{comment_id}",
        json=payload,
    )
    resp.raise_for_status()
    return InlineComment.model_validate(resp.json())


def delete_inline_comment(comment_id: str) -> None:
    resp = _get_client().delete(f"/wiki/api/v2/inline-comments/{comment_id}")
    resp.raise_for_status()


def delete_attachment(attachment_id: str) -> None:
    resp = _get_client().delete(f"/wiki/api/v2/attachments/{attachment_id}")
    resp.raise_for_status()


def create_blog_post(
    space_id: str,
    title: str,
    *,
    body: ADF | None = None,
    status: str = "current",
) -> BlogPost:
    payload: dict[str, Any] = {
        "spaceId": space_id,
        "status": status,
        "title": title,
    }
    if body is not None:
        payload["body"] = {
            "representation": "atlas_doc_format",
            "value": json.dumps(body),
        }
    resp = _get_client().post("/wiki/api/v2/blogposts", json=payload)
    resp.raise_for_status()
    return BlogPost.model_validate(resp.json())


def update_blog_post(
    blog_post_id: str,
    title: str,
    *,
    body: ADF | None = None,
    version_number: int,
    status: str = "current",
) -> BlogPost:
    payload: dict[str, Any] = {
        "id": blog_post_id,
        "status": status,
        "title": title,
        "version": {"number": version_number},
    }
    if body is not None:
        payload["body"] = {
            "representation": "atlas_doc_format",
            "value": json.dumps(body),
        }
    resp = _get_client().put(
        f"/wiki/api/v2/blogposts/{blog_post_id}",
        json=payload,
    )
    resp.raise_for_status()
    return BlogPost.model_validate(resp.json())


def delete_blog_post(blog_post_id: str) -> None:
    resp = _get_client().delete(f"/wiki/api/v2/blogposts/{blog_post_id}")
    resp.raise_for_status()


def update_task(task_id: str, status: str) -> Task:
    payload: dict[str, Any] = {"status": status}
    resp = _get_client().put(
        f"/wiki/api/v2/tasks/{task_id}",
        json=payload,
    )
    resp.raise_for_status()
    return Task.model_validate(resp.json())


# ---------------------------------------------------------------------------
# Write — v1 API (/wiki/rest/api)
# ---------------------------------------------------------------------------


def upload_attachment(
    page_id: str, *, filename: str, data: bytes, comment: str | None = None
) -> list[Attachment]:
    client = _get_client()
    files = {"file": (filename, data)}
    form_data: dict[str, str] = {"minorEdit": "true"}
    if comment is not None:
        form_data["comment"] = comment
    resp = client.post(
        f"/wiki/rest/api/content/{page_id}/child/attachment",
        files=files,
        data=form_data,
        headers={
            "X-Atlassian-Token": "nocheck",
            "Accept": "application/json",
        },
    )
    resp.raise_for_status()
    return [Attachment.model_validate(item) for item in resp.json().get("results", [])]


def move_page(page_id: str, position: str, target_id: str) -> None:
    resp = _get_client().put(
        f"/wiki/rest/api/content/{page_id}/move/{position}/{target_id}",
    )
    resp.raise_for_status()


def copy_page(
    page_id: str,
    *,
    destination_type: str,
    destination_value: str,
    title: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "destination": {"type": destination_type, "value": destination_value},
        "copyAttachments": True,
        "copyLabels": True,
    }
    if title is not None:
        payload["pageTitle"] = title
    resp = _get_client().post(
        f"/wiki/rest/api/content/{page_id}/copy",
        json=payload,
    )
    resp.raise_for_status()


def restore_page_version(
    page_id: str,
    version_number: int,
    *,
    message: str,
) -> None:
    payload: dict[str, Any] = {
        "operationKey": "restore",
        "params": {"versionNumber": version_number, "message": message},
    }
    resp = _get_client().post(
        f"/wiki/rest/api/content/{page_id}/version",
        json=payload,
    )
    resp.raise_for_status()


def add_label(page_id: str, label: str) -> list[Label]:
    payload = [{"prefix": "global", "name": label}]
    resp = _get_client().post(
        f"/wiki/rest/api/content/{page_id}/label",
        json=payload,
    )
    resp.raise_for_status()
    return [Label.model_validate(item) for item in resp.json().get("results", [])]


def remove_label(page_id: str, label: str) -> None:
    resp = _get_client().delete(
        f"/wiki/rest/api/content/{page_id}/label",
        params={"name": label},
    )
    resp.raise_for_status()
