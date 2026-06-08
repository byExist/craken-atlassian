"""Tests for atlassian.server — tool registration, write gating, describe wiring.

server.py registers tools at import time based on ``config.write_enabled`` and,
for Jira writes, the globally-unavailable permission set. The module is reloaded
under controlled settings; ``globally_unavailable`` is patched so the reload never
touches the network.
"""

import importlib

from pytest_mock import MockerFixture

# Representative tools per category.
JIRA_READ = ["jira_get_issue", "jira_search_issues", "jira_get_current_user"]
CONFLUENCE_READ = ["confluence_get_page", "confluence_search_content"]
JIRA_WRITE = ["jira_create_issue", "jira_update_issue", "jira_delete_issue"]
CONFLUENCE_WRITE = ["confluence_create_page", "confluence_delete_page"]


def _tool_map(
    mocker: MockerFixture,
    *,
    write_enabled: bool,
    unavailable: set[str] | None = None,
) -> dict[str, str]:
    """Reload server.py under the given settings; return {tool_name: description}."""
    import atlassian.server as server_module
    from atlassian.config import config
    from atlassian.jira import permissions

    mocker.patch.object(config, "write_enabled", write_enabled)
    mocker.patch.object(
        permissions, "globally_unavailable", lambda: unavailable or set()
    )
    server_module = importlib.reload(server_module)
    return {
        tool.name: tool.description or ""
        for tool in server_module.mcp._tool_manager.list_tools()
    }


# --- read-only vs write-enabled binding ---


def test_read_tools_present_in_read_only_session(mocker: MockerFixture):
    tools = _tool_map(mocker, write_enabled=False)

    for name in JIRA_READ + CONFLUENCE_READ:
        assert name in tools


def test_write_tools_absent_in_read_only_session(mocker: MockerFixture):
    tools = _tool_map(mocker, write_enabled=False)

    for name in JIRA_WRITE + CONFLUENCE_WRITE:
        assert name not in tools


def test_write_tools_present_when_enabled(mocker: MockerFixture):
    tools = _tool_map(mocker, write_enabled=True)

    for name in JIRA_WRITE + CONFLUENCE_WRITE:
        assert name in tools


def test_enabling_writes_only_adds_tools(mocker: MockerFixture):
    read_only = set(_tool_map(mocker, write_enabled=False))
    enabled = set(_tool_map(mocker, write_enabled=True))

    assert read_only < enabled  # strict superset; reads never disappear


def test_all_tools_are_namespaced(mocker: MockerFixture):
    tools = _tool_map(mocker, write_enabled=True)

    assert tools  # sanity: something registered
    assert all(name.startswith(("jira_", "confluence_")) for name in tools)
    assert all(desc for desc in tools.values())  # every tool keeps its docstring


# --- permission gating via describe() ---


def test_unavailable_permission_marks_matching_tool(mocker: MockerFixture):
    tools = _tool_map(mocker, write_enabled=True, unavailable={"CREATE_ISSUES"})

    assert "NOT PERMITTED" in tools["jira_create_issue"]
    assert "CREATE_ISSUES" in tools["jira_create_issue"]


def test_one_permission_marks_all_tools_that_need_it(mocker: MockerFixture):
    # EDIT_ISSUES backs both update_issue and change_issue_type.
    tools = _tool_map(mocker, write_enabled=True, unavailable={"EDIT_ISSUES"})

    assert "NOT PERMITTED" in tools["jira_update_issue"]
    assert "NOT PERMITTED" in tools["jira_change_issue_type"]
    # A different permission is unaffected.
    assert "NOT PERMITTED" not in tools["jira_create_issue"]


def test_unmapped_write_tool_is_never_marked(mocker: MockerFixture):
    # delete_comment has no _TOOL_PERMISSION entry -> always falls back to 403.
    tools = _tool_map(mocker, write_enabled=True, unavailable={"CREATE_ISSUES"})

    assert "NOT PERMITTED" not in tools["jira_delete_comment"]


def test_no_marks_when_all_permissions_available(mocker: MockerFixture):
    tools = _tool_map(mocker, write_enabled=True, unavailable=set())

    assert "NOT PERMITTED" not in tools["jira_create_issue"]
    assert "NOT PERMITTED" not in tools["jira_update_issue"]


def test_confluence_writes_are_never_gated(mocker: MockerFixture):
    # Confluence has no bind-time gating; even with Jira gating active its
    # write tools carry their plain docstrings.
    tools = _tool_map(mocker, write_enabled=True, unavailable={"CREATE_ISSUES"})

    assert "NOT PERMITTED" not in tools["confluence_create_page"]
