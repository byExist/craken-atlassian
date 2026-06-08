"""Confluence MCP tools — pure functions, registered by server.py."""

import base64
from typing import Annotated, Literal, TypeAlias

from marklas import to_adf, to_md
from pydantic import Field

from atlassian.confluence import client
from atlassian.confluence.schema.ancestor import MultiEntityResultAncestor
from atlassian.confluence.schema.analytics import ContentViews
from atlassian.confluence.schema.attachment import MultiEntityResultAttachment
from atlassian.confluence.schema.blog_post import BlogPost, MultiEntityResultBlogPost
from atlassian.confluence.schema.comment import MultiEntityResultComment
from atlassian.confluence.schema.inline_comment import MultiEntityResultInlineComment
from atlassian.confluence.schema.label import MultiEntityResultLabel
from atlassian.confluence.schema.page import (
    MultiEntityResultChildPage,
    MultiEntityResultPage,
    Page,
)
from atlassian.confluence.schema.search import SearchResults
from atlassian.confluence.schema.space import MultiEntityResultSpace, Space
from atlassian.confluence.schema.task import MultiEntityResultTask
from atlassian.confluence.schema.user import User
from atlassian.confluence.schema.version import MultiEntityResultPageVersion
from atlassian.files import read_body, write_body, write_temp

# Common parameter annotations — kept here so per-tool signatures stay terse and
# the descriptions are not repeated across tools.
PageId: TypeAlias = Annotated[str, Field(description="Page id.")]
SpaceId: TypeAlias = Annotated[str, Field(description="Space id.")]
CommentId: TypeAlias = Annotated[str, Field(description="Comment id.")]
Limit: TypeAlias = Annotated[int, Field(description="Max results.")]
Plain: TypeAlias = Annotated[
    bool, Field(description="Set false to keep ADF-only features for editing.")
]


# --- User ---


def get_current_user() -> User:
    """Get the currently authenticated user."""
    return client.get_current_user()


# --- Space ---


def list_spaces(
    limit: Limit = 25,
    space_type: Annotated[
        Literal[
            "global",
            "collaboration",
            "knowledge_base",
            "personal",
            "system",
            "onboarding",
            "xflow_sample_space",
        ]
        | None,
        Field(description="Filter by space type."),
    ] = None,
    status: Annotated[
        Literal["current", "archived"] | None,
        Field(description="Filter by status."),
    ] = None,
) -> MultiEntityResultSpace:
    """List spaces."""
    return client.list_spaces(
        space_type=space_type,
        status=status,
        limit=limit,
    )


def get_space(space_id: SpaceId) -> Space:
    """Get a space's details."""
    return client.get_space(space_id)


# --- Page ---


def search_content(
    cql: Annotated[str, Field(description="CQL query.")],
    limit: Limit = 25,
) -> SearchResults:
    """Search content by CQL. Use get_page for full content."""
    return client.search_content(cql, limit=limit)


def list_pages(
    space_id: SpaceId,
    title: Annotated[str | None, Field(description="Filter by exact title.")] = None,
    limit: Limit = 25,
) -> MultiEntityResultPage:
    """List pages in a space. Body is omitted; use get_page for full content."""
    result = client.list_pages(space_id, title=title, limit=limit)
    for page in result.results:
        page.body = None
    return result


def get_page(
    page_id: PageId,
    plain: Plain = True,
    to_file: Annotated[
        str | None,
        Field(
            description="Absolute path: write the body there and omit it from the "
            "response; edit, then publish with update_page(from_file=...)."
        ),
    ] = None,
) -> Page:
    """Get a page. Body is Markdown."""
    page = client.get_page(page_id)
    if isinstance(page.body, dict):
        page.body = to_md(page.body, plain=plain)
    if to_file is not None and isinstance(page.body, str):
        write_body(to_file, page.body)
        page.body = None
    return page


def get_page_children(page_id: PageId, limit: Limit = 25) -> MultiEntityResultChildPage:
    """Get a page's direct child pages."""
    return client.get_page_children(page_id, limit=limit)


def get_page_descendants(
    page_id: PageId,
    limit: Limit = 25,
    depth: Annotated[
        int | None, Field(description="Max depth; omit for the full subtree.")
    ] = None,
) -> MultiEntityResultChildPage:
    """Get all descendant pages (full subtree). get_page_children is one level; this is the whole tree."""
    return client.get_page_descendants(page_id, depth=depth, limit=limit)


def get_page_versions(
    page_id: PageId, limit: Limit = 25
) -> MultiEntityResultPageVersion:
    """Get a page's version history."""
    return client.get_page_versions(page_id, limit=limit)


def get_ancestors(page_id: PageId) -> MultiEntityResultAncestor:
    """Get a page's ancestor (parent) chain."""
    return client.get_ancestors(page_id)


def get_page_views(page_id: PageId) -> ContentViews:
    """Get a page's view count."""
    return client.get_page_views(page_id)


def get_likes(page_id: PageId) -> dict[str, int]:
    """Get a page's like count."""
    return {"count": client.get_likes_count(page_id)}


def get_attachments(page_id: PageId, limit: Limit = 25) -> MultiEntityResultAttachment:
    """Get a page's attachments."""
    return client.get_attachments(page_id, limit=limit)


def download_attachment(
    page_id: PageId,
    attachment_id: Annotated[str, Field(description="Attachment id.")],
) -> str:
    """Download an attachment to a temp file; returns the saved path. The file never enters the model's context — copy it elsewhere to keep it."""
    data, content_type = client.get_attachment_content(page_id, attachment_id)
    return write_temp(data, content_type)


def search_users(
    cql: Annotated[str, Field(description="CQL query.")],
    limit: Limit = 25,
) -> SearchResults:
    """Search users by CQL."""
    return client.search_users(cql, limit=limit)


def create_page(
    space_id: SpaceId,
    title: Annotated[str, Field(description="Page title.")],
    content: Annotated[str | None, Field(description="Markdown.")] = None,
    parent_id: Annotated[str | None, Field(description="Parent page id.")] = None,
    from_file: Annotated[
        str | None, Field(description="Absolute path to read the content from.")
    ] = None,
) -> str:
    """Create a page; returns the page id. Provide content inline or via from_file, not both."""
    if content and from_file:
        raise ValueError("provide either content or from_file, not both")
    if from_file is not None:
        content = read_body(from_file)
    adf = to_adf(content) if content else None
    page = client.create_page(
        space_id,
        title,
        body=adf,
        parent_id=parent_id,
    )
    return str(page.id)


def update_page(
    page_id: PageId,
    title: Annotated[str, Field(description="Page title.")],
    content: Annotated[str | None, Field(description="Markdown.")] = None,
    from_file: Annotated[
        str | None, Field(description="Absolute path to read the content from.")
    ] = None,
    expected_version: Annotated[
        int | None,
        Field(
            description="Version from get_page; refuse the write if the page changed "
            "since (avoids clobbering)."
        ),
    ] = None,
) -> str:
    """Update a page. Provide content inline or via from_file, not both."""
    if content and from_file:
        raise ValueError("provide either content or from_file, not both")
    if from_file is not None:
        content = read_body(from_file)
    if content is None:
        raise ValueError("provide either content or from_file")
    current = client.get_page(page_id)
    current_version = current.version.number if current.version else 0
    if expected_version is not None and current_version != expected_version:
        raise ValueError(
            f"version conflict: page is now at {current_version}, but your edits are based "
            f"on {expected_version}; re-fetch with get_page and reapply"
        )
    client.update_page(
        page_id,
        title,
        body=to_adf(content),
        version_number=(current_version or 0) + 1,
    )
    return "OK"


# --- Blog post ---


def list_blog_posts(
    space_id: Annotated[str | None, Field(description="Filter by space id.")] = None,
    limit: Limit = 25,
) -> MultiEntityResultBlogPost:
    """List blog posts. Body is omitted; use get_blog_post for full content."""
    result = client.list_blog_posts(space_id=space_id, limit=limit)
    for post in result.results:
        post.body = None
    return result


def get_blog_post(
    blog_post_id: Annotated[str, Field(description="Blog post id.")],
    plain: Plain = True,
    to_file: Annotated[
        str | None,
        Field(
            description="Absolute path: write the body there and omit it from the "
            "response; edit, then publish with update_blog_post(from_file=...)."
        ),
    ] = None,
) -> BlogPost:
    """Get a blog post. Body is Markdown."""
    post = client.get_blog_post(blog_post_id)
    if isinstance(post.body, dict):
        post.body = to_md(post.body, plain=plain)
    if to_file is not None and isinstance(post.body, str):
        write_body(to_file, post.body)
        post.body = None
    return post


def create_blog_post(
    space_id: SpaceId,
    title: Annotated[str, Field(description="Blog post title.")],
    content: Annotated[str | None, Field(description="Markdown.")] = None,
    from_file: Annotated[
        str | None, Field(description="Absolute path to read the content from.")
    ] = None,
) -> str:
    """Create a blog post; returns the blog post id. Provide content inline or via from_file, not both."""
    if content and from_file:
        raise ValueError("provide either content or from_file, not both")
    if from_file is not None:
        content = read_body(from_file)
    post = client.create_blog_post(
        space_id,
        title,
        body=to_adf(content) if content else None,
    )
    return str(post.id)


def update_blog_post(
    blog_post_id: Annotated[str, Field(description="Blog post id.")],
    title: Annotated[str, Field(description="Blog post title.")],
    content: Annotated[str | None, Field(description="Markdown.")] = None,
    from_file: Annotated[
        str | None, Field(description="Absolute path to read the content from.")
    ] = None,
    expected_version: Annotated[
        int | None,
        Field(
            description="Version from get_blog_post; refuse the write if it changed "
            "since (avoids clobbering)."
        ),
    ] = None,
) -> str:
    """Update a blog post. Provide content inline or via from_file, not both."""
    if content and from_file:
        raise ValueError("provide either content or from_file, not both")
    if from_file is not None:
        content = read_body(from_file)
    if content is None:
        raise ValueError("provide either content or from_file")
    current = client.get_blog_post(blog_post_id)
    current_version = current.version.number if current.version else 0
    if expected_version is not None and current_version != expected_version:
        raise ValueError(
            f"version conflict: blog post is now at {current_version}, but your edits are based "
            f"on {expected_version}; re-fetch with get_blog_post and reapply"
        )
    client.update_blog_post(
        blog_post_id,
        title,
        body=to_adf(content),
        version_number=(current_version or 0) + 1,
    )
    return "OK"


def delete_blog_post(
    blog_post_id: Annotated[str, Field(description="Blog post id.")],
) -> str:
    """Delete a blog post."""
    client.delete_blog_post(blog_post_id)
    return "OK"


# --- Comment ---


def get_comments(
    page_id: PageId, limit: Limit = 25, plain: Plain = True
) -> MultiEntityResultComment:
    """Get a page's footer comments. Body is Markdown."""
    result = client.get_comments(page_id, limit=limit)
    for comment in result.results:
        if isinstance(comment.body, dict):
            comment.body = to_md(comment.body, plain=plain)
    return result


def add_comment(
    page_id: PageId,
    content: Annotated[str, Field(description="Markdown.")],
) -> str:
    """Add a footer comment to a page."""
    client.add_comment(page_id, body=to_adf(content))
    return "OK"


def edit_comment(
    comment_id: CommentId,
    content: Annotated[str, Field(description="Markdown.")],
) -> str:
    """Edit a footer comment."""
    version = client.get_comment_version(comment_id)
    client.edit_comment(
        comment_id,
        body=to_adf(content),
        version_number=version + 1,
    )
    return "OK"


def delete_comment(comment_id: CommentId) -> str:
    """Delete a footer comment."""
    client.delete_comment(comment_id)
    return "OK"


def reply_to_comment(
    page_id: PageId,
    parent_comment_id: Annotated[str, Field(description="Parent comment id.")],
    content: Annotated[str, Field(description="Markdown.")],
) -> str:
    """Reply to a footer comment."""
    client.reply_to_comment(page_id, parent_comment_id, body=to_adf(content))
    return "OK"


def get_comment_replies(
    comment_id: CommentId, limit: Limit = 25, plain: Plain = True
) -> MultiEntityResultComment:
    """Get replies to a footer comment. Body is Markdown."""
    result = client.get_comment_children(comment_id, limit=limit)
    for comment in result.results:
        if isinstance(comment.body, dict):
            comment.body = to_md(comment.body, plain=plain)
    return result


# --- Inline Comment ---


def get_inline_comments(
    page_id: PageId, limit: Limit = 25, plain: Plain = True
) -> MultiEntityResultInlineComment:
    """Get a page's inline comments. Body is Markdown."""
    result = client.get_inline_comments(page_id, limit=limit)
    for comment in result.results:
        if isinstance(comment.body, dict):
            comment.body = to_md(comment.body, plain=plain)
    return result


def create_inline_comment(
    page_id: PageId,
    content: Annotated[str, Field(description="Markdown.")],
    inline_marker_ref: Annotated[
        str | None,
        Field(description="DOM marker reference for the highlighted element."),
    ] = None,
    inline_original_selection: Annotated[
        str | None, Field(description="The highlighted text to anchor the comment to.")
    ] = None,
) -> str:
    """Create an inline comment anchored to highlighted text on a page."""
    client.create_inline_comment(
        page_id,
        body=to_adf(content),
        inline_marker_ref=inline_marker_ref,
        inline_original_selection=inline_original_selection,
    )
    return "OK"


def resolve_inline_comment(comment_id: CommentId) -> str:
    """Resolve an inline comment."""
    client.resolve_inline_comment(comment_id)
    return "OK"


def delete_inline_comment(comment_id: CommentId) -> str:
    """Delete an inline comment."""
    client.delete_inline_comment(comment_id)
    return "OK"


def get_inline_comment_replies(
    comment_id: CommentId, limit: Limit = 25, plain: Plain = True
) -> MultiEntityResultInlineComment:
    """Get replies to an inline comment. Body is Markdown."""
    result = client.get_inline_comment_children(comment_id, limit=limit)
    for comment in result.results:
        if isinstance(comment.body, dict):
            comment.body = to_md(comment.body, plain=plain)
    return result


# --- Label ---


def get_labels(page_id: PageId) -> MultiEntityResultLabel:
    """Get a page's labels."""
    return client.get_labels(page_id)


def add_label(
    page_id: PageId,
    label: Annotated[str, Field(description="Label name.")],
) -> str:
    """Add a label to a page."""
    client.add_label(page_id, label)
    return "OK"


def remove_label(
    page_id: PageId,
    label: Annotated[str, Field(description="Label name.")],
) -> str:
    """Remove a label from a page."""
    client.remove_label(page_id, label)
    return "OK"


# --- Attachment ---


def upload_attachment(
    page_id: PageId,
    filename: Annotated[str, Field(description="File name.")],
    data_base64: Annotated[str, Field(description="Base64-encoded file data.")],
    comment: Annotated[str | None, Field(description="Optional comment.")] = None,
) -> str:
    """Upload an attachment to a page."""
    raw = base64.b64decode(data_base64)
    client.upload_attachment(page_id, filename=filename, data=raw, comment=comment)
    return "OK"


def delete_attachment(
    attachment_id: Annotated[str, Field(description="Attachment id.")],
) -> str:
    """Delete an attachment."""
    client.delete_attachment(attachment_id)
    return "OK"


# --- Page management ---


def delete_page(page_id: PageId) -> str:
    """Delete a page."""
    client.delete_page(page_id)
    return "OK"


def move_page(
    page_id: PageId,
    position: Annotated[
        Literal["before", "after", "append"],
        Field(description="Placement relative to target."),
    ],
    target_id: Annotated[str, Field(description="Target page id.")],
) -> str:
    """Move a page in the page tree."""
    client.move_page(page_id, position, target_id)
    return "OK"


def copy_page(
    page_id: PageId,
    destination_type: Annotated[
        Literal["parent_page", "space", "existing_page"],
        Field(description="Destination kind."),
    ],
    destination_value: Annotated[
        str,
        Field(
            description="Parent page id, space key, or page id — matching destination_type."
        ),
    ],
    title: Annotated[
        str | None, Field(description="Title for the copy; omit to keep the original.")
    ] = None,
) -> str:
    """Copy a page (with attachments and labels) to a new location."""
    client.copy_page(
        page_id,
        destination_type=destination_type,
        destination_value=destination_value,
        title=title,
    )
    return "OK"


def restore_page_version(
    page_id: PageId,
    version_number: Annotated[
        int, Field(description="Version to restore (from get_page_versions).")
    ],
    message: Annotated[
        str | None, Field(description="Optional restore message.")
    ] = None,
) -> str:
    """Restore a page to a previous version."""
    client.restore_page_version(
        page_id,
        version_number,
        message=message or f"Restored to version {version_number}",
    )
    return "OK"


# --- Task ---


def get_tasks(
    page_id: Annotated[str | None, Field(description="Filter by page id.")] = None,
    status: Annotated[
        Literal["complete", "incomplete"] | None,
        Field(description="Filter by status."),
    ] = None,
    limit: Limit = 25,
    plain: Plain = True,
) -> MultiEntityResultTask:
    """Get inline tasks (action items). Body is Markdown."""
    result = client.list_tasks(page_id=page_id, status=status, limit=limit)
    for task in result.results:
        if isinstance(task.body, dict):
            task.body = to_md(task.body, plain=plain)
    return result


def update_task(
    task_id: Annotated[str, Field(description="Task id.")],
    status: Annotated[
        Literal["complete", "incomplete"], Field(description="New status.")
    ],
) -> str:
    """Update a task's status."""
    client.update_task(task_id, status)
    return "OK"
