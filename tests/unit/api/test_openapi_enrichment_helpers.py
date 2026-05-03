from src.api.openapi_enrichment import (
    _example_from_schema,
    _infer_description,
    _infer_example,
    enrich_openapi_schema,
)


def test_openapi_enrichment_infers_domain_examples_and_descriptions() -> None:
    assert _infer_example("portfolioId", {"type": "string"}) == "DEMO_DPM_EUR_001"
    assert _infer_example("targetWeight", {"type": "number"}) == 0.125
    assert _infer_example("lastPrice", {"type": "number"}) == 1.2345
    assert _infer_example("quantity", {"type": "number"}) == 100.0
    assert _infer_example("asOfDate", {"type": "string", "format": "date"}) == "2026-03-02"
    assert _infer_example("runAt", {"type": "string", "format": "date-time"}).endswith("Z")
    assert _infer_example("workflowStatus", {"type": "string"}) == "READY"
    assert _infer_example("customEnum", {"enum": ["A", "B"]}) == "A"
    assert _infer_example("attributes", {"type": "object"}) == {"sample_key": "sample_value"}
    assert _infer_example("otherNumber", {"type": "number"}) == 10.5
    assert _infer_example("currencyCode", {"type": "string"}) == "USD"
    assert _infer_example("runTime", {"type": "string"}) == "2026-03-02T10:30:00Z"
    assert _infer_example("customId", {"type": "string"}) == "CUSTOM_001"
    assert _infer_example("unknown", {}) == "unknown_example"
    assert _infer_description("RunModel", "runAt", {"format": "date-time"}) == (
        "Timestamp for run at."
    )
    assert _infer_description("RunModel", "marketValue", {"type": "number"}) == (
        "Monetary value for market value."
    )
    assert _infer_description("RunModel", "asOfDate", {"format": "date"}) == (
        "Business date for as of date."
    )
    assert _infer_description("RunModel", "baseCurrency", {"type": "string"}) == (
        "ISO currency code for base currency."
    )
    assert _infer_description("RunModel", "quantity", {"type": "number"}) == (
        "Quantity value for quantity."
    )
    assert _infer_description("RunModel", "marketPrice", {"type": "number"}) == (
        "Rate/price value for market price."
    )


def test_openapi_enrichment_builds_examples_from_refs_composites_and_maps() -> None:
    schemas = {
        "Recursive": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "child": {"$ref": "#/components/schemas/Recursive"},
            },
        },
        "Leaf": {
            "type": "object",
            "properties": {"currency": {"type": "string"}, "amount": {"type": "number"}},
        },
    }

    assert _example_from_schema(
        "recursive",
        {"$ref": "#/components/schemas/Recursive"},
        schemas,
    ) == {"name": "sample_name", "child": {"sample_key": "sample_value"}}
    assert _example_from_schema(
        "choice",
        {"oneOf": [{"type": "null"}, {"$ref": "#/components/schemas/Leaf"}]},
        schemas,
    ) == {"currency": "USD", "amount": 10.5}
    assert _example_from_schema(
        "attributes",
        {"type": "object", "additionalProperties": {"type": "boolean"}},
        schemas,
    ) == {"sample_key": True}
    assert _example_from_schema("array", {"type": "array", "items": "bad"}, schemas) == []
    assert _example_from_schema(
        "all_of",
        {"allOf": [{"$ref": "#/components/schemas/Leaf"}]},
        schemas,
    ) == {"currency": "USD", "amount": 10.5}
    assert _example_from_schema(
        "any_of",
        {"anyOf": [{"type": "null"}, {"type": "array", "items": {"type": "string"}}]},
        schemas,
    ) == ["sample_any_of_item"]
    assert _example_from_schema("explicit_examples", {"examples": ["from-list"]}, schemas) == (
        "from-list"
    )


def test_openapi_enrichment_adds_operation_docs_errors_and_prometheus_examples() -> None:
    schema = {
        "components": {
            "schemas": {
                "Payload": {
                    "type": "object",
                    "properties": {
                        "customId": {"type": "string"},
                        "status": {"enum": ["READY", "BLOCKED"]},
                        "items": {"type": "array", "items": {"type": "integer"}},
                    },
                }
            }
        },
        "paths": {
            "/health/live": {"get": {"responses": {"200": {"description": "ok"}}}},
            "/metrics": {"get": {"responses": {"200": {"description": "metrics"}}}},
            "/api/v1/custom": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/Payload"}}
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Payload"}
                                }
                            },
                        }
                    },
                },
                "trace": {"responses": {}},
                "parameters": [],
            },
            "/non-dict": [],
        },
    }

    enriched = enrich_openapi_schema(schema, service_name="lotus-manage")

    operation = enriched["paths"]["/api/v1/custom"]["post"]
    assert operation["summary"] == "POST /api/v1/custom"
    assert operation["tags"] == ["Api"]
    assert "default" in operation["responses"]
    assert "examples" in operation["requestBody"]["content"]["application/json"]
    assert "examples" in operation["responses"]["200"]["content"]["application/json"]
    assert enriched["paths"]["/health/live"]["get"]["tags"] == ["Health"]
    metrics_content = enriched["paths"]["/metrics"]["get"]["responses"]["200"]["content"]
    assert "text/plain; version=0.0.4" in metrics_content
    assert (
        enriched["components"]["schemas"]["Payload"]["properties"]["customId"]["description"]
        == "Unique custom identifier."
    )


def test_openapi_enrichment_tolerates_non_standard_schema_fragments() -> None:
    schema = {
        "components": {
            "schemas": {
                "Broken": [],
                "NoProperties": {"properties": []},
                "MixedProperties": {"properties": {"ok": {"type": "string"}, "bad": []}},
            }
        },
        "paths": {
            "/metrics": {"get": {"responses": {"200": {"description": "ok"}, "default": []}}},
            "/api/v1/mixed": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"},
                                "examples": {"kept": {"value": {}}},
                            }
                        }
                    },
                    "responses": {"200": [], "default": {"description": "error"}},
                },
                "get": [],
            },
            "/not-dict": [],
        },
    }

    enriched = enrich_openapi_schema(schema, service_name="lotus-manage")

    assert (
        enriched["components"]["schemas"]["MixedProperties"]["properties"]["ok"]["description"]
        == "mixed properties field: ok."
    )
    assert (
        enriched["paths"]["/api/v1/mixed"]["post"]["responses"]["default"]["content"][
            "application/json"
        ]["examples"]["default"]["value"]["title"]
        == "Unexpected Error"
    )


def test_openapi_enrichment_handles_missing_schema_components() -> None:
    schema = {
        "components": {"schemas": []},
        "paths": {
            "/api/v1/basic": {
                "post": {
                    "requestBody": {
                        "content": {"application/json": {"schema": {"type": "object"}}}
                    },
                    "responses": {"200": {"content": {"application/json": {"schema": []}}}},
                }
            }
        },
    }

    enriched = enrich_openapi_schema(schema, service_name="lotus-manage")

    assert enriched["paths"]["/api/v1/basic"]["post"]["requestBody"]["content"]["application/json"][
        "examples"
    ]["default"]["value"] == {"sample_key": "sample_value"}
