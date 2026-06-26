"""JIRA REST API client.

Lazy-singleton ``httpx.Client`` with module-level functions that return typed
Pydantic models.  The HTTP client is created on first use so that the MCP server
can always start even when environment variables are not yet configured.

Required environment variables
------------------------------
ATLASSIAN_DOMAIN - e.g. ``mycompany.atlassian.net``
ATLASSIAN_USER  - e.g. ``user@company.com``
ATLASSIAN_TOKEN - Atlassian API token
"""

from typing import Any

import httpx

from atlassian.hooks import error_hook
from atlassian.config import get_auth

from atlassian.jira.schema.adf import ADF
from atlassian.jira.schema.attachment import Attachment
from atlassian.jira.schema.board import PageBeanBoard
from atlassian.jira.schema.changelog import PageBeanChangelog
from atlassian.jira.schema.comment import Comment, PageOfComments
from atlassian.jira.schema.common import IssueTypeDetails, IssueTypeWithStatus
from atlassian.jira.schema.component import Component
from atlassian.jira.schema.epic import Epic
from atlassian.jira.schema.field import PageBeanField
from atlassian.jira.schema.issue import (
    CreatedIssue,
    IssueBean,
    SearchAndReconcileResults,
    SearchResults,
)
from atlassian.jira.schema.issue_type_meta import PageOfCreateMetaIssueTypes
from atlassian.jira.schema.label import PageBeanLabel
from atlassian.jira.schema.link_type import IssueLinkTypes
from atlassian.jira.schema.permission import Permissions
from atlassian.jira.schema.project import PageBeanProject, Project
from atlassian.jira.schema.remote_link import RemoteIssueLink, RemoteIssueLinkIdentifies
from atlassian.jira.schema.sprint import SprintBean, SprintPage
from atlassian.jira.schema.transition import Transitions
from atlassian.jira.schema.user import User
from atlassian.jira.schema.version import PageBeanVersion, ProjectVersion
from atlassian.jira.schema.watcher import Watchers
from atlassian.jira.schema.worklog import PageOfWorklogs, Worklog

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
            event_hooks={"response": [error_hook("Jira", "project")]},
        )
    return _client


# ---------------------------------------------------------------------------
# Read — Core API (/rest/api/3)
# ---------------------------------------------------------------------------


def search_issues(
    jql: str,
    *,
    max_results: int = 50,
    next_page_token: str | None = None,
) -> SearchAndReconcileResults:
    body: dict[str, Any] = {
        "jql": jql,
        "maxResults": max_results,
        "fields": ["*all"],
    }
    if next_page_token is not None:
        body["nextPageToken"] = next_page_token
    resp = _get_client().post("/rest/api/3/search/jql", json=body)
    resp.raise_for_status()
    return SearchAndReconcileResults.model_validate(resp.json())


_DEFAULT_ISSUE_FIELDS = ",".join(
    [
        "summary",
        "description",
        "status",
        "assignee",
        "reporter",
        "issuetype",
        "priority",
        "labels",
        "created",
        "updated",
        "resolutiondate",
        "issuelinks",
    ]
)


def get_issue(issue_key: str, fields: list[str] | None = None) -> IssueBean:
    field_param = _DEFAULT_ISSUE_FIELDS
    if fields:
        field_param = f"{_DEFAULT_ISSUE_FIELDS},{','.join(fields)}"
    resp = _get_client().get(
        f"/rest/api/3/issue/{issue_key}",
        params={"fields": field_param},
    )
    resp.raise_for_status()
    return IssueBean.model_validate(resp.json())


def get_transitions(issue_key: str) -> Transitions:
    resp = _get_client().get(f"/rest/api/3/issue/{issue_key}/transitions")
    resp.raise_for_status()
    return Transitions.model_validate(resp.json())


def get_comments(
    issue_key: str,
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> PageOfComments:
    resp = _get_client().get(
        f"/rest/api/3/issue/{issue_key}/comment",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return PageOfComments.model_validate(resp.json())


def get_changelogs(
    issue_key: str,
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> PageBeanChangelog:
    resp = _get_client().get(
        f"/rest/api/3/issue/{issue_key}/changelog",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return PageBeanChangelog.model_validate(resp.json())


def get_worklogs(
    issue_key: str,
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> PageOfWorklogs:
    resp = _get_client().get(
        f"/rest/api/3/issue/{issue_key}/worklog",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return PageOfWorklogs.model_validate(resp.json())


def get_remote_issue_links(issue_key: str) -> list[RemoteIssueLink]:
    resp = _get_client().get(f"/rest/api/3/issue/{issue_key}/remotelink")
    resp.raise_for_status()
    return [RemoteIssueLink.model_validate(item) for item in resp.json()]


def get_watchers(issue_key: str) -> Watchers:
    resp = _get_client().get(f"/rest/api/3/issue/{issue_key}/watchers")
    resp.raise_for_status()
    return Watchers.model_validate(resp.json())


def get_attachment_content(attachment_id: str) -> tuple[bytes, str]:
    resp = _get_client().get(
        f"/rest/api/3/attachment/content/{attachment_id}",
        follow_redirects=True,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("content-type", "application/octet-stream")


def get_issue_type_metadata(
    project_key: str,
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> PageOfCreateMetaIssueTypes:
    resp = _get_client().get(
        f"/rest/api/3/issue/createmeta/{project_key}/issuetypes",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return PageOfCreateMetaIssueTypes.model_validate(resp.json())


def list_issue_types() -> list[IssueTypeDetails]:
    resp = _get_client().get("/rest/api/3/issuetype")
    resp.raise_for_status()
    return [IssueTypeDetails.model_validate(item) for item in resp.json()]


def list_projects(
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> PageBeanProject:
    resp = _get_client().get(
        "/rest/api/3/project/search",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return PageBeanProject.model_validate(resp.json())


def get_project(project_key: str) -> Project:
    resp = _get_client().get(f"/rest/api/3/project/{project_key}")
    resp.raise_for_status()
    return Project.model_validate(resp.json())


def get_project_versions(
    project_key: str,
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> PageBeanVersion:
    resp = _get_client().get(
        f"/rest/api/3/project/{project_key}/version",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return PageBeanVersion.model_validate(resp.json())


def get_project_components(project_key: str) -> list[Component]:
    resp = _get_client().get(f"/rest/api/3/project/{project_key}/components")
    resp.raise_for_status()
    return [Component.model_validate(item) for item in resp.json()]


def get_project_statuses(project_key: str) -> list[IssueTypeWithStatus]:
    resp = _get_client().get(f"/rest/api/3/project/{project_key}/statuses")
    resp.raise_for_status()
    return [IssueTypeWithStatus.model_validate(item) for item in resp.json()]


def get_link_types() -> IssueLinkTypes:
    resp = _get_client().get("/rest/api/3/issueLinkType")
    resp.raise_for_status()
    return IssueLinkTypes.model_validate(resp.json())


def search_fields(
    *,
    query: str | None = None,
    start_at: int = 0,
    max_results: int = 50,
) -> PageBeanField:
    params: dict[str, str | int] = {
        "startAt": start_at,
        "maxResults": max_results,
    }
    if query is not None:
        params["query"] = query
    resp = _get_client().get("/rest/api/3/field/search", params=params)
    resp.raise_for_status()
    return PageBeanField.model_validate(resp.json())


def get_labels(
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> PageBeanLabel:
    resp = _get_client().get(
        "/rest/api/3/label",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return PageBeanLabel.model_validate(resp.json())


def get_current_user() -> User:
    resp = _get_client().get("/rest/api/3/myself")
    resp.raise_for_status()
    return User.model_validate(resp.json())


def get_my_permissions(
    keys: list[str],
    *,
    project_key: str | None = None,
    issue_key: str | None = None,
) -> Permissions:
    """Get the user's permissions via /mypermissions.

    Without project_key/issue_key this reports the *global* context: a PROJECT
    permission is reported True if the user has it in any project, so a False
    there means the account lacks it everywhere.
    """
    params: dict[str, str] = {"permissions": ",".join(keys)}
    if project_key is not None:
        params["projectKey"] = project_key
    if issue_key is not None:
        params["issueKey"] = issue_key
    resp = _get_client().get("/rest/api/3/mypermissions", params=params)
    resp.raise_for_status()
    return Permissions.model_validate(resp.json())


def search_users(
    query: str,
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> list[User]:
    resp = _get_client().get(
        "/rest/api/3/user/search",
        params={"query": query, "startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return [User.model_validate(item) for item in resp.json()]


# ---------------------------------------------------------------------------
# Read — Agile API (/rest/agile/1.0)
# ---------------------------------------------------------------------------


def list_boards(
    *,
    project_key: str | None = None,
    board_type: str | None = None,
    start_at: int = 0,
    max_results: int = 50,
) -> PageBeanBoard:
    params: dict[str, str | int] = {
        "startAt": start_at,
        "maxResults": max_results,
    }
    if project_key is not None:
        params["projectKeyOrId"] = project_key
    if board_type is not None:
        params["type"] = board_type
    resp = _get_client().get("/rest/agile/1.0/board", params=params)
    resp.raise_for_status()
    return PageBeanBoard.model_validate(resp.json())


def get_board_issues(
    board_id: int,
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> SearchResults:
    resp = _get_client().get(
        f"/rest/agile/1.0/board/{board_id}/issue",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return SearchResults.model_validate(resp.json())


def get_backlog_issues(
    board_id: int,
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> SearchResults:
    resp = _get_client().get(
        f"/rest/agile/1.0/board/{board_id}/backlog",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return SearchResults.model_validate(resp.json())


def list_sprints(
    board_id: int,
    *,
    state: str | None = None,
    start_at: int = 0,
    max_results: int = 50,
) -> SprintPage:
    params: dict[str, str | int] = {
        "startAt": start_at,
        "maxResults": max_results,
    }
    if state is not None:
        params["state"] = state
    resp = _get_client().get(
        f"/rest/agile/1.0/board/{board_id}/sprint",
        params=params,
    )
    resp.raise_for_status()
    return SprintPage.model_validate(resp.json())


def get_sprint(sprint_id: int) -> SprintBean:
    resp = _get_client().get(f"/rest/agile/1.0/sprint/{sprint_id}")
    resp.raise_for_status()
    return SprintBean.model_validate(resp.json())


def get_sprint_issues(
    sprint_id: int,
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> SearchResults:
    resp = _get_client().get(
        f"/rest/agile/1.0/sprint/{sprint_id}/issue",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return SearchResults.model_validate(resp.json())


def get_epic_issues(
    epic_key: str,
    *,
    start_at: int = 0,
    max_results: int = 50,
) -> SearchResults:
    resp = _get_client().get(
        f"/rest/agile/1.0/epic/{epic_key}/issue",
        params={"startAt": start_at, "maxResults": max_results},
    )
    resp.raise_for_status()
    return SearchResults.model_validate(resp.json())


def get_epic(epic_key: str) -> Epic:
    resp = _get_client().get(f"/rest/agile/1.0/epic/{epic_key}")
    resp.raise_for_status()
    return Epic.model_validate(resp.json())


# ---------------------------------------------------------------------------
# Write — Core API (/rest/api/3)
# ---------------------------------------------------------------------------


def create_issue(
    project_key: str,
    summary: str,
    *,
    issue_type: str = "Task",
    description: ADF | None = None,
    assignee: str | None = None,
    parent_key: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> CreatedIssue:
    fields: dict[str, Any] = {**(extra_fields or {})}
    fields.update(
        {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }
    )
    if description is not None:
        fields["description"] = description
    if assignee is not None:
        fields["assignee"] = {"accountId": assignee}
    if parent_key is not None:
        fields["parent"] = {"key": parent_key}
    if due_date is not None:
        fields["duedate"] = due_date
    if priority is not None:
        fields["priority"] = {"name": priority}
    resp = _get_client().post("/rest/api/3/issue", json={"fields": fields})
    resp.raise_for_status()
    return CreatedIssue.model_validate(resp.json())


def update_issue(
    issue_key: str,
    *,
    summary: str | None = None,
    description: ADF | None = None,
    parent_key: str | None = None,
    assignee: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> None:
    fields: dict[str, Any] = {**(extra_fields or {})}
    if summary is not None:
        fields["summary"] = summary
    if description is not None:
        fields["description"] = description
    if parent_key is not None:
        fields["parent"] = {"key": parent_key}
    if assignee is not None:
        fields["assignee"] = {"accountId": assignee}
    if due_date is not None:
        fields["duedate"] = due_date
    if priority is not None:
        fields["priority"] = {"name": priority}
    resp = _get_client().put(
        f"/rest/api/3/issue/{issue_key}",
        json={"fields": fields},
    )
    resp.raise_for_status()


def change_issue_type(
    issue_key: str,
    *,
    issue_type: str,
    parent_key: str | None = None,
    clear_parent: bool = False,
) -> None:
    fields: dict[str, Any] = {"issuetype": {"name": issue_type}}
    update: dict[str, Any] = {}
    if parent_key is not None:
        fields["parent"] = {"key": parent_key}
    if clear_parent:
        update["parent"] = [{"set": {"none": True}}]
    body: dict[str, Any] = {"fields": fields}
    if update:
        body["update"] = update
    resp = _get_client().put(f"/rest/api/3/issue/{issue_key}", json=body)
    resp.raise_for_status()


def delete_issue(issue_key: str) -> None:
    resp = _get_client().delete(f"/rest/api/3/issue/{issue_key}")
    resp.raise_for_status()


def assign_issue(issue_key: str, assignee: str | None = None) -> None:
    body: dict[str, str | None] = {"accountId": assignee}
    resp = _get_client().put(
        f"/rest/api/3/issue/{issue_key}/assignee",
        json=body,
    )
    resp.raise_for_status()


def transition_issue(issue_key: str, transition_id: str) -> None:
    resp = _get_client().post(
        f"/rest/api/3/issue/{issue_key}/transitions",
        json={"transition": {"id": transition_id}},
    )
    resp.raise_for_status()


def add_comment(issue_key: str, body: ADF) -> Comment:
    resp = _get_client().post(
        f"/rest/api/3/issue/{issue_key}/comment",
        json={"body": body},
    )
    resp.raise_for_status()
    return Comment.model_validate(resp.json())


def update_comment(
    issue_key: str,
    comment_id: str,
    *,
    body: ADF,
) -> Comment:
    resp = _get_client().put(
        f"/rest/api/3/issue/{issue_key}/comment/{comment_id}",
        json={"body": body},
    )
    resp.raise_for_status()
    return Comment.model_validate(resp.json())


def delete_comment(issue_key: str, comment_id: str) -> None:
    resp = _get_client().delete(
        f"/rest/api/3/issue/{issue_key}/comment/{comment_id}",
    )
    resp.raise_for_status()


def add_worklog(
    issue_key: str,
    *,
    time_spent: str,
    started: str | None = None,
    comment: ADF | None = None,
) -> Worklog:
    payload: dict[str, Any] = {"timeSpent": time_spent}
    if started is not None:
        payload["started"] = started
    if comment is not None:
        payload["comment"] = comment
    resp = _get_client().post(
        f"/rest/api/3/issue/{issue_key}/worklog",
        json=payload,
    )
    resp.raise_for_status()
    return Worklog.model_validate(resp.json())


def update_worklog(
    issue_key: str,
    worklog_id: str,
    *,
    time_spent: str | None = None,
    started: str | None = None,
    comment: ADF | None = None,
) -> Worklog:
    payload: dict[str, Any] = {}
    if time_spent is not None:
        payload["timeSpent"] = time_spent
    if started is not None:
        payload["started"] = started
    if comment is not None:
        payload["comment"] = comment
    resp = _get_client().put(
        f"/rest/api/3/issue/{issue_key}/worklog/{worklog_id}",
        json=payload,
    )
    resp.raise_for_status()
    return Worklog.model_validate(resp.json())


def delete_worklog(issue_key: str, worklog_id: str) -> None:
    resp = _get_client().delete(
        f"/rest/api/3/issue/{issue_key}/worklog/{worklog_id}",
    )
    resp.raise_for_status()


def add_attachment(
    issue_key: str,
    data: bytes,
    filename: str,
) -> list[Attachment]:
    resp = _get_client().post(
        f"/rest/api/3/issue/{issue_key}/attachments",
        files={"file": (filename, data)},
        headers={"X-Atlassian-Token": "no-check"},
    )
    resp.raise_for_status()
    return [Attachment.model_validate(item) for item in resp.json()]


def create_issue_link(
    link_type: str,
    inward_issue_key: str,
    outward_issue_key: str,
) -> None:
    resp = _get_client().post(
        "/rest/api/3/issueLink",
        json={
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_issue_key},
            "outwardIssue": {"key": outward_issue_key},
        },
    )
    resp.raise_for_status()


def delete_issue_link(link_id: str) -> None:
    resp = _get_client().delete(f"/rest/api/3/issueLink/{link_id}")
    resp.raise_for_status()


def create_remote_issue_link(
    issue_key: str,
    *,
    url: str,
    title: str,
    relationship: str | None = None,
) -> RemoteIssueLinkIdentifies:
    obj: dict[str, str] = {"url": url, "title": title}
    payload: dict[str, Any] = {"object": obj}
    if relationship is not None:
        payload["relationship"] = relationship
    resp = _get_client().post(
        f"/rest/api/3/issue/{issue_key}/remotelink",
        json=payload,
    )
    resp.raise_for_status()
    return RemoteIssueLinkIdentifies.model_validate(resp.json())


def delete_remote_issue_link(issue_key: str, link_id: str) -> None:
    resp = _get_client().delete(
        f"/rest/api/3/issue/{issue_key}/remotelink/{link_id}",
    )
    resp.raise_for_status()


def add_watcher(issue_key: str, account_id: str) -> None:
    resp = _get_client().post(
        f"/rest/api/3/issue/{issue_key}/watchers",
        content=f'"{account_id}"',
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()


def remove_watcher(issue_key: str, account_id: str) -> None:
    resp = _get_client().delete(
        f"/rest/api/3/issue/{issue_key}/watchers",
        params={"accountId": account_id},
    )
    resp.raise_for_status()


def create_version(
    project_key: str,
    name: str,
    *,
    description: str | None = None,
    start_date: str | None = None,
    release_date: str | None = None,
    released: bool = False,
) -> ProjectVersion:
    payload: dict[str, Any] = {
        "project": project_key,
        "name": name,
        "released": released,
    }
    if description is not None:
        payload["description"] = description
    if start_date is not None:
        payload["startDate"] = start_date
    if release_date is not None:
        payload["releaseDate"] = release_date
    resp = _get_client().post("/rest/api/3/version", json=payload)
    resp.raise_for_status()
    return ProjectVersion.model_validate(resp.json())


def update_version(
    version_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    start_date: str | None = None,
    release_date: str | None = None,
    released: bool | None = None,
) -> ProjectVersion:
    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if start_date is not None:
        payload["startDate"] = start_date
    if release_date is not None:
        payload["releaseDate"] = release_date
    if released is not None:
        payload["released"] = released
    resp = _get_client().put(f"/rest/api/3/version/{version_id}", json=payload)
    resp.raise_for_status()
    return ProjectVersion.model_validate(resp.json())


def delete_version(version_id: str) -> None:
    resp = _get_client().delete(f"/rest/api/3/version/{version_id}")
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Write — Agile API (/rest/agile/1.0)
# ---------------------------------------------------------------------------


def create_sprint(
    board_id: int,
    name: str,
    *,
    goal: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> SprintBean:
    payload: dict[str, Any] = {
        "originBoardId": board_id,
        "name": name,
    }
    if goal is not None:
        payload["goal"] = goal
    if start_date is not None:
        payload["startDate"] = start_date
    if end_date is not None:
        payload["endDate"] = end_date
    resp = _get_client().post("/rest/agile/1.0/sprint", json=payload)
    resp.raise_for_status()
    return SprintBean.model_validate(resp.json())


def update_sprint(
    sprint_id: int,
    *,
    name: str | None = None,
    state: str | None = None,
    goal: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> SprintBean:
    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if state is not None:
        payload["state"] = state
    if goal is not None:
        payload["goal"] = goal
    if start_date is not None:
        payload["startDate"] = start_date
    if end_date is not None:
        payload["endDate"] = end_date
    resp = _get_client().post(
        f"/rest/agile/1.0/sprint/{sprint_id}",
        json=payload,
    )
    resp.raise_for_status()
    return SprintBean.model_validate(resp.json())


def delete_sprint(sprint_id: int) -> None:
    resp = _get_client().delete(f"/rest/agile/1.0/sprint/{sprint_id}")
    resp.raise_for_status()


def move_issues_to_sprint(
    sprint_id: int,
    *,
    issue_keys: list[str],
) -> None:
    resp = _get_client().post(
        f"/rest/agile/1.0/sprint/{sprint_id}/issue",
        json={"issues": issue_keys},
    )
    resp.raise_for_status()


def move_to_backlog(*, issue_keys: list[str]) -> None:
    resp = _get_client().post(
        "/rest/agile/1.0/backlog/issue",
        json={"issues": issue_keys},
    )
    resp.raise_for_status()


def link_to_epic(epic_key: str, *, issue_keys: list[str]) -> None:
    resp = _get_client().post(
        f"/rest/agile/1.0/epic/{epic_key}/issue",
        json={"issues": issue_keys},
    )
    resp.raise_for_status()
