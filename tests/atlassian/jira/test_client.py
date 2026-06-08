"""Tests for atlassian.jira.client — request shaping and response parsing.

Every client call goes through an httpx.MockTransport (see support.MockServer),
so these assert the HTTP request that would be sent and that the JSON response is
parsed into the right typed model.
"""

from collections.abc import Callable

import pytest

from atlassian.jira import client
from atlassian.jira.schema.board import PageBeanBoard
from atlassian.jira.schema.comment import Comment, PageOfComments
from atlassian.jira.schema.issue import (
    CreatedIssue,
    IssueBean,
    SearchAndReconcileResults,
)
from atlassian.jira.schema.permission import Permissions
from atlassian.jira.schema.project import PageBeanProject, Project
from atlassian.jira.schema.sprint import SprintBean
from atlassian.jira.schema.user import User
from atlassian.jira.schema.version import ProjectVersion
from atlassian.jira.schema.worklog import Worklog
from support import MockServer


# ---------------------------------------------------------------------------
# Read — Core API
# ---------------------------------------------------------------------------


def test_search_issues_posts_jql_with_all_fields(jira_api: MockServer):
    jira_api.add(
        "POST",
        "/rest/api/3/search/jql",
        json={"issues": [{"key": "ABC-1"}], "isLast": True},
    )

    result = client.search_issues("project = ABC", max_results=10)

    req = jira_api.request("POST", "/rest/api/3/search/jql")
    body = jira_api.body(req)
    assert body == {"jql": "project = ABC", "maxResults": 10, "fields": ["*all"]}
    assert isinstance(result, SearchAndReconcileResults)
    assert result.issues[0].key == "ABC-1"
    assert result.is_last is True


def test_search_issues_includes_next_page_token_only_when_given(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/search/jql", json={"issues": []})

    client.search_issues("x", next_page_token="tok-2")

    assert jira_api.body(jira_api.last)["nextPageToken"] == "tok-2"


def test_get_issue_fetches_by_key(jira_api: MockServer):
    jira_api.add(
        "GET",
        "/rest/api/3/issue/ABC-1",
        json={"key": "ABC-1", "fields": {"summary": "Hi"}},
    )

    issue = client.get_issue("ABC-1")

    assert isinstance(issue, IssueBean)
    assert issue.key == "ABC-1"
    assert issue.fields is not None
    assert issue.fields.summary == "Hi"


def test_get_comments_passes_pagination_params(jira_api: MockServer):
    jira_api.add(
        "GET", "/rest/api/3/issue/ABC-1/comment", json={"comments": [], "total": 0}
    )

    result = client.get_comments("ABC-1", start_at=5, max_results=20)

    req = jira_api.request("GET", "/rest/api/3/issue/ABC-1/comment")
    assert req.url.params["startAt"] == "5"
    assert req.url.params["maxResults"] == "20"
    assert isinstance(result, PageOfComments)


def test_get_remote_issue_links_parses_a_list(jira_api: MockServer):
    jira_api.add(
        "GET",
        "/rest/api/3/issue/ABC-1/remotelink",
        json=[{"id": 1}, {"id": 2}],
    )

    links = client.get_remote_issue_links("ABC-1")

    assert len(links) == 2


def test_get_attachment_content_returns_bytes_and_content_type(jira_api: MockServer):
    jira_api.add(
        "GET",
        "/rest/api/3/attachment/content/42",
        content=b"\x89PNG",
        headers={"content-type": "image/png"},
    )

    data, content_type = client.get_attachment_content("42")

    assert data == b"\x89PNG"
    assert content_type == "image/png"


def test_list_projects_returns_page_bean(jira_api: MockServer):
    jira_api.add(
        "GET",
        "/rest/api/3/project/search",
        json={"values": [{"key": "ABC"}], "total": 1},
    )

    result = client.list_projects(start_at=0, max_results=50)

    assert isinstance(result, PageBeanProject)


def test_get_project_returns_project(jira_api: MockServer):
    jira_api.add("GET", "/rest/api/3/project/ABC", json={"key": "ABC", "name": "Acme"})

    project = client.get_project("ABC")

    assert isinstance(project, Project)
    assert project.key == "ABC"


def test_get_project_components_parses_a_list(jira_api: MockServer):
    jira_api.add(
        "GET",
        "/rest/api/3/project/ABC/components",
        json=[{"name": "api"}, {"name": "ui"}],
    )

    components = client.get_project_components("ABC")

    assert [c.name for c in components] == ["api", "ui"]


def test_get_current_user_hits_myself(jira_api: MockServer):
    jira_api.add(
        "GET", "/rest/api/3/myself", json={"accountId": "abc", "displayName": "Dev"}
    )

    user = client.get_current_user()

    assert isinstance(user, User)
    assert user.account_id == "abc"
    assert user.display_name == "Dev"


def test_get_my_permissions_joins_keys_and_omits_context(jira_api: MockServer):
    jira_api.add(
        "GET",
        "/rest/api/3/mypermissions",
        json={"permissions": {"CREATE_ISSUES": {"havePermission": True}}},
    )

    result = client.get_my_permissions(["CREATE_ISSUES", "EDIT_ISSUES"])

    req = jira_api.request("GET", "/rest/api/3/mypermissions")
    assert req.url.params["permissions"] == "CREATE_ISSUES,EDIT_ISSUES"
    assert "projectKey" not in req.url.params
    assert "issueKey" not in req.url.params
    assert isinstance(result, Permissions)
    assert result.permissions["CREATE_ISSUES"].have_permission is True


def test_get_my_permissions_adds_project_and_issue_context(jira_api: MockServer):
    jira_api.add("GET", "/rest/api/3/mypermissions", json={"permissions": {}})

    client.get_my_permissions(["CREATE_ISSUES"], project_key="ABC", issue_key="ABC-1")

    req = jira_api.last
    assert req.url.params["projectKey"] == "ABC"
    assert req.url.params["issueKey"] == "ABC-1"


def test_search_fields_omits_query_when_absent(jira_api: MockServer):
    jira_api.add("GET", "/rest/api/3/field/search", json={"values": []})

    client.search_fields()

    assert "query" not in jira_api.last.url.params


def test_search_fields_includes_query_when_given(jira_api: MockServer):
    jira_api.add("GET", "/rest/api/3/field/search", json={"values": []})

    client.search_fields(query="story points")

    assert jira_api.last.url.params["query"] == "story points"


def test_search_users_passes_query(jira_api: MockServer):
    jira_api.add("GET", "/rest/api/3/user/search", json=[{"accountId": "u1"}])

    users = client.search_users("alice", max_results=10)

    req = jira_api.last
    assert req.url.params["query"] == "alice"
    assert req.url.params["maxResults"] == "10"
    assert users[0].account_id == "u1"


# ---------------------------------------------------------------------------
# Read — Agile API
# ---------------------------------------------------------------------------


def test_list_boards_maps_optional_filters(jira_api: MockServer):
    jira_api.add("GET", "/rest/agile/1.0/board", json={"values": []})

    client.list_boards(project_key="ABC", board_type="scrum")

    req = jira_api.last
    assert req.url.params["projectKeyOrId"] == "ABC"
    assert req.url.params["type"] == "scrum"


def test_list_boards_omits_absent_filters(jira_api: MockServer):
    jira_api.add("GET", "/rest/agile/1.0/board", json={"values": []})

    result = client.list_boards()

    req = jira_api.last
    assert "projectKeyOrId" not in req.url.params
    assert "type" not in req.url.params
    assert isinstance(result, PageBeanBoard)


def test_list_sprints_includes_state_when_given(jira_api: MockServer):
    jira_api.add("GET", "/rest/agile/1.0/board/7/sprint", json={"values": []})

    client.list_sprints(7, state="active")

    assert jira_api.last.url.params["state"] == "active"


def test_get_sprint_fetches_by_id(jira_api: MockServer):
    jira_api.add(
        "GET", "/rest/agile/1.0/sprint/99", json={"id": 99, "name": "Sprint 1"}
    )

    sprint = client.get_sprint(99)

    assert isinstance(sprint, SprintBean)
    assert sprint.id == 99


# ---------------------------------------------------------------------------
# Write — Core API
# ---------------------------------------------------------------------------


def test_create_issue_builds_minimal_fields(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/issue", json={"id": "1", "key": "ABC-9"})

    created = client.create_issue("ABC", "New thing")

    body = jira_api.body(jira_api.request("POST", "/rest/api/3/issue"))
    assert body["fields"]["project"] == {"key": "ABC"}
    assert body["fields"]["summary"] == "New thing"
    assert body["fields"]["issuetype"] == {"name": "Task"}
    assert "description" not in body["fields"]
    assert "assignee" not in body["fields"]
    assert isinstance(created, CreatedIssue)
    assert created.key == "ABC-9"


def test_create_issue_includes_description_and_assignee(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/issue", json={"key": "ABC-9"})

    client.create_issue(
        "ABC",
        "T",
        issue_type="Bug",
        description={"type": "doc", "content": []},
        assignee="acc-1",
    )

    body = jira_api.body(jira_api.last)
    assert body["fields"]["issuetype"] == {"name": "Bug"}
    assert body["fields"]["description"] == {"type": "doc", "content": []}
    assert body["fields"]["assignee"] == {"accountId": "acc-1"}


def test_update_issue_puts_only_provided_fields(jira_api: MockServer):
    jira_api.add("PUT", "/rest/api/3/issue/ABC-1", json={})

    client.update_issue("ABC-1", summary="Renamed")

    req = jira_api.request("PUT", "/rest/api/3/issue/ABC-1")
    assert jira_api.body(req) == {"fields": {"summary": "Renamed"}}


def test_change_issue_type_sets_parent(jira_api: MockServer):
    jira_api.add("PUT", "/rest/api/3/issue/ABC-1", json={})

    client.change_issue_type("ABC-1", issue_type="Sub-task", parent_key="ABC-2")

    body = jira_api.body(jira_api.last)
    assert body["fields"]["issuetype"] == {"name": "Sub-task"}
    assert body["fields"]["parent"] == {"key": "ABC-2"}


def test_change_issue_type_clears_parent(jira_api: MockServer):
    jira_api.add("PUT", "/rest/api/3/issue/ABC-1", json={})

    client.change_issue_type("ABC-1", issue_type="Task", clear_parent=True)

    body = jira_api.body(jira_api.last)
    assert body["update"]["parent"] == [{"set": {"none": True}}]


def test_delete_issue_issues_delete(jira_api: MockServer):
    jira_api.add("DELETE", "/rest/api/3/issue/ABC-1", json={})

    client.delete_issue("ABC-1")

    assert jira_api.last.method == "DELETE"


def test_assign_issue_puts_account_id(jira_api: MockServer):
    jira_api.add("PUT", "/rest/api/3/issue/ABC-1/assignee", json={})

    client.assign_issue("ABC-1", "acc-1")

    assert jira_api.body(jira_api.last) == {"accountId": "acc-1"}


def test_assign_issue_unassigns_with_null(jira_api: MockServer):
    jira_api.add("PUT", "/rest/api/3/issue/ABC-1/assignee", json={})

    client.assign_issue("ABC-1", None)

    assert jira_api.body(jira_api.last) == {"accountId": None}


def test_transition_issue_posts_transition_id(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/issue/ABC-1/transitions", json={})

    client.transition_issue("ABC-1", "31")

    assert jira_api.body(jira_api.last) == {"transition": {"id": "31"}}


def test_add_comment_posts_body_and_parses_comment(jira_api: MockServer):
    jira_api.add(
        "POST", "/rest/api/3/issue/ABC-1/comment", json={"id": "10", "body": None}
    )

    result = client.add_comment("ABC-1", {"type": "doc", "content": []})

    assert jira_api.body(jira_api.last) == {"body": {"type": "doc", "content": []}}
    assert isinstance(result, Comment)
    assert result.id == "10"


def test_add_worklog_posts_time_spent(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/issue/ABC-1/worklog", json={"id": "5"})

    result = client.add_worklog(
        "ABC-1", time_spent="2h", started="2026-01-01T00:00:00.000+0000"
    )

    body = jira_api.body(jira_api.last)
    assert body["timeSpent"] == "2h"
    assert body["started"] == "2026-01-01T00:00:00.000+0000"
    assert isinstance(result, Worklog)


def test_add_attachment_uses_multipart_and_nocheck_header(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/issue/ABC-1/attachments", json=[{"id": "att-1"}])

    result = client.add_attachment("ABC-1", b"binary-bytes", "diagram.png")

    req = jira_api.last
    assert req.headers["X-Atlassian-Token"] == "no-check"
    assert b"diagram.png" in req.content
    assert b"binary-bytes" in req.content
    assert result[0].id == "att-1"


def test_create_issue_link_posts_typed_link(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/issueLink", json={})

    client.create_issue_link("Blocks", "ABC-1", "ABC-2")

    body = jira_api.body(jira_api.last)
    assert body == {
        "type": {"name": "Blocks"},
        "inwardIssue": {"key": "ABC-1"},
        "outwardIssue": {"key": "ABC-2"},
    }


def test_add_watcher_posts_quoted_account_id_as_json(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/issue/ABC-1/watchers", json={})

    client.add_watcher("ABC-1", "acc-9")

    req = jira_api.last
    assert req.content == b'"acc-9"'
    assert req.headers["Content-Type"] == "application/json"


def test_remove_watcher_passes_account_id_param(jira_api: MockServer):
    jira_api.add("DELETE", "/rest/api/3/issue/ABC-1/watchers", json={})

    client.remove_watcher("ABC-1", "acc-9")

    assert jira_api.last.url.params["accountId"] == "acc-9"


def test_create_version_posts_payload(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/version", json={"id": "v1", "name": "1.0"})

    result = client.create_version("ABC", "1.0", description="first", released=True)

    body = jira_api.body(jira_api.last)
    assert body["project"] == "ABC"
    assert body["name"] == "1.0"
    assert body["released"] is True
    assert body["description"] == "first"
    assert isinstance(result, ProjectVersion)


def test_delete_version_issues_delete(jira_api: MockServer):
    jira_api.add("DELETE", "/rest/api/3/version/v1", json={})

    client.delete_version("v1")

    assert jira_api.last.method == "DELETE"
    assert jira_api.last.url.path == "/rest/api/3/version/v1"


# ---------------------------------------------------------------------------
# Write — Agile API
# ---------------------------------------------------------------------------


def test_create_sprint_posts_origin_board(jira_api: MockServer):
    jira_api.add("POST", "/rest/agile/1.0/sprint", json={"id": 1, "name": "S1"})

    client.create_sprint(7, "S1", goal="ship")

    body = jira_api.body(jira_api.last)
    assert body["originBoardId"] == 7
    assert body["name"] == "S1"
    assert body["goal"] == "ship"


def test_update_sprint_uses_post_not_put(jira_api: MockServer):
    jira_api.add("POST", "/rest/agile/1.0/sprint/1", json={"id": 1})

    client.update_sprint(1, state="closed")

    req = jira_api.last
    assert req.method == "POST"
    assert jira_api.body(req) == {"state": "closed"}


def test_move_issues_to_sprint_posts_issue_keys(jira_api: MockServer):
    jira_api.add("POST", "/rest/agile/1.0/sprint/1/issue", json={})

    client.move_issues_to_sprint(1, issue_keys=["ABC-1", "ABC-2"])

    assert jira_api.body(jira_api.last) == {"issues": ["ABC-1", "ABC-2"]}


def test_link_to_epic_posts_issue_keys(jira_api: MockServer):
    jira_api.add("POST", "/rest/agile/1.0/epic/ABC-1/issue", json={})

    client.link_to_epic("ABC-1", issue_keys=["ABC-2"])

    assert jira_api.body(jira_api.last) == {"issues": ["ABC-2"]}


def test_move_to_backlog_posts_issue_keys(jira_api: MockServer):
    jira_api.add("POST", "/rest/agile/1.0/backlog/issue", json={})

    client.move_to_backlog(issue_keys=["ABC-1"])

    assert jira_api.body(jira_api.last) == {"issues": ["ABC-1"]}


# ---------------------------------------------------------------------------
# Remaining read endpoints — method + path (an unmatched route yields 200 {},
# which every all-optional model parses, so these assert routing/parsing run).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("invoke", "method", "path"),
    [
        (
            lambda: client.get_transitions("A-1"),
            "GET",
            "/rest/api/3/issue/A-1/transitions",
        ),
        (
            lambda: client.get_changelogs("A-1"),
            "GET",
            "/rest/api/3/issue/A-1/changelog",
        ),
        (lambda: client.get_worklogs("A-1"), "GET", "/rest/api/3/issue/A-1/worklog"),
        (lambda: client.get_watchers("A-1"), "GET", "/rest/api/3/issue/A-1/watchers"),
        (
            lambda: client.get_issue_type_metadata("ABC"),
            "GET",
            "/rest/api/3/issue/createmeta/ABC/issuetypes",
        ),
        (lambda: client.list_issue_types(), "GET", "/rest/api/3/issuetype"),
        (
            lambda: client.get_project_versions("ABC"),
            "GET",
            "/rest/api/3/project/ABC/version",
        ),
        (
            lambda: client.get_project_statuses("ABC"),
            "GET",
            "/rest/api/3/project/ABC/statuses",
        ),
        (lambda: client.get_link_types(), "GET", "/rest/api/3/issueLinkType"),
        (lambda: client.get_labels(), "GET", "/rest/api/3/label"),
        (lambda: client.get_board_issues(7), "GET", "/rest/agile/1.0/board/7/issue"),
        (
            lambda: client.get_backlog_issues(7),
            "GET",
            "/rest/agile/1.0/board/7/backlog",
        ),
        (lambda: client.get_sprint_issues(9), "GET", "/rest/agile/1.0/sprint/9/issue"),
        (
            lambda: client.get_epic_issues("E-1"),
            "GET",
            "/rest/agile/1.0/epic/E-1/issue",
        ),
        (lambda: client.get_epic("E-1"), "GET", "/rest/agile/1.0/epic/E-1"),
    ],
)
def test_read_endpoint_targets_expected_path(
    jira_api: MockServer, invoke: Callable[[], object], method: str, path: str
):
    invoke()

    assert jira_api.request(method, path).url.path == path


def test_get_changelogs_passes_pagination(jira_api: MockServer):
    client.get_changelogs("A-1", start_at=10, max_results=5)

    req = jira_api.last
    assert req.url.params["startAt"] == "10"
    assert req.url.params["maxResults"] == "5"


# ---------------------------------------------------------------------------
# Remaining write endpoints
# ---------------------------------------------------------------------------


def test_update_issue_includes_description(jira_api: MockServer):
    jira_api.add("PUT", "/rest/api/3/issue/A-1", json={})

    client.update_issue("A-1", description={"type": "doc"})

    assert jira_api.body(jira_api.last) == {"fields": {"description": {"type": "doc"}}}


def test_update_comment_puts_body(jira_api: MockServer):
    jira_api.add("PUT", "/rest/api/3/issue/A-1/comment/c1", json={"id": "c1"})

    result = client.update_comment("A-1", "c1", body={"type": "doc"})

    assert jira_api.body(jira_api.last) == {"body": {"type": "doc"}}
    assert isinstance(result, Comment)


def test_delete_comment_issues_delete(jira_api: MockServer):
    jira_api.add("DELETE", "/rest/api/3/issue/A-1/comment/c1", json={})

    client.delete_comment("A-1", "c1")

    assert jira_api.last.method == "DELETE"
    assert jira_api.last.url.path == "/rest/api/3/issue/A-1/comment/c1"


def test_add_worklog_includes_comment(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/issue/A-1/worklog", json={})

    client.add_worklog("A-1", time_spent="1h", comment={"type": "doc"})

    body = jira_api.body(jira_api.last)
    assert body["timeSpent"] == "1h"
    assert body["comment"] == {"type": "doc"}


def test_update_worklog_puts_provided_fields(jira_api: MockServer):
    jira_api.add("PUT", "/rest/api/3/issue/A-1/worklog/w1", json={})

    client.update_worklog(
        "A-1",
        "w1",
        time_spent="3h",
        started="2026-01-01T00:00:00.000+0000",
        comment={"type": "doc"},
    )

    body = jira_api.body(jira_api.last)
    assert body == {
        "timeSpent": "3h",
        "started": "2026-01-01T00:00:00.000+0000",
        "comment": {"type": "doc"},
    }


def test_delete_worklog_issues_delete(jira_api: MockServer):
    jira_api.add("DELETE", "/rest/api/3/issue/A-1/worklog/w1", json={})

    client.delete_worklog("A-1", "w1")

    assert jira_api.last.url.path == "/rest/api/3/issue/A-1/worklog/w1"


def test_delete_issue_link_issues_delete(jira_api: MockServer):
    jira_api.add("DELETE", "/rest/api/3/issueLink/l1", json={})

    client.delete_issue_link("l1")

    assert jira_api.last.url.path == "/rest/api/3/issueLink/l1"


def test_create_remote_issue_link_posts_object(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/issue/A-1/remotelink", json={"id": 1})

    client.create_remote_issue_link(
        "A-1", url="https://x", title="X", relationship="mentions"
    )

    body = jira_api.body(jira_api.last)
    assert body["object"] == {"url": "https://x", "title": "X"}
    assert body["relationship"] == "mentions"


def test_delete_remote_issue_link_issues_delete(jira_api: MockServer):
    jira_api.add("DELETE", "/rest/api/3/issue/A-1/remotelink/l1", json={})

    client.delete_remote_issue_link("A-1", "l1")

    assert jira_api.last.url.path == "/rest/api/3/issue/A-1/remotelink/l1"


def test_create_version_includes_dates(jira_api: MockServer):
    jira_api.add("POST", "/rest/api/3/version", json={})

    client.create_version(
        "ABC", "1.0", start_date="2026-01-01", release_date="2026-02-01"
    )

    body = jira_api.body(jira_api.last)
    assert body["startDate"] == "2026-01-01"
    assert body["releaseDate"] == "2026-02-01"


def test_update_version_puts_all_fields(jira_api: MockServer):
    jira_api.add("PUT", "/rest/api/3/version/v1", json={})

    client.update_version(
        "v1",
        name="2.0",
        description="d",
        start_date="2026-01-01",
        release_date="2026-02-01",
        released=True,
    )

    body = jira_api.body(jira_api.last)
    assert body == {
        "name": "2.0",
        "description": "d",
        "startDate": "2026-01-01",
        "releaseDate": "2026-02-01",
        "released": True,
    }


def test_create_sprint_includes_dates(jira_api: MockServer):
    jira_api.add("POST", "/rest/agile/1.0/sprint", json={})

    client.create_sprint(7, "S1", start_date="2026-01-01", end_date="2026-01-14")

    body = jira_api.body(jira_api.last)
    assert body["startDate"] == "2026-01-01"
    assert body["endDate"] == "2026-01-14"


def test_update_sprint_puts_all_fields(jira_api: MockServer):
    jira_api.add("POST", "/rest/agile/1.0/sprint/1", json={})

    client.update_sprint(
        1, name="S2", goal="g", start_date="2026-01-01", end_date="2026-01-14"
    )

    body = jira_api.body(jira_api.last)
    assert body == {
        "name": "S2",
        "goal": "g",
        "startDate": "2026-01-01",
        "endDate": "2026-01-14",
    }


def test_delete_sprint_issues_delete(jira_api: MockServer):
    jira_api.add("DELETE", "/rest/agile/1.0/sprint/1", json={})

    client.delete_sprint(1)

    assert jira_api.last.url.path == "/rest/agile/1.0/sprint/1"
