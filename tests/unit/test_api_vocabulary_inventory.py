from typing import Any

import pytest

from scripts.api_vocabulary_inventory import (
    _extract_fields,
    _extract_request_fields,
    _fallback_example,
    _schema_type,
    app,
    build_inventory,
)


@pytest.mark.parametrize("composition", ["anyOf", "oneOf"])
@pytest.mark.parametrize("primitive", ["string", "integer", "number", "boolean", "array"])
@pytest.mark.parametrize("null_first", [False, True])
def test_schema_type_extracts_single_nullable_primitive(
    composition: str, primitive: str, null_first: bool
) -> None:
    variant: dict[str, Any] = {"type": primitive}
    if primitive == "array":
        variant["items"] = {"type": "string"}
    variants = [variant, {"type": "null", "title": "Absent"}]
    if null_first:
        variants.reverse()

    assert _schema_type({composition: variants}) == primitive
    assert _schema_type({composition: [variant]}) == primitive


@pytest.mark.parametrize("composition", ["anyOf", "oneOf"])
@pytest.mark.parametrize(
    "variants",
    [
        [{"type": "object", "properties": {"value": {"type": "string"}}}, {"type": "null"}],
        [{"$ref": "#/components/schemas/SourceRecord"}, {"type": "null"}],
        [{"type": "string"}, {"type": "integer"}, {"type": "null"}],
        [{"type": "string"}, {"type": "object"}],
        [{"type": "string"}, {"$ref": "#/components/schemas/SourceRecord"}],
        [{"type": "string"}, {"type": "string"}],
        [{"type": "string"}, {}],
        [{"type": "string"}, False],
        [],
        [{"type": "null"}],
        [{"type": "null"}, {"type": "null"}],
    ],
)
def test_schema_type_preserves_object_and_ambiguous_compositions(
    composition: str, variants: list[Any]
) -> None:
    assert _schema_type({composition: variants}) == "object"


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"type": "string"}, "string"),
        ({"type": "object"}, "object"),
        ({"$ref": "#/components/schemas/SourceRecord"}, "SourceRecord"),
        ({"$ref": "#/components/schemas/SourceRecord", "type": "string"}, "SourceRecord"),
        ({"type": "object", "anyOf": [{"type": "string"}, {"type": "null"}]}, "object"),
        ({"allOf": [{"type": "string"}, {"type": "null"}]}, "object"),
        ({"anyOf": {"type": "string"}}, "object"),
        ({}, "object"),
    ],
)
def test_schema_type_preserves_direct_and_unsupported_schemas(
    schema: dict[str, Any], expected: str
) -> None:
    assert _schema_type(schema) == expected


@pytest.mark.parametrize(
    ("schema_name", "field_name"),
    [
        ("DpmSourceProductLineage", "source_record_id"),
        ("AuthoritativeClientRestrictionRule", "source_record_id"),
        ("AuthoritativeSustainabilityPreference", "source_record_id"),
        ("LineageData", "source_system"),
    ],
)
def test_native_openapi_extraction_keeps_nullable_source_fields_scalar(
    schema_name: str, field_name: str
) -> None:
    components = app.openapi()["components"]
    schema = components["schemas"][schema_name]
    declaration = schema["properties"][field_name]
    assert declaration["anyOf"] == [{"type": "string"}, {"type": "null"}]

    fields = _extract_fields(schema, components=components)
    field = next(item for item in fields if item["name"] == field_name)
    assert field["type"] == "string"
    assert field["required"] is False
    assert field["semanticId"] == f"lotus.{field_name}"
    assert field["example"] == declaration["example"]
    assert isinstance(field["example"], str)


def test_native_inventory_publishes_scalar_source_identifiers() -> None:
    inventory = build_inventory()
    catalog = {item["semanticId"]: item for item in inventory["attributeCatalog"]}
    for semantic_id in ("lotus.source_record_id", "lotus.source_system"):
        assert catalog[semantic_id]["type"] == "string"
        assert catalog[semantic_id]["observedTypes"] == ["string"]
        assert isinstance(catalog[semantic_id]["example"], str)

    source_fields = [
        field
        for endpoint in inventory["endpoints"]
        for direction in ("request", "response")
        for field in endpoint[direction]["fields"]
        if field["semanticId"] in ("lotus.source_record_id", "lotus.source_system")
    ]
    assert source_fields
    assert all(field["type"] == "string" for field in source_fields)


@pytest.mark.parametrize("composition", ["anyOf", "oneOf"])
@pytest.mark.parametrize("null_first", [False, True])
@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        ({"type": "string"}, "STANDARD_VALUE"),
        ({"type": "integer"}, 1),
        ({"type": "number"}, 0.1),
        ({"type": "boolean"}, True),
        ({"type": "array", "items": {"type": "string"}}, ["STANDARD_VALUE"]),
    ],
)
def test_nullable_fallback_examples_match_primitive_types(
    composition: str, null_first: bool, variant: dict[str, Any], expected: Any
) -> None:
    variants = [variant, {"type": "null"}]
    if null_first:
        variants.reverse()
    example = _fallback_example("option", {composition: variants})
    assert example == expected
    assert type(example) is type(expected)


@pytest.mark.parametrize("composition", ["anyOf", "oneOf"])
@pytest.mark.parametrize("null_first", [False, True])
@pytest.mark.parametrize(
    ("variant", "expected"),
    [
        ({"type": "string", "enum": ["USD", "SGD"]}, "USD"),
        ({"type": "integer", "enum": [0, 2]}, 0),
        ({"type": "number", "enum": [0.25, 0.75]}, 0.25),
        ({"type": "boolean", "enum": [False]}, False),
        ({"type": "string", "format": "date"}, "2025-03-31"),
        ({"type": "string", "format": "date-time"}, "2025-03-31T00:00:00Z"),
        ({"type": "array", "enum": [["SELECTED"]]}, ["SELECTED"]),
        ({"type": "array", "items": {"type": "integer"}}, [1]),
        ({"type": "array", "items": {"type": "boolean", "enum": [False]}}, [False]),
        ({"type": "array", "items": {"type": "string", "enum": ["SELECTED"]}}, ["SELECTED"]),
        ({"type": "array", "items": {"type": "string", "format": "date"}}, ["2025-03-31"]),
        ({"type": "array", "items": {"type": "integer", "example": 17}}, [17]),
        (
            {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
            [[0.1]],
        ),
    ],
)
def test_nullable_fallback_examples_use_branch_enum_format_and_items(
    composition: str, null_first: bool, variant: dict[str, Any], expected: Any
) -> None:
    variants = [variant, {"type": "null"}]
    if null_first:
        variants.reverse()
    example = _fallback_example("option", {composition: variants})
    assert example == expected
    assert type(example) is type(expected)


@pytest.mark.parametrize("composition", ["anyOf", "oneOf"])
@pytest.mark.parametrize(
    ("variant", "explicit"),
    [
        ({"type": "string"}, ""),
        ({"type": "integer"}, 0),
        ({"type": "number"}, 0.0),
        ({"type": "boolean"}, False),
        ({"type": "array", "items": {"type": "string"}}, []),
    ],
)
def test_explicit_nullable_examples_preserve_false_zero_and_empty_values(
    composition: str, variant: dict[str, Any], explicit: Any
) -> None:
    schema = {composition: [variant, {"type": "null"}], "example": explicit}
    fields = _extract_fields({"type": "object", "properties": {"option": schema}}, components={})
    assert fields[0]["example"] == explicit
    assert type(fields[0]["example"]) is type(explicit)
    _, controls = _extract_request_fields(
        {"parameters": [{"name": "option", "in": "query", "schema": schema, "example": explicit}]},
        {},
    )
    assert controls[0]["example"] == explicit
    assert type(controls[0]["example"]) is type(explicit)
    assert _fallback_example("option", schema) == explicit
    assert (
        _fallback_example(
            "option", {composition: [{**variant, "example": explicit}, {"type": "null"}]}
        )
        == explicit
    )


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"type": "boolean"}, True),
        ({"type": "integer"}, 1),
        ({"type": "number"}, 0.1),
        ({"type": "string"}, "STANDARD_VALUE"),
        ({"type": "array", "items": {"type": "integer"}}, ["VALUE"]),
        ({"type": "object"}, {"key": "value"}),
        ({"$ref": "#/components/schemas/SourceRecord"}, "STANDARD_VALUE"),
        ({"anyOf": [{"type": "string"}, {"type": "integer"}]}, "STANDARD_VALUE"),
        ({"oneOf": [{"type": "boolean"}, {"type": "boolean"}]}, "STANDARD_VALUE"),
        ({"anyOf": [{"type": "object"}, {"type": "null"}]}, "STANDARD_VALUE"),
        (
            {"oneOf": [{"$ref": "#/components/schemas/SourceRecord"}, {"type": "null"}]},
            "STANDARD_VALUE",
        ),
        ({"allOf": [{"type": "boolean"}, {"type": "null"}]}, "STANDARD_VALUE"),
        ({"anyOf": [{"type": "null"}]}, "STANDARD_VALUE"),
        ({"oneOf": []}, "STANDARD_VALUE"),
        ({"anyOf": [{"type": "boolean"}, False]}, "STANDARD_VALUE"),
        ({"type": "object", "anyOf": [{"type": "boolean"}, {"type": "null"}]}, {"key": "value"}),
    ],
)
def test_fallback_examples_preserve_direct_and_unsupported_behavior(
    schema: dict[str, Any], expected: Any
) -> None:
    assert _fallback_example("option", schema) == expected


@pytest.mark.parametrize(
    ("name", "expected_type", "example_type"),
    [("enabled", "boolean", bool), ("portfolio_ids", "array", list)],
)
def test_native_nullable_query_controls_publish_examples_of_the_declared_type(
    name: str, expected_type: str, example_type: type
) -> None:
    matched = []
    for methods in app.openapi()["paths"].values():
        for operation in methods.values():
            for parameter in operation.get("parameters", []):
                if parameter["name"] != name:
                    continue
                assert parameter.get("example") is None
                _, controls = _extract_request_fields({"parameters": [parameter]}, {})
                control = controls[0]
                assert control["type"] == expected_type
                assert type(control["example"]) is example_type
                if name == "portfolio_ids":
                    assert control["example"]
                    assert all(isinstance(item, str) for item in control["example"])
                matched.append(control)
    assert matched

    controls = [item for item in build_inventory()["controlsCatalog"] if item["name"] == name]
    assert controls
    assert all(type(item["example"]) is example_type for item in controls)
