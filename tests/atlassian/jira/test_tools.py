"""Tests for atlassian.jira.tools — the MCP tool layer.

Tools are thin orchestration over ``client`` plus Markdown<->ADF conversion
(via marklas) and a few rules. Here ``client`` and the ``to_md``/``to_adf``
seams are patched with ``mocker`` so the tool's own logic is what's exercised
— not the network (covered in jira/test_client.py) nor marklas's conversion
fidelity (marklas has its own tests).
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from pytest_mock import MockerFixture

from atlassian.jira import client, tools
from atlassian.jira.schema.comment import Comment, PageOfComments
from atlassian.jira.schema.common import IssueTypeDetails
from atlassian.jira.schema.issue import (
    CreatedIssue,
    IssueBean,
    JiraIssueFields,
    SearchAndReconcileResults,
    SearchResults,
)
from atlassian.jira.schema.sprint import SprintBean
from atlassian.jira.schema.version import ProjectVersion
from atlassian.jira.schema.worklog import PageOfWorklogs, Worklog

ALL_TYPES = [
    IssueTypeDetails(name="Sub-task", hierarchy_level=-1),
    IssueTypeDetails(name="Task", hierarchy_level=0),
    IssueTypeDetails(name="Story", hierarchy_level=0),
    IssueTypeDetails(name="Bug", hierarchy_level=0),
    IssueTypeDetails(name="Epic", hierarchy_level=1),
]


def _issue(type_name: str | None, level: int | None) -> IssueBean:
    itype = None
    if type_name is not None:
        itype = IssueTypeDetails(name=type_name, hierarchy_level=level)
    return IssueBean(key="ABC-1", fields=JiraIssueFields(issue_type=itype))


# ---------------------------------------------------------------------------
# Delegation / argument mapping
# ---------------------------------------------------------------------------


def test_search_users_maps_limit_to_max_results(mocker: MockerFixture):
    sentinel = object()
    search = mocker.patch.object(client, "search_users", return_value=sentinel)

    result = tools.search_users("alice", limit=10)

    assert result is sentinel
    assert search.call_args == call("alice", start_at=0, max_results=10)


def test_get_project_delegates(mocker: MockerFixture):
    sentinel = object()
    get_project = mocker.patch.object(client, "get_project", return_value=sentinel)

    assert tools.get_project("ABC") is sentinel
    assert get_project.call_args == call("ABC")


def test_get_sprint_converts_id_to_int(mocker: MockerFixture):
    get_sprint = mocker.patch.object(client, "get_sprint", return_value=object())

    tools.get_sprint("99")

    assert get_sprint.call_args == call(99)


# ---------------------------------------------------------------------------
# Description stripping on issue lists
# ---------------------------------------------------------------------------


def test_search_issues_strips_descriptions(mocker: MockerFixture):
    results = SearchAndReconcileResults(
        issues=[
            IssueBean(key="A-1", fields=JiraIssueFields(description={"type": "doc"})),
            IssueBean(key="A-2", fields=JiraIssueFields(description="text")),
        ]
    )
    search = mocker.patch.object(client, "search_issues", return_value=results)

    out = tools.search_issues("project = A", limit=5)

    assert search.call_args == call("project = A", max_results=5, next_page_token=None)
    for issue in out.issues:
        assert issue.fields is not None
        assert issue.fields.description is None


def test_get_board_issues_converts_id_and_strips_descriptions(mocker: MockerFixture):
    results = SearchAndReconcileResults(
        issues=[IssueBean(key="A-1", fields=JiraIssueFields(description={"x": 1}))]
    )
    board_issues = mocker.patch.object(client, "get_board_issues", return_value=results)

    out = tools.get_board_issues("7")

    assert board_issues.call_args == call(7, start_at=0, max_results=50)
    first = out.issues[0].fields
    assert first is not None
    assert first.description is None


# ---------------------------------------------------------------------------
# ADF -> Markdown on reads
# ---------------------------------------------------------------------------


def test_get_issue_converts_description_to_markdown(mocker: MockerFixture):
    issue = IssueBean(key="A-1", fields=JiraIssueFields(description={"type": "doc"}))
    mocker.patch.object(client, "get_issue", return_value=issue)
    to_md = mocker.patch.object(tools, "to_md", return_value="# Heading")

    out = tools.get_issue("A-1")

    assert to_md.call_args == call({"type": "doc"}, plain=True)
    assert out.fields is not None
    assert out.fields.description == "# Heading"


def test_get_issue_forwards_plain_false(mocker: MockerFixture):
    issue = IssueBean(key="A-1", fields=JiraIssueFields(description={"type": "doc"}))
    mocker.patch.object(client, "get_issue", return_value=issue)
    to_md = mocker.patch.object(tools, "to_md", return_value="md")

    tools.get_issue("A-1", plain=False)

    assert to_md.call_args == call({"type": "doc"}, plain=False)


def test_get_issue_to_file_writes_body_and_omits_it(
    mocker: MockerFixture, tmp_path: Path
):
    issue = IssueBean(key="A-1", fields=JiraIssueFields(description={"type": "doc"}))
    mocker.patch.object(client, "get_issue", return_value=issue)
    mocker.patch.object(tools, "to_md", return_value="file body")
    target = tmp_path / "desc.md"

    out = tools.get_issue("A-1", to_file=str(target))

    assert target.read_text() == "file body"
    assert out.fields is not None
    assert out.fields.description is None


def test_get_issue_skips_conversion_without_adf(mocker: MockerFixture):
    issue = IssueBean(key="A-1", fields=JiraIssueFields(description=None))
    mocker.patch.object(client, "get_issue", return_value=issue)
    to_md = mocker.patch.object(tools, "to_md")

    out = tools.get_issue("A-1")

    to_md.assert_not_called()
    assert out.fields is not None
    assert out.fields.description is None


def test_get_comments_converts_bodies(mocker: MockerFixture):
    page = PageOfComments(comments=[Comment(id="1", body={"type": "doc"})])
    mocker.patch.object(client, "get_comments", return_value=page)
    mocker.patch.object(tools, "to_md", return_value="md body")

    out = tools.get_comments("A-1")

    assert out.comments[0].body == "md body"


def test_get_worklogs_converts_comments(mocker: MockerFixture):
    page = PageOfWorklogs(worklogs=[Worklog(time_spent="1h", comment={"type": "doc"})])
    mocker.patch.object(client, "get_worklogs", return_value=page)
    mocker.patch.object(tools, "to_md", return_value="logged")

    out = tools.get_worklogs("A-1")

    assert out.worklogs[0].comment == "logged"


# ---------------------------------------------------------------------------
# Markdown -> ADF on writes
# ---------------------------------------------------------------------------


def test_create_issue_converts_markdown_to_adf(mocker: MockerFixture):
    create = mocker.patch.object(
        client, "create_issue", return_value=CreatedIssue(key="A-9")
    )
    to_adf = mocker.patch.object(tools, "to_adf", return_value={"adf": True})

    out = tools.create_issue("ABC", "Title", description="# Hi")

    assert to_adf.call_args == call("# Hi")
    assert create.call_args == call(
        "ABC",
        "Title",
        issue_type="Task",
        description={"adf": True},
        assignee=None,
        parent_key=None,
    )
    assert out == "A-9"


def test_create_issue_passes_none_when_no_description(mocker: MockerFixture):
    create = mocker.patch.object(client, "create_issue", return_value=CreatedIssue())
    to_adf = mocker.patch.object(tools, "to_adf")

    tools.create_issue("ABC", "Title")

    to_adf.assert_not_called()
    assert create.call_args == call(
        "ABC",
        "Title",
        issue_type="Task",
        description=None,
        assignee=None,
        parent_key=None,
    )


def test_create_issue_reads_from_file(mocker: MockerFixture, tmp_path: Path):
    body_file = tmp_path / "body.md"
    body_file.write_text("from disk")
    mocker.patch.object(client, "create_issue", return_value=CreatedIssue())
    to_adf = mocker.patch.object(tools, "to_adf", return_value={"adf": 1})

    tools.create_issue("ABC", "Title", from_file=str(body_file))

    assert to_adf.call_args == call("from disk")


def test_create_issue_rejects_description_and_from_file_together():
    with pytest.raises(ValueError, match="not both"):
        tools.create_issue("ABC", "Title", description="x", from_file="/tmp/y.md")


def test_create_issue_passes_parent(mocker: MockerFixture):
    create = mocker.patch.object(
        client, "create_issue", return_value=CreatedIssue(key="A-9")
    )

    tools.create_issue("ABC", "Title", parent="ABC-1")

    assert create.call_args == call(
        "ABC",
        "Title",
        issue_type="Task",
        description=None,
        assignee=None,
        parent_key="ABC-1",
    )


def test_update_issue_converts_and_returns_ok(mocker: MockerFixture):
    update = mocker.patch.object(client, "update_issue")
    mocker.patch.object(tools, "to_adf", return_value={"adf": True})

    assert tools.update_issue("A-1", summary="S", description="# d") == "OK"
    assert update.call_args == call(
        "A-1", summary="S", description={"adf": True}, parent_key=None
    )


def test_update_issue_rejects_description_and_from_file_together():
    with pytest.raises(ValueError, match="not both"):
        tools.update_issue("A-1", description="x", from_file="/tmp/y.md")


def test_update_issue_passes_parent(mocker: MockerFixture):
    update = mocker.patch.object(client, "update_issue")

    assert tools.update_issue("A-1", parent="A-2") == "OK"
    assert update.call_args == call(
        "A-1", summary=None, description=None, parent_key="A-2"
    )


def test_add_comment_converts_and_returns_ok(mocker: MockerFixture):
    add = mocker.patch.object(client, "add_comment")
    mocker.patch.object(tools, "to_adf", return_value={"adf": True})

    assert tools.add_comment("A-1", "hello") == "OK"
    assert add.call_args == call("A-1", body={"adf": True})


def test_add_worklog_converts_comment(mocker: MockerFixture):
    add = mocker.patch.object(client, "add_worklog")
    mocker.patch.object(tools, "to_adf", return_value={"adf": True})

    assert tools.add_worklog("A-1", "2h", comment="note") == "OK"
    assert add.call_args == call(
        "A-1", time_spent="2h", started=None, comment={"adf": True}
    )


# ---------------------------------------------------------------------------
# change_issue_type — hierarchy orchestration
# ---------------------------------------------------------------------------


@pytest.fixture
def change_type(mocker: MockerFixture) -> MagicMock:
    """Patch the lookups change_issue_type depends on; return the write mock."""
    mocker.patch.object(client, "list_issue_types", return_value=ALL_TYPES)
    return mocker.patch.object(client, "change_issue_type")


def test_change_issue_type_noop_when_same(
    mocker: MockerFixture, change_type: MagicMock
):
    mocker.patch.object(client, "get_issue", return_value=_issue("Task", 0))

    assert tools.change_issue_type("ABC-1", "Task") == "already 'Task'; no change"
    change_type.assert_not_called()


def test_change_issue_type_unknown_target(
    mocker: MockerFixture, change_type: MagicMock
):
    mocker.patch.object(client, "get_issue", return_value=_issue("Task", 0))

    with pytest.raises(ValueError, match="unknown issue type"):
        tools.change_issue_type("ABC-1", "Spaceship")


def test_change_issue_type_down_requires_parent(
    mocker: MockerFixture, change_type: MagicMock
):
    mocker.patch.object(client, "get_issue", return_value=_issue("Task", 0))

    with pytest.raises(ValueError, match="requires parent"):
        tools.change_issue_type("ABC-1", "Sub-task")


def test_change_issue_type_down_with_parent(
    mocker: MockerFixture, change_type: MagicMock
):
    mocker.patch.object(client, "get_issue", return_value=_issue("Task", 0))

    assert tools.change_issue_type("ABC-1", "Sub-task", parent="ABC-2") == "OK"
    assert change_type.call_args == call(
        "ABC-1", issue_type="Sub-task", parent_key="ABC-2"
    )


def test_change_issue_type_up_rejects_parent(
    mocker: MockerFixture, change_type: MagicMock
):
    mocker.patch.object(client, "get_issue", return_value=_issue("Task", 0))

    with pytest.raises(ValueError, match="takes no parent"):
        tools.change_issue_type("ABC-1", "Epic", parent="ABC-2")


def test_change_issue_type_up_clears_parent(
    mocker: MockerFixture, change_type: MagicMock
):
    mocker.patch.object(client, "get_issue", return_value=_issue("Task", 0))

    assert tools.change_issue_type("ABC-1", "Epic") == "OK"
    assert change_type.call_args == call("ABC-1", issue_type="Epic", clear_parent=True)


def test_change_issue_type_same_level_rejects_parent(
    mocker: MockerFixture, change_type: MagicMock
):
    mocker.patch.object(client, "get_issue", return_value=_issue("Task", 0))

    with pytest.raises(ValueError, match="same level"):
        tools.change_issue_type("ABC-1", "Story", parent="ABC-2")


def test_change_issue_type_same_level(mocker: MockerFixture, change_type: MagicMock):
    mocker.patch.object(client, "get_issue", return_value=_issue("Task", 0))

    assert tools.change_issue_type("ABC-1", "Story") == "OK"
    assert change_type.call_args == call("ABC-1", issue_type="Story")


def test_change_issue_type_rejects_multi_level_jump(
    mocker: MockerFixture, change_type: MagicMock
):
    mocker.patch.object(client, "get_issue", return_value=_issue("Sub-task", -1))

    with pytest.raises(ValueError, match="multiple hierarchy levels"):
        tools.change_issue_type("ABC-1", "Epic")


def test_change_issue_type_undeterminable_current(
    mocker: MockerFixture, change_type: MagicMock
):
    mocker.patch.object(client, "get_issue", return_value=_issue(None, None))

    with pytest.raises(ValueError, match="cannot determine the current type"):
        tools.change_issue_type("ABC-1", "Task")


def test_change_issue_type_target_without_hierarchy_level(mocker: MockerFixture):
    mocker.patch.object(client, "get_issue", return_value=_issue("Task", 0))
    mocker.patch.object(
        client,
        "list_issue_types",
        return_value=[IssueTypeDetails(name="Weird", hierarchy_level=None)],
    )
    mocker.patch.object(client, "change_issue_type")

    with pytest.raises(ValueError, match="cannot determine the hierarchy level"):
        tools.change_issue_type("ABC-1", "Weird")


# ---------------------------------------------------------------------------
# Write tools that return "OK"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("invoke", "client_attr"),
    [
        (lambda: tools.assign_issue("A-1", "acc"), "assign_issue"),
        (lambda: tools.delete_issue("A-1"), "delete_issue"),
        (lambda: tools.transition_issue("A-1", "31"), "transition_issue"),
        (lambda: tools.delete_comment("A-1", "c1"), "delete_comment"),
        (lambda: tools.create_issue_link("Blocks", "A-1", "A-2"), "create_issue_link"),
        (lambda: tools.remove_issue_link("l1"), "delete_issue_link"),
        (
            lambda: tools.delete_remote_issue_link("A-1", "l1"),
            "delete_remote_issue_link",
        ),
        (lambda: tools.add_watcher("A-1", "acc"), "add_watcher"),
        (lambda: tools.remove_watcher("A-1", "acc"), "remove_watcher"),
        (lambda: tools.delete_worklog("A-1", "w1"), "delete_worklog"),
        (lambda: tools.delete_version("v1"), "delete_version"),
        (lambda: tools.delete_sprint("1"), "delete_sprint"),
        (lambda: tools.move_to_backlog(["A-1"]), "move_to_backlog"),
        (lambda: tools.link_to_epic("E-1", ["A-1"]), "link_to_epic"),
        (lambda: tools.move_issues_to_sprint("1", ["A-1"]), "move_issues_to_sprint"),
        (lambda: tools.update_sprint("1", name="S2"), "update_sprint"),
        (lambda: tools.edit_comment("A-1", "c1", "x"), "update_comment"),
        (
            lambda: tools.create_remote_issue_link("A-1", "u", "t"),
            "create_remote_issue_link",
        ),
        (lambda: tools.update_worklog("A-1", "w1", time_spent="1h"), "update_worklog"),
        (lambda: tools.update_version("v1", name="2.0"), "update_version"),
    ],
)
def test_write_tools_return_ok(
    mocker: MockerFixture, invoke: Callable[[], object], client_attr: str
):
    client_mock = mocker.patch.object(client, client_attr, return_value=None)

    assert invoke() == "OK"
    client_mock.assert_called_once()


def test_create_version_returns_id(mocker: MockerFixture):
    mocker.patch.object(
        client, "create_version", return_value=ProjectVersion(id="10000")
    )

    assert tools.create_version("ABC", "1.0") == "10000"


def test_create_sprint_returns_id(mocker: MockerFixture):
    mocker.patch.object(client, "create_sprint", return_value=SprintBean(id=42))

    assert tools.create_sprint("7", "S1") == "42"


# ---------------------------------------------------------------------------
# Attachment file helpers
# ---------------------------------------------------------------------------


def test_download_attachment_writes_temp_file(mocker: MockerFixture):
    mocker.patch.object(
        client, "get_attachment_content", return_value=(b"\x89PNG", "image/png")
    )

    from pathlib import Path

    path = tools.download_attachment("42")
    try:
        assert path.endswith(".png")
        assert Path(path).read_bytes() == b"\x89PNG"
    finally:
        Path(path).unlink(missing_ok=True)


def test_upload_attachment_reads_file_then_calls_client(
    mocker: MockerFixture, tmp_path: Path
):
    f = tmp_path / "pic.png"
    f.write_bytes(b"img-bytes")
    add = mocker.patch.object(client, "add_attachment", return_value=[])

    tools.upload_attachment("A-1", str(f))

    assert add.call_args == call("A-1", b"img-bytes", "pic.png")


# ---------------------------------------------------------------------------
# Pass-through readers — delegate to client with mapped args, return its result
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("invoke", "client_attr", "expected"),
    [
        (lambda: tools.get_current_user(), "get_current_user", call()),
        (
            lambda: tools.list_projects(limit=10),
            "list_projects",
            call(start_at=0, max_results=10),
        ),
        (
            lambda: tools.get_project_versions("ABC", limit=10),
            "get_project_versions",
            call("ABC", start_at=0, max_results=10),
        ),
        (
            lambda: tools.get_project_components("ABC"),
            "get_project_components",
            call("ABC"),
        ),
        (
            lambda: tools.get_project_statuses("ABC"),
            "get_project_statuses",
            call("ABC"),
        ),
        (lambda: tools.list_issue_types(), "list_issue_types", call()),
        (
            lambda: tools.get_changelogs("A-1", limit=10),
            "get_changelogs",
            call("A-1", start_at=0, max_results=10),
        ),
        (
            lambda: tools.get_issue_type_metadata("ABC", limit=10),
            "get_issue_type_metadata",
            call("ABC", start_at=0, max_results=10),
        ),
        (lambda: tools.get_transitions("A-1"), "get_transitions", call("A-1")),
        (lambda: tools.get_link_types(), "get_link_types", call()),
        (
            lambda: tools.get_remote_issue_links("A-1"),
            "get_remote_issue_links",
            call("A-1"),
        ),
        (lambda: tools.get_watchers("A-1"), "get_watchers", call("A-1")),
        (
            lambda: tools.search_fields(query="q", limit=10),
            "search_fields",
            call(query="q", start_at=0, max_results=10),
        ),
        (
            lambda: tools.get_labels(limit=10),
            "get_labels",
            call(start_at=0, max_results=10),
        ),
        (
            lambda: tools.list_boards(project_key="ABC", limit=10),
            "list_boards",
            call(project_key="ABC", board_type=None, start_at=0, max_results=10),
        ),
        (lambda: tools.get_epic("E-1"), "get_epic", call("E-1")),
        (
            lambda: tools.list_sprints("7", state="active", limit=10),
            "list_sprints",
            call(7, state="active", start_at=0, max_results=10),
        ),
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


@pytest.mark.parametrize(
    ("invoke", "client_attr", "expected_id"),
    [
        (lambda: tools.get_backlog_issues("7"), "get_backlog_issues", 7),
        (lambda: tools.get_sprint_issues("9"), "get_sprint_issues", 9),
        (lambda: tools.get_epic_issues("E-1"), "get_epic_issues", "E-1"),
    ],
)
def test_issue_list_readers_strip_descriptions(
    mocker: MockerFixture,
    invoke: Callable[[], object],
    client_attr: str,
    expected_id: object,
):
    results = SearchResults(
        issues=[IssueBean(key="A-1", fields=JiraIssueFields(description={"x": 1}))]
    )
    delegate = mocker.patch.object(client, client_attr, return_value=results)

    out = invoke()

    assert delegate.call_args == call(expected_id, start_at=0, max_results=50)
    assert isinstance(out, SearchResults)
    first = out.issues[0].fields
    assert first is not None
    assert first.description is None


def test_update_issue_reads_from_file(mocker: MockerFixture, tmp_path: Path):
    body_file = tmp_path / "body.md"
    body_file.write_text("disk body")
    update = mocker.patch.object(client, "update_issue")
    to_adf = mocker.patch.object(tools, "to_adf", return_value={"adf": 1})

    assert tools.update_issue("A-1", from_file=str(body_file)) == "OK"
    assert to_adf.call_args == call("disk body")
    assert update.call_args == call(
        "A-1", summary=None, description={"adf": 1}, parent_key=None
    )
