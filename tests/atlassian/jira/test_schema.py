"""Tests for the JIRA pydantic schema layer.

Focuses on the cross-cutting JiraModel behaviour (camelCase aliasing,
``populate_by_name``, the None-dropping serializer, ignoring unknown keys) and
the trickier issue/permission models — these guarantees hold for every model
built on JiraModel.
"""

from collections.abc import Callable

import pytest
from pydantic import ValidationError

import payloads
from atlassian.jira.schema.base import JiraModel
from atlassian.jira.schema.common import IssueTypeWithStatus
from atlassian.jira.schema.field import FieldDetail
from atlassian.jira.schema.field_meta import FieldCreateMetadata
from atlassian.jira.schema.issue import (
    IssueBean,
    JiraIssueFields,
    SearchAndReconcileResults,
)
from atlassian.jira.schema.issue_link import IssueLink
from atlassian.jira.schema.permission import Permissions
from atlassian.jira.schema.remote_link import RemoteObject
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


def test_attachment_list_is_typed_when_present():
    fields = JiraIssueFields.model_validate(
        {
            "attachment": [
                {
                    "id": "334569",
                    "filename": "bounce-loading.gif",
                    "mimeType": "image/gif",
                    "size": 117101,
                    "self": "https://example/rest/api/3/attachment/334569",
                }
            ]
        }
    )

    assert fields.attachment is not None
    dumped = fields.model_dump(by_alias=True)["attachment"]
    assert dumped == [
        {
            "id": "334569",
            "filename": "bounce-loading.gif",
            "mimeType": "image/gif",
            "size": 117101,
        }
    ]


def test_attachment_is_omitted_when_not_requested():
    dumped = JiraIssueFields.model_validate({"summary": "s"}).model_dump(by_alias=True)

    assert "attachment" not in dumped


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


def test_jql_constants_keep_ids():
    """Names come back translated and JQL only matches them by id."""
    fields = JiraIssueFields.model_validate(
        {
            "status": {"self": "s", "id": "6", "name": "종료"},
            "priority": {"self": "p", "id": "3", "name": "주요"},
            "resolution": {
                "self": "r",
                "id": "6",
                "description": "Verified on Production",
                "name": "배포 되어 확인 함",
            },
        }
    )

    dumped = fields.model_dump(by_alias=True)
    assert dumped["status"] == {"id": "6", "name": "종료"}
    assert dumped["priority"] == {"id": "3", "name": "주요"}
    assert dumped["resolution"] == {"id": "6", "name": "배포 되어 확인 함"}


def test_unresolved_issue_omits_resolution():
    dumped = JiraIssueFields.model_validate({"resolution": None}).model_dump(
        by_alias=True
    )

    assert "resolution" not in dumped


def test_search_and_reconcile_results_aliases():
    result = SearchAndReconcileResults.model_validate(
        {"issues": [{"key": "A-1"}], "nextPageToken": "tok", "isLast": False}
    )

    assert result.issues[0].key == "A-1"
    assert result.next_page_token == "tok"
    assert result.is_last is False


# --- requiredness contract ---


@pytest.mark.parametrize(
    ("model", "build", "required"),
    [
        (RemoteObject, payloads.remote_object, ("url", "title")),
        (IssueTypeWithStatus, payloads.issue_type_with_status, ("name", "statuses")),
        (IssueLink, payloads.issue_link, ("type",)),
    ],
)
def test_required_fields(
    model: type[JiraModel],
    build: Callable[[], dict[str, object]],
    required: tuple[str, ...],
):
    model.model_validate(build())  # minimal payload parses
    for field in required:
        payload = build()
        del payload[field]
        with pytest.raises(ValidationError):
            model.model_validate(payload)


def test_field_schema_keeps_wire_name_schema():
    detail = FieldDetail.model_validate(
        {"id": "customfield_1", "schema": {"type": "string", "custom": "x:textarea"}}
    )

    assert detail.field_schema is not None
    assert detail.field_schema.custom == "x:textarea"
    assert detail.model_dump(by_alias=True)["schema"] == {
        "type": "string",
        "custom": "x:textarea",
    }


@pytest.mark.parametrize("missing", ["fieldId", "key", "name", "required", "schema"])
def test_field_create_metadata_requires_spec_required_fields(missing: str):
    payload: dict[str, object] = {
        "fieldId": "summary",
        "key": "summary",
        "name": "Summary",
        "required": True,
        "schema": {"type": "string"},
    }
    FieldCreateMetadata.model_validate(payload)
    del payload[missing]
    with pytest.raises(ValidationError):
        FieldCreateMetadata.model_validate(payload)


def test_issue_link_carries_one_direction():
    """Spec marks inward+outward required, but each link has exactly one."""
    inward = IssueLink.model_validate(payloads.issue_link(inwardIssue={"key": "A-1"}))
    outward = IssueLink.model_validate(payloads.issue_link(outwardIssue={"key": "A-2"}))

    assert inward.inward_issue is not None and inward.outward_issue is None
    assert outward.outward_issue is not None and outward.inward_issue is None


def test_permissions_map_parses_have_permission():
    perms = Permissions.model_validate(
        {
            "permissions": {
                "CREATE_ISSUES": {"key": "CREATE_ISSUES", "havePermission": True}
            }
        }
    )

    assert perms.permissions["CREATE_ISSUES"].have_permission is True
