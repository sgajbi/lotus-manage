from src.api.openapi_enrichment import (
    _composite_example_from_schema,
    _collection_example_from_schema,
    _description_context,
    _enum_example,
    _example_from_schema,
    _ensure_metrics_path_examples,
    _ensure_operation_default_docs,
    _ensure_operation_default_error_response,
    _ensure_operation_examples,
    _infer_description,
    _infer_example,
    _is_error_status_code,
    _is_http_operation_method,
    _number_example_for_key,
    _operation_has_error_response,
    _operation_tag_for_path,
    _ref_example_from_schema,
    _schema_declared_example,
    _schema_format_example,
    _schema_http_operations,
    _schema_type_example,
    _SEMANTIC_DESCRIPTION_RULES,
    _semantic_description_for_context,
    _semantic_string_example_for_key,
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


def test_openapi_enrichment_number_examples_follow_domain_semantics() -> None:
    assert _number_example_for_key("target_weight") == 0.125
    assert _number_example_for_key("last_price") == 1.2345
    assert _number_example_for_key("fx_rate") == 1.2345
    assert _number_example_for_key("quantity") == 100.0
    assert _number_example_for_key("other_number") == 10.5


def test_openapi_enrichment_description_helpers_follow_domain_semantics() -> None:
    context = _description_context("portfolioId", {"format": "uuid"})

    assert context.key == "portfolio_id"
    assert context.text == "portfolio id"
    assert context.schema_format == "uuid"
    assert _semantic_description_for_context(context) == "Unique portfolio identifier."
    assert (
        _semantic_description_for_context(
            _description_context("workflowStatus", {"type": "string"})
        )
        == "Current status for workflow status."
    )
    assert (
        _semantic_description_for_context(_description_context("displayName", {"type": "string"}))
        is None
    )


def test_openapi_enrichment_description_rules_match_and_render_schema_context() -> None:
    rule_by_template = {rule.template: rule for rule in _SEMANTIC_DESCRIPTION_RULES}

    date_rule = rule_by_template["Business date for {text}."]
    timestamp_rule = rule_by_template["Timestamp for {text}."]

    assert date_rule.matches(_description_context("asOfDate", {"format": "date"}))
    assert date_rule.render(_description_context("asOfDate", {"format": "date"})) == (
        "Business date for as of date."
    )
    assert not date_rule.matches(_description_context("effectivePeriod", {"format": "date"}))
    assert timestamp_rule.matches(_description_context("generatedAt", {"format": "date-time"}))
    assert timestamp_rule.render(_description_context("generatedAt", {"format": "date-time"})) == (
        "Timestamp for generated at."
    )


def test_openapi_enrichment_semantic_string_examples_follow_domain_semantics() -> None:
    assert _semantic_string_example_for_key("custom_id", "string") == "CUSTOM_001"
    assert _semantic_string_example_for_key("base_currency", "string") == "USD"
    assert _semantic_string_example_for_key("as_of_date", "string") == "2026-03-02"
    assert _semantic_string_example_for_key("run_time", "string") == "2026-03-02T10:30:00Z"
    assert _semantic_string_example_for_key("updated_timestamp", "string") == (
        "2026-03-02T10:30:00Z"
    )
    assert _semantic_string_example_for_key("workflow_status", "string") == "READY"
    assert _semantic_string_example_for_key("display_name", "string") == "sample_display_name"
    assert _semantic_string_example_for_key("unknown", None) is None


def test_openapi_enrichment_infer_example_helpers_separate_schema_concerns() -> None:
    assert _enum_example({"enum": ["READY", "BLOCKED"]}) == (True, "READY")
    assert _enum_example({"enum": []}) == (False, None)
    assert _schema_type_example(
        "allocations",
        key="allocations",
        prop_schema={"type": "array", "items": {"type": "integer"}},
    ) == (True, [10])
    assert _schema_type_example(
        "metadata",
        key="metadata",
        prop_schema={"type": "object"},
    ) == (True, {"sample_key": "sample_value"})
    assert _schema_type_example(
        "targetWeight",
        key="target_weight",
        prop_schema={"type": "number"},
    ) == (True, 0.125)
    assert _schema_type_example(
        "displayName",
        key="display_name",
        prop_schema={"type": "string"},
    ) == (False, None)
    assert _schema_format_example({"format": "date"}) == (True, "2026-03-02")
    assert _schema_format_example({"format": "date-time"}) == (
        True,
        "2026-03-02T10:30:00Z",
    )
    assert _schema_format_example({"format": "uuid"}) == (False, None)


def test_openapi_enrichment_prefers_declared_schema_examples() -> None:
    assert _schema_declared_example({"example": {"status": "READY"}}) == (
        True,
        {"status": "READY"},
    )
    assert _schema_declared_example({"examples": ["first", "second"]}) == (True, "first")
    assert _schema_declared_example({"examples": []}) == (False, None)
    assert _schema_declared_example({"type": "string"}) == (False, None)


def test_openapi_enrichment_collects_object_array_and_map_examples() -> None:
    schemas = {
        "Leaf": {
            "type": "object",
            "properties": {"currency": {"type": "string"}, "amount": {"type": "number"}},
        }
    }

    assert _collection_example_from_schema(
        prop_name="position",
        prop_schema={
            "properties": {"id": {"type": "string"}, "leaf": {"$ref": "#/components/schemas/Leaf"}}
        },
        schemas=schemas,
        seen_refs=set(),
    ) == (True, {"id": "sample_id", "leaf": {"currency": "USD", "amount": 10.5}})
    assert _collection_example_from_schema(
        prop_name="items",
        prop_schema={"type": "array", "items": {"type": "string"}},
        schemas=schemas,
        seen_refs=set(),
    ) == (True, ["sample_items_item"])
    assert _collection_example_from_schema(
        prop_name="props",
        prop_schema={"type": "array", "items": "bad"},
        schemas=schemas,
        seen_refs=set(),
    ) == (True, [])
    assert _collection_example_from_schema(
        prop_name="tags",
        prop_schema={
            "type": "object",
            "additionalProperties": {"type": "boolean"},
        },
        schemas=schemas,
        seen_refs=set(),
    ) == (True, {"sample_key": True})
    assert _collection_example_from_schema(
        prop_name="meta",
        prop_schema={"type": "object"},
        schemas=schemas,
        seen_refs=set(),
    ) == (True, {"sample_key": "sample_value"})
    assert _collection_example_from_schema(
        prop_name="value",
        prop_schema={"type": "string"},
        schemas=schemas,
        seen_refs=set(),
    ) == (False, None)


def test_openapi_enrichment_ref_example_helper_resolves_and_guards_recursion() -> None:
    schemas = {
        "Recursive": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "child": {"$ref": "#/components/schemas/Recursive"},
            },
        }
    }

    assert _ref_example_from_schema(
        {"$ref": "#/components/schemas/Recursive"},
        schemas,
        set(),
    ) == (
        True,
        {"name": "sample_name", "child": {"sample_key": "sample_value"}},
    )
    assert _ref_example_from_schema(
        {"$ref": "#/components/schemas/Recursive"},
        schemas,
        {"Recursive"},
    ) == (True, {"sample_key": "sample_value"})
    assert _ref_example_from_schema({"type": "string"}, schemas, set()) == (False, None)


def test_openapi_enrichment_composite_example_helper_uses_first_non_null_option() -> None:
    schemas = {
        "Leaf": {
            "type": "object",
            "properties": {"currency": {"type": "string"}, "amount": {"type": "number"}},
        }
    }

    assert _composite_example_from_schema(
        "choice",
        {"oneOf": [{"type": "null"}, {"$ref": "#/components/schemas/Leaf"}]},
        schemas,
        set(),
    ) == (True, {"currency": "USD", "amount": 10.5})
    assert _composite_example_from_schema(
        "plain",
        {"type": "string"},
        schemas,
        set(),
    ) == (False, None)


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


def test_openapi_enrichment_adds_operation_level_examples_and_errors() -> None:
    operation = {
        "requestBody": {
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Payload"}}}
        },
        "responses": {
            "200": {"content": {"application/json": {"schema": {"type": "string"}}}},
            "409": {"description": "Conflict detected."},
        },
    }

    _ensure_operation_examples(
        method="post",
        path="/api/v1/example",
        operation=operation,
        schemas={
            "Payload": {
                "type": "object",
                "properties": {"portfolio_id": {"type": "string"}},
            }
        },
    )

    assert operation["requestBody"]["content"]["application/json"]["examples"]["default"][
        "value"
    ] == {"portfolio_id": "DEMO_DPM_EUR_001"}
    assert (
        operation["responses"]["200"]["content"]["application/json"]["examples"]["default"]["value"]
        == "sample_post_/api/v1/example_200_response"
    )
    assert (
        operation["responses"]["409"]["content"]["application/json"]["examples"]["default"][
            "value"
        ]["status"]
        == 409
    )


def test_openapi_enrichment_operation_tag_for_path_uses_governed_fallbacks() -> None:
    assert _operation_tag_for_path("/health/live") == "Health"
    assert _operation_tag_for_path("/metrics") == "Monitoring"
    assert _operation_tag_for_path("/api/v1/rebalance") == "Api"
    assert _operation_tag_for_path("/") == "Default"


def test_openapi_enrichment_operation_error_response_detection() -> None:
    assert _operation_has_error_response({"200": {}, "409": {}}) is True
    assert _operation_has_error_response({"200": {}, "default": {}}) is True
    assert _operation_has_error_response({"200": {}, "302": {}}) is False


def test_openapi_enrichment_operation_method_and_error_status_helpers() -> None:
    assert _is_http_operation_method("GET")
    assert _is_http_operation_method("patch")
    assert not _is_http_operation_method("trace")
    assert _is_error_status_code("404")
    assert _is_error_status_code("default")
    assert not _is_error_status_code("302")


def test_openapi_enrichment_operation_documentation_helpers_handle_defaults() -> None:
    operation = {"responses": {"200": {"description": "ok"}}}

    _ensure_operation_default_docs(
        operation=operation,
        method="post",
        path="/api/v1/custom-items",
        service_name="lotus-manage",
    )
    _ensure_operation_default_error_response(operation)

    assert operation["summary"] == "POST /api/v1/custom-items"
    assert operation["description"] == ("POST operation for /api/v1/custom-items in lotus-manage.")
    assert operation["tags"] == ["Api"]
    assert operation["responses"]["default"] == {"description": "Unexpected error response."}

    existing = {
        "summary": "Existing summary",
        "description": "Existing description",
        "tags": ["Existing"],
        "responses": {"200": {}, "409": {"description": "Conflict."}},
    }

    _ensure_operation_default_docs(
        operation=existing,
        method="get",
        path="/health/live",
        service_name="lotus-manage",
    )
    _ensure_operation_default_error_response(existing)

    assert existing["summary"] == "Existing summary"
    assert existing["description"] == "Existing description"
    assert existing["tags"] == ["Existing"]
    assert "default" not in existing["responses"]


def test_openapi_enrichment_schema_http_operations_filters_schema_fragments() -> None:
    operation = {"responses": {"200": {"description": "ok"}}}

    schema = {
        "paths": {
            "/api/v1/custom": {"get": operation, "trace": {"responses": {}}},
            "/non-dict": [],
            42: {"get": {"responses": {}}},
            "/bad-operation": {"post": []},
        }
    }

    assert list(_schema_http_operations(schema)) == [("/api/v1/custom", "get", operation)]
    assert list(_schema_http_operations({"paths": []})) == []


def test_openapi_enrichment_metrics_helper_adds_prometheus_and_error_examples() -> None:
    methods = {"get": {"responses": {"200": {"description": "metrics"}, "503": {}}}}

    _ensure_metrics_path_examples(methods)

    responses = methods["get"]["responses"]
    metrics_content = responses["200"]["content"]
    assert "text/plain; version=0.0.4" in metrics_content
    assert (
        "http_requests_total"
        in metrics_content["text/plain; version=0.0.4"]["examples"]["prometheus"]["value"]
    )
    assert (
        responses["503"]["content"]["application/json"]["examples"]["default"]["value"]["status"]
        == 503
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
