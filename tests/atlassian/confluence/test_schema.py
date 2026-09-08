"""Tests for the Confluence schema layer.

The ConfluenceModel base mirrors JiraModel (camelCase aliasing, populate_by_name,
the None-dropping serializer). On top of that the schema absorbs two v2 response
quirks at parse time: ``Body`` unwraps ``body.atlas_doc_format.value`` and
``CursorPage`` lifts the next-page cursor out of ``_links.next``.
"""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from atlassian.confluence.schema.blog_post import BlogPost
from atlassian.confluence.schema.comment import Comment, MultiEntityResultComment
from atlassian.confluence.schema.page import MultiEntityResultPage, Page
from atlassian.confluence.schema.space import MultiEntityResultSpace, Space


# --- ConfluenceModel base behaviour ---


def test_camel_case_alias_parsing():
    page = Page.model_validate({"id": "p1", "spaceId": "s1", "parentId": "root"})

    assert page.space_id == "s1"
    assert page.parent_id == "root"


def test_populate_by_name_accepts_snake_case():
    assert Page.model_validate({"space_id": "s1"}).space_id == "s1"


def test_nested_version_parses():
    page = Page.model_validate({"id": "p1", "version": {"number": 3, "message": "x"}})

    assert page.version is not None
    assert page.version.number == 3
    assert page.version.message == "x"


def test_unknown_keys_ignored():
    assert Page.model_validate({"id": "p1", "mystery": 1}).id == "p1"


def test_serializer_drops_none_and_aliases():
    assert Space(id="1").model_dump(by_alias=True) == {"id": "1"}


def test_serializer_keeps_empty_results_drops_none_cursor():
    dumped = MultiEntityResultSpace().model_dump()

    assert dumped == {"results": []}  # cursor (None) dropped, [] kept


# --- Body ---


def test_body_unwraps_v2_json_string_value():
    raw = {"body": {"atlas_doc_format": {"value": json.dumps({"type": "doc"})}}}

    assert Page.model_validate(raw).body == {"type": "doc"}


def test_body_unwraps_v2_dict_value():
    raw = {"body": {"atlas_doc_format": {"value": {"type": "doc"}}}}

    assert Page.model_validate(raw).body == {"type": "doc"}


def test_body_passes_through_bare_adf_and_markdown():
    assert Page.model_validate({"body": {"type": "doc"}}).body == {"type": "doc"}
    assert Page.model_validate({"body": "plain"}).body == "plain"
    assert Page(body={"type": "doc"}).body == {"type": "doc"}


@pytest.mark.parametrize(
    "body",
    [None, {}, {"atlas_doc_format": {}}, {"atlas_doc_format": {"value": ""}}],
)
def test_body_none_when_absent_or_empty(body: object):
    assert Page.model_validate({"body": body}).body is None
    assert Page.model_validate({}).body is None


def test_body_applies_to_every_content_model():
    raw = {"atlas_doc_format": {"value": json.dumps({"type": "doc"})}}

    assert BlogPost.model_validate({"body": raw}).body == {"type": "doc"}
    assert Comment.model_validate({"body": raw}).body == {"type": "doc"}


# --- CursorPage ---


def test_cursor_read_from_next_link():
    raw: dict[str, Any] = {
        "results": [],
        "_links": {"next": "/wiki/api/v2/spaces?cursor=ABC&limit=25"},
    }

    assert MultiEntityResultSpace.model_validate(raw).cursor == "ABC"


@pytest.mark.parametrize(
    "links",
    [{}, {"next": ""}, {"next": "/wiki/api/v2/spaces?limit=25"}],
)
def test_cursor_none_without_usable_next_link(links: dict[str, str]):
    assert MultiEntityResultSpace.model_validate({"_links": links}).cursor is None
    assert MultiEntityResultSpace.model_validate({}).cursor is None


def test_explicit_cursor_wins_over_links():
    raw = {"cursor": "GIVEN", "_links": {"next": "/x?cursor=LINK"}}

    assert MultiEntityResultSpace.model_validate(raw).cursor == "GIVEN"


def test_page_list_parses_nested_bodies_and_cursor():
    raw = {
        "results": [
            {
                "id": "p1",
                "body": {"atlas_doc_format": {"value": json.dumps({"type": "doc"})}},
            },
            {"id": "p2"},
        ],
        "_links": {"next": "/x?cursor=NEXT&limit=25"},
    }

    result = MultiEntityResultPage.model_validate(raw)

    assert [p.id for p in result.results] == ["p1", "p2"]
    assert result.results[0].body == {"type": "doc"}
    assert result.results[1].body is None
    assert result.cursor == "NEXT"


def test_comment_list_parses_nested_bodies():
    doc = json.dumps({"type": "doc"})
    raw = {"results": [{"id": "c1", "body": {"atlas_doc_format": {"value": doc}}}]}

    assert MultiEntityResultComment.model_validate(raw).results[0].body == {
        "type": "doc"
    }


def test_cursor_validator_leaves_non_dict_input_to_pydantic():
    with pytest.raises(ValidationError):
        MultiEntityResultSpace.model_validate(["not", "a", "dict"])
