from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from atlassian.config import config
from atlassian.confluence import tools as confluence
from atlassian.jira import permissions as jira_permissions
from atlassian.jira import tools as jira

mcp = FastMCP(
    "atlassian",
    instructions=(
        "Jira and Confluence via Markdown (not raw ADF). Search issues with JQL "
        "(jira_search_issues) and pages with CQL (confluence_search_content). "
        "Write tools (create/update/delete) are gated by config and absent in "
        "read-only sessions — if a write tool is missing, it can be enabled via "
        "/plugin config atlassian."
    ),
)


def _bind(
    prefix: str,
    fns: list[Callable[..., Any]],
    *,
    gated: set[str] | None = None,
) -> None:
    for fn in fns:
        if gated is None:
            mcp.tool(name=f"{prefix}_{fn.__name__}")(fn)
        else:
            mcp.tool(
                name=f"{prefix}_{fn.__name__}",
                description=jira_permissions.describe(fn, gated),
            )(fn)


# --- JIRA ---

_bind(
    "jira",
    [
        jira.get_current_user,
        jira.search_users,
        jira.list_projects,
        jira.get_project,
        jira.get_project_versions,
        jira.get_project_components,
        jira.get_project_statuses,
        jira.search_issues,
        jira.get_issue,
        jira.get_transitions,
        jira.get_changelogs,
        jira.get_issue_type_metadata,
        jira.list_issue_types,
        jira.download_attachment,
        jira.get_comments,
        jira.get_link_types,
        jira.get_remote_issue_links,
        jira.get_watchers,
        jira.search_fields,
        jira.get_labels,
        jira.get_worklogs,
        jira.list_boards,
        jira.get_board_issues,
        jira.get_backlog_issues,
        jira.get_epic_issues,
        jira.get_epic,
        jira.list_sprints,
        jira.get_sprint,
        jira.get_sprint_issues,
    ],
)

if config.write_enabled:
    _gated = jira_permissions.globally_unavailable()
    _bind(
        "jira",
        [
            jira.create_issue,
            jira.update_issue,
            jira.change_issue_type,
            jira.assign_issue,
            jira.delete_issue,
            jira.upload_attachment,
            jira.transition_issue,
            jira.add_comment,
            jira.edit_comment,
            jira.delete_comment,
            jira.create_issue_link,
            jira.remove_issue_link,
            jira.create_remote_issue_link,
            jira.delete_remote_issue_link,
            jira.add_watcher,
            jira.remove_watcher,
            jira.add_worklog,
            jira.update_worklog,
            jira.delete_worklog,
            jira.create_version,
            jira.update_version,
            jira.delete_version,
            jira.move_issues_to_sprint,
            jira.link_to_epic,
            jira.move_to_backlog,
            jira.create_sprint,
            jira.update_sprint,
            jira.delete_sprint,
        ],
        gated=_gated,
    )

# --- Confluence ---

_bind(
    "confluence",
    [
        confluence.get_current_user,
        confluence.search_users,
        confluence.list_spaces,
        confluence.get_space,
        confluence.search_content,
        confluence.list_pages,
        confluence.get_page,
        confluence.get_page_children,
        confluence.get_page_descendants,
        confluence.get_page_versions,
        confluence.get_ancestors,
        confluence.get_page_views,
        confluence.get_likes,
        confluence.get_comments,
        confluence.get_comment_replies,
        confluence.get_inline_comments,
        confluence.get_inline_comment_replies,
        confluence.get_labels,
        confluence.get_attachments,
        confluence.download_attachment,
        confluence.list_blog_posts,
        confluence.get_blog_post,
        confluence.get_tasks,
    ],
)

# Confluence has no global self-permission API (unlike Jira's /mypermissions),
# so there is no bind-time gating to apply here; permission gaps surface as 403s
# (handled by the client's forbidden hook).
if config.write_enabled:
    _bind(
        "confluence",
        [
            confluence.create_page,
            confluence.update_page,
            confluence.delete_page,
            confluence.move_page,
            confluence.add_comment,
            confluence.edit_comment,
            confluence.delete_comment,
            confluence.reply_to_comment,
            confluence.create_inline_comment,
            confluence.resolve_inline_comment,
            confluence.delete_inline_comment,
            confluence.add_label,
            confluence.remove_label,
            confluence.upload_attachment,
            confluence.delete_attachment,
            confluence.copy_page,
            confluence.restore_page_version,
            confluence.create_blog_post,
            confluence.update_blog_post,
            confluence.delete_blog_post,
            confluence.update_task,
        ],
    )
