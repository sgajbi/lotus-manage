import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from scripts.api_vocabulary_inventory import (
    _extract_fields,
    _extract_request_fields,
    _fallback_example,
    _schema_type,
    app,
    build_inventory,
    validate_inventory,
)
from src.core.rebalance_runs import models as run_models


@pytest.mark.parametrize("name", ["artifact", "async_operation", "idempotency_history"])
def test_native_declared_null_examples_survive_inventory_extraction(name: str) -> None:
    components = app.openapi()["components"]
    schema = components["schemas"]["DpmRunSupportBundleResponse"]
    declaration = schema["properties"][name]
    assert declaration["examples"] == [None]
    assert "example" in declaration and declaration["example"] is None
    assert {"type": "null"} in declaration["anyOf"]
    adapter = TypeAdapter(
        run_models.DpmRunSupportBundleResponse.model_fields[name].rebuild_annotation()
    )
    adapter.rebuild(_types_namespace=vars(run_models))
    assert adapter.validate_json("null", strict=True) is None
    with pytest.raises(ValidationError):
        adapter.validate_json('"STANDARD_VALUE"', strict=True)

    fields = _extract_fields(schema, components=components)
    assert next(field for field in fields if field["name"] == name)["example"] is None
    attributes = {row["semanticId"]: row for row in build_inventory()["attributeCatalog"]}
    assert attributes[f"lotus.{name}"]["example"] is None


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ({"type": "string", "example": ""}, ""),
        ({"type": "boolean", "example": False}, False),
        ({"type": "integer", "example": 0}, 0),
        ({"type": "array", "example": []}, []),
        ({"type": "object", "example": {}}, {}),
        ({"anyOf": [{"type": "string"}, {"type": "null"}], "example": None}, None),
        ({"anyOf": [{"type": "number"}, {"type": "string"}], "example": "100"}, "100"),
    ],
)
def test_fallback_preserves_present_examples_before_synthesis(
    declaration: dict[str, Any], expected: Any
) -> None:
    actual = _fallback_example("option", declaration)
    assert actual == expected
    assert type(actual) is type(expected)


@pytest.mark.parametrize("composition", ["anyOf", "oneOf"])
def test_nullable_fallback_preserves_branch_and_array_item_null_examples(composition: str) -> None:
    item = {composition: [{"type": "integer"}, {"type": "null"}], "example": None}
    assert (
        _fallback_example(
            "option", {composition: [{"type": "integer", "example": None}, {"type": "null"}]}
        )
        is None
    )
    assert _fallback_example(
        "option",
        {composition: [{"type": "array", "items": item}, {"type": "null"}]},
    ) == [None]
    assert _fallback_example(
        "option",
        {
            composition: [
                {"type": "array", "items": {"type": "array", "items": item}},
                {"type": "null"},
            ]
        },
    ) == [[None]]


def test_nested_reference_extraction_preserves_resolved_declared_null() -> None:
    components = {
        "schemas": {
            "NullableValue": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "example": None,
            },
            "Container": {
                "type": "object",
                "properties": {"value": {"$ref": "#/components/schemas/NullableValue"}},
            },
        }
    }
    fields = _extract_fields(
        {"type": "object", "properties": {"nested": {"$ref": "#/components/schemas/Container"}}},
        components=components,
    )
    assert next(field for field in fields if field["name"] == "nested.value")["example"] is None


@pytest.mark.parametrize(
    ("parameter_example", "schema_example", "expected"),
    [
        ({"example": None}, {"example": "SCHEMA"}, None),
        ({}, {"example": None}, None),
        ({"example": False}, {"example": True}, False),
        ({"example": 0}, {"example": 1}, 0),
        ({"example": ""}, {"example": "SCHEMA"}, ""),
        ({"example": []}, {"example": [1]}, []),
    ],
)
def test_request_controls_distinguish_example_presence_and_precedence(
    parameter_example: dict[str, Any], schema_example: dict[str, Any], expected: Any
) -> None:
    primitive = {bool: "boolean", int: "integer", list: "array"}.get(type(expected), "string")
    _, controls = _extract_request_fields(
        {
            "parameters": [
                {
                    "name": "option",
                    "in": "query",
                    **parameter_example,
                    "schema": {"anyOf": [{"type": primitive}, {"type": "null"}], **schema_example},
                }
            ]
        },
        {},
    )
    assert controls[0]["example"] == expected
    assert type(controls[0]["example"]) is type(expected)


def test_absent_examples_still_use_existing_fallbacks() -> None:
    schema = {"anyOf": [{"type": "boolean"}, {"type": "null"}]}
    assert "example" not in schema
    fields = _extract_fields({"type": "object", "properties": {"option": schema}}, components={})
    assert fields[0]["example"] is True
    _, controls = _extract_request_fields(
        {"parameters": [{"name": "option", "in": "query", "schema": schema}]}, {}
    )
    assert controls[0]["example"] is True


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


def _usage_field(**overrides: Any) -> dict[str, Any]:
    return {
        "name": "shared",
        "location": "body",
        "required": True,
        "type": "string",
        "semanticId": "lotus.shared",
        "attributeRef": "#/attributeCatalog/lotus.shared",
        **overrides,
    }


@pytest.mark.parametrize("composition", ["anyOf", "oneOf"])
def test_inventory_publishes_unique_variant_usages_and_preserves_first_metadata(
    monkeypatch: pytest.MonkeyPatch, composition: str
) -> None:
    amount = {
        "anyOf": [{"type": "number"}, {"type": "string"}, {"type": "null"}],
        "example": "100",
    }
    schemas = {
        "First": {
            "type": "object",
            "required": ["shared"],
            "properties": {
                "shared": {"type": "string", "description": "First branch.", "example": "FIRST"},
                "count": {"type": "integer", "example": 0},
                "amount": amount,
            },
        },
        "Second": {
            "type": "object",
            "required": ["shared"],
            "properties": {
                "shared": {"type": "string", "description": "Second branch.", "example": "SECOND"},
                "enabled": {"type": "boolean", "example": False},
                "amount": {**amount, "example": "200"},
            },
        },
        "Optional": {"type": "object", "properties": {"shared": {"type": "string"}}},
    }
    variants = {
        composition: [
            {
                "oneOf": [
                    {"$ref": "#/components/schemas/First"},
                    {"$ref": "#/components/schemas/Second"},
                ]
            },
            {"$ref": "#/components/schemas/First"},
            {"$ref": "#/components/schemas/Optional"},
        ]
    }
    operation = {
        "parameters": [
            {
                "name": "optional_note",
                "in": "query",
                "schema": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "example": None,
            }
        ],
        "requestBody": {"content": {"application/json": {"schema": variants}}},
        "responses": {"200": {"content": {"application/json": {"schema": variants}}}},
    }
    monkeypatch.setattr(
        app,
        "openapi",
        lambda: {
            "components": {"schemas": schemas},
            "paths": {"/first": {"post": operation}, "/second": {"post": operation}},
        },
    )

    inventory = build_inventory()
    body_usages = [
        ("shared", True, "string"),
        ("count", False, "integer"),
        ("amount", False, "object"),
        ("enabled", False, "boolean"),
        ("shared", False, "string"),
    ]
    assert len(inventory["endpoints"]) == 2
    for endpoint in inventory["endpoints"]:
        assert [
            (field["name"], field["required"], field["type"])
            for field in endpoint["response"]["fields"]
        ] == body_usages
        assert [
            (field["name"], field["required"], field["type"])
            for field in endpoint["request"]["fields"]
        ] == [("optional_note", False, "string"), *body_usages]

    attributes = {row["semanticId"]: row for row in inventory["attributeCatalog"]}
    assert attributes["lotus.shared"]["description"] == "First branch."
    assert attributes["lotus.shared"]["example"] == "FIRST"
    assert attributes["lotus.count"]["example"] == 0
    assert attributes["lotus.enabled"]["example"] is False
    assert attributes["lotus.amount"]["example"] == "100"
    assert attributes["lotus.optional_note"]["example"] is None
    assert validate_inventory(inventory) == []


@pytest.mark.parametrize("direction", ["request", "response"])
def test_inventory_validator_rejects_exact_duplicate_endpoint_usages(direction: str) -> None:
    field = _usage_field()
    inventory = {
        "endpoints": [
            {"method": "POST", "path": "/example", direction: {"fields": [field, dict(field)]}}
        ]
    }

    assert validate_inventory(inventory) == [
        f"duplicate endpoint {direction} field usage: POST /example::shared"
    ]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("name", "another"),
        ("location", "query"),
        ("required", False),
        ("type", "integer"),
        ("semanticId", "lotus.another"),
        ("attributeRef", "#/attributeCatalog/lotus.another"),
    ],
)
def test_inventory_validator_accepts_distinct_usage_mappings_and_scopes(
    key: str, value: Any
) -> None:
    fields = [_usage_field(), _usage_field(**{key: value})]
    inventory = {
        "endpoints": [
            {
                "method": method,
                "path": path,
                "request": {"fields": fields},
                "response": {"fields": fields},
            }
            for method, path in [("GET", "/first"), ("POST", "/first"), ("GET", "/second")]
        ]
    }

    assert validate_inventory(inventory) == []


def test_native_inventory_preserves_every_distinct_usage_in_first_occurrence_order() -> None:
    baseline = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "docs/standards/api-vocabulary/lotus-manage-api-vocabulary.v1.json"
        ).read_text(encoding="utf-8")
    )
    inventory = build_inventory()

    assert inventory["attributeCatalog"] == baseline["attributeCatalog"]
    assert inventory["controlsCatalog"] == baseline["controlsCatalog"]
    assert len(inventory["endpoints"]) == len(baseline["endpoints"])
    for actual, previous in zip(inventory["endpoints"], baseline["endpoints"], strict=True):
        assert {
            key: value for key, value in actual.items() if key not in ("request", "response")
        } == {key: value for key, value in previous.items() if key not in ("request", "response")}
        for direction in ("request", "response"):
            expected: list[dict[str, Any]] = []
            for field in previous[direction]["fields"]:
                if field not in expected:
                    expected.append(field)
            assert actual[direction]["fields"] == expected
    assert validate_inventory(inventory) == []
