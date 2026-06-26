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
from urllib.parse import parse_qs, urlparse

import httpx

from atlassian.hooks import error_hook
from atlassian.config import get_auth
from atlassian.confluence.schema.adf import ADF
from atlassian.confluence.schema.ancestor import Ancestor, MultiEntityResultAncestor
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
    PageVersion,
)

# ---------------------------------------------------------------------------
# Lazy singleton
# ---------------------------------------------------------------------------

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client  # noqa: PLW0603
    if _client is None:
        auth = get_auth()
        _client = httpx.Client(
            base_url=auth.url.rstrip("/"),
            auth=(auth.user, auth.token.get_secret_value()),
            # No default Content-Type: httpx sets it per request (application/json
            # for json=, multipart for files=). A fixed default would break uploads.
            headers={"Accept": "application/json"},
            event_hooks={"response": [error_hook("Confluence", "space")]},
        )
    return _client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_cursor(data: dict[str, Any]) -> str | None:
    """Extract cursor from ``_links.next`` URL in v2 API response."""
    links: dict[str, Any] = data.get("_links") or {}
    next_url: str | None = links.get("next")
    if not next_url:
        return None
    parsed = urlparse(next_url)
    cursors: list[str] | None = parse_qs(parsed.query).get("cursor")
    return cursors[0] if cursors else None


def _extract_adf_body(data: dict[str, Any]) -> dict[str, Any] | None:
    """Extract ADF dict from nested v2 body structure.

    v2 API returns: ``body.atlas_doc_format.value`` (JSON string).
    """
    body: dict[str, Any] | None = data.get("body")
    if not body:
        return None
    adf_format: dict[str, Any] | None = body.get("atlas_doc_format")
    if not adf_format:
        return None
    value: str | dict[str, Any] | None = adf_format.get("value")
    if not value:
        return None
    return json.loads(value) if isinstance(value, str) else value


def _parse_page(data: dict[str, Any]) -> Page:
    """Parse a page dict, extracting ADF body."""
    adf = _extract_adf_body(data)
    data["body"] = adf
    return Page.model_validate(data)


def _parse_page_list(data: dict[str, Any]) -> MultiEntityResultPage:
    """Parse paginated page list, injecting cursor."""
    pages = [_parse_page(item) for item in data.get("results", [])]
    return MultiEntityResultPage(
        results=pages,
        cursor=_extract_cursor(data),
    )


def _parse_blog_post(data: dict[str, Any]) -> BlogPost:
    """Parse a blog post dict, extracting ADF body."""
    adf = _extract_adf_body(data)
    data["body"] = adf
    return BlogPost.model_validate(data)


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


def get_attachment_content(page_id: str, attachment_id: str) -> tuple[bytes, str]:
    resp = _get_client().get(
        f"/wiki/rest/api/content/{page_id}/child/attachment/{attachment_id}/download",
        follow_redirects=True,
    )
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "application/octet-stream")
    return resp.content, content_type


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
    data = resp.json()
    result = MultiEntityResultSpace.model_validate(data)
    result.cursor = _extract_cursor(data)
    return result


def get_space(space_id: str) -> Space:
    resp = _get_client().get(f"/wiki/api/v2/spaces/{space_id}")
    resp.raise_for_status()
    return Space.model_validate(resp.json())


def resolve_space_id(space: str) -> str:
    """Return the numeric space id for a space id or key.

    A numeric ``space`` is treated as an id and returned unchanged; otherwise it
    is looked up as a key (e.g. ``DEV`` or ``~accountId``) via list_spaces.
    """
    if space.isdigit():
        return space
    result = list_spaces(keys=[space], limit=1)
    space_id = result.results[0].id if result.results else None
    if space_id is None:
        raise ValueError(f"no Confluence space found with key {space!r}")
    return space_id


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
    return _parse_page_list(resp.json())


def get_page(page_id: str) -> Page:
    resp = _get_client().get(
        f"/wiki/api/v2/pages/{page_id}",
        params={"body-format": "atlas_doc_format"},
    )
    resp.raise_for_status()
    return _parse_page(resp.json())


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
    data = resp.json()
    result = MultiEntityResultChildPage.model_validate(data)
    result.cursor = _extract_cursor(data)
    return result


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
    data = resp.json()
    result = MultiEntityResultChildPage.model_validate(data)
    result.cursor = _extract_cursor(data)
    return result


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
    data = resp.json()
    results = [PageVersion.model_validate(item) for item in data.get("results", [])]
    return MultiEntityResultPageVersion(
        results=results,
        cursor=_extract_cursor(data),
    )


def get_ancestors(page_id: str) -> MultiEntityResultAncestor:
    resp = _get_client().get(f"/wiki/api/v2/pages/{page_id}/ancestors")
    resp.raise_for_status()
    data = resp.json()
    results = [Ancestor.model_validate(item) for item in data.get("results", [])]
    return MultiEntityResultAncestor(results=results)


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
    data = resp.json()
    comments: list[Comment] = []
    for item in data.get("results", []):
        adf = _extract_adf_body(item)
        item["body"] = adf
        comments.append(Comment.model_validate(item))
    return MultiEntityResultComment(
        results=comments,
        cursor=_extract_cursor(data),
    )


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
    data = resp.json()
    comments: list[Comment] = []
    for item in data.get("results", []):
        adf = _extract_adf_body(item)
        item["body"] = adf
        comments.append(Comment.model_validate(item))
    return MultiEntityResultComment(
        results=comments,
        cursor=_extract_cursor(data),
    )


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
    data = resp.json()
    comments: list[InlineComment] = []
    for item in data.get("results", []):
        adf = _extract_adf_body(item)
        item["body"] = adf
        comments.append(InlineComment.model_validate(item))
    return MultiEntityResultInlineComment(
        results=comments,
        cursor=_extract_cursor(data),
    )


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
    data = resp.json()
    comments: list[InlineComment] = []
    for item in data.get("results", []):
        adf = _extract_adf_body(item)
        item["body"] = adf
        comments.append(InlineComment.model_validate(item))
    return MultiEntityResultInlineComment(
        results=comments,
        cursor=_extract_cursor(data),
    )


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
    data = resp.json()
    result = MultiEntityResultLabel.model_validate(data)
    result.cursor = _extract_cursor(data)
    return result


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
    data = resp.json()
    results = [Attachment.model_validate(item) for item in data.get("results", [])]
    return MultiEntityResultAttachment(
        results=results,
        cursor=_extract_cursor(data),
    )


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
    data = resp.json()
    results = [_parse_blog_post(item) for item in data.get("results", [])]
    return MultiEntityResultBlogPost(
        results=results,
        cursor=_extract_cursor(data),
    )


def get_blog_post(blog_post_id: str) -> BlogPost:
    resp = _get_client().get(
        f"/wiki/api/v2/blogposts/{blog_post_id}",
        params={"body-format": "atlas_doc_format"},
    )
    resp.raise_for_status()
    return _parse_blog_post(resp.json())


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
    data = resp.json()
    tasks: list[Task] = []
    for item in data.get("results", []):
        adf = _extract_adf_body(item)
        item["body"] = adf
        tasks.append(Task.model_validate(item))
    return MultiEntityResultTask(
        results=tasks,
        cursor=_extract_cursor(data),
    )


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
    return _parse_page(resp.json())


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
    return _parse_page(resp.json())


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
    data = resp.json()
    adf = _extract_adf_body(data)
    data["body"] = adf
    return Comment.model_validate(data)


def get_comment_version(comment_id: str) -> int:
    """Get the current version number of a footer comment."""
    resp = _get_client().get(
        f"/wiki/api/v2/footer-comments/{comment_id}",
        params={"body-format": "atlas_doc_format"},
    )
    resp.raise_for_status()
    return resp.json().get("version", {}).get("number", 1)


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
    data = resp.json()
    adf = _extract_adf_body(data)
    data["body"] = adf
    return Comment.model_validate(data)


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
    data = resp.json()
    adf = _extract_adf_body(data)
    data["body"] = adf
    return Comment.model_validate(data)


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
    data = resp.json()
    adf_body = _extract_adf_body(data)
    data["body"] = adf_body
    return InlineComment.model_validate(data)


def resolve_inline_comment(comment_id: str) -> InlineComment:
    current_resp = _get_client().get(
        f"/wiki/api/v2/inline-comments/{comment_id}",
        params={"body-format": "atlas_doc_format"},
    )
    current_resp.raise_for_status()
    current_data = current_resp.json()
    current_version = current_data.get("version", {}).get("number", 1)
    payload: dict[str, Any] = {
        "version": {"number": current_version + 1},
        "body": current_data.get("body", {}),
        "resolutionStatus": "resolved",
    }
    resp = _get_client().put(
        f"/wiki/api/v2/inline-comments/{comment_id}",
        json=payload,
    )
    resp.raise_for_status()
    data = resp.json()
    adf_body = _extract_adf_body(data)
    data["body"] = adf_body
    return InlineComment.model_validate(data)


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
    return _parse_blog_post(resp.json())


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
    return _parse_blog_post(resp.json())


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
    data = resp.json()
    adf = _extract_adf_body(data)
    data["body"] = adf
    return Task.model_validate(data)


# ---------------------------------------------------------------------------
# Write — v1 API (/wiki/rest/api)
# ---------------------------------------------------------------------------


def upload_attachment(
    page_id: str, *, filename: str, data: bytes, comment: str | None = None
) -> Attachment:
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
    results = resp.json().get("results", [])
    return Attachment.model_validate(results[0]) if results else Attachment()


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
