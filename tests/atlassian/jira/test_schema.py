"""Tests for the JIRA pydantic schema layer.

Focuses on the cross-cutting JiraModel behaviour (camelCase aliasing,
``populate_by_name``, the None-dropping serializer, ignoring unknown keys) and
the trickier issue/permission models — these guarantees hold for every model
built on JiraModel.
"""

from atlassian.jira.schema.issue import (
    IssueBean,
    JiraIssueFields,
    SearchAndReconcileResults,
)
from atlassian.jira.schema.permission import Permissions
from atlassian.jira.schema.user import User


# --- aliasing & populate_by_name ---


def test_camel_case_alias_parsing():
    user = User.model_validate({"accountId": "acc-1", "displayName": "Dev"})

    assert user.account_id == "acc-1"
    assert user.display_name == "Dev"


def test_populate_by_name_accepts_snake_case():
    user = User.model_validate({"account_id": "acc-1"})

    assert user.account_id == "acc-1"


def test_explicit_validation_alias_overrides_generated_one():
    fields = JiraIssueFields.model_validate(
        {
            "issuetype": {"name": "Bug"},
            "resolutiondate": "2026-01-01",
            "issuelinks": [],
        }
    )

    assert fields.issue_type is not None
    assert fields.issue_type.name == "Bug"
    assert fields.resolution_date == "2026-01-01"
    assert fields.issue_links == []


def test_unknown_keys_are_ignored():
    issue = IssueBean.model_validate({"key": "A-1", "somethingNew": 123})

    assert issue.key == "A-1"


def test_empty_payload_validates():
    assert IssueBean.model_validate({}).key is None


# --- ADF | str union on rich-text fields ---


def test_description_accepts_adf_dict():
    fields = JiraIssueFields.model_validate({"description": {"type": "doc"}})

    assert fields.description == {"type": "doc"}


def test_description_accepts_plain_string():
    fields = JiraIssueFields.model_validate({"description": "agile plain text"})

    assert fields.description == "agile plain text"


# --- None-dropping serializer ---


def test_serializer_drops_none_keys_with_alias():
    dumped = User(account_id="acc-1").model_dump(by_alias=True)

    assert dumped == {"accountId": "acc-1"}  # displayName (None) omitted


def test_serializer_uses_snake_case_without_alias():
    dumped = User(account_id="acc-1", display_name="Dev").model_dump()

    assert dumped == {"account_id": "acc-1", "display_name": "Dev"}


def test_serializer_keeps_empty_collections():
    dumped = JiraIssueFields(summary="S").model_dump(by_alias=True)

    assert dumped["summary"] == "S"
    assert dumped["labels"] == []  # [] signals "fetched, none present"
    assert "description" not in dumped  # None dropped
    assert "status" not in dumped


# --- nested models & pagination ---


def test_nested_models_parse():
    issue = IssueBean.model_validate(
        {
            "key": "A-1",
            "fields": {
                "summary": "S",
                "status": {"name": "Open"},
                "assignee": {"accountId": "u-1"},
            },
        }
    )

    fields = issue.fields
    assert fields is not None
    assert fields.summary == "S"
    assert fields.status is not None
    assert fields.status.name == "Open"
    assert fields.assignee is not None
    assert fields.assignee.account_id == "u-1"


def test_search_and_reconcile_results_aliases():
    result = SearchAndReconcileResults.model_validate(
        {"issues": [{"key": "A-1"}], "nextPageToken": "tok", "isLast": False}
    )

    assert result.issues[0].key == "A-1"
    assert result.next_page_token == "tok"
    assert result.is_last is False


def test_permissions_map_parses_have_permission():
    perms = Permissions.model_validate(
        {
            "permissions": {
                "CREATE_ISSUES": {"key": "CREATE_ISSUES", "havePermission": True}
            }
        }
    )

    assert perms.permissions["CREATE_ISSUES"].have_permission is True
