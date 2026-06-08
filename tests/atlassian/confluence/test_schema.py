"""Tests for the Confluence schema layer and the client's pure parse helpers.

The ConfluenceModel base mirrors JiraModel (camelCase aliasing, populate_by_name,
the None-dropping serializer). The cursor / ADF-body extraction helpers in
``confluence.client`` are pure functions and are unit-tested here directly.
"""

import json

from atlassian.confluence.client import (
    _extract_adf_body,
    _extract_cursor,
    _parse_blog_post,
    _parse_page,
    _parse_page_list,
)
from atlassian.confluence.schema.page import Page
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


def test_body_accepts_adf_and_string():
    assert Page.model_validate({"body": {"type": "doc"}}).body == {"type": "doc"}
    assert Page.model_validate({"body": "plain"}).body == "plain"


def test_unknown_keys_ignored():
    assert Page.model_validate({"id": "p1", "mystery": 1}).id == "p1"


def test_serializer_drops_none_and_aliases():
    assert Space(id="1").model_dump(by_alias=True) == {"id": "1"}


def test_serializer_keeps_empty_results_drops_none_cursor():
    dumped = MultiEntityResultSpace().model_dump()

    assert dumped == {"results": []}  # cursor (None) dropped, [] kept


# --- _extract_cursor ---


def test_extract_cursor_reads_cursor_query_param():
    data = {"_links": {"next": "/wiki/api/v2/spaces?cursor=ABC123&limit=25"}}

    assert _extract_cursor(data) == "ABC123"


def test_extract_cursor_none_when_no_cursor_in_next():
    assert _extract_cursor({"_links": {"next": "/wiki/api/v2/spaces?limit=25"}}) is None


def test_extract_cursor_none_when_no_next():
    assert _extract_cursor({"_links": {}}) is None
    assert _extract_cursor({}) is None
    assert _extract_cursor({"_links": {"next": ""}}) is None


# --- _extract_adf_body ---


def test_extract_adf_body_parses_json_string_value():
    data = {"body": {"atlas_doc_format": {"value": json.dumps({"type": "doc"})}}}

    assert _extract_adf_body(data) == {"type": "doc"}


def test_extract_adf_body_passes_through_dict_value():
    data = {"body": {"atlas_doc_format": {"value": {"type": "doc"}}}}

    assert _extract_adf_body(data) == {"type": "doc"}


def test_extract_adf_body_none_when_missing():
    assert _extract_adf_body({}) is None
    assert _extract_adf_body({"body": None}) is None
    assert _extract_adf_body({"body": {}}) is None
    assert _extract_adf_body({"body": {"atlas_doc_format": {}}}) is None
    assert _extract_adf_body({"body": {"atlas_doc_format": {"value": ""}}}) is None


# --- _parse_page / _parse_page_list / _parse_blog_post ---


def test_parse_page_extracts_adf_body():
    data = {
        "id": "p1",
        "title": "T",
        "body": {"atlas_doc_format": {"value": json.dumps({"type": "doc"})}},
    }

    page = _parse_page(data)

    assert isinstance(page, Page)
    assert page.body == {"type": "doc"}


def test_parse_page_list_parses_results_and_cursor():
    data = {
        "results": [
            {
                "id": "p1",
                "body": {"atlas_doc_format": {"value": json.dumps({"type": "doc"})}},
            },
            {"id": "p2"},
        ],
        "_links": {"next": "/x?cursor=NEXT&limit=25"},
    }

    result = _parse_page_list(data)

    assert [p.id for p in result.results] == ["p1", "p2"]
    assert result.results[0].body == {"type": "doc"}
    assert result.results[1].body is None
    assert result.cursor == "NEXT"


def test_parse_blog_post_extracts_adf_body():
    data = {
        "id": "b1",
        "body": {"atlas_doc_format": {"value": json.dumps({"type": "doc"})}},
    }

    post = _parse_blog_post(data)

    assert post.id == "b1"
    assert post.body == {"type": "doc"}
