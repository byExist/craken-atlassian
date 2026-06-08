"""Tests for atlassian.jira.permissions — bind-time write-tool gating."""

from pytest_mock import MockerFixture

from atlassian.jira import client as jira_client
from atlassian.jira import permissions
from atlassian.jira import tools as jira_tools
from atlassian.jira.schema.permission import Permissions, UserPermission


def _permissions(**have: bool | None) -> Permissions:
    return Permissions(
        permissions={
            key: UserPermission(key=key, have_permission=value)
            for key, value in have.items()
        }
    )


# --- _TOOL_PERMISSION mapping integrity ---


def test_every_mapped_tool_exists_and_is_a_write_tool():
    for tool_name, perm_key in permissions._TOOL_PERMISSION.items():
        fn = getattr(jira_tools, tool_name, None)
        assert callable(fn), f"{tool_name} is not a jira tool"
        assert perm_key.isupper(), f"{perm_key} is not a permission constant"


# --- globally_unavailable ---


def test_globally_unavailable_returns_only_false_everywhere(mocker: MockerFixture):
    captured: dict[str, list[str]] = {}

    def fake(keys: list[str], **kwargs: object) -> Permissions:
        captured["keys"] = keys
        return _permissions(
            CREATE_ISSUES=False,  # lacking everywhere -> reported
            EDIT_ISSUES=True,  # has it somewhere -> excluded
            DELETE_ISSUES=None,  # unknown -> excluded
            # ASSIGN_ISSUES absent from response -> excluded
        )

    mocker.patch.object(jira_client, "get_my_permissions", fake)

    result = permissions.globally_unavailable()

    assert result == {"CREATE_ISSUES"}
    # It queries the deduplicated, sorted set of every mapped permission.
    assert captured["keys"] == sorted(set(permissions._TOOL_PERMISSION.values()))


def test_globally_unavailable_empty_when_all_held(mocker: MockerFixture):
    held = set(permissions._TOOL_PERMISSION.values())

    def all_held(keys: list[str], **kwargs: object) -> Permissions:
        return _permissions(**dict.fromkeys(held, True))

    mocker.patch.object(jira_client, "get_my_permissions", all_held)

    assert permissions.globally_unavailable() == set()


def test_globally_unavailable_swallows_lookup_failure(mocker: MockerFixture):
    def boom(keys: list[str], **kwargs: object) -> Permissions:
        raise RuntimeError("no credentials")

    mocker.patch.object(jira_client, "get_my_permissions", boom)

    # A failed lookup must not crash bind time; gating is simply skipped.
    assert permissions.globally_unavailable() == set()


# --- describe ---


def test_describe_appends_note_when_permission_unavailable():
    doc = permissions.describe(jira_tools.create_issue, {"CREATE_ISSUES"})

    assert "NOT PERMITTED" in doc
    assert "CREATE_ISSUES" in doc
    # Original docstring is preserved ahead of the note.
    assert doc.startswith((jira_tools.create_issue.__doc__ or "").rstrip())


def test_describe_returns_plain_docstring_when_permission_available():
    doc = permissions.describe(jira_tools.create_issue, set())

    assert "NOT PERMITTED" not in doc
    assert doc == (jira_tools.create_issue.__doc__ or "").rstrip()


def test_describe_ignores_unmapped_tools():
    # get_issue has no entry in _TOOL_PERMISSION, so it never gets a note.
    doc = permissions.describe(jira_tools.get_issue, {"CREATE_ISSUES", "EDIT_ISSUES"})

    assert "NOT PERMITTED" not in doc
    assert doc == (jira_tools.get_issue.__doc__ or "").rstrip()


def test_describe_handles_missing_docstring():
    def delete_issue():  # name matches a mapped tool; no docstring
        pass

    doc = permissions.describe(delete_issue, {"DELETE_ISSUES"})

    assert "NOT PERMITTED" in doc
    assert "DELETE_ISSUES" in doc
