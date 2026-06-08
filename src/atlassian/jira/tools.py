"""JIRA MCP tools — pure functions, registered by server.py."""

from typing import Annotated, Literal, TypeAlias

from marklas import to_adf, to_md
from pydantic import Field

from atlassian.jira import client
from atlassian.jira.schema.attachment import Attachment
from atlassian.jira.schema.board import PageBeanBoard
from atlassian.jira.schema.changelog import PageBeanChangelog
from atlassian.jira.schema.comment import PageOfComments
from atlassian.jira.schema.common import IssueTypeDetails, IssueTypeWithStatus
from atlassian.jira.schema.component import Component
from atlassian.jira.schema.epic import Epic
from atlassian.jira.schema.field import PageBeanField
from atlassian.jira.schema.issue import (
    IssueBean,
    SearchAndReconcileResults,
    SearchResults,
)
from atlassian.jira.schema.issue_type_meta import PageOfCreateMetaIssueTypes
from atlassian.jira.schema.label import PageBeanLabel
from atlassian.jira.schema.link_type import IssueLinkTypes
from atlassian.jira.schema.project import PageBeanProject, Project
from atlassian.jira.schema.remote_link import RemoteIssueLink
from atlassian.jira.schema.sprint import SprintBean, SprintPage
from atlassian.jira.schema.transition import Transitions
from atlassian.jira.schema.user import User
from atlassian.jira.schema.version import PageBeanVersion
from atlassian.jira.schema.watcher import Watchers
from atlassian.jira.schema.worklog import PageOfWorklogs
from atlassian.files import read_body, read_bytes, write_body, write_temp

# Common parameter annotations — kept here so per-tool signatures stay terse and
# the descriptions are not repeated across tools.
IssueKey: TypeAlias = Annotated[str, Field(description="Issue key, e.g. PROJ-123.")]
ProjectKey: TypeAlias = Annotated[str, Field(description="Project key, e.g. PROJ.")]
Limit: TypeAlias = Annotated[int, Field(description="Max results.")]
Offset: TypeAlias = Annotated[int, Field(description="Pagination offset (0-based).")]
Plain: TypeAlias = Annotated[
    bool, Field(description="Set false to keep ADF-only features for editing.")
]
AccountId: TypeAlias = Annotated[
    str, Field(description="User accountId (from search_users).")
]
_TIME_SPENT = 'Time spent, e.g. "3h 20m" (#d/#h/#m).'
_STARTED = "Start time, ISO8601, e.g. 2021-01-17T12:34:00.000+0000."
_VERSION_DATE = "Date, YYYY-MM-DD."
_SPRINT_DATE = "ISO8601 datetime, e.g. 2015-04-11T15:22:00.000+10:00."


# --- User ---


def get_current_user() -> User:
    """Get the currently authenticated user."""
    return client.get_current_user()


def search_users(
    query: Annotated[str, Field(description="Name or email to match.")],
    limit: Limit = 50,
) -> list[User]:
    """Search for users."""
    return client.search_users(query, max_results=limit)


# --- Project ---


def list_projects(
    start_at: Offset = 0,
    limit: Limit = 50,
) -> PageBeanProject:
    """List projects. Use get_project if you already know the project key."""
    return client.list_projects(start_at=start_at, max_results=limit)


def get_project(project_key: ProjectKey) -> Project:
    """Get a project's details."""
    return client.get_project(project_key)


def get_project_versions(
    project_key: ProjectKey,
    start_at: Offset = 0,
    limit: Limit = 50,
) -> PageBeanVersion:
    """Get a project's versions (releases)."""
    return client.get_project_versions(
        project_key, start_at=start_at, max_results=limit
    )


def get_project_components(project_key: ProjectKey) -> list[Component]:
    """Get a project's components."""
    return client.get_project_components(project_key)


def get_project_statuses(project_key: ProjectKey) -> list[IssueTypeWithStatus]:
    """Get statuses per issue type in a project. Useful for finding JQL status values."""
    return client.get_project_statuses(project_key)


# --- Issue ---


def search_issues(
    jql: Annotated[str, Field(description="JQL query.")],
    limit: Limit = 50,
    next_page_token: Annotated[
        str | None,
        Field(description="Token from a previous response for the next page."),
    ] = None,
) -> SearchAndReconcileResults:
    """Search issues by JQL. Description is omitted; use get_issue for full detail."""
    result = client.search_issues(
        jql, max_results=limit, next_page_token=next_page_token
    )
    for issue in result.issues:
        if issue.fields:
            issue.fields.description = None
    return result


def get_issue(
    issue_key: IssueKey,
    plain: Plain = True,
    to_file: Annotated[
        str | None,
        Field(
            description="Absolute path: write the description there and omit it from "
            "the response; edit, then publish with update_issue(from_file=...)."
        ),
    ] = None,
) -> IssueBean:
    """Get an issue. Description is Markdown."""
    issue = client.get_issue(issue_key)
    if issue.fields and isinstance(issue.fields.description, dict):
        issue.fields.description = to_md(issue.fields.description, plain=plain)
    if (
        to_file is not None
        and issue.fields
        and isinstance(issue.fields.description, str)
    ):
        write_body(to_file, issue.fields.description)
        issue.fields.description = None
    return issue


def create_issue(
    project_key: ProjectKey,
    summary: Annotated[str, Field(description="Issue summary.")],
    issue_type: Annotated[
        str, Field(description="Issue type name, e.g. Task, Bug, Story.")
    ] = "Task",
    description: Annotated[str | None, Field(description="Markdown.")] = None,
    assignee: Annotated[str | None, Field(description="Assignee accountId.")] = None,
    from_file: Annotated[
        str | None,
        Field(description="Absolute path to read the description from."),
    ] = None,
) -> str:
    """Create an issue; returns the issue key. Provide description inline or via from_file, not both."""
    if description and from_file:
        raise ValueError("provide either description or from_file, not both")
    if from_file is not None:
        description = read_body(from_file)
    issue = client.create_issue(
        project_key,
        summary,
        issue_type=issue_type,
        description=to_adf(description) if description else None,
        assignee=assignee,
    )
    return str(issue.key)


def update_issue(
    issue_key: IssueKey,
    summary: Annotated[str | None, Field(description="New summary.")] = None,
    description: Annotated[str | None, Field(description="Markdown.")] = None,
    from_file: Annotated[
        str | None,
        Field(description="Absolute path to read the description from."),
    ] = None,
) -> str:
    """Update an issue. Provide description inline or via from_file, not both."""
    if description and from_file:
        raise ValueError("provide either description or from_file, not both")
    if from_file is not None:
        description = read_body(from_file)
    client.update_issue(
        issue_key,
        summary=summary,
        description=to_adf(description) if description else None,
    )
    return "OK"


def change_issue_type(
    issue_key: IssueKey,
    issue_type: Annotated[str, Field(description="Target issue type name.")],
    parent: Annotated[
        str | None,
        Field(description="Parent issue key; required when moving down a level."),
    ] = None,
) -> str:
    """Change an issue's type. Moving down a level requires parent; moving up detaches the existing parent. Two-level jumps and demoting an issue with children are unsupported."""
    current = client.get_issue(issue_key)
    cur = current.fields.issue_type if current.fields else None
    if cur is None or cur.name is None or cur.hierarchy_level is None:
        raise ValueError(f"cannot determine the current type of {issue_key}")
    if cur.name == issue_type:
        return f"already '{issue_type}'; no change"

    target = next((t for t in client.list_issue_types() if t.name == issue_type), None)
    if target is None:
        raise ValueError(
            f"unknown issue type '{issue_type}'; use list_issue_types to see valid names"
        )
    if target.hierarchy_level is None:
        raise ValueError(f"cannot determine the hierarchy level of '{issue_type}'")

    diff = target.hierarchy_level - cur.hierarchy_level
    if abs(diff) >= 2:
        raise ValueError(
            f"cannot change '{cur.name}' to '{issue_type}' across multiple hierarchy levels"
        )
    if diff < 0:
        if parent is None:
            raise ValueError(
                f"changing '{cur.name}' to '{issue_type}' moves it down a level and "
                "requires parent (the key of the issue one level up)"
            )
        client.change_issue_type(issue_key, issue_type=issue_type, parent_key=parent)
    elif diff > 0:
        if parent is not None:
            raise ValueError(
                f"changing to '{issue_type}' moves it up a level and takes no parent "
                "(the existing parent is removed)"
            )
        client.change_issue_type(issue_key, issue_type=issue_type, clear_parent=True)
    else:
        if parent is not None:
            raise ValueError(
                f"changing to '{issue_type}' stays at the same level and takes no parent"
            )
        client.change_issue_type(issue_key, issue_type=issue_type)
    return "OK"


def assign_issue(
    issue_key: IssueKey,
    assignee: Annotated[
        str | None,
        Field(description="Assignee accountId (from search_users); omit to unassign."),
    ] = None,
) -> str:
    """Assign an issue, or unassign if assignee is omitted."""
    client.assign_issue(issue_key, assignee)
    return "OK"


def delete_issue(issue_key: IssueKey) -> str:
    """Delete an issue."""
    client.delete_issue(issue_key)
    return "OK"


def get_changelogs(
    issue_key: IssueKey,
    start_at: Offset = 0,
    limit: Limit = 50,
) -> PageBeanChangelog:
    """Get an issue's changelog (field change history)."""
    return client.get_changelogs(issue_key, start_at=start_at, max_results=limit)


def get_issue_type_metadata(
    project_key: ProjectKey,
    start_at: Offset = 0,
    limit: Limit = 50,
) -> PageOfCreateMetaIssueTypes:
    """Get issue types creatable in a project."""
    return client.get_issue_type_metadata(
        project_key, start_at=start_at, max_results=limit
    )


def list_issue_types() -> list[IssueTypeDetails]:
    """List all issue types (Bug, Task, Story, …). Use get_issue_type_metadata for what's creatable in a project."""
    return client.list_issue_types()


def download_attachment(
    attachment_id: Annotated[str, Field(description="Attachment id.")],
) -> str:
    """Download an attachment to a temp file; returns the saved path. The file never enters the model's context — copy it elsewhere to keep it."""
    data, content_type = client.get_attachment_content(attachment_id)
    return write_temp(data, content_type)


def upload_attachment(
    issue_key: IssueKey,
    file_path: Annotated[str, Field(description="Absolute path to the file.")],
) -> list[Attachment]:
    """Attach a local file to an issue."""
    data, filename = read_bytes(file_path)
    return client.add_attachment(issue_key, data, filename)


# --- Transition ---


def get_transitions(issue_key: IssueKey) -> Transitions:
    """Get an issue's available status transitions."""
    return client.get_transitions(issue_key)


def transition_issue(
    issue_key: IssueKey,
    transition_id: Annotated[
        str, Field(description="Transition id (from get_transitions).")
    ],
) -> str:
    """Transition an issue to a new status."""
    client.transition_issue(issue_key, transition_id)
    return "OK"


# --- Comment ---


def get_comments(
    issue_key: IssueKey,
    start_at: Offset = 0,
    limit: Limit = 50,
    plain: Plain = True,
) -> PageOfComments:
    """Get an issue's comments. Body is Markdown."""
    result = client.get_comments(issue_key, start_at=start_at, max_results=limit)
    for comment in result.comments:
        if isinstance(comment.body, dict):
            comment.body = to_md(comment.body, plain=plain)
    return result


def add_comment(
    issue_key: IssueKey,
    body: Annotated[str, Field(description="Markdown.")],
) -> str:
    """Add a comment to an issue."""
    client.add_comment(issue_key, body=to_adf(body))
    return "OK"


def edit_comment(
    issue_key: IssueKey,
    comment_id: Annotated[str, Field(description="Comment id.")],
    body: Annotated[str, Field(description="Markdown.")],
) -> str:
    """Edit a comment."""
    client.update_comment(issue_key, comment_id, body=to_adf(body))
    return "OK"


def delete_comment(
    issue_key: IssueKey,
    comment_id: Annotated[str, Field(description="Comment id.")],
) -> str:
    """Delete a comment."""
    client.delete_comment(issue_key, comment_id)
    return "OK"


# --- Link ---


def get_link_types() -> IssueLinkTypes:
    """Get available issue link types."""
    return client.get_link_types()


def create_issue_link(
    link_type: Annotated[
        str, Field(description="Link type name (from get_link_types).")
    ],
    inward_issue_key: Annotated[str, Field(description="Inward issue key.")],
    outward_issue_key: Annotated[str, Field(description="Outward issue key.")],
) -> str:
    """Create a link between two issues."""
    client.create_issue_link(link_type, inward_issue_key, outward_issue_key)
    return "OK"


def remove_issue_link(
    link_id: Annotated[str, Field(description="Link id.")],
) -> str:
    """Remove a link between two issues."""
    client.delete_issue_link(link_id)
    return "OK"


# --- Remote Link ---


def get_remote_issue_links(issue_key: IssueKey) -> list[RemoteIssueLink]:
    """Get remote links (e.g. GitHub PRs, Confluence pages) on an issue."""
    return client.get_remote_issue_links(issue_key)


def create_remote_issue_link(
    issue_key: IssueKey,
    url: Annotated[str, Field(description="Target URL.")],
    title: Annotated[str, Field(description="Link title.")],
    relationship: Annotated[
        str | None, Field(description="Relationship text, e.g. 'relates to'.")
    ] = None,
) -> str:
    """Create a remote link on an issue."""
    client.create_remote_issue_link(
        issue_key,
        url=url,
        title=title,
        relationship=relationship,
    )
    return "OK"


def delete_remote_issue_link(
    issue_key: IssueKey,
    link_id: Annotated[str, Field(description="Remote link id.")],
) -> str:
    """Delete a remote link from an issue."""
    client.delete_remote_issue_link(issue_key, link_id)
    return "OK"


# --- Watcher ---


def get_watchers(issue_key: IssueKey) -> Watchers:
    """Get watchers of an issue."""
    return client.get_watchers(issue_key)


def add_watcher(issue_key: IssueKey, account_id: AccountId) -> str:
    """Add a watcher to an issue."""
    client.add_watcher(issue_key, account_id)
    return "OK"


def remove_watcher(issue_key: IssueKey, account_id: AccountId) -> str:
    """Remove a watcher from an issue."""
    client.remove_watcher(issue_key, account_id)
    return "OK"


# --- Field ---


def search_fields(
    query: Annotated[
        str | None, Field(description="Text to match in field names; omit for all.")
    ] = None,
    start_at: Offset = 0,
    limit: Limit = 50,
) -> PageBeanField:
    """Search fields (system and custom). Useful for finding field IDs for JQL."""
    return client.search_fields(query=query, start_at=start_at, max_results=limit)


def get_labels(
    start_at: Offset = 0,
    limit: Limit = 50,
) -> PageBeanLabel:
    """Get all labels used across issues."""
    return client.get_labels(start_at=start_at, max_results=limit)


# --- Board ---


def list_boards(
    project_key: Annotated[
        str | None, Field(description="Filter by project key.")
    ] = None,
    board_type: Annotated[
        Literal["scrum", "kanban", "simple"] | None,
        Field(description="Filter by board type."),
    ] = None,
    start_at: Offset = 0,
    limit: Limit = 50,
) -> PageBeanBoard:
    """List agile boards."""
    return client.list_boards(
        project_key=project_key,
        board_type=board_type,
        start_at=start_at,
        max_results=limit,
    )


def get_board_issues(
    board_id: Annotated[str, Field(description="Board id.")],
    start_at: Offset = 0,
    limit: Limit = 50,
) -> SearchResults:
    """Get issues on a board. Description is omitted; use get_issue for full detail."""
    result = client.get_board_issues(
        int(board_id),
        start_at=start_at,
        max_results=limit,
    )
    for issue in result.issues:
        if issue.fields:
            issue.fields.description = None
    return result


def get_backlog_issues(
    board_id: Annotated[str, Field(description="Board id.")],
    start_at: Offset = 0,
    limit: Limit = 50,
) -> SearchResults:
    """Get backlog issues (not in any sprint) on a board. Description is omitted; use get_issue for full detail."""
    result = client.get_backlog_issues(
        int(board_id),
        start_at=start_at,
        max_results=limit,
    )
    for issue in result.issues:
        if issue.fields:
            issue.fields.description = None
    return result


def get_epic_issues(
    epic_key: Annotated[str, Field(description="Epic issue key.")],
    start_at: Offset = 0,
    limit: Limit = 50,
) -> SearchResults:
    """Get issues in an epic. Description is omitted; use get_issue for full detail."""
    result = client.get_epic_issues(
        epic_key,
        start_at=start_at,
        max_results=limit,
    )
    for issue in result.issues:
        if issue.fields:
            issue.fields.description = None
    return result


def get_epic(
    epic_key: Annotated[str, Field(description="Epic issue key.")],
) -> Epic:
    """Get an epic's details (name, summary, done status)."""
    return client.get_epic(epic_key)


# --- Sprint ---


def list_sprints(
    board_id: Annotated[str, Field(description="Board id.")],
    state: Annotated[
        Literal["active", "closed", "future"] | None,
        Field(description="Filter by sprint state."),
    ] = None,
    start_at: Offset = 0,
    limit: Limit = 50,
) -> SprintPage:
    """List a board's sprints."""
    return client.list_sprints(
        int(board_id),
        state=state,
        start_at=start_at,
        max_results=limit,
    )


def get_sprint_issues(
    sprint_id: Annotated[str, Field(description="Sprint id.")],
    start_at: Offset = 0,
    limit: Limit = 50,
) -> SearchResults:
    """Get issues in a sprint. Description is omitted; use get_issue for full detail."""
    result = client.get_sprint_issues(
        int(sprint_id),
        start_at=start_at,
        max_results=limit,
    )
    for issue in result.issues:
        if issue.fields:
            issue.fields.description = None
    return result


def get_sprint(
    sprint_id: Annotated[str, Field(description="Sprint id.")],
) -> SprintBean:
    """Get a sprint's details."""
    return client.get_sprint(int(sprint_id))


def move_issues_to_sprint(
    sprint_id: Annotated[str, Field(description="Sprint id.")],
    issue_keys: Annotated[list[str], Field(description="Issue keys to move.")],
) -> str:
    """Move issues to a sprint."""
    client.move_issues_to_sprint(int(sprint_id), issue_keys=issue_keys)
    return "OK"


def create_sprint(
    board_id: Annotated[str, Field(description="Board id.")],
    name: Annotated[str, Field(description="Sprint name.")],
    goal: Annotated[str | None, Field(description="Sprint goal.")] = None,
    start_date: Annotated[str | None, Field(description=_SPRINT_DATE)] = None,
    end_date: Annotated[str | None, Field(description=_SPRINT_DATE)] = None,
) -> str:
    """Create a sprint; returns the sprint id."""
    sprint = client.create_sprint(
        int(board_id),
        name,
        goal=goal,
        start_date=start_date,
        end_date=end_date,
    )
    return str(sprint.id)


def update_sprint(
    sprint_id: Annotated[str, Field(description="Sprint id.")],
    name: Annotated[str | None, Field(description="New name.")] = None,
    state: Annotated[
        Literal["active", "closed", "future"] | None,
        Field(description="New state."),
    ] = None,
    goal: Annotated[str | None, Field(description="New goal.")] = None,
    start_date: Annotated[str | None, Field(description=_SPRINT_DATE)] = None,
    end_date: Annotated[str | None, Field(description=_SPRINT_DATE)] = None,
) -> str:
    """Update a sprint."""
    client.update_sprint(
        int(sprint_id),
        name=name,
        state=state,
        goal=goal,
        start_date=start_date,
        end_date=end_date,
    )
    return "OK"


def delete_sprint(
    sprint_id: Annotated[str, Field(description="Sprint id.")],
) -> str:
    """Delete a sprint."""
    client.delete_sprint(int(sprint_id))
    return "OK"


def link_to_epic(
    epic_key: Annotated[str, Field(description="Epic issue key.")],
    issue_keys: Annotated[list[str], Field(description="Issue keys to link.")],
) -> str:
    """Link issues to an epic."""
    client.link_to_epic(epic_key, issue_keys=issue_keys)
    return "OK"


def move_to_backlog(
    issue_keys: Annotated[list[str], Field(description="Issue keys to move.")],
) -> str:
    """Move issues from sprints back to the backlog."""
    client.move_to_backlog(issue_keys=issue_keys)
    return "OK"


# --- Worklog ---


def get_worklogs(
    issue_key: IssueKey,
    start_at: Offset = 0,
    limit: Limit = 50,
    plain: Plain = True,
) -> PageOfWorklogs:
    """Get an issue's worklog entries. Comment is Markdown."""
    result = client.get_worklogs(issue_key, start_at=start_at, max_results=limit)
    for wl in result.worklogs:
        if isinstance(wl.comment, dict):
            wl.comment = to_md(wl.comment, plain=plain)
    return result


def add_worklog(
    issue_key: IssueKey,
    time_spent: Annotated[str, Field(description=_TIME_SPENT)],
    started: Annotated[str | None, Field(description=_STARTED)] = None,
    comment: Annotated[str | None, Field(description="Markdown.")] = None,
) -> str:
    """Add a worklog entry to an issue."""
    client.add_worklog(
        issue_key,
        time_spent=time_spent,
        started=started,
        comment=to_adf(comment) if comment else None,
    )
    return "OK"


def update_worklog(
    issue_key: IssueKey,
    worklog_id: Annotated[str, Field(description="Worklog id.")],
    time_spent: Annotated[str | None, Field(description=_TIME_SPENT)] = None,
    started: Annotated[str | None, Field(description=_STARTED)] = None,
    comment: Annotated[str | None, Field(description="Markdown.")] = None,
) -> str:
    """Update a worklog entry."""
    client.update_worklog(
        issue_key,
        worklog_id,
        time_spent=time_spent,
        started=started,
        comment=to_adf(comment) if comment else None,
    )
    return "OK"


def delete_worklog(
    issue_key: IssueKey,
    worklog_id: Annotated[str, Field(description="Worklog id.")],
) -> str:
    """Delete a worklog entry from an issue."""
    client.delete_worklog(issue_key, worklog_id)
    return "OK"


# --- Version ---


def create_version(
    project_key: ProjectKey,
    name: Annotated[str, Field(description="Version name.")],
    description: Annotated[
        str | None, Field(description="Version description.")
    ] = None,
    start_date: Annotated[str | None, Field(description=_VERSION_DATE)] = None,
    release_date: Annotated[str | None, Field(description=_VERSION_DATE)] = None,
    released: Annotated[bool, Field(description="Mark as released.")] = False,
) -> str:
    """Create a version (release); returns the version id."""
    version = client.create_version(
        project_key,
        name,
        description=description,
        start_date=start_date,
        release_date=release_date,
        released=released,
    )
    return str(version.id)


def update_version(
    version_id: Annotated[str, Field(description="Version id.")],
    name: Annotated[str | None, Field(description="New name.")] = None,
    description: Annotated[str | None, Field(description="New description.")] = None,
    start_date: Annotated[str | None, Field(description=_VERSION_DATE)] = None,
    release_date: Annotated[str | None, Field(description=_VERSION_DATE)] = None,
    released: Annotated[bool | None, Field(description="Mark as released.")] = None,
) -> str:
    """Update a version (release)."""
    client.update_version(
        version_id,
        name=name,
        description=description,
        start_date=start_date,
        release_date=release_date,
        released=released,
    )
    return "OK"


def delete_version(
    version_id: Annotated[str, Field(description="Version id.")],
) -> str:
    """Delete a version (release)."""
    client.delete_version(version_id)
    return "OK"
